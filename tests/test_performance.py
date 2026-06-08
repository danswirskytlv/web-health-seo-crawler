"""
Unit tests for analyzer.performance.

Same shape as test_analyzer.py and test_accessibility.py — small in-memory
HTML inputs, fast, no network.
"""

from __future__ import annotations

from analyzer.performance import (
    INLINE_CSS_BYTES,
    INLINE_HANDLERS,
    LARGE_PAGE_BYTES,
    MANY_RESOURCES,
    PERF_EXCESSIVE_INLINE_CSS,
    PERF_LARGE_PAGE_SIZE,
    PERF_RENDER_BLOCKING_SCRIPT,
    PERF_SLOW_RESPONSE,
    PERF_TOO_MANY_INLINE_HANDLERS,
    PERF_TOO_MANY_RESOURCES,
    SLOW_RESPONSE_THRESHOLD_SECONDS,
    analyze_pages_performance,
)
from models.result_models import (
    CATEGORY_PERFORMANCE,
    PageResult,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)


# Minimal HTML head so checks that look in <head> have something to inspect.
_BASE_HEAD = '<html lang="en"><head><meta name="viewport" content="x"></head>'


def _page(
    html: str = "",
    *,
    status: int | None = 200,
    size: int | None = None,
    response_time: float | None = 0.1,
) -> PageResult:
    return PageResult(
        url="http://x/",
        status_code=status,
        response_time=response_time,
        html=html,
        response_size=size if size is not None else (len(html) if html else None),
        content_type="text/html",
    )


def _types(issues) -> set[str]:
    return {i.issue_type for i in issues}


# --- Large page size ----------------------------------------------------

class TestLargePageSize:
    def test_below_threshold_not_flagged(self):
        page = _page(_BASE_HEAD + "<body></body></html>",
                     size=LARGE_PAGE_BYTES - 1)
        assert PERF_LARGE_PAGE_SIZE not in _types(analyze_pages_performance([page]))

    def test_above_threshold_flagged(self):
        page = _page(_BASE_HEAD + "<body></body></html>",
                     size=LARGE_PAGE_BYTES + 1)
        issues = analyze_pages_performance([page])
        assert PERF_LARGE_PAGE_SIZE in _types(issues)

    def test_severity_is_medium(self):
        page = _page(_BASE_HEAD + "<body></body></html>",
                     size=LARGE_PAGE_BYTES + 1024)
        issue = next(i for i in analyze_pages_performance([page])
                     if i.issue_type == PERF_LARGE_PAGE_SIZE)
        assert issue.severity == SEVERITY_MEDIUM
        assert issue.category == CATEGORY_PERFORMANCE

    def test_no_size_means_no_check(self):
        page = _page(_BASE_HEAD + "<body></body></html>", size=None)
        # Replace the auto-computed size with explicit None
        page.response_size = None
        assert PERF_LARGE_PAGE_SIZE not in _types(analyze_pages_performance([page]))


# --- Excessive HTTP resources ------------------------------------------

class TestTooManyResources:
    def test_at_threshold_not_flagged(self):
        # MANY_RESOURCES exactly, not above
        imgs = "".join(f'<img src="x{i}.png">' for i in range(MANY_RESOURCES))
        html = _BASE_HEAD + f"<body>{imgs}</body></html>"
        assert PERF_TOO_MANY_RESOURCES not in _types(
            analyze_pages_performance([_page(html)])
        )

    def test_above_threshold_flagged(self):
        imgs = "".join(f'<img src="x{i}.png">' for i in range(MANY_RESOURCES + 1))
        html = _BASE_HEAD + f"<body>{imgs}</body></html>"
        assert PERF_TOO_MANY_RESOURCES in _types(
            analyze_pages_performance([_page(html)])
        )

    def test_counts_all_resource_types(self):
        # Mix images, scripts, stylesheets, iframes — together over threshold.
        n = (MANY_RESOURCES // 4) + 1
        body = (
            "".join(f'<img src="i{i}.png">' for i in range(n))
            + "".join(f'<script src="s{i}.js"></script>' for i in range(n))
            + "".join(f'<link rel="stylesheet" href="c{i}.css">' for i in range(n))
            + "".join(f'<iframe src="if{i}"></iframe>' for i in range(n))
        )
        html = _BASE_HEAD + f"<body>{body}</body></html>"
        assert PERF_TOO_MANY_RESOURCES in _types(
            analyze_pages_performance([_page(html)])
        )


# --- Render-blocking scripts --------------------------------------------

class TestRenderBlockingScript:
    def test_blocking_script_flagged(self):
        html = (
            '<html><head>'
            '<script src="/legacy/jquery.js"></script>'
            '</head><body></body></html>'
        )
        assert PERF_RENDER_BLOCKING_SCRIPT in _types(
            analyze_pages_performance([_page(html)])
        )

    def test_defer_not_flagged(self):
        html = (
            '<html><head>'
            '<script src="/legacy/jquery.js" defer></script>'
            '</head><body></body></html>'
        )
        assert PERF_RENDER_BLOCKING_SCRIPT not in _types(
            analyze_pages_performance([_page(html)])
        )

    def test_async_not_flagged(self):
        html = (
            '<html><head>'
            '<script src="/legacy/jquery.js" async></script>'
            '</head><body></body></html>'
        )
        assert PERF_RENDER_BLOCKING_SCRIPT not in _types(
            analyze_pages_performance([_page(html)])
        )

    def test_inline_script_not_flagged(self):
        # Inline scripts in head are not external requests.
        html = (
            '<html><head>'
            '<script>console.log("ok")</script>'
            '</head><body></body></html>'
        )
        assert PERF_RENDER_BLOCKING_SCRIPT not in _types(
            analyze_pages_performance([_page(html)])
        )

    def test_script_in_body_not_flagged(self):
        # We only flag scripts in <head>.
        html = (
            '<html><head></head><body>'
            '<script src="/legacy/jquery.js"></script>'
            '</body></html>'
        )
        assert PERF_RENDER_BLOCKING_SCRIPT not in _types(
            analyze_pages_performance([_page(html)])
        )


# --- Excessive inline CSS ----------------------------------------------

class TestExcessiveInlineCss:
    def test_small_style_not_flagged(self):
        html = (
            f'{_BASE_HEAD[:-7]}<style>body{{color:red}}</style></head>'
            '<body></body></html>'
        )
        assert PERF_EXCESSIVE_INLINE_CSS not in _types(
            analyze_pages_performance([_page(html)])
        )

    def test_huge_style_flagged(self):
        big_css = ".x{margin:0}" * (INLINE_CSS_BYTES // 11 + 100)
        html = (
            f'{_BASE_HEAD[:-7]}<style>{big_css}</style></head>'
            '<body></body></html>'
        )
        assert PERF_EXCESSIVE_INLINE_CSS in _types(
            analyze_pages_performance([_page(html)])
        )

    def test_multiple_style_tags_sum(self):
        # Each block alone is below threshold; together they exceed it.
        chunk = ".x{margin:0}" * (INLINE_CSS_BYTES // 22 + 50)
        html = (
            f'{_BASE_HEAD[:-7]}<style>{chunk}</style><style>{chunk}</style></head>'
            '<body></body></html>'
        )
        assert PERF_EXCESSIVE_INLINE_CSS in _types(
            analyze_pages_performance([_page(html)])
        )


# --- Too many inline event handlers ------------------------------------

class TestInlineHandlers:
    def test_below_threshold_not_flagged(self):
        handlers = "".join(
            f'<div onclick="x()">item</div>' for _ in range(INLINE_HANDLERS)
        )
        html = _BASE_HEAD + f"<body>{handlers}</body></html>"
        assert PERF_TOO_MANY_INLINE_HANDLERS not in _types(
            analyze_pages_performance([_page(html)])
        )

    def test_above_threshold_flagged(self):
        handlers = "".join(
            f'<div onclick="x()">item</div>' for _ in range(INLINE_HANDLERS + 1)
        )
        html = _BASE_HEAD + f"<body>{handlers}</body></html>"
        assert PERF_TOO_MANY_INLINE_HANDLERS in _types(
            analyze_pages_performance([_page(html)])
        )

    def test_mixed_handler_types_count_together(self):
        # 6 onclick + 6 onmouseover = 12 > threshold (10).
        html = (
            _BASE_HEAD
            + "<body>"
            + "".join(f'<a onclick="x()">a</a>' for _ in range(6))
            + "".join(f'<a onmouseover="y()">a</a>' for _ in range(6))
            + "</body></html>"
        )
        assert PERF_TOO_MANY_INLINE_HANDLERS in _types(
            analyze_pages_performance([_page(html)])
        )


# --- Skip on error pages -----------------------------------------------

class TestErrorPagesSkipped:
    def test_404_page_not_analyzed(self):
        # A 404 page with all the perf bugs in the world should produce no
        # performance issues — error pages aren't part of the user-facing
        # site.
        html = (
            '<html><head>'
            '<script src="/big.js"></script>'
            '<style>' + (".x{margin:0}" * (INLINE_CSS_BYTES // 11 + 100)) + '</style>'
            '</head><body>'
            + "".join(f'<div onclick="x()">i</div>' for _ in range(20))
            + "</body></html>"
        )
        page = _page(html, status=404, size=LARGE_PAGE_BYTES + 1)
        assert analyze_pages_performance([page]) == []

    def test_slow_error_page_only_flags_slow_response(self):
        # The slow-response check is the one exception: it runs on every page
        # that has a timing, so a slow 404 still gets exactly that one issue
        # (and none of the HTML-based perf checks).
        page = _page("<html></html>", status=404, response_time=5.0)
        types = _types(analyze_pages_performance([page]))
        assert types == {PERF_SLOW_RESPONSE}


# --- Slow response time --------------------------------------------------

class TestSlowResponse:
    def test_fast_page_not_flagged(self):
        issues = analyze_pages_performance([_page(response_time=0.5)])
        assert PERF_SLOW_RESPONSE not in _types(issues)

    def test_at_threshold_not_flagged(self):
        # Exactly at the threshold is fine — the comparison is "<=".
        page = _page(response_time=SLOW_RESPONSE_THRESHOLD_SECONDS)
        assert PERF_SLOW_RESPONSE not in _types(analyze_pages_performance([page]))

    def test_above_threshold_flagged(self):
        issues = analyze_pages_performance([_page(response_time=3.5)])
        assert PERF_SLOW_RESPONSE in _types(issues)

    def test_no_response_time_not_flagged(self):
        # A page that never responded (no timing) can't be judged slow.
        page = _page(response_time=None, status=None)
        assert PERF_SLOW_RESPONSE not in _types(analyze_pages_performance([page]))

    def test_slow_response_issue_is_performance_category(self):
        issues = analyze_pages_performance([_page(response_time=3.5)])
        slow = [i for i in issues if i.issue_type == PERF_SLOW_RESPONSE]
        assert slow and all(i.category == CATEGORY_PERFORMANCE for i in slow)
        assert slow[0].severity == SEVERITY_MEDIUM


# --- Category tag --------------------------------------------------------

class TestCategoryTag:
    def test_all_issues_are_performance(self):
        # Trigger multiple performance issues at once
        html = (
            '<html><head>'
            '<script src="/x.js"></script>'
            '<style>' + (".x{margin:0}" * (INLINE_CSS_BYTES // 11 + 100)) + '</style>'
            '</head><body>'
            + "".join(f'<a onclick="x()">a</a>' for _ in range(INLINE_HANDLERS + 1))
            + "</body></html>"
        )
        issues = analyze_pages_performance([_page(html)])
        assert issues
        for i in issues:
            assert i.category == CATEGORY_PERFORMANCE
