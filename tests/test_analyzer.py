"""
Unit tests for analyzer.seo_analyzer.

Each test builds a minimal in-memory PageResult and asserts that the
analyzer detects (or doesn't detect) the expected issue. No network,
no test site needed — this runs in milliseconds.
"""

from __future__ import annotations

from analyzer.seo_analyzer import (
    ISSUE_BROKEN_LINK,
    ISSUE_MISSING_ALT,
    ISSUE_MISSING_H1,
    ISSUE_MISSING_META_DESC,
    ISSUE_MISSING_TITLE,
    ISSUE_SERVER_ERROR,
    ISSUE_UNREACHABLE,
    analyze_pages,
)
from models.result_models import (
    PageResult,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)


# --- Small helpers --------------------------------------------------------

def _page(
    url: str = "http://example.com/",
    status_code: int | None = 200,
    response_time: float | None = 0.1,
    html: str | None = "<html><head><title>x</title></head><body><h1>x</h1></body></html>",
    links: list[str] | None = None,
    error: str | None = None,
) -> PageResult:
    """Build a PageResult with sensible defaults — override only what matters."""
    return PageResult(
        url=url,
        status_code=status_code,
        response_time=response_time,
        html=html,
        links=links or [],
        error=error,
    )


def _types(issues) -> set[str]:
    return {i.issue_type for i in issues}


# --- Missing Title --------------------------------------------------------

class TestMissingTitle:
    def test_detected_when_no_title_tag(self):
        html = "<html><head></head><body><h1>x</h1></body></html>"
        issues = analyze_pages([_page(html=html)])
        assert ISSUE_MISSING_TITLE in _types(issues)

    def test_detected_when_title_is_empty(self):
        html = "<html><head><title></title></head><body><h1>x</h1></body></html>"
        issues = analyze_pages([_page(html=html)])
        assert ISSUE_MISSING_TITLE in _types(issues)

    def test_detected_when_title_is_whitespace_only(self):
        html = "<html><head><title>   </title></head><body><h1>x</h1></body></html>"
        issues = analyze_pages([_page(html=html)])
        assert ISSUE_MISSING_TITLE in _types(issues)

    def test_not_detected_when_title_present(self):
        html = "<html><head><title>Real Title</title></head><body><h1>x</h1></body></html>"
        issues = analyze_pages([_page(html=html)])
        assert ISSUE_MISSING_TITLE not in _types(issues)

    def test_severity_is_high(self):
        html = "<html><head></head><body><h1>x</h1></body></html>"
        issues = analyze_pages([_page(html=html)])
        title_issue = next(i for i in issues if i.issue_type == ISSUE_MISSING_TITLE)
        assert title_issue.severity == SEVERITY_HIGH


# --- Missing H1 -----------------------------------------------------------

class TestMissingH1:
    def test_detected_when_no_h1(self):
        html = "<html><head><title>t</title></head><body><h2>x</h2></body></html>"
        issues = analyze_pages([_page(html=html)])
        assert ISSUE_MISSING_H1 in _types(issues)

    def test_not_detected_when_h1_present(self):
        html = "<html><head><title>t</title></head><body><h1>Real H1</h1></body></html>"
        issues = analyze_pages([_page(html=html)])
        assert ISSUE_MISSING_H1 not in _types(issues)

    def test_severity_is_medium(self):
        html = "<html><head><title>t</title></head><body></body></html>"
        issues = analyze_pages([_page(html=html)])
        h1_issue = next(i for i in issues if i.issue_type == ISSUE_MISSING_H1)
        assert h1_issue.severity == SEVERITY_MEDIUM


# --- Missing Meta Description --------------------------------------------

class TestMissingMetaDescription:
    def test_detected_when_no_meta_tag(self):
        html = "<html><head><title>t</title></head><body><h1>x</h1></body></html>"
        issues = analyze_pages([_page(html=html)])
        assert ISSUE_MISSING_META_DESC in _types(issues)

    def test_detected_when_meta_content_empty(self):
        html = ('<html><head><title>t</title>'
                '<meta name="description" content="">'
                '</head><body><h1>x</h1></body></html>')
        issues = analyze_pages([_page(html=html)])
        assert ISSUE_MISSING_META_DESC in _types(issues)

    def test_not_detected_when_meta_present(self):
        html = ('<html><head><title>t</title>'
                '<meta name="description" content="real description">'
                '</head><body><h1>x</h1></body></html>')
        issues = analyze_pages([_page(html=html)])
        assert ISSUE_MISSING_META_DESC not in _types(issues)


# --- Missing Alt ----------------------------------------------------------

class TestMissingAlt:
    def test_detected_for_each_image_without_alt(self):
        html = ('<html><head><title>t</title></head><body><h1>x</h1>'
                '<img src="a.jpg"><img src="b.jpg"><img src="c.jpg">'
                '</body></html>')
        issues = analyze_pages([_page(html=html)])
        alt_issues = [i for i in issues if i.issue_type == ISSUE_MISSING_ALT]
        assert len(alt_issues) == 3

    def test_image_with_alt_is_not_flagged(self):
        html = ('<html><head><title>t</title></head><body><h1>x</h1>'
                '<img src="ok.jpg" alt="describes the image">'
                '</body></html>')
        issues = analyze_pages([_page(html=html)])
        assert ISSUE_MISSING_ALT not in _types(issues)

    def test_image_with_whitespace_alt_is_flagged(self):
        # alt="   " is effectively missing.
        html = ('<html><head><title>t</title></head><body><h1>x</h1>'
                '<img src="x.jpg" alt="   ">'
                '</body></html>')
        issues = analyze_pages([_page(html=html)])
        assert ISSUE_MISSING_ALT in _types(issues)

    def test_severity_is_low(self):
        html = ('<html><head><title>t</title></head><body><h1>x</h1>'
                '<img src="x.jpg"></body></html>')
        issues = analyze_pages([_page(html=html)])
        alt_issue = next(i for i in issues if i.issue_type == ISSUE_MISSING_ALT)
        assert alt_issue.severity == SEVERITY_LOW


# --- HTTP status checks ---------------------------------------------------

class TestHttpStatus:
    def test_404_flagged_as_broken_link(self):
        page = _page(status_code=404, html="<html><body>404</body></html>")
        issues = analyze_pages([page])
        assert ISSUE_BROKEN_LINK in _types(issues)

    def test_500_flagged_as_server_error(self):
        page = _page(status_code=500, html=None)
        issues = analyze_pages([page])
        assert ISSUE_SERVER_ERROR in _types(issues)

    def test_unreachable_when_no_status(self):
        page = _page(status_code=None, html=None, error="Timeout")
        issues = analyze_pages([page])
        assert ISSUE_UNREACHABLE in _types(issues)

    def test_200_is_not_flagged(self):
        page = _page(status_code=200)
        issues = analyze_pages([page])
        types = _types(issues)
        assert ISSUE_BROKEN_LINK not in types
        assert ISSUE_SERVER_ERROR not in types
        assert ISSUE_UNREACHABLE not in types

    def test_html_checks_skipped_on_error_pages(self):
        """A 404 page is broken; we shouldn't double-flag its missing title."""
        page = _page(
            status_code=404,
            html="<html><head></head><body>Not found</body></html>",
        )
        issues = analyze_pages([page])
        types = _types(issues)
        assert ISSUE_BROKEN_LINK in types
        # Crucially, these should NOT show up on a 404:
        assert ISSUE_MISSING_TITLE not in types
        assert ISSUE_MISSING_H1 not in types
        assert ISSUE_MISSING_META_DESC not in types


# Note: the "Slow Response Time" check moved to the Performance analyzer in
# Stage 10 (it measures server response time, a performance signal). Its tests
# now live in tests/test_performance.py.


# --- Cross-page broken link detection -------------------------------------

class TestCrossPageBrokenLinks:
    def test_page_linking_to_broken_target_gets_flagged(self):
        target = "http://x/missing"
        linker_html = f'<html><head><title>t</title></head><body><h1>x</h1><a href="{target}">go</a></body></html>'
        pages = [
            _page(url="http://x/linker", status_code=200, html=linker_html,
                  links=[target]),
            _page(url=target, status_code=404, html=None, links=[]),
        ]
        issues = analyze_pages(pages)
        # Broken Link should be flagged on BOTH the broken page and the linker.
        broken_link_urls = [i.url for i in issues if i.issue_type == ISSUE_BROKEN_LINK]
        assert "http://x/linker" in broken_link_urls
        assert target in broken_link_urls

    def test_no_broken_links_when_all_pages_ok(self):
        pages = [
            _page(url="http://x/a", status_code=200, links=["http://x/b"]),
            _page(url="http://x/b", status_code=200, links=[]),
        ]
        issues = analyze_pages(pages)
        assert ISSUE_BROKEN_LINK not in _types(issues)
