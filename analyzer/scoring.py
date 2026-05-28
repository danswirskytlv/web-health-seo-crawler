"""
scoring.py
==========

Compute an overall Website Health Score (0-100) from a list of Issues.

Algorithm (matches the project plan exactly):
    Start at 100.
    Subtract for each issue:
        High   -> 10 points
        Medium ->  5 points
        Low    ->  2 points
    Floor at 0.

Grade bands:
    90-100 : Excellent
    75-89  : Good
    50-74  : Needs Improvement
     0-49  : Critical

Keeping scoring simple and explainable is intentional — the user must be
able to point at the dashboard and say "I lost 15 points because of these
3 high-severity issues."  A black-box ML model would make demoing the
scoring meaningless.
"""

from __future__ import annotations

from models.result_models import (
    Issue,
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


# --- Public API -----------------------------------------------------------

def calculate_score(issues: list[Issue]) -> ScoreResult:
    """
    Given a list of detected issues, compute the site's health score.

    The result includes per-severity counts so the UI can display
    "3 High / 5 Medium / 8 Low" alongside the headline number.
    """
    high = sum(1 for i in issues if i.severity == SEVERITY_HIGH)
    medium = sum(1 for i in issues if i.severity == SEVERITY_MEDIUM)
    low = sum(1 for i in issues if i.severity == SEVERITY_LOW)

    penalty = (
        high * POINTS_PER_HIGH
        + medium * POINTS_PER_MEDIUM
        + low * POINTS_PER_LOW
    )
    raw_score = INITIAL_SCORE - penalty

    # Clamp to [MIN_SCORE, INITIAL_SCORE].
    score = max(MIN_SCORE, min(INITIAL_SCORE, raw_score))

    return ScoreResult(
        score=score,
        grade=_grade_for(score),
        high_count=high,
        medium_count=medium,
        low_count=low,
    )
