"""
Unit tests for analyzer.tls (the pure logic — no real sockets).

We test cert-expiry parsing, outdated-version detection, and the
days-until-expiry math. The socket-opening inspect_tls() is exercised only
for its never-raises contract against an unresolvable host.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from analyzer.tls import (
    FAILURE_EXPIRED,
    FAILURE_HOSTNAME,
    FAILURE_SELF_SIGNED,
    FAILURE_UNTRUSTED,
    TlsInfo,
    _classify_verification_error,
    _parse_cert_expiry,
    inspect_tls,
)


# --- Cert expiry parsing --------------------------------------------------

class TestParseCertExpiry:
    def test_parses_standard_format(self):
        dt = _parse_cert_expiry("Jun  1 12:00:00 2027 GMT")
        assert dt is not None
        assert dt.year == 2027 and dt.month == 6 and dt.day == 1
        assert dt.tzinfo is not None  # tz-aware (UTC)

    def test_empty_returns_none(self):
        assert _parse_cert_expiry("") is None

    def test_garbage_returns_none(self):
        assert _parse_cert_expiry("not a date") is None


# --- Outdated version detection -------------------------------------------

class TestOutdatedVersion:
    def test_tls10_is_outdated(self):
        assert TlsInfo("h", True, protocol_version="TLSv1").is_outdated_version

    def test_tls11_is_outdated(self):
        assert TlsInfo("h", True, protocol_version="TLSv1.1").is_outdated_version

    def test_tls12_is_current(self):
        assert not TlsInfo("h", True, protocol_version="TLSv1.2").is_outdated_version

    def test_tls13_is_current(self):
        assert not TlsInfo("h", True, protocol_version="TLSv1.3").is_outdated_version

    def test_none_is_not_outdated(self):
        assert not TlsInfo("h", False, protocol_version=None).is_outdated_version


# --- Days until expiry ----------------------------------------------------

class TestDaysUntilExpiry:
    def test_future_cert_positive(self):
        now = datetime.now(timezone.utc)
        info = TlsInfo("h", True, cert_not_after=now + timedelta(days=45))
        assert info.days_until_expiry(now) == 45

    def test_expired_cert_negative(self):
        now = datetime.now(timezone.utc)
        info = TlsInfo("h", True, cert_not_after=now - timedelta(days=3))
        assert info.days_until_expiry(now) == -3

    def test_no_cert_returns_none(self):
        assert TlsInfo("h", False, cert_not_after=None).days_until_expiry() is None


# --- Verification-error classification ------------------------------------

class _FakeVerifyError(Exception):
    """Stand-in for ssl.SSLCertVerificationError with verify_code/message."""
    def __init__(self, code=None, message=""):
        super().__init__(message)
        self.verify_code = code
        self.verify_message = message


class TestClassifyVerificationError:
    def test_expired_by_code(self):
        assert _classify_verification_error(_FakeVerifyError(code=10)) == FAILURE_EXPIRED

    def test_self_signed_by_code(self):
        assert _classify_verification_error(_FakeVerifyError(code=18)) == FAILURE_SELF_SIGNED
        assert _classify_verification_error(_FakeVerifyError(code=19)) == FAILURE_SELF_SIGNED

    def test_hostname_by_code(self):
        assert _classify_verification_error(_FakeVerifyError(code=62)) == FAILURE_HOSTNAME

    def test_expired_by_message_fallback(self):
        e = _FakeVerifyError(code=None, message="certificate has expired")
        assert _classify_verification_error(e) == FAILURE_EXPIRED

    def test_self_signed_by_message_fallback(self):
        e = _FakeVerifyError(code=None, message="self-signed certificate")
        assert _classify_verification_error(e) == FAILURE_SELF_SIGNED

    def test_unknown_is_untrusted(self):
        assert _classify_verification_error(_FakeVerifyError(code=999, message="weird")) == FAILURE_UNTRUSTED


class TestCertIsExpired:
    def test_true_when_failure_kind_expired(self):
        assert TlsInfo("h", False, failure_kind=FAILURE_EXPIRED).cert_is_expired

    def test_false_otherwise(self):
        assert not TlsInfo("h", False, failure_kind=FAILURE_SELF_SIGNED).cert_is_expired
        assert not TlsInfo("h", True).cert_is_expired


# --- inspect_tls never raises ---------------------------------------------

class TestInspectTlsContract:
    def test_unresolvable_host_returns_failed_info(self):
        # Must not raise; returns handshake_ok=False with an error.
        info = inspect_tls("nonexistent.invalid.example.test", timeout=3)
        assert info.handshake_ok is False
        assert info.error
