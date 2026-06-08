"""
exposed_paths.py
================

Active probe for sensitive paths a site shouldn't expose.

Most analyzers here inspect pages the crawler *found* by following links. But
files like `/.env` or `/.git/config` are never linked — that's the whole
point. To find them we have to actively REQUEST a small, conservative list of
well-known sensitive paths and see whether the server returns them.

Because this sends requests the site didn't advertise, it is treated like a
gentle, opt-in vulnerability check:

- It is OFF by default and only runs when the user explicitly enables it
  (the tool is meant for owners auditing their OWN site).
- The path list is short and conservative — common, high-signal targets only.
- It runs ONCE per host, not per page.
- It never raises; any request failure simply means "not found".

A path is only reported when the server returns a real 200 with actual
content — soft-404s, redirects (often to a login page), and empty bodies are
ignored to avoid false positives.

Output: Issues in the "Information Disclosure" category.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse, urlunparse

from models.result_models import (
    CATEGORY_INFO_DISCLOSURE,
    Issue,
    PageResult,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
)

logger = logging.getLogger(__name__)

EXPOSED_PATH = "Exposed Sensitive Path"

PROBE_TIMEOUT = 6.0
# Below this many bytes a 200 is probably a stub/soft-404, not the real file.
_MIN_REAL_BYTES = 8

# Hosts we never probe (the local test server etc.).
_SKIP_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}

# (path, human description, severity). Conservative, high-signal list only.
_SENSITIVE_PATHS: list[tuple[str, str, str]] = [
    ("/.env",            "environment file (often holds DB passwords / API keys)", SEVERITY_HIGH),
    ("/.git/config",     "Git repository config (can expose source history)",      SEVERITY_HIGH),
    ("/.git/HEAD",       "Git repository metadata",                                SEVERITY_HIGH),
    ("/wp-config.php.bak", "WordPress config backup (database credentials)",       SEVERITY_HIGH),
    ("/config.php.bak",  "PHP config backup",                                      SEVERITY_HIGH),
    ("/backup.sql",      "database SQL dump",                                      SEVERITY_HIGH),
    ("/database.sql",    "database SQL dump",                                      SEVERITY_HIGH),
    ("/.htaccess",       "Apache config (rules and rewrite logic)",                SEVERITY_MEDIUM),
    ("/.htpasswd",       "Apache password file (hashed credentials)",             SEVERITY_HIGH),
    ("/phpinfo.php",     "phpinfo() output (full server configuration)",           SEVERITY_MEDIUM),
    ("/server-status",   "Apache server-status (live request data)",               SEVERITY_MEDIUM),
    ("/.DS_Store",       "macOS folder index (leaks file/directory names)",        SEVERITY_MEDIUM),
]


def _build_issue(page: PageResult, path: str, what: str, severity: str, url: str) -> Issue:
    return Issue(
        url=url,
        issue_type=EXPOSED_PATH,
        severity=severity,
        category=CATEGORY_INFO_DISCLOSURE,
        description=(
            f"The path {path} is publicly accessible and returns content — a "
            f"{what}. Anyone on the internet can read it."
        ),
        recommendation=(
            f"Block access to {path} at the web-server level (deny rule) or "
            "remove the file. Sensitive files should never be web-reachable."
        ),
        status_code=page.status_code,
        response_time=page.response_time,
    )


def _base_url(page: PageResult) -> str | None:
    """scheme://host[:port] for the page, or None for skip-listed hosts."""
    parsed = urlparse(page.final_url or page.url)
    host = (parsed.hostname or "").lower()
    if not host or host in _SKIP_HOSTS:
        return None
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def _unique_bases(pages: list[PageResult]) -> dict[str, PageResult]:
    """One representative page per base URL (scheme+host), skip-listed removed."""
    bases: dict[str, PageResult] = {}
    for page in pages:
        if not page.is_ok:
            continue
        base = _base_url(page)
        if base:
            bases.setdefault(base, page)
    return bases


def _default_probe(url: str):
    """
    Real network probe. Returns True if `url` returns a genuine 200 with body.

    Never raises. Does not follow redirects, so a redirect (e.g. to a login
    page) counts as 'not exposed'.
    """
    try:
        import requests
        resp = requests.get(url, timeout=PROBE_TIMEOUT, allow_redirects=False, stream=True)
        if resp.status_code != 200:
            return False
        body = resp.content or b""
        return len(body) >= _MIN_REAL_BYTES
    except Exception as exc:  # noqa: BLE001 — a probe must never break a scan
        logger.info("Probe failed for %s: %s", url, exc)
        return False


def analyze_pages_exposed(pages: list[PageResult], probe=None) -> list[Issue]:
    """
    Probe each unique host for the sensitive paths and report any that exist.

    `probe(url) -> bool` defaults to a real HTTP request; tests inject a fake.
    Returns [] if there are no probable hosts.
    """
    if probe is None:
        probe = _default_probe

    issues: list[Issue] = []
    for base, page in _unique_bases(pages).items():
        for path, what, severity in _SENSITIVE_PATHS:
            url = base + path
            if probe(url):
                issues.append(_build_issue(page, path, what, severity, url))
    return issues
