"""
schema_org.py
=============

Rule-based Schema.org / structured-data checks (Stage 12).

Structured data is machine-readable markup — almost always JSON-LD inside a
`<script type="application/ld+json">` tag — that tells search engines what a
page *is*: an Article, a LocalBusiness, an FAQ, a Product. When present and
valid, it unlocks "rich results" (star ratings, FAQ accordions, breadcrumbs)
in Google, which is why site owners care about it.

Like the other analyzers, this one is static: it reads the HTML the crawler
already captured. It does three things the roadmap asks for:

  Detect    — find JSON-LD blocks and read their @type.
  Validate  — flag JSON that won't parse, or that is missing @context /
              @type (the two fields every schema.org object needs).
  Recommend — when a page has no structured data at all, guess the page type
              from its URL and content and suggest the schema that fits
              (e.g. a blog post -> Article, a contact page -> Organization,
              a Q&A page -> FAQPage).

This is intentionally not a full schema.org validator (that would need the
entire type vocabulary and every property's expected shape). It catches the
mistakes that actually keep rich results from showing up, and explains them
in plain language — consistent with the rest of the project.

All issues use category="Schema" so the UI groups them under the 📐 Schema
section alongside SEO, Accessibility, Performance and Security.
"""

from __future__ import annotations

import json

from bs4 import BeautifulSoup

from models.result_models import (
    CATEGORY_SCHEMA,
    Issue,
    PageResult,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)


# --- Issue type names ----------------------------------------------------

SCHEMA_MISSING = "Missing Structured Data"
SCHEMA_INVALID_JSON = "Invalid JSON-LD Syntax"
SCHEMA_MISSING_CONTEXT = "JSON-LD Missing @context"
SCHEMA_MISSING_TYPE = "JSON-LD Missing @type"


# --- Page-type heuristics -------------------------------------------------

# Each entry: (url keywords, recommended schema @type, why).
# Checked in order; the first match wins. A page that matches nothing falls
# back to the generic "WebPage" recommendation.
_URL_TYPE_HINTS: list[tuple[tuple[str, ...], str, str]] = [
    (("blog", "article", "news", "post"), "Article",
     "Article (or BlogPosting) markup can earn a headline, author and date in "
     "search results."),
    (("faq", "questions", "help"), "FAQPage",
     "FAQPage markup can show your questions as an expandable accordion right "
     "in Google."),
    (("product", "shop", "store", "pricing", "offers", "buy"), "Product",
     "Product (with Offer) markup can show price, availability and review "
     "stars in search results."),
    (("contact", "about"), "Organization",
     "Organization (or LocalBusiness) markup ties your name, logo, address "
     "and contact details together for the knowledge panel."),
    (("event", "events", "booking"), "Event",
     "Event markup can show dates, location and ticket info directly in "
     "search results."),
    (("recipe", "recipes"), "Recipe",
     "Recipe markup can show cook time, ratings and a photo in search "
     "results."),
]


def _recommend_type(page: PageResult, soup: BeautifulSoup) -> tuple[str, str]:
    """
    Guess the most useful schema @type for a page from its URL and content.

    Returns (recommended_type, reason). Falls back to a generic WebPage
    recommendation when nothing more specific matches.
    """
    url_lower = page.url.lower()
    for keywords, schema_type, reason in _URL_TYPE_HINTS:
        if any(kw in url_lower for kw in keywords):
            return schema_type, reason

    # Content-based fallback: a page that looks like a Q&A (several question
    # marks in headings) is probably an FAQ even if the URL doesn't say so.
    question_headings = 0
    for h in soup.find_all(["h2", "h3", "h4"]):
        text = h.get_text(strip=True)
        if text.endswith("?"):
            question_headings += 1
    if question_headings >= 3:
        return ("FAQPage",
                "This page looks like a list of questions and answers; FAQPage "
                "markup can show them as an expandable accordion in Google.")

    return ("WebPage",
            "Even a generic WebPage type with a name and description helps "
            "search engines understand the page.")


# --- Helpers --------------------------------------------------------------

def _build_issue(
    page: PageResult,
    issue_type: str,
    severity: str,
    description: str,
    recommendation: str,
) -> Issue:
    """Construct a Schema-category Issue with page metadata copied in."""
    return Issue(
        url=page.url,
        issue_type=issue_type,
        severity=severity,
        category=CATEGORY_SCHEMA,
        description=description,
        recommendation=recommendation,
        status_code=page.status_code,
        response_time=page.response_time,
    )


def _parse_html(page: PageResult) -> BeautifulSoup | None:
    if not page.html:
        return None
    return BeautifulSoup(page.html, "html.parser")


def _ld_json_blocks(soup: BeautifulSoup) -> list[str]:
    """Return the raw text of every <script type="application/ld+json"> block."""
    blocks = []
    for tag in soup.find_all("script"):
        script_type = (tag.get("type") or "").strip().lower()
        if script_type == "application/ld+json":
            blocks.append(tag.string or tag.get_text() or "")
    return blocks


def _context_is_schema_org(context_value) -> bool:
    """
    True if an @context value refers to schema.org.

    @context can be a string ("https://schema.org"), or a dict / list in more
    advanced setups. We accept any of them as long as 'schema.org' appears.
    """
    return "schema.org" in json.dumps(context_value).lower()


def _iter_schema_objects(parsed):
    """
    Yield the individual schema objects from a parsed JSON-LD payload.

    JSON-LD may be a single object, a list of objects, or a {"@graph": [...]}
    wrapper. This normalises all three into a flat sequence of dicts.
    """
    if isinstance(parsed, list):
        for item in parsed:
            yield from _iter_schema_objects(item)
    elif isinstance(parsed, dict):
        if "@graph" in parsed and isinstance(parsed["@graph"], list):
            # The top-level object may itself carry @context; yield it too so a
            # missing @context on the wrapper is still caught.
            top = {k: v for k, v in parsed.items() if k != "@graph"}
            if top:
                yield top
            for item in parsed["@graph"]:
                yield from _iter_schema_objects(item)
        else:
            yield parsed


# --- Individual checks ----------------------------------------------------

def _check_page(page: PageResult, soup: BeautifulSoup) -> list[Issue]:
    """Run detect + validate + recommend on a single page."""
    blocks = _ld_json_blocks(soup)

    # --- No structured data at all -> recommend by page type. -------------
    if not blocks:
        schema_type, reason = _recommend_type(page, soup)
        return [_build_issue(
            page,
            issue_type=SCHEMA_MISSING,
            severity=SEVERITY_MEDIUM,
            description=(
                "The page has no JSON-LD structured data. Without it, search "
                "engines can't show rich results (ratings, FAQs, breadcrumbs) "
                "for this page."
            ),
            recommendation=(
                f"Add a <script type=\"application/ld+json\"> block. Based on "
                f"this page, a good starting type is \"{schema_type}\". {reason}"
            ),
        )]

    # --- Structured data exists -> validate each block. -------------------
    issues: list[Issue] = []
    for raw in blocks:
        raw_stripped = (raw or "").strip()
        if not raw_stripped:
            # An empty ld+json block is effectively broken markup.
            issues.append(_build_issue(
                page,
                issue_type=SCHEMA_INVALID_JSON,
                severity=SEVERITY_HIGH,
                description=(
                    "A <script type=\"application/ld+json\"> block is empty. "
                    "Search engines will ignore it."
                ),
                recommendation=(
                    "Populate the block with a valid JSON-LD object, or remove "
                    "the empty tag."
                ),
            ))
            continue

        try:
            parsed = json.loads(raw_stripped)
        except (ValueError, TypeError) as exc:
            issues.append(_build_issue(
                page,
                issue_type=SCHEMA_INVALID_JSON,
                severity=SEVERITY_HIGH,
                description=(
                    f"A JSON-LD block does not parse as valid JSON ({exc}). "
                    "Browsers stay silent about this, but search engines simply "
                    "discard the markup."
                ),
                recommendation=(
                    "Fix the JSON syntax (common culprits: trailing commas, "
                    "single quotes, unescaped characters). Validate with "
                    "Google's Rich Results Test."
                ),
            ))
            continue

        # Valid JSON — now check the schema.org essentials on each object.
        for obj in _iter_schema_objects(parsed):
            if not isinstance(obj, dict):
                continue
            if "@context" not in obj:
                issues.append(_build_issue(
                    page,
                    issue_type=SCHEMA_MISSING_CONTEXT,
                    severity=SEVERITY_LOW,
                    description=(
                        "A JSON-LD object is missing the @context field, so "
                        "search engines don't know it follows the schema.org "
                        "vocabulary."
                    ),
                    recommendation=(
                        'Add "@context": "https://schema.org" to the JSON-LD '
                        "object."
                    ),
                ))
            elif not _context_is_schema_org(obj["@context"]):
                issues.append(_build_issue(
                    page,
                    issue_type=SCHEMA_MISSING_CONTEXT,
                    severity=SEVERITY_LOW,
                    description=(
                        "A JSON-LD object's @context does not reference "
                        "schema.org, so search engines may not recognise its "
                        "types."
                    ),
                    recommendation=(
                        'Set "@context": "https://schema.org" (this is what '
                        "Google's rich results expect)."
                    ),
                ))

            if "@type" not in obj:
                issues.append(_build_issue(
                    page,
                    issue_type=SCHEMA_MISSING_TYPE,
                    severity=SEVERITY_LOW,
                    description=(
                        "A JSON-LD object is missing the @type field, so search "
                        "engines don't know what kind of thing it describes."
                    ),
                    recommendation=(
                        'Add an "@type" (for example "Article", "Product" or '
                        '"Organization") to the JSON-LD object.'
                    ),
                ))

    return issues


# --- Public API -----------------------------------------------------------

def analyze_pages_schema(pages: list[PageResult]) -> list[Issue]:
    """
    Run every structured-data check on every page and return a flat list.

    Mirrors the other analyzers: same input, same output type, independent
    module. Only successfully-loaded (2xx) HTML pages are inspected.
    """
    issues: list[Issue] = []

    for page in pages:
        if not page.is_ok:
            continue
        soup = _parse_html(page)
        if soup is None:
            continue
        issues.extend(_check_page(page, soup))

    return issues
