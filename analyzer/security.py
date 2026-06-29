"""
security.py
===========

Rule-based security checks (Stage 11).

Like the other analyzers, this is a *static* auditor: it inspects the URL,
the response headers, and the HTML body that the crawler already captured.
It does not open new connections, run JavaScript, or inspect the TLS
handshake. Anything that needs a live socket (TLS protocol version,
certificate expiry, cipher strength) is intentionally out of scope here and
is tracked as a separate, later stage.

The checks are grouped into four audit categories so the UI can show them as
distinct sections, matching how a real security report is organised:

  Transport Security
    - Site not served over HTTPS
    - Missing HSTS (Strict-Transport-Security) header
    - Mixed content (http:// resources on an https page)

  Security Headers
    - Missing Content-Security-Policy
    - Missing X-Frame-Options
    - Missing X-Content-Type-Options
    - Missing Referrer-Policy
    - Missing Permissions-Policy
    - target="_blank" links without rel="noopener"

  Information Disclosure
    - Server header reveals software / version
    - X-Powered-By header present

  Cookies
    - Set-Cookie without the Secure flag (on HTTPS)
    - Set-Cookie without HttpOnly
    - Set-Cookie without a SameSite attribute

Live TLS inspection (protocol version, certificate expiry, cipher strength)
is deliberately left to a follow-up stage; its category already exists in the
model so it can slot in without a schema change.

Each check emits Issues with the matching category so the dashboard groups
them cleanly alongside SEO, Accessibility and Performance.
"""

from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from models.result_models import (
    CATEGORY_COOKIES,
    CATEGORY_INFO_DISCLOSURE,
    CATEGORY_SECURITY_HEADERS,
    CATEGORY_TRANSPORT_SECURITY,
    Issue,
    PageResult,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)


# --- Issue type names ----------------------------------------------------

SEC_NO_HTTPS = "Site Not Served Over HTTPS"
SEC_MISSING_HSTS = "Missing HSTS Header"
SEC_MIXED_CONTENT = "Mixed Content"

SEC_MISSING_CSP = "Missing Content-Security-Policy"
SEC_MISSING_X_FRAME = "Missing X-Frame-Options"
SEC_MISSING_X_CONTENT_TYPE = "Missing X-Content-Type-Options"
SEC_MISSING_REFERRER_POLICY = "Missing Referrer-Policy"
SEC_MISSING_PERMISSIONS_POLICY = "Missing Permissions-Policy"
SEC_BLANK_WITHOUT_NOOPENER = "target=_blank Without rel=noopener"

SEC_SERVER_HEADER_DISCLOSURE = "Server Header Discloses Software"
SEC_X_POWERED_BY = "X-Powered-By Header Present"

SEC_COOKIE_NO_SECURE = "Cookie Without Secure Flag"
SEC_COOKIE_NO_HTTPONLY = "Cookie Without HttpOnly Flag"
SEC_COOKIE_NO_SAMESITE = "Cookie Without SameSite Attribute"

SEC_TLS_OUTDATED = "Outdated TLS Protocol"
SEC_TLS_HANDSHAKE_FAILED = "TLS Handshake Failed"
SEC_CERT_EXPIRED = "TLS Certificate Expired"
SEC_CERT_EXPIRING = "TLS Certificate Expiring Soon"
SEC_CERT_UNTRUSTED = "TLS Certificate Not Trusted"
SEC_CERT_HOSTNAME = "TLS Certificate Hostname Mismatch"

# Warn when a certificate expires within this many days.
CERT_EXPIRY_WARNING_DAYS = 30

# Hosts we never run live TLS against (no real, publicly-trusted certificate).
_TLS_SKIP_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


# --- Helpers --------------------------------------------------------------

def _build_issue(
    page: PageResult,
    issue_type: str,
    severity: str,
    category: str,
    description: str,
    recommendation: str,
) -> Issue:
    """Construct a security Issue with page metadata copied in."""
    return Issue(
        url=page.url,
        issue_type=issue_type,
        severity=severity,
        category=category,
        description=description,
        recommendation=recommendation,
        status_code=page.status_code,
        response_time=page.response_time,
    )


def _effective_url(page: PageResult) -> str:
    """The URL the page actually resolved to (after any redirects)."""
    return page.final_url or page.url


def _is_https(page: PageResult) -> bool:
    """True if the page's effective URL uses the https scheme."""
    return urlparse(_effective_url(page)).scheme == "https"


def _header(page: PageResult, name: str) -> str | None:
    """
    Case-insensitive response-header lookup.

    HTTP header names are case-insensitive, but `dict(response.headers)`
    stores whatever casing the server used, so we normalise here.
    """
    if not page.headers:
        return None
    target = name.lower()
    for key, value in page.headers.items():
        if key.lower() == target:
            return value
    return None


def _has_header(page: PageResult, name: str) -> bool:
    value = _header(page, name)
    return value is not None and value.strip() != ""


def _parse_html(page: PageResult) -> BeautifulSoup | None:
    if not page.html:
        return None
    return BeautifulSoup(page.html, "html.parser")


# --- Transport Security ---------------------------------------------------

def _check_https(page: PageResult) -> list[Issue]:
    """
    Flag pages that are not served over HTTPS.

    We judge by the *effective* URL: if the crawler requested http:// but the
    server redirected to https://, that's the correct behaviour and we do NOT
    flag it. Only a page that ultimately lands on http:// is a problem.
    """
    if _is_https(page):
        return []
    return [_build_issue(
        page,
        issue_type=SEC_NO_HTTPS,
        severity=SEVERITY_HIGH,
        category=CATEGORY_TRANSPORT_SECURITY,
        # Description is intentionally page-agnostic (no per-page URL) so this
        # site-wide issue de-duplicates into a single row across all pages.
        description=(
            "The site is served over plain HTTP instead of HTTPS. Traffic can "
            "be read or modified in transit, and modern browsers mark the site "
            "as 'Not secure'."
        ),
        recommendation=(
            "Obtain a TLS certificate (e.g. via Let's Encrypt) and serve the "
            "site over HTTPS. Redirect all HTTP requests to the HTTPS version."
        ),
    )]


def _check_hsts(page: PageResult) -> list[Issue]:
    """
    Flag https pages that don't send a Strict-Transport-Security header.

    HSTS only makes sense on HTTPS, so we skip http pages (their real problem
    is the lack of HTTPS, already flagged by _check_https).
    """
    if not _is_https(page):
        return []
    if _has_header(page, "Strict-Transport-Security"):
        return []
    return [_build_issue(
        page,
        issue_type=SEC_MISSING_HSTS,
        severity=SEVERITY_MEDIUM,
        category=CATEGORY_TRANSPORT_SECURITY,
        description=(
            "The page is served over HTTPS but does not send a "
            "Strict-Transport-Security (HSTS) header. Without it, a user's "
            "first request can still be downgraded to HTTP by an attacker."
        ),
        recommendation=(
            "Add a header such as "
            "'Strict-Transport-Security: max-age=31536000; includeSubDomains'. "
            "Start with a short max-age while you confirm everything works."
        ),
    )]


def _check_mixed_content(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """
    Flag http:// sub-resources loaded by an https page.

    Browsers block or warn on mixed content because the insecure resource
    undermines the security of the whole page.
    """
    if not _is_https(page):
        return []

    # Attributes that pull in a sub-resource the browser will fetch.
    resource_attrs = (("img", "src"), ("script", "src"), ("link", "href"),
                      ("iframe", "src"), ("audio", "src"), ("video", "src"),
                      ("source", "src"), ("embed", "src"))

    insecure: list[str] = []
    for tag_name, attr in resource_attrs:
        for el in soup.find_all(tag_name):
            value = (el.get(attr) or "").strip()
            if value.lower().startswith("http://"):
                insecure.append(value)

    if not insecure:
        return []
    sample = insecure[0]
    return [_build_issue(
        page,
        issue_type=SEC_MIXED_CONTENT,
        severity=SEVERITY_HIGH,
        category=CATEGORY_TRANSPORT_SECURITY,
        description=(
            f"This HTTPS page loads {len(insecure)} resource(s) over insecure "
            f"HTTP. Example: {sample}. Browsers block or warn on mixed content, "
            "and it weakens the page's security."
        ),
        recommendation=(
            "Update the resource URLs to https:// (or protocol-relative //) so "
            "every sub-resource is loaded securely."
        ),
    )]


# --- Security Headers -----------------------------------------------------

# (header name, issue type, severity, short human description, recommendation)
_HEADER_CHECKS = [
    (
        "Content-Security-Policy",
        SEC_MISSING_CSP,
        SEVERITY_MEDIUM,
        "A Content-Security-Policy header restricts which scripts, styles and "
        "other resources may load, which is the single strongest defence "
        "against cross-site scripting (XSS).",
        "Add a Content-Security-Policy header. Start in report-only mode "
        "(Content-Security-Policy-Report-Only) to find violations safely.",
    ),
    (
        "X-Frame-Options",
        SEC_MISSING_X_FRAME,
        SEVERITY_MEDIUM,
        "Without X-Frame-Options the page can be embedded in an <iframe> on a "
        "malicious site and used for clickjacking.",
        "Add 'X-Frame-Options: DENY' (or SAMEORIGIN), or use the "
        "frame-ancestors directive in your Content-Security-Policy.",
    ),
    (
        "X-Content-Type-Options",
        SEC_MISSING_X_CONTENT_TYPE,
        SEVERITY_LOW,
        "Without X-Content-Type-Options the browser may MIME-sniff responses "
        "and execute a file as a different, more dangerous type.",
        "Add the header 'X-Content-Type-Options: nosniff'.",
    ),
    (
        "Referrer-Policy",
        SEC_MISSING_REFERRER_POLICY,
        SEVERITY_LOW,
        "Without a Referrer-Policy the full URL (which may contain sensitive "
        "data) can leak to third-party sites via the Referer header.",
        "Add a header such as "
        "'Referrer-Policy: strict-origin-when-cross-origin'.",
    ),
    (
        "Permissions-Policy",
        SEC_MISSING_PERMISSIONS_POLICY,
        SEVERITY_LOW,
        "A Permissions-Policy header lets you disable powerful browser "
        "features (camera, microphone, geolocation) that the page doesn't use, "
        "reducing the attack surface.",
        "Add a Permissions-Policy header that disables unused features, e.g. "
        "'Permissions-Policy: geolocation=(), camera=(), microphone=()'.",
    ),
]


def _check_security_headers(page: PageResult) -> list[Issue]:
    """Flag each recommended security header that is missing."""
    # These headers only matter once we have an HTTPS page that actually
    # responded. For plain-HTTP pages the headline issue is the missing HTTPS.
    if not _is_https(page):
        return []

    issues: list[Issue] = []
    for header_name, issue_type, severity, description, recommendation in _HEADER_CHECKS:
        if _has_header(page, header_name):
            continue
        issues.append(_build_issue(
            page,
            issue_type=issue_type,
            severity=severity,
            category=CATEGORY_SECURITY_HEADERS,
            description=f"The response is missing the {header_name} header. {description}",
            recommendation=recommendation,
        ))
    return issues


def _check_blank_without_noopener(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """
    Flag links that open in a new tab without rel="noopener".

    A target="_blank" link without noopener lets the opened page control the
    original tab via window.opener (reverse-tabnabbing). rel="noreferrer"
    also implies noopener and is accepted here.
    """
    offending: list[str] = []
    for a in soup.find_all("a", target=True):
        if a.get("target", "").strip().lower() != "_blank":
            continue
        rel_tokens = {t.lower() for t in (a.get("rel") or [])}
        # BeautifulSoup parses rel into a list; if it came through as a string
        # (rare), normalise it.
        if isinstance(a.get("rel"), str):
            rel_tokens = {t.lower() for t in a.get("rel").split()}
        if "noopener" in rel_tokens or "noreferrer" in rel_tokens:
            continue
        offending.append(a.get("href", "(no href)"))

    if not offending:
        return []
    sample = offending[0]
    return [_build_issue(
        page,
        issue_type=SEC_BLANK_WITHOUT_NOOPENER,
        severity=SEVERITY_MEDIUM,
        category=CATEGORY_SECURITY_HEADERS,
        description=(
            f"{len(offending)} link(s) use target=\"_blank\" without "
            f"rel=\"noopener\". Example: {sample}. The newly opened page can "
            "manipulate this tab via window.opener (reverse tabnabbing)."
        ),
        recommendation=(
            'Add rel="noopener" (or rel="noopener noreferrer") to every '
            'target="_blank" link.'
        ),
    )]


# --- Information Disclosure ------------------------------------------------

def _check_server_header(page: PageResult) -> list[Issue]:
    """
    Flag a Server header that reveals the software and/or its version.

    Knowing the exact server/version makes it trivial for an attacker to look
    up known CVEs. A bare product name with no version is far less useful to
    them, so we only flag when a version number (a digit) is present.
    """
    server = _header(page, "Server")
    if not server or not server.strip():
        return []
    if not any(ch.isdigit() for ch in server):
        # e.g. "Server: cloudflare" with no version — low value to attackers.
        return []
    return [_build_issue(
        page,
        issue_type=SEC_SERVER_HEADER_DISCLOSURE,
        severity=SEVERITY_LOW,
        category=CATEGORY_INFO_DISCLOSURE,
        description=(
            f"The Server header reveals software and version: \"{server.strip()}\". "
            "This helps an attacker target known vulnerabilities for that exact "
            "version."
        ),
        recommendation=(
            "Configure the server to suppress or generalise the Server header "
            "(e.g. hide the version, or remove the header entirely)."
        ),
    )]


def _check_x_powered_by(page: PageResult) -> list[Issue]:
    """Flag the presence of an X-Powered-By header (pure information leak)."""
    value = _header(page, "X-Powered-By")
    if not value or not value.strip():
        return []
    return [_build_issue(
        page,
        issue_type=SEC_X_POWERED_BY,
        severity=SEVERITY_LOW,
        category=CATEGORY_INFO_DISCLOSURE,
        description=(
            f"The response sends an X-Powered-By header (\"{value.strip()}\"), "
            "advertising the underlying technology stack. This gives attackers "
            "free reconnaissance and provides no benefit to users."
        ),
        recommendation=(
            "Remove the X-Powered-By header in your server or framework "
            "configuration (e.g. app.disable('x-powered-by') in Express)."
        ),
    )]


# --- Cookies --------------------------------------------------------------

def _parse_cookie(raw: str) -> tuple[str, set[str]]:
    """
    Parse a raw Set-Cookie header into (cookie_name, lowercased_attributes).

    Example:
        "sid=abc; Path=/; Secure; HttpOnly; SameSite=Lax"
        -> ("sid", {"path", "secure", "httponly", "samesite"})

    We only need to know which attributes are *present*, so for flag-style
    attributes (Secure, HttpOnly) and key=value attributes (SameSite=Lax)
    alike we keep just the attribute name.
    """
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    if not parts:
        return "", set()
    # First part is the cookie's name=value.
    name = parts[0].split("=", 1)[0].strip()
    attrs = set()
    for attr in parts[1:]:
        key = attr.split("=", 1)[0].strip().lower()
        if key:
            attrs.add(key)
    return name, attrs


def _check_cookies(page: PageResult) -> list[Issue]:
    """
    Inspect each Set-Cookie header for the three protective attributes.

    - Secure   : the cookie is only sent over HTTPS. Flagged only on https
                 pages (on http there's no Secure transport to bind to, and
                 the missing-HTTPS issue already covers the bigger problem).
    - HttpOnly : the cookie is hidden from JavaScript, limiting XSS theft.
    - SameSite : restricts cross-site sending, mitigating CSRF.
    """
    issues: list[Issue] = []
    is_https = _is_https(page)

    for raw in page.set_cookie_headers:
        name, attrs = _parse_cookie(raw)
        if not name:
            continue
        label = f'The cookie "{name}"'

        if is_https and "secure" not in attrs:
            issues.append(_build_issue(
                page,
                issue_type=SEC_COOKIE_NO_SECURE,
                severity=SEVERITY_HIGH,
                category=CATEGORY_COOKIES,
                description=(
                    f"{label} is set without the Secure flag, so the browser "
                    "will also send it over plain HTTP where it can be "
                    "intercepted."
                ),
                recommendation=(
                    "Add the Secure attribute to the Set-Cookie header so the "
                    "cookie is only ever transmitted over HTTPS."
                ),
            ))

        if "httponly" not in attrs:
            issues.append(_build_issue(
                page,
                issue_type=SEC_COOKIE_NO_HTTPONLY,
                severity=SEVERITY_MEDIUM,
                category=CATEGORY_COOKIES,
                description=(
                    f"{label} is set without the HttpOnly flag, so client-side "
                    "JavaScript can read it. If the site has an XSS flaw, the "
                    "cookie (e.g. a session token) can be stolen."
                ),
                recommendation=(
                    "Add the HttpOnly attribute unless the cookie genuinely "
                    "needs to be read by JavaScript."
                ),
            ))

        if "samesite" not in attrs:
            issues.append(_build_issue(
                page,
                issue_type=SEC_COOKIE_NO_SAMESITE,
                severity=SEVERITY_LOW,
                category=CATEGORY_COOKIES,
                description=(
                    f"{label} has no SameSite attribute. Without it the cookie "
                    "is sent on cross-site requests, which can enable CSRF."
                ),
                recommendation=(
                    "Add SameSite=Lax (a good default) or SameSite=Strict to "
                    "the Set-Cookie header."
                ),
            ))

    return issues


# --- Public API -----------------------------------------------------------

# --- TLS (live, per host) -------------------------------------------------

def _https_hosts(pages: list[PageResult]) -> dict[str, PageResult]:
    """
    Map each unique HTTPS host to a representative page (for issue URLs).

    TLS is a property of the host, not the page, so we inspect each host once.
    Skips localhost-style hosts that have no real, publicly-trusted cert.
    """
    hosts: dict[str, PageResult] = {}
    for page in pages:
        if not page.is_ok or not _is_https(page):
            continue
        host = urlparse(_effective_url(page)).hostname or ""
        if not host or host.lower() in _TLS_SKIP_HOSTS:
            continue
        hosts.setdefault(host, page)
    return hosts


def _tls_issues_for(host: str, page: PageResult, info) -> list[Issue]:
    """Turn one host's TlsInfo into graded Transport Security issues."""
    issues: list[Issue] = []

    # Failed handshake — classify the reason so the message is actionable.
    if not info.handshake_ok:
        from analyzer.tls import (
            FAILURE_EXPIRED, FAILURE_HOSTNAME, FAILURE_SELF_SIGNED,
        )
        kind = info.failure_kind

        if kind == FAILURE_EXPIRED:
            return [_build_issue(
                page,
                issue_type=SEC_CERT_EXPIRED,
                severity=SEVERITY_HIGH,
                category=CATEGORY_TRANSPORT_SECURITY,
                description=(
                    f"The TLS certificate for {host} has expired. Browsers show "
                    "a full-page security warning and block the site."
                ),
                recommendation=(
                    "Renew the certificate immediately and automate renewal "
                    "(e.g. certbot) so it can't lapse again."
                ),
            )]

        if kind == FAILURE_HOSTNAME:
            return [_build_issue(
                page,
                issue_type=SEC_CERT_HOSTNAME,
                severity=SEVERITY_HIGH,
                category=CATEGORY_TRANSPORT_SECURITY,
                description=(
                    f"The TLS certificate served by {host} does not cover that "
                    "hostname. Browsers reject it with a name-mismatch warning."
                ),
                recommendation=(
                    "Install a certificate whose Subject Alternative Names "
                    f"include {host} (or a matching wildcard)."
                ),
            )]

        if kind == FAILURE_SELF_SIGNED:
            return [_build_issue(
                page,
                issue_type=SEC_CERT_UNTRUSTED,
                severity=SEVERITY_HIGH,
                category=CATEGORY_TRANSPORT_SECURITY,
                description=(
                    f"The TLS certificate for {host} is self-signed or chains to "
                    "an untrusted root, so browsers won't trust it."
                ),
                recommendation=(
                    "Use a certificate from a publicly-trusted CA (e.g. Let's "
                    "Encrypt) and serve the full certificate chain."
                ),
            )]

        # Network-level failures (DNS, timeout, refused) are likely transient
        # or environmental — report them, but as the generic handshake issue.
        detail = info.error or "the connection could not be established"
        return [_build_issue(
            page,
            issue_type=SEC_TLS_HANDSHAKE_FAILED,
            severity=SEVERITY_HIGH,
            category=CATEGORY_TRANSPORT_SECURITY,
            description=(
                f"The TLS handshake with {host} failed ({detail}). Visitors may "
                "see a browser security warning instead of the site."
            ),
            recommendation=(
                "Check that the certificate is valid, unexpired, matches the "
                "hostname, the full chain is served, and the host is reachable. "
                "Test with Qualys SSL Labs."
            ),
        )]

    # Outdated protocol version.
    if info.is_outdated_version:
        issues.append(_build_issue(
            page,
            issue_type=SEC_TLS_OUTDATED,
            severity=SEVERITY_HIGH,
            category=CATEGORY_TRANSPORT_SECURITY,
            description=(
                f"{host} negotiated {info.protocol_version}, a deprecated TLS "
                "version with known weaknesses. Modern browsers warn on or "
                "block these."
            ),
            recommendation=(
                "Reconfigure the server to require TLS 1.2 or higher (TLS 1.3 "
                "preferred) and disable SSLv3 / TLS 1.0 / TLS 1.1."
            ),
        ))

    # Certificate expiry.
    days = info.days_until_expiry()
    if days is not None:
        if days < 0:
            issues.append(_build_issue(
                page,
                issue_type=SEC_CERT_EXPIRED,
                severity=SEVERITY_HIGH,
                category=CATEGORY_TRANSPORT_SECURITY,
                description=(
                    f"The TLS certificate for {host} expired {abs(days)} day(s) "
                    "ago. Browsers will show a full-page security warning."
                ),
                recommendation=(
                    "Renew the certificate immediately. Automate renewal (e.g. "
                    "certbot) so it can't lapse again."
                ),
            ))
        elif days <= CERT_EXPIRY_WARNING_DAYS:
            issues.append(_build_issue(
                page,
                issue_type=SEC_CERT_EXPIRING,
                severity=SEVERITY_MEDIUM,
                category=CATEGORY_TRANSPORT_SECURITY,
                description=(
                    f"The TLS certificate for {host} expires in {days} day(s). "
                    "If it lapses, visitors will see a security warning."
                ),
                recommendation=(
                    "Renew the certificate before it expires, and set up "
                    "automatic renewal so this doesn't recur."
                ),
            ))

    return issues


def _check_tls(pages: list[PageResult], inspector=None) -> list[Issue]:
    """
    Run live TLS inspection once per unique HTTPS host.

    `inspector` defaults to analyzer.tls.inspect_tls; tests inject a fake.
    """
    if inspector is None:
        from analyzer.tls import inspect_tls as inspector

    issues: list[Issue] = []
    for host, page in _https_hosts(pages).items():
        info = inspector(host)
        issues.extend(_tls_issues_for(host, page, info))
    return issues


# --- Public API -----------------------------------------------------------

def analyze_pages_security(
    pages: list[PageResult],
    check_tls: bool = True,
    tls_inspector=None,
) -> list[Issue]:
    """
    Run every security check on every page and return a flat list of issues.

    Mirrors analyze_pages_performance() / analyze_pages_a11y(): same input,
    same output type, independent module. Only successfully-loaded (2xx) pages
    are inspected — flagging the security headers of a 404 page is noise.

    `check_tls` runs a live, per-host TLS inspection (one socket per unique
    HTTPS host). It can be disabled (e.g. for fully-offline runs), and
    `tls_inspector` lets tests inject a fake so no real sockets are opened.
    """
    issues: list[Issue] = []

    for page in pages:
        if not page.is_ok:
            continue

        # URL- and header-based checks (no HTML needed).
        issues.extend(_check_https(page))
        issues.extend(_check_hsts(page))
        issues.extend(_check_security_headers(page))
        issues.extend(_check_server_header(page))
        issues.extend(_check_x_powered_by(page))
        issues.extend(_check_cookies(page))

        # HTML-based checks.
        soup = _parse_html(page)
        if soup is None:
            continue
        issues.extend(_check_mixed_content(page, soup))
        issues.extend(_check_blank_without_noopener(page, soup))

    # Live TLS inspection, once per unique HTTPS host.
    if check_tls:
        issues.extend(_check_tls(pages, inspector=tls_inspector))

    return issues
