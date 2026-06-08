"""
Unit tests for analyzer.privacy (third-party tracker detection).

Fully offline — reads only in-memory HTML.
"""

from __future__ import annotations

from analyzer.privacy import (
    PRIV_MANY_THIRD_PARTY,
    PRIV_TRACKER,
    analyze_pages_privacy,
)
from models.result_models import (
    CATEGORY_PRIVACY,
    PageResult,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)


def _page(html: str, url: str = "https://shop.test/", status: int = 200) -> PageResult:
    return PageResult(url=url, status_code=status, response_time=0.1, html=html, final_url=url)


def _descs(issues, t=PRIV_TRACKER):
    return [i.description for i in issues if i.issue_type == t]


class TestTrackerDetection:
    def test_google_analytics_detected(self):
        html = '<html><body><script src="https://www.google-analytics.com/ga.js"></script></body></html>'
        assert any("Google Analytics" in d for d in _descs(analyze_pages_privacy([_page(html)])))

    def test_facebook_pixel_detected(self):
        html = '<html><body><script src="https://connect.facebook.net/en_US/fbevents.js"></script></body></html>'
        assert any("Meta (Facebook) Pixel" in d for d in _descs(analyze_pages_privacy([_page(html)])))

    def test_hotjar_detected_in_iframe(self):
        html = '<html><body><iframe src="https://vars.hotjar.com/box.html"></iframe></body></html>'
        assert any("Hotjar" in d for d in _descs(analyze_pages_privacy([_page(html)])))

    def test_no_trackers_clean(self):
        html = '<html><body><script src="https://shop.test/app.js"></script></body></html>'
        assert analyze_pages_privacy([_page(html)]) == []

    def test_same_site_resource_ignored(self):
        # A script from the page's own domain is not a third party.
        html = '<html><body><script src="https://shop.test/analytics.js"></script></body></html>'
        assert _descs(analyze_pages_privacy([_page(html)])) == []

    def test_subdomain_of_site_is_same_site(self):
        html = '<html><body><script src="https://cdn.shop.test/app.js"></script></body></html>'
        assert analyze_pages_privacy([_page(html)]) == []

    def test_one_issue_per_tracker_per_page(self):
        # Two GA tags on the same page -> a single Google Analytics issue.
        html = ('<html><body>'
                '<script src="https://www.google-analytics.com/ga.js"></script>'
                '<img src="https://www.google-analytics.com/collect">'
                '</body></html>')
        ga = [d for d in _descs(analyze_pages_privacy([_page(html)])) if "Google Analytics" in d]
        assert len(ga) == 1

    def test_category_and_severity(self):
        html = '<html><body><script src="https://www.doubleclick.net/x.js"></script></body></html>'
        issues = analyze_pages_privacy([_page(html)])
        assert issues and issues[0].category == CATEGORY_PRIVACY
        # DoubleClick (advertising) is Medium.
        assert issues[0].severity == SEVERITY_MEDIUM


class TestManyThirdParty:
    def test_many_domains_flagged(self):
        html = "<html><body>" + "".join(
            f'<script src="https://cdn{i}.other.com/x.js"></script>' for i in range(12)
        ) + "</body></html>"
        assert any(i.issue_type == PRIV_MANY_THIRD_PARTY for i in analyze_pages_privacy([_page(html)]))

    def test_few_domains_not_flagged(self):
        html = ('<html><body>'
                '<script src="https://a.other.com/x.js"></script>'
                '<script src="https://b.other.com/x.js"></script>'
                '</body></html>')
        assert not any(i.issue_type == PRIV_MANY_THIRD_PARTY for i in analyze_pages_privacy([_page(html)]))


class TestGeneralBehaviour:
    def test_non_ok_page_skipped(self):
        html = '<html><body><script src="https://www.google-analytics.com/ga.js"></script></body></html>'
        assert analyze_pages_privacy([_page(html, status=404)]) == []

    def test_page_without_html_skipped(self):
        p = PageResult(url="https://shop.test/", status_code=200, response_time=0.1, html=None)
        assert analyze_pages_privacy([p]) == []
