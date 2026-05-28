"""
crawler.py
==========

The site crawler.

Given a root URL, walks every internal page on the same domain (BFS),
respecting a depth limit and a page-count limit, and returns one PageResult
per URL it visited.

Design choices
--------------
- BFS, not DFS — closer-to-root pages are usually more important, so if we
  hit the page limit we'd rather have shallow coverage than deep coverage
  of one branch.

- ThreadPoolExecutor for concurrency. The work is almost entirely network I/O,
  so threads are cheap and effective. We don't use asyncio because we want the
  code to stay readable for someone learning Python; threads are simpler to
  reason about for this scale (50-200 pages).

- robots.txt is consulted once, at the start. If the site disallows our
  user-agent on the root path, we still scan but log a warning — this is a
  developer tool aimed at site owners auditing their OWN sites, not a
  general-purpose crawler hitting other people's servers.

- "Polite delay" between requests inside each thread, configurable.
  Default is short (0.1s) but the parameter is exposed so demos can dial it up.

- Errors never crash the crawl. Every fetch is wrapped in a try/except;
  failures become PageResult entries with `error` set, and the BFS keeps going.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from crawler.url_utils import (
    extract_links,
    filter_internal_links,
    get_domain,
    normalize_url,
    should_skip_url,
)
from models.result_models import PageResult

# --- Configuration --------------------------------------------------------

USER_AGENT = "WebHealthSEOCrawler/1.0 (BSc final project; +https://github.com/)"

DEFAULT_MAX_PAGES = 50
DEFAULT_MAX_DEPTH = 2
DEFAULT_TIMEOUT = 5.0
DEFAULT_MAX_WORKERS = 8
DEFAULT_POLITE_DELAY = 0.1  # seconds between requests, per thread


# --- Logging --------------------------------------------------------------

# Get a module-level logger. The application can configure logging globally
# (level, format, handlers) without us needing to know how.
logger = logging.getLogger(__name__)


# --- robots.txt helper ----------------------------------------------------

class RobotsChecker:
    """
    Minimal robots.txt support.

    Fetches /robots.txt once at startup. If it can't be fetched (404, timeout,
    parsing error), we assume "allow everything" — a missing robots.txt is the
    universally accepted signal of an open site.
    """

    def __init__(self, root_url: str, user_agent: str = USER_AGENT) -> None:
        self.user_agent = user_agent
        self._rp: Optional[RobotFileParser] = None

        parsed = urlparse(root_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        try:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            self._rp = rp
            logger.info("Loaded robots.txt from %s", robots_url)
        except Exception as exc:  # noqa: BLE001 - we genuinely want any failure
            logger.info("No usable robots.txt at %s (%s) — assuming allow", robots_url, exc)
            self._rp = None

    def can_fetch(self, url: str) -> bool:
        """Return True if our user-agent is allowed to fetch `url`."""
        if self._rp is None:
            return True
        try:
            return self._rp.can_fetch(self.user_agent, url)
        except Exception:  # noqa: BLE001
            # Be permissive on parser errors; we're an audit tool on consenting sites.
            return True


# --- Single-page fetch ----------------------------------------------------

def fetch_url(url: str, timeout: float = DEFAULT_TIMEOUT) -> PageResult:
    """
    Fetch one URL and return a PageResult describing what happened.

    Never raises. On any error, returns a PageResult with `error` set and
    `status_code=None`.
    """
    headers = {"User-Agent": USER_AGENT}
    start = time.perf_counter()

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
        )
        elapsed = time.perf_counter() - start

        # Was this an HTML page? Only then do we parse links + keep the body.
        # Saves memory on the occasional binary that slipped past should_skip_url.
        content_type = response.headers.get("Content-Type", "").lower()
        is_html = "text/html" in content_type

        html = response.text if is_html else None
        links = extract_links(html, url) if is_html else []

        return PageResult(
            url=url,
            status_code=response.status_code,
            response_time=round(elapsed, 3),
            html=html,
            links=links,
            error=None,
        )

    except requests.exceptions.Timeout:
        elapsed = time.perf_counter() - start
        logger.warning("Timeout fetching %s after %.2fs", url, elapsed)
        return PageResult(url=url, error="Timeout")

    except requests.exceptions.ConnectionError as exc:
        logger.warning("Connection error for %s: %s", url, exc)
        return PageResult(url=url, error=f"ConnectionError: {exc}")

    except requests.exceptions.RequestException as exc:
        logger.warning("Request failed for %s: %s", url, exc)
        return PageResult(url=url, error=f"RequestError: {exc}")

    except Exception as exc:  # noqa: BLE001
        # Last-resort safety net — never let one bad page kill the whole crawl.
        logger.exception("Unexpected error fetching %s", url)
        return PageResult(url=url, error=f"UnexpectedError: {exc}")


# --- Main crawler ---------------------------------------------------------

def crawl_site(
    root_url: str,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    timeout: float = DEFAULT_TIMEOUT,
    max_workers: int = DEFAULT_MAX_WORKERS,
    polite_delay: float = DEFAULT_POLITE_DELAY,
    respect_robots: bool = True,
    progress_callback=None,
) -> list[PageResult]:
    """
    Crawl `root_url` and return one PageResult per visited URL.

    Parameters
    ----------
    root_url : str
        The starting URL. Crawler stays on this URL's exact domain.
    max_pages : int
        Hard ceiling on how many pages we'll visit. Default 50.
    max_depth : int
        How many link-clicks deep from root we're willing to go. Default 2.
    timeout : float
        Per-request HTTP timeout, in seconds.
    max_workers : int
        Number of concurrent fetches. Default 8 is a good balance for small
        sites; increase for big audits, decrease to be gentler.
    polite_delay : float
        Seconds to sleep AFTER each fetch (inside each worker), to avoid
        hammering the target server.
    respect_robots : bool
        If True (default), checks robots.txt and skips disallowed URLs.
    progress_callback : Optional[Callable[[int, int], None]]
        If supplied, called with (pages_done, pages_total_so_far) after each
        page completes. Used by the UI to show progress.

    Returns
    -------
    list[PageResult]
        One entry per URL we attempted, including failures.
    """
    root_url = normalize_url(root_url)
    root_domain = get_domain(root_url)
    logger.info("Starting crawl of %s (domain=%s)", root_url, root_domain)

    robots = RobotsChecker(root_url) if respect_robots else None

    # State shared across the BFS levels.
    visited: set[str] = set()
    results: list[PageResult] = []
    # Lock protects `visited` and `results` from concurrent worker updates.
    state_lock = Lock()

    # BFS frontier: list of URLs to process at the current depth.
    current_frontier: list[str] = [root_url]
    visited.add(root_url)
    current_depth = 0

    # Worker function — fetches one URL with the polite delay built in.
    def _fetch(url: str) -> PageResult:
        page = fetch_url(url, timeout=timeout)
        if polite_delay > 0:
            time.sleep(polite_delay)
        return page

    # Process one depth level at a time. This way `max_depth` is enforced
    # naturally, and we know exactly when to stop expanding.
    while current_frontier and current_depth <= max_depth:
        logger.info(
            "Depth %d: %d URLs to fetch (total fetched so far: %d / %d)",
            current_depth,
            len(current_frontier),
            len(results),
            max_pages,
        )

        next_frontier: list[str] = []

        # Cap this level's work so we don't blow past max_pages.
        remaining = max_pages - len(results)
        if remaining <= 0:
            break
        batch = current_frontier[:remaining]

        # Concurrent fetch of this depth level.
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_url = {pool.submit(_fetch, url): url for url in batch}

            for future in as_completed(future_to_url):
                page = future.result()

                with state_lock:
                    results.append(page)
                    pages_done = len(results)

                if progress_callback is not None:
                    progress_callback(pages_done, max_pages)

                # Find candidate links to add to the next depth level.
                # We only follow links from pages we successfully fetched.
                if page.html and current_depth < max_depth:
                    candidates = filter_internal_links(page.links, root_domain)

                    for link in candidates:
                        # Skip what we've already seen or scheduled.
                        with state_lock:
                            if link in visited:
                                continue
                            visited.add(link)

                        # Skip non-HTML extensions one more time, just in case.
                        if should_skip_url(link):
                            continue

                        # Respect robots.txt.
                        if robots is not None and not robots.can_fetch(link):
                            logger.info("robots.txt disallows %s — skipping", link)
                            continue

                        next_frontier.append(link)

        current_frontier = next_frontier
        current_depth += 1

    logger.info(
        "Crawl finished: %d pages visited (max_pages=%d, max_depth=%d)",
        len(results),
        max_pages,
        max_depth,
    )
    return results
