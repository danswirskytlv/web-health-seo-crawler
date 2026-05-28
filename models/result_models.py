"""
result_models.py
================

Typed data classes used everywhere in the project.

We use @dataclass instead of plain dicts so the whole codebase has a single,
predictable shape for "what is a crawled page" and "what is a detected issue".
PyCharm autocompletes the fields, mistyped attributes raise errors instead
of silently returning None, and the data flows cleanly between modules:

    Crawler   -> List[PageResult]
    Analyzer  -> List[Issue]   (derived from the PageResults)
    Scorer    -> ScoreResult   (derived from the Issues)
    UI/Report -> consumes all of the above
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# --- Severity levels ------------------------------------------------------

# We use plain string constants instead of an Enum to keep CSV / JSON export
# trivial and to make UI rendering (color tags etc.) straightforward.
SEVERITY_HIGH = "High"
SEVERITY_MEDIUM = "Medium"
SEVERITY_LOW = "Low"

VALID_SEVERITIES = {SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW}


# --- Page result ----------------------------------------------------------

@dataclass
class PageResult:
    """
    Everything the crawler captures about a single page it visited.

    The analyzer reads these fields to detect SEO issues.
    The UI and reports also display them directly (status code, response time).
    """

    # The URL we tried to fetch (already normalized).
    url: str

    # HTTP status code we got back. None means we couldn't even connect
    # (DNS failure, timeout, refused connection, ...).
    status_code: Optional[int] = None

    # How long the request took, in seconds. None on connection failure.
    response_time: Optional[float] = None

    # Raw HTML body of the page. None for non-HTML responses or on error.
    html: Optional[str] = None

    # All <a href="..."> targets found on the page, as absolute URLs.
    # Empty list for non-HTML or failed responses.
    links: list[str] = field(default_factory=list)

    # Human-readable error message if the fetch failed. None on success.
    # Example: "Timeout", "ConnectionError: Name or service not known".
    error: Optional[str] = None

    @property
    def is_ok(self) -> bool:
        """True for 2xx responses we could actually parse."""
        return self.status_code is not None and 200 <= self.status_code < 300

    @property
    def is_redirect(self) -> bool:
        """True for 3xx responses."""
        return self.status_code is not None and 300 <= self.status_code < 400

    @property
    def is_client_error(self) -> bool:
        """True for 4xx — typically broken links."""
        return self.status_code is not None and 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """True for 5xx — server-side problems."""
        return self.status_code is not None and 500 <= self.status_code < 600


# --- Detected issue -------------------------------------------------------

@dataclass
class Issue:
    """
    One SEO / web-health problem detected on one page.

    The analyzer creates these; the UI displays them in a table; the AI
    Assistant gets them as input and returns an explanation + fix.
    """

    # Which page the issue was found on.
    url: str

    # Short identifier of the issue type.
    # Examples: "Missing Title", "Broken Link", "Image Missing Alt".
    issue_type: str

    # "High" | "Medium" | "Low".
    severity: str

    # One-sentence human-readable description of the problem.
    description: str

    # Short fix recommendation. The AI Assistant can later expand on it.
    recommendation: str

    # Snapshot of HTTP status from the PageResult, copied here so issues
    # can be exported / displayed without joining back to pages.
    status_code: Optional[int] = None

    # Same idea — snapshot of response time.
    response_time: Optional[float] = None

    def __post_init__(self) -> None:
        # Cheap sanity check — catches typos like "high" or "Hgih".
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"Invalid severity {self.severity!r}. "
                f"Must be one of {sorted(VALID_SEVERITIES)}."
            )


# --- Aggregate score ------------------------------------------------------

@dataclass
class ScoreResult:
    """
    Output of the scoring module: an overall site health number + breakdown.
    """

    # 0-100. Higher is better.
    score: int

    # Human-friendly label derived from the score
    # (e.g., "Excellent", "Good", "Needs Improvement", "Critical").
    grade: str

    # Counts per severity, useful for the dashboard widgets.
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    @property
    def total_issues(self) -> int:
        return self.high_count + self.medium_count + self.low_count


# --- Full scan result -----------------------------------------------------

@dataclass
class ScanResult:
    """
    The complete output of a scan, ready to be rendered or exported.

    This is what the UI receives after a scan finishes.
    """

    root_url: str
    pages: list[PageResult] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    score: Optional[ScoreResult] = None

    # Useful summary fields for the dashboard cards.
    @property
    def pages_scanned(self) -> int:
        return len(self.pages)

    @property
    def issues_found(self) -> int:
        return len(self.issues)

    @property
    def broken_links(self) -> int:
        return sum(1 for i in self.issues if i.issue_type == "Broken Link")

    @property
    def average_response_time(self) -> Optional[float]:
        """Average response time across pages we could actually fetch."""
        times = [p.response_time for p in self.pages if p.response_time is not None]
        if not times:
            return None
        return sum(times) / len(times)
