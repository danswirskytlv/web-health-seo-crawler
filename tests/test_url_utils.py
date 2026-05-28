"""
Unit tests for crawler.url_utils.

These functions are pure (no network, no I/O), so they're cheap to test
and worth testing thoroughly — they're the foundation everything else
in the crawler relies on.
"""

from __future__ import annotations

import pytest

from crawler.url_utils import (
    extract_links,
    filter_internal_links,
    get_domain,
    is_internal_url,
    normalize_url,
    should_skip_url,
)


# --- normalize_url --------------------------------------------------------

class TestNormalizeUrl:
    """Canonical form should be the same for all equivalent variants."""

    def test_lowercases_scheme_and_host(self):
        assert normalize_url("HTTP://Example.COM/About") == "http://example.com/About"

    def test_preserves_path_case(self):
        # Many servers actually distinguish /Page from /page,
        # so we must NOT lowercase the path.
        assert normalize_url("https://example.com/Page") == "https://example.com/Page"

    def test_drops_fragment(self):
        assert normalize_url("https://example.com/about#team") == "https://example.com/about"

    def test_strips_trailing_slash(self):
        assert normalize_url("https://example.com/about/") == "https://example.com/about"

    def test_root_variants_all_collapse(self):
        # The three equivalent ways to address the root must normalize equally.
        a = normalize_url("http://localhost:8000")
        b = normalize_url("http://localhost:8000/")
        c = normalize_url("http://localhost:8000/index.html")
        assert a == b == c

    def test_index_html_collapses_to_folder(self):
        assert normalize_url("https://example.com/blog/index.html") == "https://example.com/blog"

    def test_non_index_html_preserved(self):
        # Don't accidentally strip non-index html files.
        assert normalize_url("https://example.com/about.html") == "https://example.com/about.html"

    def test_keeps_query_string(self):
        # Query parameters can be semantically meaningful.
        assert (
            normalize_url("https://example.com/search?q=python")
            == "https://example.com/search?q=python"
        )


# --- is_internal_url ------------------------------------------------------

class TestIsInternalUrl:
    def test_same_domain_is_internal(self):
        assert is_internal_url("https://example.com/about", "example.com")

    def test_different_domain_is_external(self):
        assert not is_internal_url("https://other.com/about", "example.com")

    def test_subdomain_is_NOT_internal_by_default(self):
        # Conservative: blog.example.com is NOT the same as example.com.
        assert not is_internal_url("https://blog.example.com/", "example.com")

    def test_case_insensitive(self):
        assert is_internal_url("https://EXAMPLE.com/x", "example.com")

    def test_localhost_with_port(self):
        assert is_internal_url("http://localhost:8000/a", "localhost:8000")
        assert not is_internal_url("http://localhost:9000/a", "localhost:8000")


# --- should_skip_url ------------------------------------------------------

class TestShouldSkipUrl:
    @pytest.mark.parametrize("url", [
        "mailto:hello@example.com",
        "tel:+972501234567",
        "javascript:void(0)",
        "ftp://example.com/file.zip",
    ])
    def test_skips_non_http_schemes(self, url: str):
        assert should_skip_url(url)

    @pytest.mark.parametrize("url", [
        "https://example.com/cat.jpg",
        "https://example.com/Cat.JPG",          # case-insensitive
        "https://example.com/photo.png",
        "https://example.com/docs/report.pdf",
        "https://example.com/video.mp4",
        "https://example.com/data.xlsx",
        "https://example.com/file.zip",
    ])
    def test_skips_binary_extensions(self, url: str):
        assert should_skip_url(url)

    @pytest.mark.parametrize("url", [
        "https://example.com/",
        "https://example.com/about.html",
        "https://example.com/some/page",
        "https://example.com/path?query=1",
    ])
    def test_keeps_html_pages(self, url: str):
        assert not should_skip_url(url)


# --- extract_links --------------------------------------------------------

class TestExtractLinks:
    def test_extracts_absolute_links(self):
        html = '<a href="https://example.com/a">a</a><a href="https://example.com/b">b</a>'
        links = extract_links(html, "https://example.com/")
        assert "https://example.com/a" in links
        assert "https://example.com/b" in links

    def test_resolves_relative_links(self):
        html = '<a href="/about">about</a>'
        links = extract_links(html, "https://example.com/page")
        assert "https://example.com/about" in links

    def test_deduplicates_links_on_same_page(self):
        html = '<a href="/x">1</a><a href="/x">2</a><a href="/x">3</a>'
        links = extract_links(html, "https://example.com/")
        # Only one entry for /x even though it appears three times.
        assert links.count("https://example.com/x") == 1

    def test_skips_empty_hrefs(self):
        html = '<a href="">empty</a><a href="/real">real</a>'
        links = extract_links(html, "https://example.com/")
        assert "https://example.com/real" in links
        assert "" not in links

    def test_empty_html_returns_empty_list(self):
        assert extract_links("", "https://example.com/") == []
        assert extract_links(None, "https://example.com/") == []

    def test_html_with_no_anchors_returns_empty(self):
        html = "<html><body><p>No links here.</p></body></html>"
        assert extract_links(html, "https://example.com/") == []

    def test_links_are_normalized(self):
        # Verify that the normalization rules are applied
        # (trailing slash stripped, fragment dropped).
        html = '<a href="/about/#team">about</a>'
        links = extract_links(html, "https://example.com/")
        assert links == ["https://example.com/about"]


# --- get_domain -----------------------------------------------------------

class TestGetDomain:
    def test_returns_netloc(self):
        assert get_domain("https://example.com/path") == "example.com"

    def test_includes_port(self):
        assert get_domain("http://localhost:8000/x") == "localhost:8000"

    def test_lowercases(self):
        assert get_domain("https://EXAMPLE.com/x") == "example.com"


# --- filter_internal_links ------------------------------------------------

class TestFilterInternalLinks:
    def test_filters_external_domains(self):
        links = [
            "https://example.com/a",
            "https://other.com/b",
            "https://example.com/c",
        ]
        result = filter_internal_links(links, "example.com")
        assert result == ["https://example.com/a", "https://example.com/c"]

    def test_filters_binary_extensions(self):
        links = [
            "https://example.com/page.html",
            "https://example.com/image.jpg",
            "https://example.com/doc.pdf",
        ]
        result = filter_internal_links(links, "example.com")
        assert result == ["https://example.com/page.html"]

    def test_deduplicates(self):
        links = ["https://example.com/a", "https://example.com/a"]
        result = filter_internal_links(links, "example.com")
        assert result == ["https://example.com/a"]
