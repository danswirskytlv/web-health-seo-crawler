"""
Unit tests for analyzer.exposed_paths (active sensitive-path probe).

The network probe is injected as a fake, so these run fully offline.
"""

from __future__ import annotations

from analyzer.exposed_paths import (
    EXPOSED_PATH,
    _unique_bases,
    analyze_pages_exposed,
)
from models.result_models import (
    CATEGORY_INFO_DISCLOSURE,
    PageResult,
    SEVERITY_HIGH,
)


def _page(url: str, status: int = 200) -> PageResult:
    return PageResult(url=url, status_code=status, response_time=0.1,
                      html="<html></html>", final_url=url)


def _exposed_paths(issues):
    return sorted(i.description.split("The path ")[1].split(" is")[0] for i in issues)


class TestExposedPaths:
    def test_detects_exposed_env_and_git(self):
        def probe(url):
            return url.endswith("/.env") or url.endswith("/.git/config")
        issues = analyze_pages_exposed([_page("https://shop.test/")], probe=probe)
        paths = _exposed_paths(issues)
        assert "/.env" in paths and "/.git/config" in paths

    def test_nothing_exposed_is_empty(self):
        assert analyze_pages_exposed([_page("https://clean.test/")], probe=lambda u: False) == []

    def test_issues_are_info_disclosure_category(self):
        issues = analyze_pages_exposed([_page("https://shop.test/")],
                                       probe=lambda u: u.endswith("/.env"))
        assert issues and all(i.category == CATEGORY_INFO_DISCLOSURE for i in issues)

    def test_env_is_high_severity(self):
        issues = analyze_pages_exposed([_page("https://shop.test/")],
                                       probe=lambda u: u.endswith("/.env"))
        assert issues and issues[0].severity == SEVERITY_HIGH

    def test_issue_url_is_the_probed_url(self):
        issues = analyze_pages_exposed([_page("https://shop.test/")],
                                       probe=lambda u: u.endswith("/.env"))
        assert issues[0].url == "https://shop.test/.env"

    def test_probes_once_per_host(self):
        calls = []

        def counting(url):
            calls.append(url)
            return False

        pages = [_page("https://h.test/a"), _page("https://h.test/b"), _page("https://h.test/c")]
        analyze_pages_exposed(pages, probe=counting)
        # One host, so each sensitive path is probed exactly once.
        assert len(calls) == len(set(calls))
        assert all(u.startswith("https://h.test/") for u in calls)

    def test_two_hosts_probed_separately(self):
        calls = []

        def counting(url):
            calls.append(url)
            return False

        analyze_pages_exposed([_page("https://a.test/"), _page("https://b.test/")], probe=counting)
        assert any("a.test" in u for u in calls)
        assert any("b.test" in u for u in calls)

    def test_localhost_skipped(self):
        calls = []

        def spy(url):
            calls.append(url)
            return True

        analyze_pages_exposed([_page("http://localhost:8000/")], probe=spy)
        assert calls == []

    def test_non_ok_pages_excluded(self):
        bases = _unique_bases([_page("https://x.test/", status=404)])
        assert bases == {}
