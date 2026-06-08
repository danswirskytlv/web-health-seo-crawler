"""
scoring.py
==========

Compute a Website Health Score (0-100) from the issues found on a site.

Hybrid per-page model
----------------------
The original model summed a flat penalty across the *whole* site and floored
at 0. With six audit categories now active, that made almost every real site
pin to 0 — every broken site looked identical. The current model spreads
scores across the full 0-100 range while staying explainable:

    For each page:
        penalty   = 10*High + 5*Medium + 2*Low   (that page's issues)
        penalty   = min(penalty, 100)            (a page can lose at most 100)
        page_score = 100 - penalty               (so it floors at 0)
    overall_score = average(page_score over all pages)

A page with no issues scores 100, so a large site with a few clean pages
stays well above 0 even if one page is a disaster. The "points lost" idea is
still explainable per page.

Per-category sub-scores
-----------------------
The same method, restricted to one category's issues at a time, yields a
0-100 sub-score per category (SEO, Accessibility, Performance, Security,
Schema). A category with no issues on the site scores 100.

Grade bands (applied to the overall score):
    90-100 : Excellent
    75-89  : Good
    50-74  : Needs Improvement
     0-49  : Critical

When no pages are supplied, the function falls back to treating all issues as
belonging to a single page — handy for quick checks and unit tests.
"""

from __future__ import annotations

from typing import Optional

from models.result_models import (
    Issue,
    PageResult,
    ScoreResult,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)

# --- Tunable weights ------------------------------------------------------

POINTS_PER_HIGH = 10
POINTS_PER_MEDIUM = 5
POINTS_PER_LOW = 2

INITIAL_SCORE = 100
MIN_SCORE = 0

# A single page can lose at most this many points, so one catastrophic page
# can't drag the averaged site score below its fair share.
MAX_PAGE_PENALTY = 100


# --- Grade bands ----------------------------------------------------------

# Inclusive lower bound, label.
# Ordered from highest to lowest because we scan top-down.
_GRADE_BANDS: list[tuple[int, str]] = [
    (90, "Excellent"),
    (75, "Good"),
    (50, "Needs Improvement"),
    (0, "Critical"),
]


def _grade_for(score: int) -> str:
    """Return the human-readable grade label for `score`."""
    for threshold, label in _GRADE_BANDS:
        if score >= threshold:
            return label
    # Shouldn't happen — the last band starts at 0 — but be defensive.
    return "Critical"


# --- Penalty helpers ------------------------------------------------------

def _issue_penalty(issue: Issue) -> int:
    """Points a single issue costs, by severity."""
    if issue.severity == SEVERITY_HIGH:
        return POINTS_PER_HIGH
    if issue.severity == SEVERITY_MEDIUM:
        return POINTS_PER_MEDIUM
    return POINTS_PER_LOW


def _page_score(page_issues: list[Issue]) -> int:
    """Score for one page: 100 minus its capped penalty, floored at 0."""
    penalty = sum(_issue_penalty(i) for i in page_issues)
    penalty = min(penalty, MAX_PAGE_PENALTY)
    return max(MIN_SCORE, INITIAL_SCORE - penalty)


def _average_page_score(
    issues: list[Issue],
    page_urls: list[str],
) -> int:
    """
    Average per-page score across the given page URLs.

    `issues` are grouped by their `url`; every page in `page_urls` counts,
    so clean pages (no issues) contribute a perfect 100 and lift the average.
    """
    if not page_urls:
        # No page list: treat all issues as one page (fallback / tests).
        return _page_score(issues)

    by_url: dict[str, list[Issue]] = {url: [] for url in page_urls}
    for issue in issues:
        # Issues on URLs we don't know about still count, under their own key.
        by_url.setdefault(issue.url, []).append(issue)

    scores = [_page_score(group) for group in by_url.values()]
    return round(sum(scores) / len(scores))


# --- Public API -----------------------------------------------------------

def calculate_score(
    issues: list[Issue],
    pages: Optional[list[PageResult]] = None,
) -> ScoreResult:
    """
    Compute the site's health score and per-category sub-scores.

    Parameters
    ----------
    issues : list[Issue]
        Every issue detected across the site.
    pages : list[PageResult], optional
        The crawled pages. When supplied, scoring averages per-page scores
        (the recommended path). When omitted, all issues are treated as a
        single page — useful for quick checks and unit tests.

    The result includes per-severity counts (for the dashboard breakdown) and
    a category_scores dict mapping each audit category to its 0-100 sub-score.
    """
    high = sum(1 for i in issues if i.severity == SEVERITY_HIGH)
    medium = sum(1 for i in issues if i.severity == SEVERITY_MEDIUM)
    low = sum(1 for i in issues if i.severity == SEVERITY_LOW)

    # Build the list of page URLs to average over. Without pages we fall back
    # to whatever URLs the issues mention (or a single synthetic page).
    if pages is not None:
        page_urls = [p.url for p in pages]
    else:
        page_urls = []

    overall = _average_page_score(issues, page_urls)

    # Per-category sub-scores: same averaging, restricted to one category.
    categories = sorted({i.category for i in issues})
    category_scores: dict[str, int] = {}
    for category in categories:
        cat_issues = [i for i in issues if i.category == category]
        category_scores[category] = _average_page_score(cat_issues, page_urls)

    return ScoreResult(
        score=overall,
        grade=_grade_for(overall),
        high_count=high,
        medium_count=medium,
        low_count=low,
        category_scores=category_scores,
    )
