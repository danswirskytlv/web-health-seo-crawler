"""
Unit tests for database.db.

Each test uses a temporary SQLite file so tests are fully isolated from
each other and from any real data the user has accumulated.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from database.db import (
    ScanDiff,
    ScanSummary,
    delete_scan,
    get_diff,
    get_scan,
    init_db,
    list_scans,
    save_scan,
)
from models.result_models import (
    CATEGORY_ACCESSIBILITY,
    CATEGORY_SEO,
    Issue,
    PageResult,
    ScanResult,
    ScoreResult,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)


# --- Fixtures -------------------------------------------------------------

@pytest.fixture
def db_path():
    """Per-test temporary database. Cleaned up afterwards."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def _make_scan(
    root_url: str = "http://localhost:8000",
    score: int = 90,
    grade: str = "Excellent",
    issues: list[Issue] | None = None,
    category_scores: dict | None = None,
) -> ScanResult:
    pages = [
        PageResult(url=root_url, status_code=200, response_time=0.1),
        PageResult(url=f"{root_url}/about", status_code=200, response_time=0.2),
    ]
    if issues is None:
        issues = [
            Issue(url=root_url, issue_type="Missing Title", severity=SEVERITY_HIGH,
                  description="no title", recommendation="add one", status_code=200),
        ]
    high = sum(1 for i in issues if i.severity == SEVERITY_HIGH)
    medium = sum(1 for i in issues if i.severity == SEVERITY_MEDIUM)
    low = sum(1 for i in issues if i.severity == SEVERITY_LOW)
    return ScanResult(
        root_url=root_url,
        pages=pages,
        issues=issues,
        score=ScoreResult(score=score, grade=grade,
                          high_count=high, medium_count=medium, low_count=low,
                          category_scores=category_scores or {}),
    )


# --- init_db -------------------------------------------------------------

class TestInitDb:
    def test_creates_database_file(self, db_path):
        # The fixture already called init_db; verify the file exists.
        assert Path(db_path).exists()

    def test_is_idempotent(self, db_path):
        # Calling init_db twice should not raise.
        init_db(db_path)
        init_db(db_path)


# --- save_scan -----------------------------------------------------------

class TestSaveScan:
    def test_returns_positive_id(self, db_path):
        sid = save_scan(_make_scan(), db_path)
        assert isinstance(sid, int)
        assert sid > 0

    def test_ids_are_unique(self, db_path):
        sid1 = save_scan(_make_scan(), db_path)
        sid2 = save_scan(_make_scan(), db_path)
        assert sid1 != sid2

    def test_rejects_scan_without_score(self, db_path):
        scan = _make_scan()
        scan.score = None
        with pytest.raises(ValueError):
            save_scan(scan, db_path)

    def test_saves_empty_issue_list(self, db_path):
        scan = _make_scan(issues=[])
        sid = save_scan(scan, db_path)
        loaded = get_scan(sid, db_path)
        assert loaded is not None
        assert loaded.issues == []


# --- list_scans ----------------------------------------------------------

class TestListScans:
    def test_returns_empty_when_db_is_empty(self, db_path):
        assert list_scans(db_path=db_path) == []

    def test_returns_summary_objects(self, db_path):
        save_scan(_make_scan(), db_path)
        result = list_scans(db_path=db_path)
        assert len(result) == 1
        assert isinstance(result[0], ScanSummary)

    def test_newest_first(self, db_path):
        save_scan(_make_scan(score=50, grade="Needs Improvement"), db_path)
        save_scan(_make_scan(score=90, grade="Excellent"), db_path)
        scans = list_scans(db_path=db_path)
        # The most recently saved scan should be first.
        assert scans[0].score == 90
        assert scans[1].score == 50

    def test_filters_by_root_url(self, db_path):
        save_scan(_make_scan(root_url="http://a.com"), db_path)
        save_scan(_make_scan(root_url="http://b.com"), db_path)
        a = list_scans(root_url="http://a.com", db_path=db_path)
        assert len(a) == 1
        assert a[0].root_url == "http://a.com"

    def test_limit_is_respected(self, db_path):
        for _ in range(5):
            save_scan(_make_scan(), db_path)
        assert len(list_scans(limit=3, db_path=db_path)) == 3


# --- get_scan ------------------------------------------------------------

class TestGetScan:
    def test_returns_none_for_missing_id(self, db_path):
        assert get_scan(9999, db_path=db_path) is None

    def test_round_trips_score(self, db_path):
        sid = save_scan(_make_scan(score=73, grade="Needs Improvement"), db_path)
        loaded = get_scan(sid, db_path)
        assert loaded is not None
        assert loaded.score.score == 73
        assert loaded.score.grade == "Needs Improvement"

    def test_round_trips_category_scores(self, db_path):
        scan = _make_scan(category_scores={"SEO": 80, "Security": 40, "Schema": 0})
        sid = save_scan(scan, db_path)
        loaded = get_scan(sid, db_path)
        assert loaded.score.category_scores == {"SEO": 80, "Security": 40, "Schema": 0}

    def test_empty_category_scores_round_trips_as_empty(self, db_path):
        # A scan saved with no sub-scores loads back with an empty dict, not None.
        sid = save_scan(_make_scan(category_scores={}), db_path)
        loaded = get_scan(sid, db_path)
        assert loaded.score.category_scores == {}

    def test_round_trips_pages(self, db_path):
        sid = save_scan(_make_scan(), db_path)
        loaded = get_scan(sid, db_path)
        assert len(loaded.pages) == 2

    def test_round_trips_issues_with_all_fields(self, db_path):
        original = Issue(
            url="http://x/a",
            issue_type="Missing H1",
            severity=SEVERITY_MEDIUM,
            description="desc",
            recommendation="rec",
            status_code=200,
            response_time=0.5,
            category=CATEGORY_ACCESSIBILITY,
        )
        scan = _make_scan(issues=[original])
        sid = save_scan(scan, db_path)
        loaded = get_scan(sid, db_path)
        assert len(loaded.issues) == 1
        r = loaded.issues[0]
        assert r.url == original.url
        assert r.issue_type == original.issue_type
        assert r.severity == original.severity
        assert r.description == original.description
        assert r.recommendation == original.recommendation
        assert r.status_code == original.status_code
        assert r.response_time == original.response_time
        assert r.category == original.category

    def test_default_category_is_seo(self, db_path):
        # Issue without explicit category should round-trip as SEO.
        sid = save_scan(_make_scan(), db_path)
        loaded = get_scan(sid, db_path)
        assert loaded.issues[0].category == CATEGORY_SEO


# --- delete_scan ---------------------------------------------------------

class TestDeleteScan:
    def test_returns_true_for_existing_scan(self, db_path):
        sid = save_scan(_make_scan(), db_path)
        assert delete_scan(sid, db_path) is True

    def test_returns_false_for_missing_scan(self, db_path):
        assert delete_scan(9999, db_path) is False

    def test_cascades_to_pages_and_issues(self, db_path):
        sid = save_scan(_make_scan(), db_path)
        delete_scan(sid, db_path)
        # The scan is gone; therefore get_scan must return None.
        assert get_scan(sid, db_path) is None

        # And listing shouldn't return it either.
        assert list_scans(db_path=db_path) == []


# --- get_diff ------------------------------------------------------------

class TestGetDiff:
    def test_returns_none_when_either_missing(self, db_path):
        sid = save_scan(_make_scan(), db_path)
        assert get_diff(sid, 9999, db_path=db_path) is None
        assert get_diff(9999, sid, db_path=db_path) is None

    def test_returns_diff_object(self, db_path):
        sid1 = save_scan(_make_scan(), db_path)
        sid2 = save_scan(_make_scan(), db_path)
        diff = get_diff(sid1, sid2, db_path=db_path)
        assert isinstance(diff, ScanDiff)

    def test_detects_fixed_issue(self, db_path):
        # Old scan has a Missing Title; new scan has fixed it.
        old = _make_scan(score=90)
        new = _make_scan(score=100, grade="Excellent", issues=[])
        sid_old = save_scan(old, db_path)
        sid_new = save_scan(new, db_path)
        diff = get_diff(sid_old, sid_new, db_path=db_path)
        assert len(diff.fixed_issues) == 1
        assert diff.fixed_issues[0].issue_type == "Missing Title"
        assert len(diff.new_issues) == 0

    def test_detects_new_issue(self, db_path):
        old = _make_scan(issues=[])
        new_issue = Issue(
            url="http://localhost:8000",
            issue_type="Missing H1",
            severity=SEVERITY_MEDIUM,
            description="d",
            recommendation="r",
        )
        new = _make_scan(score=95, issues=[new_issue])
        sid_old = save_scan(old, db_path)
        sid_new = save_scan(new, db_path)
        diff = get_diff(sid_old, sid_new, db_path=db_path)
        assert len(diff.new_issues) == 1
        assert diff.new_issues[0].issue_type == "Missing H1"
        assert len(diff.fixed_issues) == 0

    def test_detects_unchanged_issue(self, db_path):
        same_issue = Issue(
            url="http://localhost:8000",
            issue_type="Missing Title",
            severity=SEVERITY_HIGH,
            description="d",
            recommendation="r",
        )
        sid_old = save_scan(_make_scan(issues=[same_issue]), db_path)
        sid_new = save_scan(_make_scan(issues=[same_issue]), db_path)
        diff = get_diff(sid_old, sid_new, db_path=db_path)
        assert len(diff.unchanged_issues) == 1
        assert len(diff.fixed_issues) == 0
        assert len(diff.new_issues) == 0

    def test_score_delta_is_correct(self, db_path):
        sid_old = save_scan(_make_scan(score=50, grade="Needs Improvement"), db_path)
        sid_new = save_scan(_make_scan(score=85, grade="Good"), db_path)
        diff = get_diff(sid_old, sid_new, db_path=db_path)
        assert diff.score_delta == 35

    def test_summaries_are_populated(self, db_path):
        sid_old = save_scan(_make_scan(), db_path)
        sid_new = save_scan(_make_scan(), db_path)
        diff = get_diff(sid_old, sid_new, db_path=db_path)
        assert diff.from_scan.id == sid_old
        assert diff.to_scan.id == sid_new
