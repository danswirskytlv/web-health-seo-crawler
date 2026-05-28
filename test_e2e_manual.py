"""
test_e2e_manual.py
==================

End-to-end sanity check for the full pipeline:
    Crawler -> Analyzer -> Scoring

Runs against the local test site and verifies that the issues and score
match the ground truth documented in sample_sites/README.md.

Run with:
    python test_e2e_manual.py

Prerequisite:
    The test site server must already be running. In a separate terminal:
        python serve_test_site.py
"""

from __future__ import annotations

import logging
import sys
from collections import Counter

from analyzer.scoring import calculate_score
from analyzer.seo_analyzer import (
    ISSUE_BROKEN_LINK,
    ISSUE_MISSING_ALT,
    ISSUE_MISSING_H1,
    ISSUE_MISSING_META_DESC,
    ISSUE_MISSING_TITLE,
    ISSUE_SLOW_RESPONSE,
    analyze_pages,
)
from crawler.crawler import crawl_site


# Expected per-type counts on the test site
# (see sample_sites/README.md for the rationale of each one).
EXPECTED_COUNTS = {
    ISSUE_MISSING_TITLE: 2,        # about.html, blog.html
    ISSUE_MISSING_H1: 2,           # services.html, blog.html
    ISSUE_MISSING_META_DESC: 1,    # services.html
    ISSUE_MISSING_ALT: 3,          # gallery.html × 3
    ISSUE_SLOW_RESPONSE: 1,        # faq.html
    # Broken Link is split across two checks:
    # - 1 on /portfolio.html itself (the 4xx page)
    # - 1 on /pricing.html (the page that links to /portfolio.html)
    ISSUE_BROKEN_LINK: 2,
}


def _check(label: str, ok: bool, detail: str = "") -> None:
    mark = "PASS" if ok else "FAIL"
    line = f"  [{mark}] {label}"
    if detail:
        line += f"  ({detail})"
    print(line)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    root = "http://localhost:8000"
    print(f"\nRunning full pipeline against {root}\n")

    try:
        pages = crawl_site(
            root_url=root,
            max_pages=50,
            max_depth=2,
            timeout=10.0,
            max_workers=4,
            polite_delay=0.0,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"\nCrawl failed: {exc}")
        print("Is the test site running? Try:  python serve_test_site.py")
        sys.exit(1)

    issues = analyze_pages(pages)
    score = calculate_score(issues)

    # ---- Issues breakdown ----
    print("\n" + "=" * 70)
    print(f"  Issues found: {len(issues)}")
    print("=" * 70)

    by_type = Counter(i.issue_type for i in issues)
    for issue_type, count in sorted(by_type.items()):
        print(f"  {issue_type:30s}  x{count}")

    # ---- Issues table ----
    print("\n  " + "-" * 68)
    print(f"  {'SEVERITY':<8}  {'TYPE':<28}  URL")
    print("  " + "-" * 68)
    severity_order = {"High": 0, "Medium": 1, "Low": 2}
    for issue in sorted(issues, key=lambda i: (severity_order.get(i.severity, 9), i.issue_type, i.url)):
        # Shorten URL for the table (drop the localhost:8000 prefix).
        short_url = issue.url.replace(root, "") or "/"
        print(f"  {issue.severity:<8}  {issue.issue_type:<28}  {short_url}")

    # ---- Score ----
    print("\n" + "=" * 70)
    print(f"  Website Health Score: {score.score}/100  ({score.grade})")
    print("=" * 70)
    print(f"  High issues:   {score.high_count}")
    print(f"  Medium issues: {score.medium_count}")
    print(f"  Low issues:    {score.low_count}")
    print(f"  Total:         {score.total_issues}")

    # ---- Sanity checks vs ground truth ----
    print("\n" + "=" * 70)
    print("  Sanity checks (vs sample_sites/README.md ground truth)")
    print("=" * 70)

    for issue_type, expected in EXPECTED_COUNTS.items():
        actual = by_type.get(issue_type, 0)
        _check(
            f"Detected exactly {expected} '{issue_type}'",
            actual == expected,
            f"got {actual}",
        )

    _check(
        "Score is between 0 and 100",
        0 <= score.score <= 100,
        f"got {score.score}",
    )
    _check(
        "At least one High-severity issue was detected",
        score.high_count >= 1,
    )
    _check(
        "Grade label is one of the four expected",
        score.grade in {"Excellent", "Good", "Needs Improvement", "Critical"},
        f"got {score.grade!r}",
    )

    print()


if __name__ == "__main__":
    main()
