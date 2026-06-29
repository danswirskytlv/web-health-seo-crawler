"""
seo_analyzer.py
===============

The rule-based analysis engine.

Takes a list of PageResults (from the crawler) and returns a list of Issues
(structured problems to display, score, and ask the AI about).

Design principle: this module is the SINGLE source of truth for "is this a
problem?". The AI Assistant explains and suggests fixes, but it does NOT
decide what counts as an issue. Keeping detection deterministic and
rule-based makes the system predictable, testable, and explainable to
users — and lets us defend that design choice in the project defense.

Each check is a small private function (`_check_*`) that takes a PageResult
and returns 0 or more Issues. The public `analyze_pages` function just runs
all the checks across all pages.
"""

from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from models.result_models import (
    Issue,
    PageResult,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)

# --- Issue type names -----------------------------------------------------

# Plain string constants instead of an Enum — easier to filter, sort and
# display in the UI, and trivial to export to CSV.
ISSUE_BROKEN_LINK = "Broken Link"
ISSUE_SERVER_ERROR = "Server Error"
ISSUE_UNREACHABLE = "Unreachable Page"
ISSUE_MISSING_TITLE = "Missing Title"
ISSUE_MISSING_H1 = "Missing H1"
ISSUE_MISSING_META_DESC = "Missing Meta Description"
ISSUE_MISSING_ALT = "Image Missing Alt"
ISSUE_PAGES_404 = "Pages Returning 404"

# Only these 4xx codes mean "this link leads to a missing page" — a real
# broken link. Other 4xx codes are NOT broken links:
#   401/403 = access-controlled (the page exists, you just can't see it)
#   405/406 = method / content-negotiation quirks
#   429     = rate-limited (the crawler hit a limit; transient, not broken)
# Flagging those as "Broken Link" produces noise on real sites, so we don't.
BROKEN_LINK_STATUS = {404, 410}


def _is_broken_status(status_code) -> bool:
    """True only for status codes that mean the target page is genuinely gone."""
    return status_code in BROKEN_LINK_STATUS


# --- Helpers --------------------------------------------------------------

def _build_issue(
    page: PageResult,
    issue_type: str,
    severity: str,
    description: str,
    recommendation: str,
) -> Issue:
    """Tiny constructor that copies page metadata into the Issue."""
    return Issue(
        url=page.url,
        issue_type=issue_type,
        severity=severity,
        description=description,
        recommendation=recommendation,
        status_code=page.status_code,
        response_time=page.response_time,
    )


def _parse_html(page: PageResult) -> BeautifulSoup | None:
    """
    Parse the page's HTML once. Returns None if there's nothing to parse
    (e.g., we got a 404 or a connection failure).
    """
    if not page.html:
        return None
    return BeautifulSoup(page.html, "html.parser")


# --- Individual checks ----------------------------------------------------

def _check_http_status(page: PageResult) -> list[Issue]:
    """
    Classify the HTTP response itself.

    - Unreachable (no status code at all): connection failures, timeouts.
    - 5xx: server error.

    404/410 pages are NOT flagged here — they're collected and reported once,
    together, by _check_404_pages(), because a server-side scanner can't tell a
    genuinely-missing page from an anti-bot block, so we present them as a
    "worth checking manually" note rather than hard errors.

    Redirects (3xx) and successes (2xx) are not flagged as problems here.
    """
    issues: list[Issue] = []

    if page.status_code is None:
        # We never got a response — usually a timeout or connection refused.
        issues.append(_build_issue(
            page,
            issue_type=ISSUE_UNREACHABLE,
            severity=SEVERITY_HIGH,
            description=(
                f"The page could not be reached"
                + (f" ({page.error})." if page.error else ".")
            ),
            recommendation=(
                "Verify the URL is correct and the server is online. "
                "Check DNS, firewall and timeout settings."
            ),
        ))
        return issues

    # 404/410 are handled by _check_404_pages() (grouped note), not here.

    if page.is_server_error:  # 5xx
        issues.append(_build_issue(
            page,
            issue_type=ISSUE_SERVER_ERROR,
            severity=SEVERITY_HIGH,
            description=(
                f"The server returned HTTP {page.status_code}, which means "
                f"an error occurred on the server while generating this page."
            ),
            recommendation=(
                "Check server logs to identify the cause. "
                "Common causes: unhandled exceptions, database errors, or misconfigured routes."
            ),
        ))

    return issues


def _check_missing_title(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """Flag pages with no <title> or an empty <title>."""
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""

    if not title_text:
        return [_build_issue(
            page,
            issue_type=ISSUE_MISSING_TITLE,
            severity=SEVERITY_HIGH,
            description=(
                "The page is missing a <title> tag, or the tag is empty. "
                "The title is what appears in the browser tab and in Google's search results."
            ),
            recommendation=(
                "Add a unique, descriptive <title> tag of 50-60 characters that summarizes the page."
            ),
        )]
    return []


def _check_missing_h1(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """Flag pages with no <h1>."""
    h1_tag = soup.find("h1")
    h1_text = h1_tag.get_text(strip=True) if h1_tag else ""

    if not h1_text:
        return [_build_issue(
            page,
            issue_type=ISSUE_MISSING_H1,
            severity=SEVERITY_MEDIUM,
            description=(
                "The page is missing an <h1> heading. "
                "The H1 is the main heading and helps both users and search engines "
                "understand what the page is about."
            ),
            recommendation=(
                "Add exactly one <h1> tag near the top of the page that clearly describes its topic."
            ),
        )]
    return []


def _check_missing_meta_description(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """Flag pages with no <meta name="description"> or an empty content."""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    content = meta_tag.get("content", "").strip() if meta_tag else ""

    if not content:
        return [_build_issue(
            page,
            issue_type=ISSUE_MISSING_META_DESC,
            severity=SEVERITY_MEDIUM,
            description=(
                "The page is missing a meta description. "
                "This is the snippet Google shows under the page title in search results."
            ),
            recommendation=(
                "Add <meta name=\"description\" content=\"...\"> in the <head> "
                "with a 120-160 character summary of the page."
            ),
        )]
    return []


def _check_images_missing_alt(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """Flag every <img> without a non-empty alt attribute."""
    issues: list[Issue] = []
    for img in soup.find_all("img"):
        alt = img.get("alt", None)
        # `alt=""` is technically valid (declares the image as decorative),
        # but for this audit we still flag empty alts as Low severity since
        # most empty alts are oversights, not intentional decorative markers.
        if alt is None or not alt.strip():
            src = img.get("src", "(no src)")
            issues.append(_build_issue(
                page,
                issue_type=ISSUE_MISSING_ALT,
                severity=SEVERITY_LOW,
                description=(
                    f"An image (<img src=\"{src}\">) on this page is missing alt text. "
                    "Alt text describes the image for screen readers and search engines."
                ),
                recommendation=(
                    "Add an alt=\"...\" attribute describing the image, "
                    "or alt=\"\" if the image is purely decorative."
                ),
            ))
    return issues


# --- Broken-link verification --------------------------------------------

# --- Site-wide check: pages that returned 404 -----------------------------

# Cap how many URLs we spell out in the note, so the description stays readable
# on a site with a large number of 404s. The full count is always stated.
_MAX_404_URLS_LISTED = 25


def _check_404_pages(pages: list[PageResult]) -> list[Issue]:
    """
    Collect every URL that returned 404/410 into ONE informational note.

    Why one grouped note instead of per-link "Broken Link" errors:
    a server-side scanner cannot tell a genuinely-missing page apart from an
    anti-bot block. Shopify/Cloudflare/WAF-protected sites routinely return
    404/403 to automated tools for pages that work fine in a real browser, so
    flagging each one as a hard "Broken Link" produces false alarms. Instead we
    list the URLs and recommend the owner verify them manually — honest about
    the ambiguity, and still surfaces genuinely dead pages.

    Attached to the first crawled page (a stable anchor for the UI). Low
    severity / informational — it's a heads-up, not a confirmed defect.
    """
    if not pages:
        return []

    not_found = [p.url for p in pages if _is_broken_status(p.status_code)]
    if not_found:
        # de-dup while preserving crawl order
        seen: set[str] = set()
        unique = [u for u in not_found if not (u in seen or seen.add(u))]
    else:
        unique = []
    if not unique:
        return []

    listed = unique[:_MAX_404_URLS_LISTED]
    more = len(unique) - len(listed)
    url_lines = "\n".join(f"  • {u}" for u in listed)
    if more > 0:
        url_lines += f"\n  • …and {more} more"

    count = len(unique)
    noun = "URL" if count == 1 else "URLs"
    description = (
        f"{count} {noun} returned HTTP 404 (page not found) during this scan:\n"
        f"{url_lines}\n\n"
        "Note: a 404 here can mean the page is genuinely missing, OR that the "
        "site is blocking automated scanners (common with Shopify, Cloudflare "
        "and similar protections) and the page actually works in a real browser. "
        "We can't tell these two cases apart from the outside, so this is a "
        "heads-up rather than a confirmed broken link."
    )

    return [Issue(
        url=pages[0].url,
        issue_type=ISSUE_PAGES_404,
        severity=SEVERITY_LOW,
        description=description,
        recommendation=(
            "Open each of these URLs in a browser to check them manually. "
            "If a page really is missing, fix or remove the links pointing to it "
            "(or add a 301 redirect to its new location). If it loads fine, the "
            "site is just blocking scanners and you can ignore it."
        ),
        status_code=None,
        response_time=None,
        # Structured payload: the FULL list of 404 URLs, so the UI can render
        # them as a clean list (the Notes section) rather than parsing the
        # description string.
        details={"urls": unique},
    )]


# --- Public API -----------------------------------------------------------

def analyze_pages(
    pages: list[PageResult],
    check_tls: bool = False,
    check_exposed_paths: bool = False,
    verify_broken_links: bool = False,
    broken_link_verifier=None,
) -> list[Issue]:
    """
    Run every check on every page and return a flat list of issues.

    Returned issues are NOT deduplicated — the same problem on multiple
    pages becomes multiple issues, which is what the UI and the scorer want.

    Network-touching options, all off by default so this function stays fully
    offline and deterministic for tests:
      - `check_tls`: live, per-host TLS inspection.
      - `check_exposed_paths`: active probe for sensitive paths (.env, .git, …).
      - `verify_broken_links` / `broken_link_verifier`: accepted for backward
        compatibility with the API/tests but no longer used. 404s are now
        reported as one grouped, informational "Pages Returning 404" note
        (see _check_404_pages) instead of per-link "Broken Link" errors,
        because a server-side scanner cannot distinguish a genuinely-missing
        page from an anti-bot block.

    Categories included:
      - SEO: title, h1, meta description, image alts, status codes,
        a grouped 404 note
      - Accessibility (Stage 9): lang, viewport, form labels, link text,
        heading order, button text, contrast (delegated to
        analyzer.accessibility)
      - Performance (Stage 10): page weight, resource count, render-blocking
        scripts, inline CSS/handlers, and slow response time (delegated to
        analyzer.performance)
      - Security (Stage 11): transport security, security headers, cookies,
        information disclosure (delegated to analyzer.security)
      - Schema (Stage 12): JSON-LD detection, validation and per-page-type
        recommendations (delegated to analyzer.schema_org)
    """
    issues: list[Issue] = []

    for page in pages:
        # 1. HTTP-level checks always run, even if there's no HTML body.
        #    (404/410 are NOT flagged here — see _check_404_pages below.)
        issues.extend(_check_http_status(page))

        # 2. HTML-based SEO checks should ONLY run on pages that actually
        # loaded successfully (2xx). A 404 page may technically contain HTML,
        # but flagging its missing meta description as an SEO problem is
        # noise — error pages aren't meant to be indexed in the first place.
        if not page.is_ok:
            continue

        soup = _parse_html(page)
        if soup is None:
            continue

        issues.extend(_check_missing_title(page, soup))
        issues.extend(_check_missing_h1(page, soup))
        issues.extend(_check_missing_meta_description(page, soup))
        issues.extend(_check_images_missing_alt(page, soup))

    # 4. Site-wide: collect every 404/410 URL into one informational note
    #    recommending manual verification (honest about anti-bot ambiguity).
    issues.extend(_check_404_pages(pages))

    # 5. Run the accessibility analyzer over the same pages. Done as a
    # separate pass so the accessibility module can stay clean (no imports
    # from this module). It adds category="Accessibility" Issues alongside
    # the SEO ones.
    from analyzer.accessibility import analyze_pages_a11y
    issues.extend(analyze_pages_a11y(pages))

    # 6. Run the performance analyzer (Stage 10). Same pattern — independent
    # module, contributes category="Performance" Issues.
    from analyzer.performance import analyze_pages_performance
    issues.extend(analyze_pages_performance(pages))

    # 7. Run the security analyzer (Stage 11). Same pattern again — adds
    # Transport Security / Security Headers / Information Disclosure Issues.
    # Live TLS inspection only runs when the caller opts in (check_tls).
    from analyzer.security import analyze_pages_security
    issues.extend(analyze_pages_security(pages, check_tls=check_tls))

    # 8. Run the schema.org analyzer (Stage 12). Adds category="Schema"
    # structured-data Issues (detect / validate / recommend JSON-LD).
    from analyzer.schema_org import analyze_pages_schema
    issues.extend(analyze_pages_schema(pages))

    # 9. Run the privacy analyzer. Static/offline — adds category="Privacy"
    # third-party-tracker Issues read from the page's own markup.
    from analyzer.privacy import analyze_pages_privacy
    issues.extend(analyze_pages_privacy(pages))

    # 10. Active exposed-paths probe (opt-in). Sends requests for sensitive
    # paths the site didn't link, so it only runs when explicitly enabled.
    if check_exposed_paths:
        from analyzer.exposed_paths import analyze_pages_exposed
        issues.extend(analyze_pages_exposed(pages))

    return issues
