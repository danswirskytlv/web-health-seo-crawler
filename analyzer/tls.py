"""
tls.py
======

Live TLS / certificate inspection (completes Stage 11 — Security).

Unlike every other check in this project, TLS facts are NOT in the HTTP
response the crawler already captured. The protocol version that was
negotiated and the certificate's expiry date are properties of the TLS
handshake itself, which `requests` does not expose. So this module opens a
dedicated SSL socket to the host and reads them directly.

Two design points that match the rest of the project:

- TLS is a property of the HOST, not the page. Every page on
  https://example.com shares the same certificate and protocol support, so
  the security analyzer calls this ONCE per unique host, not per page.

- It must never raise. A DNS failure, timeout, or refused connection becomes
  a TlsInfo with handshake_ok=False and an error string, so a single bad host
  can never break a scan.

This is intentionally a thin inspector: it reports what it sees (version,
expiry, whether the handshake worked). The security analyzer turns those
facts into graded Issues.
"""

from __future__ import annotations

import logging
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_TLS_PORT = 443
DEFAULT_TLS_TIMEOUT = 8.0

# Certificate `notAfter` looks like: "Jun  1 12:00:00 2027 GMT".
_CERT_TIME_FORMAT = "%b %d %H:%M:%S %Y %Z"

# Protocol versions older than this are considered insecure/deprecated.
# ssock.version() returns strings like "TLSv1", "TLSv1.1", "TLSv1.2", "TLSv1.3".
_OUTDATED_VERSIONS = {"SSLv2", "SSLv3", "TLSv1", "TLSv1.1"}


# Classification of why a handshake failed, so the analyzer can give a
# specific, actionable message instead of one generic "handshake failed".
FAILURE_EXPIRED = "expired"              # certificate is past its notAfter date
FAILURE_SELF_SIGNED = "self_signed"      # self-signed / untrusted-root chain
FAILURE_HOSTNAME = "hostname_mismatch"   # cert doesn't cover this hostname
FAILURE_UNTRUSTED = "untrusted"          # other verification failure
FAILURE_PROTOCOL = "protocol"            # SSL/TLS-level error (e.g. no shared protocol)
FAILURE_NETWORK = "network"              # DNS / timeout / refused — not a cert problem

# OpenSSL X509 verification error codes we care about.
# (See `openssl errstr` / X509_V_ERR_* constants.)
_VERIFY_CODE_EXPIRED = 10        # X509_V_ERR_CERT_HAS_EXPIRED
_VERIFY_CODE_SELF_SIGNED = {18, 19}  # self-signed cert / self-signed in chain
_VERIFY_CODE_HOSTNAME = 62      # X509_V_ERR_HOSTNAME_MISMATCH


@dataclass
class TlsInfo:
    """What we learned from one TLS handshake with a host."""
    host: str
    handshake_ok: bool
    protocol_version: Optional[str] = None     # e.g. "TLSv1.3"
    cert_not_after: Optional[datetime] = None  # tz-aware UTC, when the cert expires
    error: Optional[str] = None                # set when handshake_ok is False
    failure_kind: Optional[str] = None         # one of the FAILURE_* constants

    @property
    def is_outdated_version(self) -> bool:
        """True if the negotiated protocol is a deprecated/insecure version."""
        return self.protocol_version in _OUTDATED_VERSIONS

    @property
    def cert_is_expired(self) -> bool:
        """True if the handshake failed specifically because the cert expired."""
        return self.failure_kind == FAILURE_EXPIRED

    def days_until_expiry(self, now: Optional[datetime] = None) -> Optional[int]:
        """
        Days until the certificate expires (negative if already expired).

        Rounds to the nearest whole day rather than truncating, so a cert
        almost exactly N days out reads as N, not N-1 (which made boundary
        comparisons against the warning window flaky).
        """
        if self.cert_not_after is None:
            return None
        now = now or datetime.now(timezone.utc)
        return round((self.cert_not_after - now).total_seconds() / 86400)


def _parse_cert_expiry(not_after: str) -> Optional[datetime]:
    """Parse a certificate notAfter string into a tz-aware UTC datetime."""
    if not not_after:
        return None
    try:
        dt = datetime.strptime(not_after, _CERT_TIME_FORMAT)
        # The "GMT" suffix means UTC; attach the timezone explicitly.
        return dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError) as exc:
        logger.info("Could not parse cert expiry %r: %s", not_after, exc)
        return None


def _build_context() -> ssl.SSLContext:
    """
    Build a verifying SSL context with a reliable CA trust store.

    Python (especially the python.org build on macOS) does not always have
    access to the OS certificate store, which makes it reject even valid
    certificates with "unable to get local issuer certificate". We load
    certifi's Mozilla CA bundle — the same bundle `requests` uses — so
    verification matches what a real browser does.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001 — fall back to the system default
        return ssl.create_default_context()


def _classify_verification_error(exc: ssl.SSLCertVerificationError) -> str:
    """Map an SSL verification error to one of the FAILURE_* reason codes."""
    code = getattr(exc, "verify_code", None)
    if code == _VERIFY_CODE_EXPIRED:
        return FAILURE_EXPIRED
    if code in _VERIFY_CODE_SELF_SIGNED:
        return FAILURE_SELF_SIGNED
    if code == _VERIFY_CODE_HOSTNAME:
        return FAILURE_HOSTNAME
    # Some hostname mismatches arrive without a verify_code; sniff the message.
    msg = (getattr(exc, "verify_message", "") or str(exc)).lower()
    if "hostname mismatch" in msg or "doesn't match" in msg:
        return FAILURE_HOSTNAME
    if "expired" in msg:
        return FAILURE_EXPIRED
    if "self-signed" in msg or "self signed" in msg:
        return FAILURE_SELF_SIGNED
    return FAILURE_UNTRUSTED


def inspect_tls(
    host: str,
    port: int = DEFAULT_TLS_PORT,
    timeout: float = DEFAULT_TLS_TIMEOUT,
) -> TlsInfo:
    """
    Open one TLS connection to `host:port` and report what we find.

    Never raises. On any failure returns TlsInfo(handshake_ok=False, ...),
    with `failure_kind` classifying the cause (expired cert, self-signed,
    hostname mismatch, other untrusted cert, protocol error, or network).
    Verification uses certifi's CA bundle, so a valid certificate verifies
    and only genuinely-broken ones fail — exactly like a real browser.
    """
    context = _build_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                version = ssock.version()
                cert = ssock.getpeercert()
                not_after = _parse_cert_expiry(cert.get("notAfter", "") if cert else "")
                return TlsInfo(
                    host=host,
                    handshake_ok=True,
                    protocol_version=version,
                    cert_not_after=not_after,
                )
    except ssl.SSLCertVerificationError as exc:
        kind = _classify_verification_error(exc)
        logger.info("TLS cert verification failed for %s (%s): %s", host, kind, exc)
        return TlsInfo(
            host=host,
            handshake_ok=False,
            error=f"certificate error: {exc.verify_message or exc}",
            failure_kind=kind,
        )
    except (socket.timeout, TimeoutError):
        return TlsInfo(host=host, handshake_ok=False,
                       error="connection timed out", failure_kind=FAILURE_NETWORK)
    except ssl.SSLError as exc:
        # A non-verification SSL error: e.g. no shared protocol version.
        logger.info("TLS protocol error for %s: %s", host, exc)
        return TlsInfo(host=host, handshake_ok=False,
                       error=str(exc), failure_kind=FAILURE_PROTOCOL)
    except OSError as exc:
        # DNS failure, connection refused, etc. — a network problem, not a cert one.
        logger.info("TLS connection failed for %s: %s", host, exc)
        return TlsInfo(host=host, handshake_ok=False,
                       error=str(exc), failure_kind=FAILURE_NETWORK)
    except Exception as exc:  # noqa: BLE001 — TLS inspection must never break a scan
        logger.info("Unexpected TLS error for %s: %s", host, exc)
        return TlsInfo(host=host, handshake_ok=False,
                       error=str(exc), failure_kind=FAILURE_UNTRUSTED)
