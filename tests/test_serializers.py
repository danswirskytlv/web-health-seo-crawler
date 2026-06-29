"""
Tests for api.serializers — the JSON shapes the React frontend depends on,
plus the issue de-duplication that keeps the Issues board readable on real
sites. Pure functions, no network, no FastAPI.
"""

from __future__ import annotations

from api.serializers import (
    dedupe_issues,
    diff_to_dict,
    issue_to_dict,
    scan_result_to_dict,
    scan_summary_to_dict,
)
from database.db import ScanDiff, ScanSummary
from models.result_models import (
    CATEGORY_SEO,
    CATEGORY_SECURITY_HEADERS,
    Issue,
    PageResult,
    ScanResult,
    ScoreResult,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)


def _issue(url, t="Image Missing Alt", sev=SEVERITY_LOW, cat=CATEGORY_SEO, desc="img has no alt"):
    return Issue(url=url, issue_type=t, severity=sev, category=cat,
                 description=desc, recommendation="add alt", status_code=200)


def _scan(issues, score=80):
    return ScanResult(
        root_url="https://x/",
        pages=[PageResult(url="https://x/", status_code=200, response_time=0.1)],
        issues=issues,
        score=ScoreResult(score=score, grade="Good", high_count=0,
                          medium_count=0, low_count=len(issues)),
    )


# --- issue_to_dict --------------------------------------------------------

class TestIssueToDict:
    def test_fields_mapped(self):
        d = issue_to_dict(_issue("https://x/a"))
        assert d["url"] == "https://x/a"
        assert d["issueType"] == "Image Missing Alt"
        assert d["severity"] == "Low"
        assert d["statusCode"] == 200


# --- de-duplication -------------------------------------------------------

class TestDedupe:
    def test_identical_issues_collapse(self):
        issues = [_issue(f"https://x/p{i}") for i in range(12)]
        ded = dedupe_issues(issues)
        assert len(ded) == 1
        assert ded[0]["affectedPages"] == 12

    def test_distinct_issue_types_not_merged(self):
        issues = [
            _issue("https://x/a", t="Missing Title"),
            _issue("https://x/b", t="Image Missing Alt"),
        ]
        assert len(dedupe_issues(issues)) == 2

    def test_same_type_different_description_not_merged(self):
        # Different descriptions => genuinely different findings.
        issues = [
            _issue("https://x/a", desc="desc one"),
            _issue("https://x/b", desc="desc two"),
        ]
        assert len(dedupe_issues(issues)) == 2

    def test_affected_urls_capped(self):
        issues = [_issue(f"https://x/p{i}") for i in range(50)]
        ded = dedupe_issues(issues)
        assert ded[0]["affectedPages"] == 50
        assert len(ded[0]["affectedUrls"]) == 20  # sample capped

    def test_first_seen_order_preserved(self):
        issues = [
            _issue("https://x/a", t="Missing Title"),
            _issue("https://x/b", t="Missing H1"),
        ]
        ded = dedupe_issues(issues)
        assert ded[0]["issueType"] == "Missing Title"
        assert ded[1]["issueType"] == "Missing H1"

    def test_empty(self):
        assert dedupe_issues([]) == []

    def test_many_images_on_one_page_grouped(self):
        # >3 alt-less images on one page -> a single grouped row for that page.
        issues = [
            _issue("https://x/products", t="Image Missing Alt",
                   desc=f'An image (<img src="img{i}.jpg">) is missing alt text.')
            for i in range(7)
        ]
        ded = dedupe_issues(issues)
        assert len(ded) == 1
        assert ded[0]["groupedCount"] == 7
        assert "7 images need alt text" in ded[0]["description"]

    def test_three_images_stay_separate(self):
        # Exactly 3 (== threshold) should NOT group — kept specific.
        issues = [
            _issue("https://x/a", t="Image Missing Alt",
                   desc=f'An image (<img src="i{i}.jpg">) is missing alt text.')
            for i in range(3)
        ]
        assert len(dedupe_issues(issues)) == 3

    def test_grouping_is_per_page_not_site_wide(self):
        # 5 on page A (grouped), 5 on page B (grouped) -> 2 rows, not 1.
        a = [_issue("https://x/a", t="Image Missing Alt",
                    desc=f'img a{i}') for i in range(5)]
        b = [_issue("https://x/b", t="Image Missing Alt",
                    desc=f'img b{i}') for i in range(5)]
        ded = dedupe_issues(a + b)
        grouped = [d for d in ded if d.get("groupedCount")]
        assert len(grouped) == 2
        assert {d["url"] for d in grouped} == {"https://x/a", "https://x/b"}

    def test_site_wide_issue_with_same_description_dedupes(self):
        # A site-wide issue (e.g. "no HTTPS") uses a page-agnostic description,
        # so the SAME issue on many pages collapses into one row. This guards
        # against accidentally re-embedding the per-page URL in the description.
        desc = "The site is served over plain HTTP instead of HTTPS."
        issues = [
            _issue(f"http://x/p{i}.html", t="Site Not Served Over HTTPS",
                   sev=SEVERITY_HIGH, cat=CATEGORY_SECURITY_HEADERS, desc=desc)
            for i in range(8)
        ]
        ded = dedupe_issues(issues)
        assert len(ded) == 1
        assert ded[0]["affectedPages"] == 8


# --- scan_result_to_dict --------------------------------------------------

class TestScanResultToDict:
    def test_raw_count_preserved_display_deduped(self):
        # 13 raw issues (12 identical + 1) -> 2 display rows, but issuesFound=13.
        issues = [_issue(f"https://x/p{i}") for i in range(12)]
        issues.append(_issue("https://x/about", t="Missing H1", sev=SEVERITY_MEDIUM, desc="no h1"))
        d = scan_result_to_dict(_scan(issues), scan_id=5)
        assert d["scanId"] == 5
        assert d["metrics"]["issuesFound"] == 13   # raw, for scoring/headline
        assert len(d["issues"]) == 2               # deduped, for display
        assert d["uniqueIssueCount"] == 2

    def test_severity_counts_use_raw_issues(self):
        issues = [_issue(f"https://x/p{i}", sev=SEVERITY_LOW) for i in range(5)]
        d = scan_result_to_dict(_scan(issues))
        assert d["metrics"]["lowCount"] == 5  # not collapsed

    def test_category_scores_serialized(self):
        sr = _scan([_issue("https://x/a")])
        sr.score.category_scores = {"SEO": 90, "Security Headers": 80}
        d = scan_result_to_dict(sr)
        assert {"category": "SEO", "score": 90} in d["categoryScores"]


# --- summaries + diff -----------------------------------------------------

class TestSummaryAndDiff:
    def _summary(self, score, sid=1):
        return ScanSummary(id=sid, root_url="https://x/", scanned_at="2026-06-08",
                           score=score, grade="Good", pages_count=5, issues_count=2,
                           high_count=1, medium_count=1, low_count=0, avg_response_time=0.3)

    def test_summary_shape(self):
        d = scan_summary_to_dict(self._summary(72))
        assert d["score"] == 72 and d["scannedAt"] == "2026-06-08"

    def test_diff_shape(self):
        diff = ScanDiff(
            from_scan=self._summary(80, 1),
            to_scan=self._summary(60, 2),
            fixed_issues=[_issue("https://x/a", t="Missing Title")],
            new_issues=[_issue("https://x/b", t="Missing H1")],
            unchanged_issues=[],
            score_delta=-20,
        )
        d = diff_to_dict(diff)
        assert d["scoreDelta"] == -20
        assert len(d["fixedIssues"]) == 1 and len(d["newIssues"]) == 1
