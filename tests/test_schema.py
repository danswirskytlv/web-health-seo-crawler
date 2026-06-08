"""
Unit tests for analyzer.schema_org (Stage 12).

Mirrors the other analyzer test files: small in-memory HTML, fast, no network.
"""

from __future__ import annotations

import json

from analyzer.schema_org import (
    SCHEMA_INVALID_JSON,
    SCHEMA_MISSING,
    SCHEMA_MISSING_CONTEXT,
    SCHEMA_MISSING_TYPE,
    analyze_pages_schema,
)
from models.result_models import (
    CATEGORY_SCHEMA,
    PageResult,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)


def _page(html: str, url: str = "https://example.com/", status: int = 200) -> PageResult:
    return PageResult(url=url, status_code=status, response_time=0.1, html=html)


def _types(issues) -> set[str]:
    return {i.issue_type for i in issues}


def _of_type(issues, t):
    return [i for i in issues if i.issue_type == t]


def _ld(obj: dict) -> str:
    """Wrap a dict as a JSON-LD <script> block."""
    return f'<script type="application/ld+json">{json.dumps(obj)}</script>'


_VALID_ARTICLE = {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "Hello",
}


# --- Detect / missing -----------------------------------------------------

class TestMissingStructuredData:
    def test_page_with_no_jsonld_flagged(self):
        page = _page("<html><body><h1>Hi</h1></body></html>")
        assert SCHEMA_MISSING in _types(analyze_pages_schema([page]))

    def test_page_with_valid_jsonld_not_flagged_as_missing(self):
        page = _page(f"<html><body>{_ld(_VALID_ARTICLE)}</body></html>")
        assert SCHEMA_MISSING not in _types(analyze_pages_schema([page]))

    def test_severity_is_medium(self):
        page = _page("<html><body></body></html>")
        issues = _of_type(analyze_pages_schema([page]), SCHEMA_MISSING)
        assert issues and issues[0].severity == SEVERITY_MEDIUM

    def test_category_is_schema(self):
        page = _page("<html><body></body></html>")
        issues = analyze_pages_schema([page])
        assert issues and all(i.category == CATEGORY_SCHEMA for i in issues)


# --- Recommend by page type ----------------------------------------------

class TestRecommendByType:
    def _reco(self, url):
        page = _page("<html><body><h1>x</h1></body></html>", url=url)
        issues = _of_type(analyze_pages_schema([page]), SCHEMA_MISSING)
        assert issues
        return issues[0].recommendation

    def test_blog_recommends_article(self):
        assert "Article" in self._reco("https://example.com/blog/my-post")

    def test_contact_recommends_organization(self):
        assert "Organization" in self._reco("https://example.com/contact")

    def test_faq_url_recommends_faqpage(self):
        assert "FAQPage" in self._reco("https://example.com/faq")

    def test_pricing_recommends_product(self):
        assert "Product" in self._reco("https://example.com/pricing")

    def test_unknown_falls_back_to_webpage(self):
        assert "WebPage" in self._reco("https://example.com/")

    def test_qa_content_recommends_faqpage_without_url_hint(self):
        # No FAQ hint in the URL, but the content is clearly Q&A.
        html = ("<html><body>"
                "<h2>What is it?</h2><p>...</p>"
                "<h2>How much?</h2><p>...</p>"
                "<h2>Where?</h2><p>...</p>"
                "</body></html>")
        page = _page(html, url="https://example.com/info")
        reco = _of_type(analyze_pages_schema([page]), SCHEMA_MISSING)[0].recommendation
        assert "FAQPage" in reco


# --- Validate: broken JSON ------------------------------------------------

class TestInvalidJson:
    def test_broken_json_flagged(self):
        # Trailing comma — invalid JSON.
        html = '<html><body><script type="application/ld+json">{"@type": "Article",}</script></body></html>'
        page = _page(html)
        assert SCHEMA_INVALID_JSON in _types(analyze_pages_schema([page]))

    def test_single_quotes_flagged(self):
        html = "<html><body><script type=\"application/ld+json\">{'@type': 'Article'}</script></body></html>"
        page = _page(html)
        assert SCHEMA_INVALID_JSON in _types(analyze_pages_schema([page]))

    def test_empty_block_flagged(self):
        html = '<html><body><script type="application/ld+json"></script></body></html>'
        page = _page(html)
        assert SCHEMA_INVALID_JSON in _types(analyze_pages_schema([page]))

    def test_valid_json_not_flagged(self):
        page = _page(f"<html><body>{_ld(_VALID_ARTICLE)}</body></html>")
        assert SCHEMA_INVALID_JSON not in _types(analyze_pages_schema([page]))

    def test_severity_is_high(self):
        html = '<html><body><script type="application/ld+json">not json</script></body></html>'
        issues = _of_type(analyze_pages_schema([_page(html)]), SCHEMA_INVALID_JSON)
        assert issues and issues[0].severity == SEVERITY_HIGH


# --- Validate: missing @context / @type -----------------------------------

class TestMissingContextAndType:
    def test_missing_context_flagged(self):
        page = _page(f"<html><body>{_ld({'@type': 'Article'})}</body></html>")
        assert SCHEMA_MISSING_CONTEXT in _types(analyze_pages_schema([page]))

    def test_non_schema_org_context_flagged(self):
        obj = {"@context": "https://example.org/ns", "@type": "Article"}
        page = _page(f"<html><body>{_ld(obj)}</body></html>")
        assert SCHEMA_MISSING_CONTEXT in _types(analyze_pages_schema([page]))

    def test_missing_type_flagged(self):
        obj = {"@context": "https://schema.org", "headline": "x"}
        page = _page(f"<html><body>{_ld(obj)}</body></html>")
        assert SCHEMA_MISSING_TYPE in _types(analyze_pages_schema([page]))

    def test_complete_object_clean(self):
        page = _page(f"<html><body>{_ld(_VALID_ARTICLE)}</body></html>")
        types = _types(analyze_pages_schema([page]))
        assert SCHEMA_MISSING_CONTEXT not in types
        assert SCHEMA_MISSING_TYPE not in types
        assert SCHEMA_MISSING not in types

    def test_context_and_type_are_low_severity(self):
        page = _page(f"<html><body>{_ld({'headline': 'x'})}</body></html>")
        issues = analyze_pages_schema([page])
        for t in (SCHEMA_MISSING_CONTEXT, SCHEMA_MISSING_TYPE):
            matched = _of_type(issues, t)
            assert matched and matched[0].severity == SEVERITY_LOW


# --- Graph / list payloads ------------------------------------------------

class TestPayloadShapes:
    def test_list_of_objects_each_validated(self):
        # A list: one valid, one missing @type.
        payload = [_VALID_ARTICLE, {"@context": "https://schema.org"}]
        html = f'<html><body><script type="application/ld+json">{json.dumps(payload)}</script></body></html>'
        assert SCHEMA_MISSING_TYPE in _types(analyze_pages_schema([_page(html)]))

    def test_graph_wrapper_supported(self):
        payload = {"@context": "https://schema.org",
                   "@graph": [{"@type": "Article", "@context": "https://schema.org"}]}
        html = f'<html><body><script type="application/ld+json">{json.dumps(payload)}</script></body></html>'
        # Fully valid graph -> no validation issues.
        types = _types(analyze_pages_schema([_page(html)]))
        assert SCHEMA_INVALID_JSON not in types
        assert SCHEMA_MISSING not in types


# --- General behaviour -----------------------------------------------------

class TestGeneralBehaviour:
    def test_non_ok_page_skipped(self):
        page = _page("<html><body></body></html>", status=404)
        assert analyze_pages_schema([page]) == []

    def test_page_without_html_skipped(self):
        page = PageResult(url="https://example.com/", status_code=200,
                          response_time=0.1, html=None)
        assert analyze_pages_schema([page]) == []
