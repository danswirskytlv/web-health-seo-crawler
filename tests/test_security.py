"""
Unit tests for analyzer.security (Stage 11).

Mirrors the structure of test_accessibility.py / test_performance.py: small
in-memory PageResults, fast, no network. A page is given a URL (to control the
http/https scheme), an optional headers dict, and optional HTML.
"""

from __future__ import annotations

import functools

from analyzer.security import (
    SEC_BLANK_WITHOUT_NOOPENER,
    SEC_CERT_EXPIRED,
    SEC_CERT_EXPIRING,
    SEC_COOKIE_NO_HTTPONLY,
    SEC_COOKIE_NO_SAMESITE,
    SEC_COOKIE_NO_SECURE,
    SEC_MISSING_CSP,
    SEC_MISSING_HSTS,
    SEC_MISSING_PERMISSIONS_POLICY,
    SEC_MISSING_REFERRER_POLICY,
    SEC_MISSING_X_CONTENT_TYPE,
    SEC_MISSING_X_FRAME,
    SEC_MIXED_CONTENT,
    SEC_NO_HTTPS,
    SEC_SERVER_HEADER_DISCLOSURE,
    SEC_CERT_HOSTNAME,
    SEC_CERT_UNTRUSTED,
    SEC_TLS_HANDSHAKE_FAILED,
    SEC_TLS_OUTDATED,
    SEC_X_POWERED_BY,
    analyze_pages_security as _real_analyze_pages_security,
)
from analyzer.tls import (
    FAILURE_EXPIRED,
    FAILURE_HOSTNAME,
    FAILURE_NETWORK,
    FAILURE_SELF_SIGNED,
    TlsInfo,
)
from models.result_models import (
    CATEGORY_COOKIES,
    CATEGORY_INFO_DISCLOSURE,
    CATEGORY_SECURITY_HEADERS,
    CATEGORY_TRANSPORT_SECURITY,
    PageResult,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)

# All the non-TLS tests below call analyze_pages_security() on synthetic hosts.
# Default check_tls to False for them so they never open a real socket; the
# dedicated TestTls class calls the real function with a mocked inspector.
analyze_pages_security = functools.partial(_real_analyze_pages_security, check_tls=False)


# A full set of security headers, so tests that aren't about a specific
# missing header don't trip every other "missing header" check.
_ALL_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=()",
}


def _page(
    *,
    url: str = "https://example.com/",
    status: int = 200,
    html: str | None = None,
    headers: dict | None = None,
    set_cookie: list[str] | None = None,
    final_url: str | None = None,
    was_redirected: bool = False,
) -> PageResult:
    return PageResult(
        url=url,
        status_code=status,
        response_time=0.1,
        html=html,
        headers=dict(headers) if headers else {},
        set_cookie_headers=list(set_cookie) if set_cookie else [],
        final_url=final_url,
        was_redirected=was_redirected,
    )


def _secure_page(
    *,
    html: str | None = None,
    extra_headers: dict | None = None,
    set_cookie: list[str] | None = None,
) -> PageResult:
    """An https page that already has all recommended security headers."""
    headers = dict(_ALL_SECURITY_HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    return _page(url="https://example.com/", html=html, headers=headers,
                 set_cookie=set_cookie)


def _types(issues) -> set[str]:
    return {i.issue_type for i in issues}


def _of_type(issues, t):
    return [i for i in issues if i.issue_type == t]


# --- HTTPS ----------------------------------------------------------------

class TestHttps:
    def test_http_page_flagged(self):
        issues = analyze_pages_security([_page(url="http://example.com/")])
        assert SEC_NO_HTTPS in _types(issues)

    def test_https_page_not_flagged(self):
        issues = analyze_pages_security([_secure_page()])
        assert SEC_NO_HTTPS not in _types(issues)

    def test_http_redirected_to_https_not_flagged(self):
        # Requested http, but the server upgraded us to https — correct, no flag.
        page = _page(
            url="http://example.com/",
            final_url="https://example.com/",
            was_redirected=True,
            headers=_ALL_SECURITY_HEADERS,
        )
        assert SEC_NO_HTTPS not in _types(analyze_pages_security([page]))

    def test_severity_is_high(self):
        issues = _of_type(analyze_pages_security([_page(url="http://x/")]), SEC_NO_HTTPS)
        assert issues and issues[0].severity == SEVERITY_HIGH
        assert issues[0].category == CATEGORY_TRANSPORT_SECURITY


# --- HSTS -----------------------------------------------------------------

class TestHsts:
    def test_missing_on_https_flagged(self):
        headers = {k: v for k, v in _ALL_SECURITY_HEADERS.items()
                   if k != "Strict-Transport-Security"}
        page = _page(url="https://example.com/", headers=headers)
        assert SEC_MISSING_HSTS in _types(analyze_pages_security([page]))

    def test_present_not_flagged(self):
        assert SEC_MISSING_HSTS not in _types(analyze_pages_security([_secure_page()]))

    def test_not_flagged_on_http_page(self):
        # An http page's real problem is the missing HTTPS, not HSTS.
        page = _page(url="http://example.com/")
        assert SEC_MISSING_HSTS not in _types(analyze_pages_security([page]))

    def test_case_insensitive_header_lookup(self):
        headers = dict(_ALL_SECURITY_HEADERS)
        del headers["Strict-Transport-Security"]
        headers["strict-transport-security"] = "max-age=600"
        page = _page(url="https://example.com/", headers=headers)
        assert SEC_MISSING_HSTS not in _types(analyze_pages_security([page]))


# --- Mixed content --------------------------------------------------------

class TestMixedContent:
    def test_http_resource_on_https_page_flagged(self):
        html = '<html><body><img src="http://cdn.example.com/a.png"></body></html>'
        page = _secure_page(html=html)
        assert SEC_MIXED_CONTENT in _types(analyze_pages_security([page]))

    def test_all_https_resources_not_flagged(self):
        html = '<html><body><img src="https://cdn.example.com/a.png"></body></html>'
        page = _secure_page(html=html)
        assert SEC_MIXED_CONTENT not in _types(analyze_pages_security([page]))

    def test_not_checked_on_http_page(self):
        # http page is already flagged for no-HTTPS; mixed content is moot.
        html = '<html><body><img src="http://cdn/a.png"></body></html>'
        page = _page(url="http://example.com/", html=html)
        assert SEC_MIXED_CONTENT not in _types(analyze_pages_security([page]))

    def test_severity_is_high(self):
        html = '<html><body><script src="http://evil/x.js"></script></body></html>'
        issues = _of_type(analyze_pages_security([_secure_page(html=html)]), SEC_MIXED_CONTENT)
        assert issues and issues[0].severity == SEVERITY_HIGH


# --- Security headers -----------------------------------------------------

class TestSecurityHeaders:
    def test_all_present_no_issues(self):
        types = _types(analyze_pages_security([_secure_page()]))
        for t in (SEC_MISSING_CSP, SEC_MISSING_X_FRAME, SEC_MISSING_X_CONTENT_TYPE,
                  SEC_MISSING_REFERRER_POLICY, SEC_MISSING_PERMISSIONS_POLICY):
            assert t not in types

    def test_missing_csp_flagged(self):
        headers = {k: v for k, v in _ALL_SECURITY_HEADERS.items()
                   if k != "Content-Security-Policy"}
        page = _page(url="https://example.com/", headers=headers)
        assert SEC_MISSING_CSP in _types(analyze_pages_security([page]))

    def test_missing_all_headers_flags_all(self):
        page = _page(url="https://example.com/", headers={})
        types = _types(analyze_pages_security([page]))
        assert {SEC_MISSING_CSP, SEC_MISSING_X_FRAME, SEC_MISSING_X_CONTENT_TYPE,
                SEC_MISSING_REFERRER_POLICY, SEC_MISSING_PERMISSIONS_POLICY,
                SEC_MISSING_HSTS}.issubset(types)

    def test_empty_header_value_treated_as_missing(self):
        headers = dict(_ALL_SECURITY_HEADERS)
        headers["Content-Security-Policy"] = "   "
        page = _page(url="https://example.com/", headers=headers)
        assert SEC_MISSING_CSP in _types(analyze_pages_security([page]))

    def test_not_checked_on_http_page(self):
        page = _page(url="http://example.com/", headers={})
        types = _types(analyze_pages_security([page]))
        assert SEC_MISSING_CSP not in types  # only no-HTTPS should fire
        assert SEC_NO_HTTPS in types

    def test_category_is_security_headers(self):
        page = _page(url="https://example.com/", headers={})
        issues = _of_type(analyze_pages_security([page]), SEC_MISSING_CSP)
        assert issues and issues[0].category == CATEGORY_SECURITY_HEADERS


# --- target=_blank without noopener ---------------------------------------

class TestBlankWithoutNoopener:
    def test_blank_without_rel_flagged(self):
        html = '<html><body><a href="/x" target="_blank">x</a></body></html>'
        page = _secure_page(html=html)
        assert SEC_BLANK_WITHOUT_NOOPENER in _types(analyze_pages_security([page]))

    def test_blank_with_noopener_not_flagged(self):
        html = '<html><body><a href="/x" target="_blank" rel="noopener">x</a></body></html>'
        page = _secure_page(html=html)
        assert SEC_BLANK_WITHOUT_NOOPENER not in _types(analyze_pages_security([page]))

    def test_blank_with_noreferrer_not_flagged(self):
        # noreferrer implies noopener in modern browsers.
        html = '<html><body><a href="/x" target="_blank" rel="noreferrer">x</a></body></html>'
        page = _secure_page(html=html)
        assert SEC_BLANK_WITHOUT_NOOPENER not in _types(analyze_pages_security([page]))

    def test_same_tab_link_not_flagged(self):
        html = '<html><body><a href="/x">x</a></body></html>'
        page = _secure_page(html=html)
        assert SEC_BLANK_WITHOUT_NOOPENER not in _types(analyze_pages_security([page]))


# --- Information disclosure ------------------------------------------------

class TestServerHeader:
    def test_version_in_server_header_flagged(self):
        page = _secure_page(extra_headers={"Server": "Apache/2.4.41 (Ubuntu)"})
        assert SEC_SERVER_HEADER_DISCLOSURE in _types(analyze_pages_security([page]))

    def test_server_without_version_not_flagged(self):
        page = _secure_page(extra_headers={"Server": "cloudflare"})
        assert SEC_SERVER_HEADER_DISCLOSURE not in _types(analyze_pages_security([page]))

    def test_no_server_header_not_flagged(self):
        assert SEC_SERVER_HEADER_DISCLOSURE not in _types(analyze_pages_security([_secure_page()]))

    def test_severity_is_low(self):
        page = _secure_page(extra_headers={"Server": "nginx/1.18.0"})
        issues = _of_type(analyze_pages_security([page]), SEC_SERVER_HEADER_DISCLOSURE)
        assert issues and issues[0].severity == SEVERITY_LOW
        assert issues[0].category == CATEGORY_INFO_DISCLOSURE


class TestXPoweredBy:
    def test_present_flagged(self):
        page = _secure_page(extra_headers={"X-Powered-By": "PHP/8.1.2"})
        assert SEC_X_POWERED_BY in _types(analyze_pages_security([page]))

    def test_absent_not_flagged(self):
        assert SEC_X_POWERED_BY not in _types(analyze_pages_security([_secure_page()]))


# --- Cookies ---------------------------------------------------------------

# A fully-hardened cookie: nothing should be flagged.
_GOOD_COOKIE = "sid=abc; Path=/; Secure; HttpOnly; SameSite=Lax"


class TestCookies:
    def test_hardened_cookie_not_flagged(self):
        page = _secure_page(set_cookie=[_GOOD_COOKIE])
        types = _types(analyze_pages_security([page]))
        assert SEC_COOKIE_NO_SECURE not in types
        assert SEC_COOKIE_NO_HTTPONLY not in types
        assert SEC_COOKIE_NO_SAMESITE not in types

    def test_missing_secure_flagged_on_https(self):
        page = _secure_page(set_cookie=["sid=abc; HttpOnly; SameSite=Lax"])
        assert SEC_COOKIE_NO_SECURE in _types(analyze_pages_security([page]))

    def test_missing_httponly_flagged(self):
        page = _secure_page(set_cookie=["sid=abc; Secure; SameSite=Lax"])
        assert SEC_COOKIE_NO_HTTPONLY in _types(analyze_pages_security([page]))

    def test_missing_samesite_flagged(self):
        page = _secure_page(set_cookie=["sid=abc; Secure; HttpOnly"])
        assert SEC_COOKIE_NO_SAMESITE in _types(analyze_pages_security([page]))

    def test_bare_cookie_flags_all_three(self):
        page = _secure_page(set_cookie=["sid=abc"])
        types = _types(analyze_pages_security([page]))
        assert {SEC_COOKIE_NO_SECURE, SEC_COOKIE_NO_HTTPONLY,
                SEC_COOKIE_NO_SAMESITE}.issubset(types)

    def test_attribute_matching_is_case_insensitive(self):
        # Servers may send "secure", "SECURE", "httponly", etc.
        page = _secure_page(set_cookie=["sid=abc; secure; httponly; samesite=strict"])
        types = _types(analyze_pages_security([page]))
        assert SEC_COOKIE_NO_SECURE not in types
        assert SEC_COOKIE_NO_HTTPONLY not in types
        assert SEC_COOKIE_NO_SAMESITE not in types

    def test_secure_not_required_on_http_page(self):
        # On a plain-http page the missing-HTTPS issue is the real problem;
        # we don't also nag about the Secure flag (you can't bind Secure to
        # a non-secure transport meaningfully). HttpOnly/SameSite still apply.
        page = _page(url="http://example.com/", set_cookie=["sid=abc"])
        types = _types(analyze_pages_security([page]))
        assert SEC_COOKIE_NO_SECURE not in types
        assert SEC_COOKIE_NO_HTTPONLY in types
        assert SEC_COOKIE_NO_SAMESITE in types

    def test_multiple_cookies_each_evaluated(self):
        page = _secure_page(set_cookie=[
            _GOOD_COOKIE,                      # clean
            "tracker=1; Secure; SameSite=Lax",  # missing HttpOnly
        ])
        issues = analyze_pages_security([page])
        httponly = _of_type(issues, SEC_COOKIE_NO_HTTPONLY)
        assert len(httponly) == 1  # only the second cookie

    def test_expires_comma_does_not_break_parsing(self):
        # Expires dates contain a comma; make sure we still read the flags.
        cookie = ("sid=abc; Expires=Wed, 09 Jun 2027 10:18:14 GMT; "
                  "Secure; HttpOnly; SameSite=Lax")
        page = _secure_page(set_cookie=[cookie])
        types = _types(analyze_pages_security([page]))
        assert SEC_COOKIE_NO_SECURE not in types
        assert SEC_COOKIE_NO_HTTPONLY not in types
        assert SEC_COOKIE_NO_SAMESITE not in types

    def test_category_and_severity(self):
        page = _secure_page(set_cookie=["sid=abc"])
        issues = analyze_pages_security([page])
        secure = _of_type(issues, SEC_COOKIE_NO_SECURE)
        assert secure and secure[0].category == CATEGORY_COOKIES
        assert secure[0].severity == SEVERITY_HIGH

    def test_no_cookies_no_issues(self):
        page = _secure_page(set_cookie=[])
        types = _types(analyze_pages_security([page]))
        assert SEC_COOKIE_NO_SECURE not in types
        assert SEC_COOKIE_NO_HTTPONLY not in types
        assert SEC_COOKIE_NO_SAMESITE not in types


# --- General behaviour -----------------------------------------------------

class TestGeneralBehaviour:
    def test_non_ok_page_skipped(self):
        # A 404 page, even insecure, produces no security issues.
        page = _page(url="http://example.com/missing", status=404)
        assert analyze_pages_security([page]) == []

    def test_all_issues_have_a_security_category(self):
        # An insecure http page with bad HTML — every issue should belong to
        # one of the three security categories used in this stage.
        html = ('<html><body>'
                '<a href="/x" target="_blank">x</a>'
                '</body></html>')
        page = _page(url="http://example.com/", html=html,
                     headers={"Server": "nginx/1.0", "X-Powered-By": "Express"})
        issues = analyze_pages_security([page])
        assert issues
        valid = {CATEGORY_TRANSPORT_SECURITY, CATEGORY_SECURITY_HEADERS,
                 CATEGORY_INFO_DISCLOSURE}
        assert all(i.category in valid for i in issues)


# --- Live TLS (mocked inspector — no real sockets) ------------------------

from datetime import datetime, timezone, timedelta  # noqa: E402


def _https_pg(url: str = "https://secure.test/") -> PageResult:
    """A clean https page (all headers present) so only TLS findings vary."""
    return _page(url=url, html="<html><head><title>T</title></head><body><h1>H</h1></body></html>",
                 headers=_ALL_SECURITY_HEADERS)


def _inspector(*, ok=True, version="TLSv1.3", days=200, error=None, failure_kind=None):
    """Build a fake inspect_tls returning a fixed TlsInfo."""
    now = datetime.now(timezone.utc)
    not_after = now + timedelta(days=days) if days is not None else None
    return lambda host: TlsInfo(host=host, handshake_ok=ok,
                                protocol_version=version,
                                cert_not_after=not_after, error=error,
                                failure_kind=failure_kind)


def _tls_types(pages, inspector):
    issues = _real_analyze_pages_security(pages, check_tls=True, tls_inspector=inspector)
    return {i.issue_type for i in issues}


class TestTls:
    def test_healthy_host_no_tls_issues(self):
        t = _tls_types([_https_pg()], _inspector())
        assert not (t & {SEC_TLS_OUTDATED, SEC_TLS_HANDSHAKE_FAILED,
                         SEC_CERT_EXPIRED, SEC_CERT_EXPIRING})

    def test_outdated_protocol_flagged(self):
        assert SEC_TLS_OUTDATED in _tls_types([_https_pg()], _inspector(version="TLSv1"))

    def test_expired_cert_flagged(self):
        assert SEC_CERT_EXPIRED in _tls_types([_https_pg()], _inspector(days=-5))

    def test_expiring_soon_flagged(self):
        assert SEC_CERT_EXPIRING in _tls_types([_https_pg()], _inspector(days=10))

    def test_cert_just_outside_window_not_flagged(self):
        # 31 days out is beyond the 30-day warning window.
        assert SEC_CERT_EXPIRING not in _tls_types([_https_pg()], _inspector(days=31))

    def test_network_failure_is_generic_handshake_failed(self):
        t = _tls_types([_https_pg()], _inspector(ok=False, version=None, days=None,
                                                 error="refused", failure_kind=FAILURE_NETWORK))
        assert SEC_TLS_HANDSHAKE_FAILED in t
        # A failed handshake means we don't also report version/cert findings.
        assert SEC_TLS_OUTDATED not in t and SEC_CERT_EXPIRED not in t

    def test_expired_via_verification_failure_is_cert_expired(self):
        # When verification (not the date math) reports expiry, still flag it
        # as a clear "Certificate Expired", not a generic handshake failure.
        t = _tls_types([_https_pg()], _inspector(ok=False, version=None, days=None,
                                                 failure_kind=FAILURE_EXPIRED))
        assert SEC_CERT_EXPIRED in t
        assert SEC_TLS_HANDSHAKE_FAILED not in t

    def test_self_signed_is_untrusted_issue(self):
        t = _tls_types([_https_pg()], _inspector(ok=False, version=None, days=None,
                                                 failure_kind=FAILURE_SELF_SIGNED))
        assert SEC_CERT_UNTRUSTED in t
        assert SEC_TLS_HANDSHAKE_FAILED not in t

    def test_hostname_mismatch_is_hostname_issue(self):
        t = _tls_types([_https_pg()], _inspector(ok=False, version=None, days=None,
                                                 failure_kind=FAILURE_HOSTNAME))
        assert SEC_CERT_HOSTNAME in t
        assert SEC_TLS_HANDSHAKE_FAILED not in t

    def test_inspected_once_per_host(self):
        calls = []

        def counting(host):
            calls.append(host)
            return _inspector()(host)

        pages = [_https_pg("https://dup.test/a"),
                 _https_pg("https://dup.test/b"),
                 _https_pg("https://dup.test/c")]
        _real_analyze_pages_security(pages, check_tls=True, tls_inspector=counting)
        assert calls == ["dup.test"]

    def test_localhost_skipped(self):
        calls = []

        def spy(host):
            calls.append(host)
            return _inspector()(host)

        _real_analyze_pages_security([_https_pg("https://localhost:8000/")],
                                     check_tls=True, tls_inspector=spy)
        assert calls == []

    def test_http_site_has_no_tls_check(self):
        calls = []

        def spy(host):
            calls.append(host)
            return _inspector()(host)

        _real_analyze_pages_security([_page(url="http://plain.test/", html="<html></html>")],
                                     check_tls=True, tls_inspector=spy)
        assert calls == []

    def test_disabled_by_default(self):
        # The convenience partial used by the other tests never runs TLS.
        calls = []

        def spy(host):
            calls.append(host)
            return _inspector()(host)

        # check_tls defaults to False here -> inspector never consulted.
        _real_analyze_pages_security([_https_pg()], check_tls=False, tls_inspector=spy)
        assert calls == []

    def test_tls_issues_are_transport_category(self):
        issues = _real_analyze_pages_security([_https_pg()], check_tls=True,
                                              tls_inspector=_inspector(days=-1))
        tls = [i for i in issues if i.issue_type == SEC_CERT_EXPIRED]
        assert tls and tls[0].category == CATEGORY_TRANSPORT_SECURITY
        assert tls[0].severity == SEVERITY_HIGH
