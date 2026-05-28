"""
Unit tests for analyzer.scoring.

The scoring rules are simple enough that exhaustive testing is cheap.
We cover: clean site, single-issue weights, clamping at 0 and 100,
all four grade bands, and the boundary cases between bands.
"""

from __future__ import annotations

import pytest

from analyzer.scoring import (
    INITIAL_SCORE,
    POINTS_PER_HIGH,
    POINTS_PER_LOW,
    POINTS_PER_MEDIUM,
    calculate_score,
)
from models.result_models import (
    Issue,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)


def _issue(severity: str) -> Issue:
    """Minimal Issue used only to drive the scoring math."""
    return Issue(
        url="http://x/",
        issue_type="Test",
        severity=severity,
        description="d",
        recommendation="r",
    )


# --- Clean site -----------------------------------------------------------

class TestCleanSite:
    def test_no_issues_gives_perfect_score(self):
        result = calculate_score([])
        assert result.score == 100
        assert result.grade == "Excellent"
        assert result.total_issues == 0


# --- Single-issue weights ------------------------------------------------

class TestSeverityWeights:
    def test_one_high_subtracts_10(self):
        result = calculate_score([_issue(SEVERITY_HIGH)])
        assert result.score == INITIAL_SCORE - POINTS_PER_HIGH

    def test_one_medium_subtracts_5(self):
        result = calculate_score([_issue(SEVERITY_MEDIUM)])
        assert result.score == INITIAL_SCORE - POINTS_PER_MEDIUM

    def test_one_low_subtracts_2(self):
        result = calculate_score([_issue(SEVERITY_LOW)])
        assert result.score == INITIAL_SCORE - POINTS_PER_LOW

    def test_weights_add_up(self):
        # 2H + 3M + 4L = 20 + 15 + 8 = 43 penalty -> 57
        issues = (
            [_issue(SEVERITY_HIGH)] * 2
            + [_issue(SEVERITY_MEDIUM)] * 3
            + [_issue(SEVERITY_LOW)] * 4
        )
        assert calculate_score(issues).score == 57


# --- Counts ---------------------------------------------------------------

class TestCounts:
    def test_counts_are_accurate(self):
        issues = (
            [_issue(SEVERITY_HIGH)] * 2
            + [_issue(SEVERITY_MEDIUM)] * 3
            + [_issue(SEVERITY_LOW)] * 4
        )
        result = calculate_score(issues)
        assert result.high_count == 2
        assert result.medium_count == 3
        assert result.low_count == 4
        assert result.total_issues == 9


# --- Clamping -------------------------------------------------------------

class TestClamping:
    def test_score_does_not_go_below_zero(self):
        # 20 highs -> -200 -> should clamp to 0.
        issues = [_issue(SEVERITY_HIGH)] * 20
        result = calculate_score(issues)
        assert result.score == 0
        assert result.grade == "Critical"

    def test_score_capped_at_100(self):
        # No issues -> should not exceed 100.
        assert calculate_score([]).score == 100


# --- Grade bands ----------------------------------------------------------

class TestGradeBands:
    """
    Verify the grade label for representative scores in each band, including
    the boundary scores between bands.

    Note: our weights are 10 / 5 / 2, so not every integer score is reachable —
    only scores whose penalty (100 - score) can be expressed as 10h + 5m + 2l.
    We deliberately pick reachable target scores. The boundary between bands
    is verified directly via a separate test that calls the private helper.
    """

    @pytest.mark.parametrize("score_target,expected_grade", [
        (100, "Excellent"),
        (95,  "Excellent"),
        (90,  "Excellent"),         # lower edge of Excellent
        (88,  "Good"),              # just below Excellent
        (80,  "Good"),
        (75,  "Good"),              # lower edge of Good
        (70,  "Needs Improvement"), # just below Good (reachable: 3H+8M=70, etc.)
        (60,  "Needs Improvement"),
        (50,  "Needs Improvement"), # lower edge of Needs Improvement
        (48,  "Critical"),          # just below Needs Improvement
        (10,  "Critical"),
        (0,   "Critical"),
    ])
    def test_grade_for_score(self, score_target: int, expected_grade: str):
        # Build a set of issues that produces exactly score_target.
        # Greedy decomposition (10 -> 5 -> 2) works for all reachable evens.
        penalty = 100 - score_target

        highs = penalty // POINTS_PER_HIGH
        remainder = penalty - highs * POINTS_PER_HIGH
        mediums = remainder // POINTS_PER_MEDIUM
        remainder -= mediums * POINTS_PER_MEDIUM
        lows = remainder // POINTS_PER_LOW
        remainder -= lows * POINTS_PER_LOW
        assert remainder == 0, (
            f"Test bug: chose unreachable target score {score_target} "
            f"(penalty {penalty} can't be built from 10/5/2)."
        )

        issues = (
            [_issue(SEVERITY_HIGH)] * highs
            + [_issue(SEVERITY_MEDIUM)] * mediums
            + [_issue(SEVERITY_LOW)] * lows
        )
        result = calculate_score(issues)
        assert result.score == score_target
        assert result.grade == expected_grade

    def test_exact_band_boundaries(self):
        """
        Verify the band lookup directly at every threshold and one below.

        We bypass the score-building math and call the private grading helper,
        so we can check unreachable scores too (89, 74, 49) and lock in the
        band edges precisely.
        """
        from analyzer.scoring import _grade_for

        # Upper edge of each band
        assert _grade_for(100) == "Excellent"
        assert _grade_for(90)  == "Excellent"   # lower edge
        assert _grade_for(89)  == "Good"        # one below
        assert _grade_for(75)  == "Good"        # lower edge
        assert _grade_for(74)  == "Needs Improvement"
        assert _grade_for(50)  == "Needs Improvement"
        assert _grade_for(49)  == "Critical"
        assert _grade_for(0)   == "Critical"
