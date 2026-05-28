"""
test_crawler_manual.py
======================

Manual sanity-check script for the crawler.

This is NOT a unit test (those live in tests/ and run with pytest).
This script runs the crawler against the local test site and prints a
human-readable summary, so a developer can verify by eye that the crawler
is working before moving on.

Run with:
    python test_crawler_manual.py

Prerequisite:
    The test site server must already be running. In a separate terminal:
        python serve_test_site.py
"""

from __future__ import annotations

import logging
import sys

from crawler.crawler import crawl_site


def main() -> None:
    # Make the crawler's INFO logs visible in the terminal so we can see
    # the BFS depth-by-depth progress.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    root = "http://localhost:8000"
    print(f"\nCrawling {root} ...\n")

    try:
        results = crawl_site(
            root_url=root,
            max_pages=50,
            max_depth=2,
            timeout=10.0,    # generous so the slow /faq.html survives
            max_workers=4,
            polite_delay=0.0,  # no need to be polite to ourselves
        )
    except Exception as exc:  # noqa: BLE001
        print(f"\nCrawl failed: {exc}")
        print("Is the test site running? Try:  python serve_test_site.py")
        sys.exit(1)

    # ---- Summary ----
    print("\n" + "=" * 70)
    print(f"  Crawl summary — {len(results)} pages fetched")
    print("=" * 70)

    # Header row
    print(f"\n  {'STATUS':>6}  {'TIME':>6}  {'LINKS':>5}  URL")
    print("  " + "-" * 68)

    # Sort by URL for stable, readable output.
    for page in sorted(results, key=lambda p: p.url):
        status = str(page.status_code) if page.status_code is not None else "ERR"
        time_str = f"{page.response_time:.2f}s" if page.response_time is not None else "  -  "
        link_count = len(page.links)
        marker = ""
        if page.error:
            marker = f"  [{page.error}]"
        elif page.is_client_error:
            marker = "  [4xx]"
        elif page.is_server_error:
            marker = "  [5xx]"
        print(f"  {status:>6}  {time_str:>6}  {link_count:>5}  {page.url}{marker}")

    # ---- Quick sanity checks vs sample_sites/README.md ----
    print("\n" + "=" * 70)
    print("  Quick sanity checks (vs sample_sites/README.md ground truth)")
    print("=" * 70)

    urls = {p.url for p in results}
    base = "http://localhost:8000"

    # After URL normalization the root is just the base — "/" and "/index.html"
    # collapse to it. All other pages keep their explicit path.
    non_root_paths = [
        "/about.html", "/services.html", "/pricing.html", "/gallery.html",
        "/contact.html", "/blog.html", "/faq.html",
    ]

    def _check(label: str, ok: bool, detail: str = "") -> None:
        mark = "PASS" if ok else "FAIL"
        line = f"  [{mark}] {label}"
        if detail:
            line += f"  ({detail})"
        print(line)

    _check("Root URL was visited", base in urls)
    _check("No duplicate root entries", base + "/index.html" not in urls,
           "/index.html should be normalized to the root")

    for path in non_root_paths:
        full = base + path
        _check(f"Visited {path}", full in urls)

    portfolio_url = base + "/portfolio.html"
    portfolio_results = [p for p in results if p.url == portfolio_url]
    if portfolio_results:
        p = portfolio_results[0]
        _check(
            "Broken /portfolio.html returns 404",
            p.status_code == 404,
            f"got status={p.status_code}",
        )
    else:
        _check("Broken /portfolio.html was discovered as a link", False,
               "not found in crawl results — broken-link detection won't work")

    faq_results = [p for p in results if p.url == base + "/faq.html"]
    if faq_results and faq_results[0].response_time is not None:
        rt = faq_results[0].response_time
        _check("/faq.html is slow (>2s)", rt > 2.0, f"response_time={rt:.2f}s")

    print()


if __name__ == "__main__":
    main()
