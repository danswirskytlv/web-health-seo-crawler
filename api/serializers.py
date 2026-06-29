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
        # Optional structured payload (e.g. the 404 note's full URL list).
        "details": getattr(issue, "details", None),
    }


# --- Issue de-duplication (display layer) ---------------------------------

# When a single page has more than this many of the same issue type (e.g. lots
# of alt-less images), collapse them into one summary row for that page.
PER_PAGE_GROUP_THRESHOLD = 3


def _group_per_page(issues) -> list:
    """
    Collapse repeated same-type issues ON THE SAME PAGE into one summary issue.

    Example: a /products page with 12 images missing alt text becomes a single
    "12 images on this page need alt text" entry, instead of 12 rows. Only
    triggers when a page has MORE than PER_PAGE_GROUP_THRESHOLD of that type;
    pages with a few keep their individual rows so small cases stay specific.

    Returns a mixed list of original Issue objects and synthetic dicts (the
    grouped summaries carry their own pre-built dict).
    """
    # Bucket by (url, issue_type).
    buckets: dict = {}
    order: list = []
    for i in issues:
        key = (i.url, i.issue_type)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(i)

    out: list = []
    for key in order:
        group = buckets[key]
        if len(group) > PER_PAGE_GROUP_THRESHOLD:
            rep = group[0]
            noun = _group_noun(rep.issue_type, len(group))
            d = issue_to_dict(rep)
            d["description"] = (
                f"{len(group)} {noun} on this page. {rep.description}"
            )
            d["affectedPages"] = 1
            d["affectedUrls"] = [rep.url]
            d["groupedCount"] = len(group)  # how many instances on this page
            d["_grouped"] = True
            out.append(d)
        else:
            out.extend(group)
    return out


def _group_noun(issue_type: str, count: int) -> str:
    """A human phrase for a grouped page-level summary."""
    plural = {
        "Image Missing Alt": "images need alt text",
        "Form Input Without Label": "form fields are missing labels",
        "Generic Link Text": "links use vague text",
        "Skipped Heading Level": "headings skip levels",
    }.get(issue_type)
    if plural:
        return plural
    return f"instances of “{issue_type}”"


def dedupe_issues(issues) -> list[dict]:
    """
    Build the display issue list with two passes of grouping:

    1. PER-PAGE: many of the same issue on one page (e.g. 12 alt-less images)
       become one summary row for that page (see _group_per_page).
    2. CROSS-PAGE: identical issues that differ only by URL (same type +
       description across pages) collapse into one row with an "affectedPages"
       count.

    Purely a DISPLAY concern — scoring still uses the raw issue list.
    """
    pre = _group_per_page(issues)

    groups: dict = {}
    order: list = []
    for item in pre:
        if isinstance(item, dict):
            # Already-grouped per-page summary — pass it through as-is.
            order.append(id(item))
            groups[id(item)] = {"dict": item}
            continue
        i = item
        key = (i.issue_type, i.category, i.severity, i.description)
        if key not in groups:
            groups[key] = {"rep": i, "urls": []}
            order.append(key)
        groups[key]["urls"].append(i.url)

    out = []
    for key in order:
        g = groups[key]
        if "dict" in g:
            out.append(g["dict"])
            continue
        d = issue_to_dict(g["rep"])
        d["affectedPages"] = len(g["urls"])
        d["affectedUrls"] = g["urls"][:20]
        out.append(d)
    return out


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
        # Deduped for display: identical issues across pages become one grouped
        # row with an "affectedPages" count. Scoring still uses the raw list.
        "issues": dedupe_issues(scan.issues),
        "uniqueIssueCount": len(dedupe_issues(scan.issues)),
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
