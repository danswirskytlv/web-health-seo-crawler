"""
Unit tests for analyzer.scoring (hybrid per-page model).

The score is the average of per-page scores, where each page starts at 100
and loses 10/5/2 per High/Medium/Low issue (capped so a page floors at 0).
Per-category sub-scores apply the same method restricted to one category.

We cover: clean site, single-page weights, the per-page cap, averaging across
pages, clean pages lifting the average, per-category sub-scores, severity
counts, and the grade bands.
"""

from __future__ import annotations

import pytest

from analyzer.scoring import (
    INITIAL_SCORE,
    MAX_PAGE_PENALTY,
    POINTS_PER_HIGH,
    POINTS_PER_LOW,
    POINTS_PER_MEDIUM,
    calculate_score,
)
from models.result_models import (
    CATEGORY_PERFORMANCE,
    CATEGORY_SEO,
    Issue,
    PageResult,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)


def _issue(severity: str, url: str = "http://x/", category: str = CATEGORY_SEO) -> Issue:
    """Minimal Issue used only to drive the scoring math."""
    return Issue(
        url=url,
        issue_type="Test",
        severity=severity,
        category=category,
        description="d",
        recommendation="r",
    )


def _pages(*urls: str) -> list[PageResult]:
    return [PageResult(url=u, status_code=200, response_time=0.1) for u in urls]


# --- Clean site -----------------------------------------------------------

class TestCleanSite:
    def test_no_issues_no_pages_is_perfect(self):
        result = calculate_score([])
        assert result.score == 100
        assert result.grade == "Excellent"
        assert result.total_issues == 0

    def test_no_issues_with_pages_is_perfect(self):
        result = calculate_score([], _pages("http://x/", "http://x/a"))
        assert result.score == 100
        assert result.grade == "Excellent"


# --- Single-page weights (one URL) ---------------------------------------

class TestSinglePageWeights:
    def test_one_high_subtracts_10(self):
        result = calculate_score([_issue(SEVERITY_HIGH)], _pages("http://x/"))
        assert result.score == INITIAL_SCORE - POINTS_PER_HIGH

    def test_one_medium_subtracts_5(self):
        result = calculate_score([_issue(SEVERITY_MEDIUM)], _pages("http://x/"))
        assert result.score == INITIAL_SCORE - POINTS_PER_MEDIUM

    def test_one_low_subtracts_2(self):
        result = calculate_score([_issue(SEVERITY_LOW)], _pages("http://x/"))
        assert result.score == INITIAL_SCORE - POINTS_PER_LOW

    def test_weights_add_up_on_one_page(self):
        # 2H + 3M + 4L = 20 + 15 + 8 = 43 penalty -> 57 (single page).
        issues = (
            [_issue(SEVERITY_HIGH)] * 2
            + [_issue(SEVERITY_MEDIUM)] * 3
            + [_issue(SEVERITY_LOW)] * 4
        )
        assert calculate_score(issues, _pages("http://x/")).score == 57


# --- Per-page cap ---------------------------------------------------------

class TestPerPageCap:
    def test_one_page_cannot_go_below_zero(self):
        # 20 highs on one page -> penalty 200, capped at 100 -> page score 0.
        issues = [_issue(SEVERITY_HIGH)] * 20
        result = calculate_score(issues, _pages("http://x/"))
        assert result.score == 0
        assert result.grade == "Critical"

    def test_cap_constant_is_100(self):
        assert MAX_PAGE_PENALTY == 100


# --- Averaging across pages ----------------------------------------------

class TestAveraging:
    def test_average_of_two_pages(self):
        # Page A: 1 high -> 90.  Page B: clean -> 100.  Average -> 95.
        issues = [_issue(SEVERITY_HIGH, url="http://x/a")]
        result = calculate_score(issues, _pages("http://x/a", "http://x/b"))
        assert result.score == 95

    def test_clean_pages_lift_the_average(self):
        # One disastrous page (score 0) plus three clean pages -> avg 75.
        issues = [_issue(SEVERITY_HIGH, url="http://x/bad")] * 20
        pages = _pages("http://x/bad", "http://x/1", "http://x/2", "http://x/3")
        result = calculate_score(issues, pages)
        assert result.score == 75  # (0 + 100 + 100 + 100) / 4

    def test_uniformly_broken_site_scores_low(self):
        # Every page has 1 high -> every page 90 -> average 90.
        urls = [f"http://x/{i}" for i in range(5)]
        issues = [_issue(SEVERITY_HIGH, url=u) for u in urls]
        result = calculate_score(issues, _pages(*urls))
        assert result.score == 90

    def test_issue_on_unknown_url_still_counts(self):
        # An issue whose URL isn't in the page list still forms its own page.
        issues = [_issue(SEVERITY_HIGH, url="http://x/ghost")] * 10  # -> 0
        result = calculate_score(issues, _pages("http://x/clean"))  # clean -> 100
        assert result.score == 50  # (0 + 100) / 2


# --- Per-category sub-scores ----------------------------------------------

class TestCategoryScores:
    def test_sub_scores_are_per_category(self):
        # SEO: 1 high on page a -> SEO avg over {a:90, b:100} = 95.
        # Performance: 2 high on page b -> Perf avg over {a:100, b:80} = 90.
        issues = [
            _issue(SEVERITY_HIGH, url="http://x/a", category=CATEGORY_SEO),
            _issue(SEVERITY_HIGH, url="http://x/b", category=CATEGORY_PERFORMANCE),
            _issue(SEVERITY_HIGH, url="http://x/b", category=CATEGORY_PERFORMANCE),
        ]
        result = calculate_score(issues, _pages("http://x/a", "http://x/b"))
        assert result.category_scores[CATEGORY_SEO] == 95
        assert result.category_scores[CATEGORY_PERFORMANCE] == 90

    def test_category_absent_when_no_issues(self):
        # Only SEO issues -> category_scores has SEO only.
        issues = [_issue(SEVERITY_HIGH, category=CATEGORY_SEO)]
        result = calculate_score(issues, _pages("http://x/"))
        assert set(result.category_scores) == {CATEGORY_SEO}

    def test_overall_can_differ_from_each_category(self):
        # Overall mixes categories per page; sub-scores isolate them.
        issues = [
            _issue(SEVERITY_HIGH, url="http://x/a", category=CATEGORY_SEO),
            _issue(SEVERITY_HIGH, url="http://x/a", category=CATEGORY_PERFORMANCE),
        ]
        result = calculate_score(issues, _pages("http://x/a"))
        # Page a has 2 highs -> overall 80.
        assert result.score == 80
        # Each category alone has 1 high on page a -> 90.
        assert result.category_scores[CATEGORY_SEO] == 90
        assert result.category_scores[CATEGORY_PERFORMANCE] == 90


# --- Counts ---------------------------------------------------------------

class TestCounts:
    def test_counts_are_accurate(self):
        issues = (
            [_issue(SEVERITY_HIGH)] * 2
            + [_issue(SEVERITY_MEDIUM)] * 3
            + [_issue(SEVERITY_LOW)] * 4
        )
        result = calculate_score(issues, _pages("http://x/"))
        assert result.high_count == 2
        assert result.medium_count == 3
        assert result.low_count == 4
        assert result.total_issues == 9


# --- Grade bands ----------------------------------------------------------

class TestGradeBands:
    """
    Build a single page that produces exactly score_target, then verify the
    grade label. The grading helper itself is unchanged, so we keep the same
    representative scores plus the direct boundary check.
    """

    @pytest.mark.parametrize("score_target,expected_grade", [
        (100, "Excellent"),
        (95,  "Excellent"),
        (90,  "Excellent"),
        (88,  "Good"),
        (80,  "Good"),
        (75,  "Good"),
        (70,  "Needs Improvement"),
        (60,  "Needs Improvement"),
        (50,  "Needs Improvement"),
        (48,  "Critical"),
        (10,  "Critical"),
        (0,   "Critical"),
    ])
    def test_grade_for_score(self, score_target: int, expected_grade: str):
        penalty = 100 - score_target
        highs = penalty // POINTS_PER_HIGH
        remainder = penalty - highs * POINTS_PER_HIGH
        mediums = remainder // POINTS_PER_MEDIUM
        remainder -= mediums * POINTS_PER_MEDIUM
        lows = remainder // POINTS_PER_LOW
        remainder -= lows * POINTS_PER_LOW
        assert remainder == 0, (
            f"Test bug: unreachable target score {score_target}."
        )

        issues = (
            [_issue(SEVERITY_HIGH)] * highs
            + [_issue(SEVERITY_MEDIUM)] * mediums
            + [_issue(SEVERITY_LOW)] * lows
        )
        # One page so the page score equals the target exactly.
        result = calculate_score(issues, _pages("http://x/"))
        assert result.score == score_target
        assert result.grade == expected_grade

    def test_exact_band_boundaries(self):
        from analyzer.scoring import _grade_for
        assert _grade_for(100) == "Excellent"
        assert _grade_for(90)  == "Excellent"
        assert _grade_for(89)  == "Good"
        assert _grade_for(75)  == "Good"
        assert _grade_for(74)  == "Needs Improvement"
        assert _grade_for(50)  == "Needs Improvement"
        assert _grade_for(49)  == "Critical"
        assert _grade_for(0)   == "Critical"
