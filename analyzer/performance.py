"""
performance.py
==============

Rule-based performance checks.

Five quick wins that a static crawler can detect without running a real
browser. Anything that needs runtime measurement (render timing, layout
shift, JavaScript main-thread blocking) belongs in a real Lighthouse-style
audit — out of scope here, and we mention that limitation in the project.

What we check
-------------
1. Page weight — Total response body bytes per page.
2. Resource count — How many <img>, <script>, <link>, <iframe> the
   browser will need to fetch.
3. Render-blocking scripts — <script src="..."> inside <head> without
   `async` or `defer`. The browser has to download and execute these
   before it can paint anything.
4. Excessive inline CSS — Many KB of CSS embedded in <style> tags makes
   HTML bloated and uncacheable.
5. Many inline event handlers — A page with dozens of onclick=, onload=,
   onmouseover= is a sign of legacy / unmaintainable JS.

Each check emits Issues with category="Performance" so the UI groups them
cleanly with the SEO, Accessibility, Security and Schema categories.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from models.result_models import (
    CATEGORY_PERFORMANCE,
    Issue,
    PageResult,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)

# --- Thresholds ----------------------------------------------------------

# Industry guideline: pages above ~2MB feel slow on average mobile networks.
LARGE_PAGE_BYTES = 2 * 1024 * 1024

# A modern site typically loads 50-80 resources. Above 100 is unusual.
MANY_RESOURCES = 100

# 30KB of inline CSS in <style> tags is generous; above is bloat. Modern
# build pipelines emit external stylesheets long before they hit this size.
INLINE_CSS_BYTES = 30 * 1024

# More than 10 inline event handlers is rare and almost always legacy.
INLINE_HANDLERS = 10

# A page slower than this (seconds) is flagged. This measures server response
# time (roughly time-to-first-byte) — a performance signal, not an SEO one —
# which is why the check lives in this module.
SLOW_RESPONSE_THRESHOLD_SECONDS = 2.0


# --- Issue type names ----------------------------------------------------

PERF_LARGE_PAGE_SIZE = "Large Page Size"
PERF_TOO_MANY_RESOURCES = "Excessive HTTP Resources"
PERF_RENDER_BLOCKING_SCRIPT = "Render-Blocking Script"
PERF_EXCESSIVE_INLINE_CSS = "Excessive Inline CSS"
PERF_TOO_MANY_INLINE_HANDLERS = "Too Many Inline Event Handlers"
PERF_SLOW_RESPONSE = "Slow Response Time"


# --- Helpers --------------------------------------------------------------

def _build_issue(
    page: PageResult,
    issue_type: str,
    severity: str,
    description: str,
    recommendation: str,
) -> Issue:
    return Issue(
        url=page.url,
        issue_type=issue_type,
        severity=severity,
        category=CATEGORY_PERFORMANCE,
        description=description,
        recommendation=recommendation,
        status_code=page.status_code,
        response_time=page.response_time,
    )


def _format_kb(byte_count: int) -> str:
    return f"{byte_count / 1024:.1f} KB"


def _format_size(byte_count: int) -> str:
    if byte_count >= 1024 * 1024:
        return f"{byte_count / (1024 * 1024):.1f} MB"
    return _format_kb(byte_count)


# --- Individual checks ----------------------------------------------------

def _check_page_size(page: PageResult) -> list[Issue]:
    """Flag pages whose response body exceeds the weight budget."""
    if page.response_size is None:
        return []
    if page.response_size <= LARGE_PAGE_BYTES:
        return []
    return [_build_issue(
        page,
        issue_type=PERF_LARGE_PAGE_SIZE,
        severity=SEVERITY_MEDIUM,
        description=(
            f"The page weighs {_format_size(page.response_size)}, which is above "
            f"the recommended {_format_size(LARGE_PAGE_BYTES)} threshold. "
            "Large pages are slow on mobile and burn user data."
        ),
        recommendation=(
            "Compress images, defer non-critical scripts, split large bundles, "
            "and remove unused libraries to bring the page below 2 MB."
        ),
    )]


def _check_resource_count(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """Flag pages with too many fetched resources."""
    images = soup.find_all("img")
    scripts = soup.find_all("script", src=True)
    links = soup.find_all("link", rel=lambda v: v and "stylesheet" in v)
    iframes = soup.find_all("iframe")

    total = len(images) + len(scripts) + len(links) + len(iframes)
    if total <= MANY_RESOURCES:
        return []
    return [_build_issue(
        page,
        issue_type=PERF_TOO_MANY_RESOURCES,
        severity=SEVERITY_MEDIUM,
        description=(
            f"The page requests {total} resources "
            f"({len(images)} images, {len(scripts)} scripts, "
            f"{len(links)} stylesheets, {len(iframes)} iframes). "
            "Each one is a separate network request."
        ),
        recommendation=(
            "Combine and minify CSS/JS, lazy-load images below the fold, "
            "and remove unused third-party widgets to cut the request count."
        ),
    )]


def _check_render_blocking_scripts(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """
    Flag external scripts in <head> that lack `async` or `defer`.

    These force the browser to download and execute the script before it
    can render anything — a classic cause of slow first paint.
    """
    head = soup.find("head")
    if head is None:
        return []

    blocking = []
    for script in head.find_all("script", src=True):
        if script.has_attr("async") or script.has_attr("defer"):
            continue
        # Inline scripts in <head> aren't external requests, only flag <script src>.
        blocking.append(script.get("src", ""))

    if not blocking:
        return []
    sample = blocking[0]
    return [_build_issue(
        page,
        issue_type=PERF_RENDER_BLOCKING_SCRIPT,
        severity=SEVERITY_MEDIUM,
        description=(
            f"{len(blocking)} external script(s) in <head> are render-blocking "
            f"(missing async / defer). Example: {sample}. The browser must "
            "download and execute each one before the page becomes visible."
        ),
        recommendation=(
            "Add the defer attribute (preferred) or async to non-critical "
            "<script src> tags so they don't block the initial render."
        ),
    )]


def _check_inline_css_size(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """Flag pages with very large inline <style> blocks."""
    total_chars = 0
    for style in soup.find_all("style"):
        text = style.get_text() or ""
        total_chars += len(text)

    if total_chars <= INLINE_CSS_BYTES:
        return []
    return [_build_issue(
        page,
        issue_type=PERF_EXCESSIVE_INLINE_CSS,
        severity=SEVERITY_LOW,
        description=(
            f"The page embeds {_format_kb(total_chars)} of CSS inside <style> "
            "tags. Inline CSS is downloaded with every page view and cannot "
            "be cached separately."
        ),
        recommendation=(
            "Move large CSS rules into an external stylesheet linked with "
            '<link rel="stylesheet" href="..."> so the browser can cache it.'
        ),
    )]


def _check_inline_event_handlers(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """Flag pages with many inline onclick / onmouseover / onload handlers."""
    handler_attrs = (
        "onclick", "onmouseover", "onmouseout", "onmouseup", "onmousedown",
        "onload", "onunload", "onchange", "onsubmit", "onfocus", "onblur",
        "onkeydown", "onkeyup", "onkeypress",
    )
    count = 0
    for element in soup.find_all(True):
        for attr in handler_attrs:
            if element.has_attr(attr):
                count += 1
    if count <= INLINE_HANDLERS:
        return []
    return [_build_issue(
        page,
        issue_type=PERF_TOO_MANY_INLINE_HANDLERS,
        severity=SEVERITY_LOW,
        description=(
            f"The page contains {count} inline event handlers "
            "(onclick, onload, etc.). This pattern is hard to maintain and "
            "prevents the browser from caching the relevant JavaScript."
        ),
        recommendation=(
            "Move handlers into an external script and attach them with "
            "addEventListener. Easier to test, easier to cache, and safer "
            "(plays well with Content-Security-Policy)."
        ),
    )]


def _check_slow_response(page: PageResult) -> list[Issue]:
    """
    Flag pages that took longer than the threshold to respond.

    Unlike the HTML-based checks, this one runs on any page we got a timing
    for — even non-2xx responses — because a slow error page is still a
    performance problem worth surfacing.
    """
    if page.response_time is None:
        return []
    if page.response_time <= SLOW_RESPONSE_THRESHOLD_SECONDS:
        return []
    return [_build_issue(
        page,
        issue_type=PERF_SLOW_RESPONSE,
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


# --- Public API -----------------------------------------------------------

def _parse_html(page: PageResult) -> BeautifulSoup | None:
    if not page.html:
        return None
    return BeautifulSoup(page.html, "html.parser")


def analyze_pages_performance(pages: list[PageResult]) -> list[Issue]:
    """
    Run every performance check on every page.

    The HTML-based checks skip non-2xx responses (no point flagging a 404
    page for being too big), the same convention used by the SEO and
    Accessibility analyzers. The slow-response check runs on every page that
    has a timing, since a slow error page is still a performance problem.
    """
    issues: list[Issue] = []

    for page in pages:
        # Response-time check is independent of HTML and status code.
        issues.extend(_check_slow_response(page))

        if not page.is_ok:
            continue

        # Page size check doesn't need parsed HTML.
        issues.extend(_check_page_size(page))

        soup = _parse_html(page)
        if soup is None:
            continue

        issues.extend(_check_resource_count(page, soup))
        issues.extend(_check_render_blocking_scripts(page, soup))
        issues.extend(_check_inline_css_size(page, soup))
        issues.extend(_check_inline_event_handlers(page, soup))

    return issues
