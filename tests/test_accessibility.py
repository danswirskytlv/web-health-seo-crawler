"""
Unit tests for analyzer.accessibility.

Mirrors the structure of test_analyzer.py: small in-memory HTML strings,
fast (<1s for the whole file), no network.
"""

from __future__ import annotations

from analyzer.accessibility import (
    A11Y_BUTTON_WITHOUT_TEXT,
    A11Y_GENERIC_LINK_TEXT,
    A11Y_INPUT_WITHOUT_LABEL,
    A11Y_LOW_CONTRAST_INLINE,
    A11Y_MISSING_LANG,
    A11Y_MISSING_VIEWPORT,
    A11Y_SKIPPED_HEADING_LEVEL,
    analyze_pages_a11y,
)
from models.result_models import (
    CATEGORY_ACCESSIBILITY,
    PageResult,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)


def _page(html: str, url: str = "http://example.com/", status: int = 200) -> PageResult:
    return PageResult(url=url, status_code=status, response_time=0.1, html=html)


def _types(issues) -> set[str]:
    return {i.issue_type for i in issues}


# --- Missing HTML lang ---------------------------------------------------

class TestMissingLang:
    def test_detected_when_no_lang(self):
        html = "<html><head></head><body></body></html>"
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_MISSING_LANG in _types(issues)

    def test_detected_when_lang_is_empty(self):
        html = '<html lang=""><head></head><body></body></html>'
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_MISSING_LANG in _types(issues)

    def test_not_detected_when_lang_set(self):
        html = '<html lang="en"><head></head><body></body></html>'
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_MISSING_LANG not in _types(issues)

    def test_severity_is_medium(self):
        html = "<html><head></head><body></body></html>"
        issues = analyze_pages_a11y([_page(html)])
        lang_issue = next(i for i in issues if i.issue_type == A11Y_MISSING_LANG)
        assert lang_issue.severity == SEVERITY_MEDIUM
        assert lang_issue.category == CATEGORY_ACCESSIBILITY


# --- Missing viewport meta -----------------------------------------------

class TestMissingViewport:
    def test_detected_when_no_viewport(self):
        html = '<html lang="en"><head></head><body></body></html>'
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_MISSING_VIEWPORT in _types(issues)

    def test_not_detected_when_viewport_present(self):
        html = ('<html lang="en"><head>'
                '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
                '</head><body></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_MISSING_VIEWPORT not in _types(issues)


# --- Form inputs without labels ------------------------------------------

class TestInputWithoutLabel:
    def test_input_without_label_flagged(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><form><input type="text" name="email"></form></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        labels = [i for i in issues if i.issue_type == A11Y_INPUT_WITHOUT_LABEL]
        assert len(labels) == 1

    def test_label_for_satisfies(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><form>'
                '<label for="email">Email</label>'
                '<input id="email" type="text" name="email">'
                '</form></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_INPUT_WITHOUT_LABEL not in _types(issues)

    def test_wrapped_label_satisfies(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><form>'
                '<label>Email<input type="text" name="email"></label>'
                '</form></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_INPUT_WITHOUT_LABEL not in _types(issues)

    def test_aria_label_satisfies(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><form>'
                '<input type="text" name="email" aria-label="Email">'
                '</form></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_INPUT_WITHOUT_LABEL not in _types(issues)

    def test_hidden_input_not_flagged(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><form>'
                '<input type="hidden" name="csrf" value="123">'
                '</form></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_INPUT_WITHOUT_LABEL not in _types(issues)

    def test_submit_button_not_flagged(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><form>'
                '<input type="submit" value="Send">'
                '</form></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_INPUT_WITHOUT_LABEL not in _types(issues)

    def test_severity_is_high(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><form><input type="text" name="email"></form></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        lbl = next(i for i in issues if i.issue_type == A11Y_INPUT_WITHOUT_LABEL)
        assert lbl.severity == SEVERITY_HIGH


# --- Generic link text ---------------------------------------------------

class TestGenericLinkText:
    def test_click_here_flagged(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><a href="/x">click here</a></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_GENERIC_LINK_TEXT in _types(issues)

    def test_read_more_flagged(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><a href="/x">Read More</a></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_GENERIC_LINK_TEXT in _types(issues)

    def test_descriptive_link_not_flagged(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><a href="/pricing">View our pricing</a></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_GENERIC_LINK_TEXT not in _types(issues)

    def test_severity_is_low(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><a href="/x">click here</a></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        gen = next(i for i in issues if i.issue_type == A11Y_GENERIC_LINK_TEXT)
        assert gen.severity == SEVERITY_LOW


# --- Skipped heading level -----------------------------------------------

class TestSkippedHeadingLevel:
    def test_h1_then_h3_flagged(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><h1>A</h1><h3>B</h3></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_SKIPPED_HEADING_LEVEL in _types(issues)

    def test_h2_then_h4_flagged(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><h2>A</h2><h4>B</h4></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_SKIPPED_HEADING_LEVEL in _types(issues)

    def test_going_back_up_is_ok(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><h1>A</h1><h2>B</h2><h3>C</h3><h2>D</h2></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_SKIPPED_HEADING_LEVEL not in _types(issues)

    def test_proper_nesting_not_flagged(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><h1>A</h1><h2>B</h2><h3>C</h3></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_SKIPPED_HEADING_LEVEL not in _types(issues)


# --- Button / link without text ------------------------------------------

class TestButtonOrLinkWithoutText:
    def test_empty_button_flagged(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><button></button></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_BUTTON_WITHOUT_TEXT in _types(issues)

    def test_button_with_aria_label_ok(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><button aria-label="Submit"></button></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_BUTTON_WITHOUT_TEXT not in _types(issues)

    def test_button_with_text_ok(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><button>Submit</button></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_BUTTON_WITHOUT_TEXT not in _types(issues)

    def test_button_with_img_alt_ok(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><button><img src="x.png" alt="Submit"></button></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_BUTTON_WITHOUT_TEXT not in _types(issues)

    def test_link_without_text_flagged(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><a href="/x"></a></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_BUTTON_WITHOUT_TEXT in _types(issues)


# --- Inline low color contrast -------------------------------------------

class TestLowContrastInline:
    def test_color_ccc_flagged(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><p style="color: #ccc;">text</p></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_LOW_CONTRAST_INLINE in _types(issues)

    def test_color_ddd_flagged(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><p style="color: #ddd;">text</p></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_LOW_CONTRAST_INLINE in _types(issues)

    def test_normal_color_not_flagged(self):
        html = ('<html lang="en"><head><meta name="viewport" content="x"></head>'
                '<body><p style="color: #333;">text</p></body></html>')
        issues = analyze_pages_a11y([_page(html)])
        assert A11Y_LOW_CONTRAST_INLINE not in _types(issues)


# --- Skip on error pages -------------------------------------------------

class TestErrorPagesSkipped:
    def test_a11y_checks_skipped_on_404(self):
        html = '<html><head></head><body>Not found</body></html>'
        issues = analyze_pages_a11y([_page(html, status=404)])
        # No checks should fire on the error page.
        assert issues == []


# --- All categories tagged correctly ------------------------------------

class TestCategoryTag:
    def test_all_issues_are_accessibility(self):
        html = ('<html><head></head><body><h1>A</h1><h3>B</h3>'
                '<button></button><a href="/x">click here</a>'
                '</body></html>')
        issues = analyze_pages_a11y([_page(html)])
        # Every issue from this module must carry the Accessibility tag.
        assert issues, "expected some issues for the test to be meaningful"
        for issue in issues:
            assert issue.category == CATEGORY_ACCESSIBILITY
