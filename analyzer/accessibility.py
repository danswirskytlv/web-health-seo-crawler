"""
accessibility.py
================

Rule-based accessibility (WCAG) checks.

Same shape as the SEO analyzer: every check is a small private function
that takes a parsed page and returns 0 or more Issues. `analyze_pages_a11y`
runs all the checks across all pages.

Why a separate module?
----------------------
- It keeps the SEO analyzer focused and unchanged (zero risk of regression
  in the 100 existing tests).
- It makes the "category" dimension real: SEO issues come from one analyzer,
  Accessibility issues come from another. The UI can group, filter, and
  score them independently.
- It scales: stages 10, 11, 12 will add three more analyzers
  (performance, security, schema) with exactly this shape.

Why these specific checks?
--------------------------
We picked the 7 issues that:
  1. Are deterministically detectable from raw HTML (no JS execution needed)
  2. Appear in the top WCAG 2.1 AA violations list
  3. Give the user something concrete to do — vague checks are useless

What we deliberately don't check
--------------------------------
- Dynamic content (AJAX-loaded forms etc.) — needs a real browser
- Color contrast — requires CSS computation; we add a basic inline-style
  check but full contrast analysis is out of scope for a static crawler
- Keyboard navigation — needs runtime simulation
These are exactly the gaps a tool like axe-core fills, and we acknowledge
them up front rather than producing false-confidence reports.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from models.result_models import (
    CATEGORY_ACCESSIBILITY,
    Issue,
    PageResult,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)

# --- Issue type names -----------------------------------------------------

A11Y_MISSING_LANG = "Missing HTML Language"
A11Y_MISSING_VIEWPORT = "Missing Viewport Meta"
A11Y_INPUT_WITHOUT_LABEL = "Form Input Without Label"
A11Y_GENERIC_LINK_TEXT = "Generic Link Text"
A11Y_SKIPPED_HEADING_LEVEL = "Skipped Heading Level"
A11Y_BUTTON_WITHOUT_TEXT = "Button or Link Without Accessible Text"
A11Y_LOW_CONTRAST_INLINE = "Low Color Contrast (Inline Style)"

# Phrases that are commonly used as link text but don't describe the
# destination. Screen-reader users hear the link text out of context.
GENERIC_LINK_PHRASES = {
    "click here", "read more", "learn more", "more", "here",
    "this", "this link", "link", "go", "info", "details",
}


# --- Helpers --------------------------------------------------------------

def _build_issue(
    page: PageResult,
    issue_type: str,
    severity: str,
    description: str,
    recommendation: str,
) -> Issue:
    """Construct an Accessibility-category Issue with page metadata copied in."""
    return Issue(
        url=page.url,
        issue_type=issue_type,
        severity=severity,
        category=CATEGORY_ACCESSIBILITY,
        description=description,
        recommendation=recommendation,
        status_code=page.status_code,
        response_time=page.response_time,
    )


# --- Individual checks ----------------------------------------------------

def _check_html_lang(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """Every page should declare its primary language on the <html> tag."""
    html_tag = soup.find("html")
    lang = html_tag.get("lang", "").strip() if html_tag else ""
    if lang:
        return []
    return [_build_issue(
        page,
        issue_type=A11Y_MISSING_LANG,
        severity=SEVERITY_MEDIUM,
        description=(
            "The <html> element does not declare a language. "
            "Screen readers use this attribute to pick the correct "
            "pronunciation and accent."
        ),
        recommendation=(
            'Add a lang attribute to the <html> element, e.g. '
            '<html lang="en"> for English or <html lang="he"> for Hebrew.'
        ),
    )]


def _check_viewport_meta(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """Mobile devices need a viewport meta tag to render readable layouts."""
    viewport_tag = soup.find("meta", attrs={"name": "viewport"})
    if viewport_tag and viewport_tag.get("content", "").strip():
        return []
    return [_build_issue(
        page,
        issue_type=A11Y_MISSING_VIEWPORT,
        severity=SEVERITY_MEDIUM,
        description=(
            "The page is missing a viewport meta tag. On mobile devices "
            "the browser will render the page at desktop width and zoom out, "
            "making it hard to read and use."
        ),
        recommendation=(
            'Add <meta name="viewport" content="width=device-width, '
            'initial-scale=1.0"> inside the <head>.'
        ),
    )]


def _check_form_inputs_have_labels(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """
    Every form input must be reachable by a label.

    Acceptable: <label for="x"><input id="x">, <input aria-label="...">,
    <input aria-labelledby="...">, or input wrapped inside its <label>.
    """
    issues: list[Issue] = []

    # Collect all <label for="..."> mappings so we can match by id.
    labeled_ids = {
        lbl.get("for", "").strip()
        for lbl in soup.find_all("label")
        if lbl.get("for", "").strip()
    }

    for inp in soup.find_all(["input", "textarea", "select"]):
        # Skip input types that don't need a visible label.
        input_type = inp.get("type", "").lower()
        if input_type in {"hidden", "submit", "button", "reset", "image"}:
            continue

        # Multiple ways to satisfy the accessibility requirement.
        has_aria_label = bool(inp.get("aria-label", "").strip())
        has_aria_labelledby = bool(inp.get("aria-labelledby", "").strip())
        has_title = bool(inp.get("title", "").strip())
        input_id = inp.get("id", "").strip()
        has_label_for = input_id and input_id in labeled_ids

        # Check if the input is wrapped inside a <label>.
        wrapped_in_label = inp.find_parent("label") is not None

        if any([has_aria_label, has_aria_labelledby, has_title,
                has_label_for, wrapped_in_label]):
            continue

        # Describe the offending input briefly for the issue message.
        descriptor = inp.get("name", "") or input_id or input_type or "input"
        issues.append(_build_issue(
            page,
            issue_type=A11Y_INPUT_WITHOUT_LABEL,
            severity=SEVERITY_HIGH,
            description=(
                f'The form control "{descriptor}" has no associated label. '
                "Screen reader users won't know what to enter."
            ),
            recommendation=(
                'Add a <label for="..."> that points at the input, or wrap '
                'the input inside a <label>, or use aria-label="...".'
            ),
        ))

    return issues


def _check_generic_link_text(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """
    Link text should describe where the link goes, not just say "click here".

    Screen-reader users often navigate by listing all links on a page; if
    they all say "click here", the list is useless.
    """
    issues: list[Issue] = []
    for anchor in soup.find_all("a", href=True):
        text = anchor.get_text(strip=True).lower()
        if not text:
            continue  # buttons-only links handled by _check_button_text
        if text in GENERIC_LINK_PHRASES:
            issues.append(_build_issue(
                page,
                issue_type=A11Y_GENERIC_LINK_TEXT,
                severity=SEVERITY_LOW,
                description=(
                    f'The link text "{anchor.get_text(strip=True)}" does not '
                    "describe its destination. Out of context, a screen reader "
                    "user has no idea where this link leads."
                ),
                recommendation=(
                    "Rewrite the link text to describe the destination — for "
                    'example, instead of "click here" use "view our pricing".'
                ),
            ))
    return issues


def _check_skipped_heading_levels(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """
    Headings should descend without skipping levels (H1 → H2 → H3, not H1 → H3).

    Skipping levels confuses screen readers and breaks document outlines.
    """
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    if not headings:
        return []

    issues: list[Issue] = []
    prev_level = 0
    for h in headings:
        level = int(h.name[1])
        # Going UP a level is always fine (e.g., H3 followed by H2 is OK).
        # Going DOWN more than one step is the problem (e.g., H2 → H4).
        if prev_level > 0 and level > prev_level + 1:
            text = h.get_text(strip=True)[:50]
            issues.append(_build_issue(
                page,
                issue_type=A11Y_SKIPPED_HEADING_LEVEL,
                severity=SEVERITY_LOW,
                description=(
                    f'Heading level jumps from <h{prev_level}> to <h{level}> '
                    f'at "{text}". This breaks the document outline that '
                    "assistive technologies rely on."
                ),
                recommendation=(
                    f"Use <h{prev_level + 1}> instead of <h{level}>, or "
                    "restructure the headings so each level only descends by one."
                ),
            ))
        prev_level = level
    return issues


def _check_button_and_link_text(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """
    Buttons and links must have an accessible name — text content, aria-label,
    or a child element (like an image) with alt text.

    Catches common patterns like icon-only buttons that have no text fallback.
    """
    issues: list[Issue] = []
    for element in soup.find_all(["button", "a"]):
        # Anchor without href is just decorative; skip it (a "button" already
        # would be flagged in its own loop iteration).
        if element.name == "a" and not element.get("href"):
            continue

        text = element.get_text(strip=True)
        has_aria_label = bool(element.get("aria-label", "").strip())
        has_aria_labelledby = bool(element.get("aria-labelledby", "").strip())
        has_title = bool(element.get("title", "").strip())

        # An <img> child with alt text also satisfies the requirement.
        img_with_alt = element.find("img", alt=True)
        has_img_alt = img_with_alt is not None and img_with_alt.get("alt", "").strip()

        if text or has_aria_label or has_aria_labelledby or has_title or has_img_alt:
            continue

        # Flag it.
        tag_name = element.name
        descriptor = element.get("href", "") if tag_name == "a" else "button"
        issues.append(_build_issue(
            page,
            issue_type=A11Y_BUTTON_WITHOUT_TEXT,
            severity=SEVERITY_HIGH,
            description=(
                f"A <{tag_name}> element ({descriptor}) has no accessible name. "
                "Screen readers will announce it as an unnamed button or link."
            ),
            recommendation=(
                "Add visible text to the element, or use aria-label=\"...\", "
                "or include an <img> child with descriptive alt text."
            ),
        ))
    return issues


def _check_inline_color_contrast(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """
    Best-effort detection of obviously low contrast in inline styles.

    A real contrast analyzer needs to compute against the rendered DOM,
    but we can spot the common case of light gray text on white background
    (e.g., color: #ccc on no background = bad). This catches lazy CSS that
    a more sophisticated tool would also catch.
    """
    issues: list[Issue] = []
    # Light hex colors that are almost always too low contrast on white.
    low_contrast_colors = {
        "#ccc", "#cccccc", "#ddd", "#dddddd", "#eee", "#eeeeee",
        "#fff", "#ffffff",  # white-on-white is the canonical disaster
    }
    for element in soup.find_all(style=True):
        style = element["style"].lower().replace(" ", "")
        # Extract a `color:` value, very loosely.
        if "color:" not in style:
            continue
        # Find every color: declaration; pick the FIRST color value seen.
        for chunk in style.split(";"):
            if not chunk.startswith("color:"):
                continue
            value = chunk.split(":", 1)[1].strip()
            if value in low_contrast_colors:
                tag_text = element.get_text(strip=True)[:40] or element.name
                issues.append(_build_issue(
                    page,
                    issue_type=A11Y_LOW_CONTRAST_INLINE,
                    severity=SEVERITY_LOW,
                    description=(
                        f'Element "{tag_text}" uses color {value} inline, '
                        "which has very low contrast against a white background."
                    ),
                    recommendation=(
                        "Use a darker text color (#666 or darker on white) or "
                        "increase the background contrast to meet WCAG AA "
                        "(at least 4.5:1 for normal text)."
                    ),
                ))
                break  # one issue per element is enough
    return issues


# --- Public API -----------------------------------------------------------

def _parse_html(page: PageResult) -> BeautifulSoup | None:
    if not page.html:
        return None
    return BeautifulSoup(page.html, "html.parser")


def analyze_pages_a11y(pages: list[PageResult]) -> list[Issue]:
    """
    Run every accessibility check on every page and return a flat list.

    Mirror of analyze_pages() in seo_analyzer.py — same input, same output
    type, just different rules. The combined `analyze_pages()` calls both.

    Like the SEO analyzer, HTML-dependent checks are skipped for non-2xx
    responses (no point flagging a 404 page for missing viewport).
    """
    issues: list[Issue] = []

    for page in pages:
        if not page.is_ok:
            continue
        soup = _parse_html(page)
        if soup is None:
            continue

        issues.extend(_check_html_lang(page, soup))
        issues.extend(_check_viewport_meta(page, soup))
        issues.extend(_check_form_inputs_have_labels(page, soup))
        issues.extend(_check_generic_link_text(page, soup))
        issues.extend(_check_skipped_heading_levels(page, soup))
        issues.extend(_check_button_and_link_text(page, soup))
        issues.extend(_check_inline_color_contrast(page, soup))

    return issues
