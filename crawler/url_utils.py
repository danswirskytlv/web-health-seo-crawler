"""
url_utils.py
============

Small, pure helper functions for working with URLs during crawling.

Keeping these out of crawler.py makes them easy to unit-test in isolation
and keeps the crawler itself focused on the BFS / threading logic.

All functions here are pure — same input always produces the same output,
no network, no side effects.
"""

from __future__ import annotations

from typing import Iterable
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

# --- Constants ------------------------------------------------------------

# File extensions we never want to fetch as web pages — they're either binary
# (no HTML to parse), expensive (large files), or both. Skipping them up front
# saves bandwidth and avoids confusing the HTML parser.
SKIP_EXTENSIONS = {
    # images
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico", ".bmp", ".tiff",
    # documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # archives
    ".zip", ".rar", ".7z", ".tar", ".gz",
    # media
    ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".webm", ".ogg",
    # other
    ".exe", ".dmg", ".iso",
}

# Schemes we DO want to crawl. Everything else (mailto:, tel:, javascript:,
# data:, ftp:, ...) is filtered out.
ALLOWED_SCHEMES = {"http", "https"}


# --- Pure helpers ---------------------------------------------------------

# Default "directory index" filenames that servers serve when a request hits
# a folder. Normalizing these to the bare folder URL prevents the crawler
# from treating "/" and "/index.html" as two different pages.
INDEX_FILENAMES = {"index.html", "index.htm", "index.php", "default.html", "default.htm"}


def normalize_url(url: str) -> str:
    """
    Produce a canonical form of a URL so that the crawler treats minor
    syntactic variants as the same page.

    Specifically:
      - lowercases the scheme and host
      - drops the fragment (#section)
      - strips trailing slashes from the path (except the root "/")
      - collapses default index filenames to the parent folder
        ("/index.html" -> "/", "/blog/index.html" -> "/blog")
      - keeps the query string as-is (it can be semantically meaningful)

    Examples:
        >>> normalize_url("HTTP://Example.com/About/#team")
        'http://example.com/About'
        >>> normalize_url("https://example.com/")
        'https://example.com/'
        >>> normalize_url("https://example.com/index.html")
        'https://example.com/'
    """
    parsed = urlparse(url)

    # Lowercase scheme + host. Path/query stay case-sensitive — some servers
    # actually distinguish /Page from /page.
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    path = parsed.path

    # Collapse default index filenames so "/index.html" and "/" become the
    # same canonical URL. We only check the basename (case-insensitive),
    # to leave files like "/api/index.json" untouched.
    if path:
        # The basename is whatever comes after the last "/".
        # Split keeps the leading parts as the "parent" we'll fall back to.
        last_slash = path.rfind("/")
        basename = path[last_slash + 1:] if last_slash >= 0 else path
        if basename.lower() in INDEX_FILENAMES:
            # Replace the basename with empty -> ends with "/", preserve folder.
            path = path[: last_slash + 1]

    # Strip trailing slash. We strip it even for the root ("/" -> "") so that
    # all three forms of the root — "http://x", "http://x/", "http://x/index.html"
    # — collapse to the same canonical URL ("http://x").
    if path.endswith("/"):
        path = path.rstrip("/")

    # Reconstruct without the fragment.
    return urlunparse((scheme, netloc, path, parsed.params, parsed.query, ""))


def is_internal_url(url: str, root_domain: str) -> bool:
    """
    Return True if `url` belongs to the same domain we're crawling.

    "Same domain" here means: identical netloc (host + optional port).
    Subdomains are treated as DIFFERENT domains by default — blog.example.com
    is NOT considered the same site as example.com. This is the conservative
    choice; if a user needs broader crawling later, we can relax it.

        >>> is_internal_url("https://example.com/about", "example.com")
        True
        >>> is_internal_url("https://blog.example.com/post", "example.com")
        False
        >>> is_internal_url("https://other.com/", "example.com")
        False
    """
    parsed = urlparse(url)
    # Host can have a port (e.g., "localhost:8000"); compare full netloc.
    return parsed.netloc.lower() == root_domain.lower()


def should_skip_url(url: str) -> bool:
    """
    Return True if this URL should be skipped entirely (not fetched).

    Skipped because:
      - non-HTTP scheme (mailto:, tel:, javascript:, ...)
      - file extension we don't want to process (images, PDFs, ...)
    """
    parsed = urlparse(url)

    # Filter out non-HTTP schemes.
    if parsed.scheme and parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return True

    # Filter out known binary / media extensions.
    # We check the lowercased path so .JPG and .jpg both match.
    path_lower = parsed.path.lower()
    for ext in SKIP_EXTENSIONS:
        if path_lower.endswith(ext):
            return True

    return False


def extract_links(html: str, base_url: str) -> list[str]:
    """
    Pull every <a href="..."> link out of `html` and return them as
    absolute, normalized URLs.

    Relative links are resolved against `base_url` using urljoin, so
    `<a href="/about">` on `https://example.com/page` becomes
    `https://example.com/about`.

    Duplicate URLs within the same page are removed. Empty hrefs are skipped.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    links: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href:
            continue

        # Resolve relative URLs against the page they were found on.
        absolute = urljoin(base_url, href)
        normalized = normalize_url(absolute)

        # Deduplicate within the same page.
        if normalized not in seen:
            seen.add(normalized)
            links.append(normalized)

    return links


def get_domain(url: str) -> str:
    """
    Return the netloc (host + optional port) of `url`, lowercased.

    Used by the crawler to figure out which domain it should stay inside.

        >>> get_domain("https://Example.com:8080/path")
        'example.com:8080'
    """
    return urlparse(url).netloc.lower()


def filter_internal_links(
    links: Iterable[str],
    root_domain: str,
) -> list[str]:
    """
    Given an iterable of URLs, keep only those that are:
      - on the same domain as `root_domain`
      - not in the skip-extension / non-HTTP list

    Returns the filtered URLs in their original order, deduplicated.
    """
    seen: set[str] = set()
    out: list[str] = []
    for url in links:
        if url in seen:
            continue
        if should_skip_url(url):
            continue
        if not is_internal_url(url, root_domain):
            continue
        seen.add(url)
        out.append(url)
    return out
