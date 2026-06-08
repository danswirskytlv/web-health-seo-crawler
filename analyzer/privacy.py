"""
privacy.py
==========

Third-party tracker & privacy detection.

A web page often loads scripts, pixels and iframes from other companies that
track the people visiting it — analytics, ad networks, social pixels, session
recorders. Site owners are frequently unaware of everything their pages pull
in, and under privacy laws (GDPR, ePrivacy) each tracker can carry consent and
disclosure obligations.

This is a purely STATIC, offline check: it reads the external domains already
present in the page's HTML (script src, iframe src, img src, link href) and
matches them against a registry of well-known trackers. It opens no new
network connections.

Output: Issues in the "Privacy" category.
  - "Third-Party Tracker Detected" (Low/Medium) — a known tracker is present.
  - "Many Third-Party Domains"     (Low)        — the page contacts an unusually
                                                  large number of external hosts.
"""

from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from models.result_models import (
    CATEGORY_PRIVACY,
    Issue,
    PageResult,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)


# --- Issue type names ----------------------------------------------------

PRIV_TRACKER = "Third-Party Tracker Detected"
PRIV_MANY_THIRD_PARTY = "Many Third-Party Domains"


# --- Known-tracker registry ----------------------------------------------

# Maps a domain substring -> (friendly name, category, severity).
# Substring match (against the resource host) keeps this robust to the many
# regional/CDN variants each vendor uses (e.g. google-analytics.com,
# www.googletagmanager.com, region1.google-analytics.com).
_TRACKERS: list[tuple[str, str, str, str]] = [
    ("google-analytics.com",   "Google Analytics",      "analytics",      SEVERITY_LOW),
    ("googletagmanager.com",   "Google Tag Manager",    "tag manager",    SEVERITY_LOW),
    ("doubleclick.net",        "Google DoubleClick",    "advertising",    SEVERITY_MEDIUM),
    ("googlesyndication.com",  "Google AdSense",        "advertising",    SEVERITY_MEDIUM),
    ("facebook.net",           "Meta (Facebook) Pixel", "ad/social pixel", SEVERITY_MEDIUM),
    ("connect.facebook",       "Meta (Facebook) Pixel", "ad/social pixel", SEVERITY_MEDIUM),
    ("hotjar.com",             "Hotjar",                "session recording", SEVERITY_MEDIUM),
    ("clarity.ms",             "Microsoft Clarity",     "session recording", SEVERITY_MEDIUM),
    ("fullstory.com",          "FullStory",             "session recording", SEVERITY_MEDIUM),
    ("mixpanel.com",           "Mixpanel",              "analytics",      SEVERITY_LOW),
    ("segment.com",            "Segment",               "analytics",      SEVERITY_LOW),
    ("segment.io",             "Segment",               "analytics",      SEVERITY_LOW),
    ("amplitude.com",          "Amplitude",             "analytics",      SEVERITY_LOW),
    ("tiktok.com",             "TikTok Pixel",          "ad/social pixel", SEVERITY_MEDIUM),
    ("snapchat.com",           "Snap Pixel",            "ad/social pixel", SEVERITY_MEDIUM),
    ("ads-twitter.com",        "X (Twitter) Pixel",     "ad/social pixel", SEVERITY_MEDIUM),
    ("linkedin.com/px",        "LinkedIn Insight",      "ad/social pixel", SEVERITY_MEDIUM),
    ("snap.licdn.com",         "LinkedIn Insight",      "ad/social pixel", SEVERITY_MEDIUM),
    ("hubspot.com",            "HubSpot",               "marketing",      SEVERITY_LOW),
    ("hs-scripts.com",         "HubSpot",               "marketing",      SEVERITY_LOW),
    ("criteo.com",             "Criteo",                "advertising",    SEVERITY_MEDIUM),
    ("taboola.com",            "Taboola",               "advertising",    SEVERITY_MEDIUM),
    ("outbrain.com",           "Outbrain",              "advertising",    SEVERITY_MEDIUM),
]

# A page touching more than this many distinct third-party hosts is worth a note.
MANY_THIRD_PARTY_DOMAINS = 10

# Resource elements whose URLs pull in a third party.
_RESOURCE_ATTRS = (("script", "src"), ("iframe", "src"), ("img", "src"),
                   ("link", "href"), ("embed", "src"))


# --- Helpers --------------------------------------------------------------

def _build_issue(page: PageResult, issue_type: str, severity: str,
                 description: str, recommendation: str) -> Issue:
    return Issue(
        url=page.url,
        issue_type=issue_type,
        severity=severity,
        category=CATEGORY_PRIVACY,
        description=description,
        recommendation=recommendation,
        status_code=page.status_code,
        response_time=page.response_time,
    )


def _page_host(page: PageResult) -> str:
    return (urlparse(page.final_url or page.url).hostname or "").lower()


def _is_same_site(resource_host: str, page_host: str) -> bool:
    """True if the resource host is the page's own domain (or a subdomain)."""
    if not resource_host or not page_host:
        return False
    return resource_host == page_host or resource_host.endswith("." + page_host) \
        or page_host.endswith("." + resource_host)


def _external_hosts(page: PageResult, soup: BeautifulSoup) -> list[str]:
    """All distinct third-party (non-same-site) resource hosts on the page."""
    page_host = _page_host(page)
    hosts: list[str] = []
    seen: set[str] = set()
    for tag_name, attr in _RESOURCE_ATTRS:
        for el in soup.find_all(tag_name):
            value = (el.get(attr) or "").strip()
            if not value or value.startswith(("data:", "#", "javascript:")):
                continue
            host = (urlparse(value).hostname or "").lower()
            if not host or _is_same_site(host, page_host):
                continue
            if host not in seen:
                seen.add(host)
                hosts.append(host)
    return hosts


def _match_tracker(host: str):
    """Return (name, kind, severity) if host matches a known tracker, else None."""
    for needle, name, kind, severity in _TRACKERS:
        if needle in host:
            return name, kind, severity
    return None


# --- Public API -----------------------------------------------------------

def analyze_pages_privacy(pages: list[PageResult]) -> list[Issue]:
    """
    Detect third-party trackers and heavy third-party usage on each page.

    Static / offline: reads only the HTML the crawler already captured.
    De-duplicates each (page, tracker) so one issue per tracker per page.
    """
    issues: list[Issue] = []

    for page in pages:
        if not page.is_ok or not page.html:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        ext_hosts = _external_hosts(page, soup)

        reported: set[str] = set()
        for host in ext_hosts:
            match = _match_tracker(host)
            if match is None:
                continue
            name, kind, severity = match
            if name in reported:
                continue  # one issue per tracker per page
            reported.add(name)
            issues.append(_build_issue(
                page,
                issue_type=PRIV_TRACKER,
                severity=severity,
                description=(
                    f"This page loads {name} ({kind}) from {host}. It can track "
                    "visitors across the web and may require a consent banner "
                    "and privacy-policy disclosure."
                ),
                recommendation=(
                    f"Confirm {name} is necessary, load it only after consent, "
                    "and disclose it in your privacy policy. Remove it if unused."
                ),
            ))

        # Heavy third-party usage (independent of whether they're known trackers).
        if len(ext_hosts) > MANY_THIRD_PARTY_DOMAINS:
            issues.append(_build_issue(
                page,
                issue_type=PRIV_MANY_THIRD_PARTY,
                severity=SEVERITY_LOW,
                description=(
                    f"This page contacts {len(ext_hosts)} different third-party "
                    "domains. Each one can set cookies and observe your visitors."
                ),
                recommendation=(
                    "Audit the third-party scripts and remove any that aren't "
                    "essential; fewer third parties means better privacy and speed."
                ),
            ))

    return issues
