"""
serializers.py
==============

Turn the backend's dataclasses into clean JSON dicts for the React frontend.

These are pure functions (no FastAPI, no I/O) so they're trivially testable.
The shapes here are the contract the frontend depends on — keep them stable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from database.db import ScanDiff, ScanSummary
    from models.result_models import Issue, ScanResult


# --- Issues ---------------------------------------------------------------

def issue_to_dict(issue: "Issue") -> dict:
    """One detected issue as JSON."""
    return {
        "url": issue.url,
        "issueType": issue.issue_type,
        "severity": issue.severity,           # "High" | "Medium" | "Low"
        "category": issue.category,
        "description": issue.description,
        "recommendation": issue.recommendation,
        "statusCode": issue.status_code,
        "responseTime": issue.response_time,
    }


# --- Score / category breakdown -------------------------------------------

def _category_scores_list(score) -> list[dict]:
    """category_scores dict -> sorted list of {category, score} for the UI."""
    if not score or not score.category_scores:
        return []
    return [
        {"category": cat, "score": val}
        for cat, val in sorted(score.category_scores.items())
    ]


# --- Full scan result -----------------------------------------------------

def scan_result_to_dict(scan: "ScanResult", scan_id: Optional[int] = None) -> dict:
    """
    A complete scan as JSON: headline metrics, score, category breakdown,
    and the full issue list. This is what the Overview + Issues screens use.
    """
    s = scan.score
    severity_counts = {"High": 0, "Medium": 0, "Low": 0}
    for i in scan.issues:
        if i.severity in severity_counts:
            severity_counts[i.severity] += 1

    return {
        "scanId": scan_id,
        "rootUrl": scan.root_url,
        "score": s.score if s else None,
        "grade": s.grade if s else None,
        "metrics": {
            "pagesScanned": scan.pages_scanned,
            "issuesFound": scan.issues_found,
            "brokenLinks": scan.broken_links,
            "averageResponseTime": scan.average_response_time,
            "highCount": severity_counts["High"],
            "mediumCount": severity_counts["Medium"],
            "lowCount": severity_counts["Low"],
        },
        "categoryScores": _category_scores_list(s),
        "issues": [issue_to_dict(i) for i in scan.issues],
    }


# --- Scan history summary -------------------------------------------------

def scan_summary_to_dict(summary: "ScanSummary") -> dict:
    """A stored scan's headline numbers (for the History list)."""
    return {
        "id": summary.id,
        "rootUrl": summary.root_url,
        "scannedAt": summary.scanned_at,
        "score": summary.score,
        "grade": summary.grade,
        "pagesCount": summary.pages_count,
        "issuesCount": summary.issues_count,
        "highCount": summary.high_count,
        "mediumCount": summary.medium_count,
        "lowCount": summary.low_count,
        "averageResponseTime": summary.avg_response_time,
    }


# --- Diff between two scans -----------------------------------------------

def diff_to_dict(diff: "ScanDiff") -> dict:
    """A scan-to-scan comparison as JSON (for the Compare view)."""
    return {
        "fromScan": scan_summary_to_dict(diff.from_scan),
        "toScan": scan_summary_to_dict(diff.to_scan),
        "scoreDelta": diff.score_delta,
        "fixedIssues": [issue_to_dict(i) for i in diff.fixed_issues],
        "newIssues": [issue_to_dict(i) for i in diff.new_issues],
        "unchangedIssues": [issue_to_dict(i) for i in diff.unchanged_issues],
    }
