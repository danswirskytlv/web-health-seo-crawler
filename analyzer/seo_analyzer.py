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

from bs4 import BeautifulSoup

from models.result_models import (
    Issue,
    PageResult,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)

# --- Thresholds ----------------------------------------------------------

# A page that takes longer than this is flagged as Slow.
# 2.0s matches Google's "slow page" guidance for Core Web Vitals.
SLOW_RESPONSE_THRESHOLD_SECONDS = 2.0


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
ISSUE_SLOW_RESPONSE = "Slow Response Time"


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
    - 4xx: broken link / bad request.
    - 5xx: server error.

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

    if page.is_client_error:  # 4xx
        issues.append(_build_issue(
            page,
            issue_type=ISSUE_BROKEN_LINK,
            severity=SEVERITY_HIGH,
            description=(
                f"The page returned HTTP {page.status_code}, meaning the URL "
                f"is not valid or no longer exists."
            ),
            recommendation=(
                "Find the page that links to this URL and either fix or remove the link. "
                "If the page was moved, set up a 301 redirect to its new location."
            ),
        ))

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


def _check_slow_response(page: PageResult) -> list[Issue]:
    """Flag pages that took longer than the threshold."""
    if page.response_time is None:
        return []
    if page.response_time <= SLOW_RESPONSE_THRESHOLD_SECONDS:
        return []
    return [_build_issue(
        page,
        issue_type=ISSUE_SLOW_RESPONSE,
        severity=SEVERITY_MEDIUM,
        description=(
            f"The page took {page.response_time:.2f}s to respond, which is above the "
            f"recommended {SLOW_RESPONSE_THRESHOLD_SECONDS:.0f}s threshold for a good user experience."
        ),
        recommendation=(
            "Investigate slow database queries, large unoptimized assets, "
            "or missing CDN/caching configuration."
        ),
    )]


# --- Cross-page check: broken outbound links -----------------------------

def _check_outbound_broken_links(pages: list[PageResult]) -> list[Issue]:
    """
    Detect broken links by cross-referencing pages.

    A 4xx page IS itself an issue (already flagged by _check_http_status).
    But the user really wants to know WHICH pages link to it — that's how
    they fix it. So for every broken target, we add one Broken Link issue
    on each page that linked to it.
    """
    # Set of URLs that responded with 4xx — these are the broken targets.
    broken_targets = {p.url for p in pages if p.is_client_error}
    if not broken_targets:
        return []

    issues: list[Issue] = []

    for page in pages:
        # We only care about pages that successfully loaded and contain links.
        if not page.is_ok or not page.links:
            continue
        for link in page.links:
            if link in broken_targets:
                # Find the target's status code so we can include it.
                target_status = next(
                    (p.status_code for p in pages if p.url == link),
                    None,
                )
                issues.append(_build_issue(
                    page,
                    issue_type=ISSUE_BROKEN_LINK,
                    severity=SEVERITY_HIGH,
                    description=(
                        f"This page links to {link}, which returned HTTP {target_status}."
                    ),
                    recommendation=(
                        f"Update or remove the link to {link}. "
                        "If the destination has moved, link to its new location instead."
                    ),
                ))
    return issues


# --- Public API -----------------------------------------------------------

def analyze_pages(pages: list[PageResult]) -> list[Issue]:
    """
    Run every check on every page and return a flat list of issues.

    Returned issues are NOT deduplicated — the same problem on multiple
    pages becomes multiple issues, which is what the UI and the scorer want.
    """
    issues: list[Issue] = []

    for page in pages:
        # 1. HTTP-level checks always run, even if there's no HTML body.
        issues.extend(_check_http_status(page))

        # 2. Response-time check — independent of HTML.
        issues.extend(_check_slow_response(page))

        # 3. HTML-based SEO checks should ONLY run on pages that actually
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

    # 4. Cross-page check: which pages link to broken pages.
    issues.extend(_check_outbound_broken_links(pages))

    return issues
