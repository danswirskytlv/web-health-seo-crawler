"""
Unit tests for reports.csv_exporter and reports.pdf_exporter.
"""

from __future__ import annotations

import csv
import io

from models.result_models import (
    Issue,
    PageResult,
    ScanResult,
    ScoreResult,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)
from reports.csv_exporter import (
    ISSUE_COLUMNS,
    PAGE_COLUMNS,
    issues_to_csv,
    pages_to_csv,
    suggested_filename,
)
from reports.pdf_exporter import scan_to_pdf


# --- Test fixtures --------------------------------------------------------

def _make_scan() -> ScanResult:
    pages = [
        PageResult(url="http://x/", status_code=200, response_time=0.1, html="<html></html>"),
        PageResult(url="http://x/a", status_code=200, response_time=0.2, html="<html></html>"),
        PageResult(url="http://x/broken", status_code=404, response_time=0.01, html=None),
    ]
    issues = [
        Issue(url="http://x/", issue_type="Missing Title", severity=SEVERITY_HIGH,
              description="no title", recommendation="add one", status_code=200),
        Issue(url="http://x/a", issue_type="Missing H1", severity=SEVERITY_MEDIUM,
              description="no h1", recommendation="add one", status_code=200),
        Issue(url="http://x/a", issue_type="Image Missing Alt", severity=SEVERITY_LOW,
              description="no alt", recommendation="add alt", status_code=200),
        Issue(url="http://x/broken", issue_type="Broken Link", severity=SEVERITY_HIGH,
              description="404", recommendation="fix or remove", status_code=404),
    ]
    score = ScoreResult(
        score=100 - 10 - 10 - 5 - 2,  # = 73
        grade="Needs Improvement",
        high_count=2, medium_count=1, low_count=1,
    )
    return ScanResult(root_url="http://x", pages=pages, issues=issues, score=score)


# --- issues_to_csv -------------------------------------------------------

class TestIssuesToCsv:
    def test_header_row_matches_schema(self):
        scan = _make_scan()
        csv_str = issues_to_csv(scan)
        reader = csv.reader(io.StringIO(csv_str))
        header = next(reader)
        assert header == ISSUE_COLUMNS

    def test_one_row_per_issue(self):
        scan = _make_scan()
        rows = list(csv.reader(io.StringIO(issues_to_csv(scan))))
        # 4 issues + 1 header
        assert len(rows) == 5

    def test_severity_order_high_first(self):
        scan = _make_scan()
        rows = list(csv.reader(io.StringIO(issues_to_csv(scan))))
        # Index 0 is header, index 1 and 2 should both be High.
        assert rows[1][2] == SEVERITY_HIGH
        assert rows[2][2] == SEVERITY_HIGH
        assert rows[-1][2] == SEVERITY_LOW

    def test_empty_scan_still_produces_header(self):
        empty = ScanResult(root_url="http://x", pages=[], issues=[],
                           score=ScoreResult(score=100, grade="Excellent"))
        rows = list(csv.reader(io.StringIO(issues_to_csv(empty))))
        assert rows == [ISSUE_COLUMNS]


# --- pages_to_csv --------------------------------------------------------

class TestPagesToCsv:
    def test_header_row_matches_schema(self):
        scan = _make_scan()
        rows = list(csv.reader(io.StringIO(pages_to_csv(scan))))
        assert rows[0] == PAGE_COLUMNS

    def test_one_row_per_page(self):
        scan = _make_scan()
        rows = list(csv.reader(io.StringIO(pages_to_csv(scan))))
        assert len(rows) == 1 + len(scan.pages)

    def test_status_code_present(self):
        scan = _make_scan()
        rows = list(csv.reader(io.StringIO(pages_to_csv(scan))))
        # Look for the row with the broken page.
        broken_rows = [r for r in rows[1:] if r[0] == "http://x/broken"]
        assert len(broken_rows) == 1
        assert broken_rows[0][1] == "404"


# --- suggested_filename --------------------------------------------------

class TestSuggestedFilename:
    def test_includes_prefix(self):
        scan = _make_scan()
        fn = suggested_filename("seo-issues", scan)
        assert fn.startswith("seo-issues_")

    def test_no_slashes_in_host_part(self):
        # The host should be sanitized so the file is safe on all OSes.
        scan = ScanResult(root_url="https://example.com/path", pages=[], issues=[])
        fn = suggested_filename("x", scan)
        assert "/" not in fn

    def test_extension(self):
        scan = _make_scan()
        assert suggested_filename("x", scan, "pdf").endswith(".pdf")
        assert suggested_filename("x", scan, "csv").endswith(".csv")


# --- scan_to_pdf ---------------------------------------------------------

class TestScanToPdf:
    def test_returns_valid_pdf_bytes(self):
        scan = _make_scan()
        pdf = scan_to_pdf(scan)
        assert isinstance(pdf, bytes)
        # Every PDF starts with the magic header "%PDF".
        assert pdf.startswith(b"%PDF")

    def test_clean_site_pdf_does_not_crash(self):
        empty = ScanResult(
            root_url="http://x", pages=[], issues=[],
            score=ScoreResult(score=100, grade="Excellent"),
        )
        pdf = scan_to_pdf(empty)
        assert pdf.startswith(b"%PDF")
