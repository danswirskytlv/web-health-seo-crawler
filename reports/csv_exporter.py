"""
csv_exporter.py
===============

Export scan results to CSV.

We provide two flavors so the user can pick what they actually need:

- `issues_to_csv(scan_result)` — one row per issue. This is the usual export
  an SEO specialist sends to a developer or a client.
- `pages_to_csv(scan_result)` — one row per crawled page (URL, status code,
  response time). Useful for "did the crawl reach everything?" checks.

Both return strings, not files, so the API can stream them as a download
(in-memory) without touching the filesystem.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime

from models.result_models import ScanResult


# --- Issues CSV -----------------------------------------------------------

ISSUE_COLUMNS = [
    "URL",
    "Issue Type",
    "Severity",
    "Description",
    "Recommendation",
    "HTTP Status",
    "Response Time (s)",
]


def issues_to_csv(scan: ScanResult) -> str:
    """
    Render the issues list as a CSV string.

    The header row is always included. Rows are sorted by severity
    (High -> Medium -> Low) and then by URL for stable output.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(ISSUE_COLUMNS)

    severity_order = {"High": 0, "Medium": 1, "Low": 2}
    sorted_issues = sorted(
        scan.issues,
        key=lambda i: (severity_order.get(i.severity, 9), i.url, i.issue_type),
    )

    for issue in sorted_issues:
        writer.writerow([
            issue.url,
            issue.issue_type,
            issue.severity,
            issue.description,
            issue.recommendation,
            issue.status_code if issue.status_code is not None else "",
            f"{issue.response_time:.3f}" if issue.response_time is not None else "",
        ])

    return buf.getvalue()


# --- Pages CSV ------------------------------------------------------------

PAGE_COLUMNS = [
    "URL",
    "HTTP Status",
    "Response Time (s)",
    "Outbound Links",
    "Error",
]


def pages_to_csv(scan: ScanResult) -> str:
    """Render the visited-pages list as a CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(PAGE_COLUMNS)

    for page in sorted(scan.pages, key=lambda p: p.url):
        writer.writerow([
            page.url,
            page.status_code if page.status_code is not None else "",
            f"{page.response_time:.3f}" if page.response_time is not None else "",
            len(page.links),
            page.error or "",
        ])

    return buf.getvalue()


# --- Filename helper ------------------------------------------------------

def suggested_filename(prefix: str, scan: ScanResult, extension: str = "csv") -> str:
    """
    Build a sensible default filename, e.g.
        seo-issues_localhost-8000_20260528-194512.csv

    The host is stripped of characters that some filesystems hate, so the
    filename is safe on Windows / macOS / Linux.
    """
    # Strip the scheme so we don't end up with "https://..." in the filename.
    host = scan.root_url.split("://", 1)[-1]
    safe_host = "".join(c if c.isalnum() else "-" for c in host).strip("-")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{prefix}_{safe_host}_{timestamp}.{extension}"
