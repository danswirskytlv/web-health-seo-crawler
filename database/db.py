"""
db.py
=====

Thin SQLite-backed persistence layer for scan results.

Why this exists
---------------
Until this stage every scan was held in `st.session_state` and disappeared
the moment the browser closed. Persisting scans unlocks three things:

  1. The user can come back later and see what their site used to look like.
  2. We can diff two scans — "what got fixed, what's new, what's still broken".
  3. Stage 14 (Root Cause Analysis) can feed real history to the AI.

Design notes
------------
- One SQLite file. No server, no auth, no migrations framework. It's a
  desktop tool with a single user, and that's exactly what SQLite is for.
- The DAO returns ScanResult / Issue / PageResult objects, never raw rows.
  The rest of the app talks in dataclasses; this module is the single seam
  between rich Python objects and tabular storage.
- All writes happen inside one transaction per scan, so a crash in the
  middle leaves the DB consistent (either all of the scan is saved or none
  of it).
- Foreign keys + ON DELETE CASCADE are enabled per-connection (SQLite
  requires this — see the PRAGMA in _connect).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from models.result_models import (
    Issue,
    PageResult,
    ScanResult,
    ScoreResult,
    CATEGORY_SEO,
    VALID_CATEGORIES,
)

logger = logging.getLogger(__name__)


# --- Configuration --------------------------------------------------------

# Default DB location. Sits next to the rest of the project so it follows
# the repo around without needing config from the user.
DEFAULT_DB_PATH = Path(__file__).parent.parent / "sitepulse.db"

# Path to the schema file, used by init_db().
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


# --- Connection helper ---------------------------------------------------

def _connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    """
    Open a connection with the conventions we want everywhere.

    - Foreign keys turned on (off by default in SQLite — a real footgun).
    - Row factory set so we can read columns by name (`row["score"]`).
    - Reasonable timeout for the rare case of concurrent access.
    """
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# --- Initialization -----------------------------------------------------

def init_db(db_path: Path | str | None = None) -> None:
    """
    Create tables and indices if they don't already exist.

    Idempotent — safe to call on every app start. The API calls this on
    startup (see api/main.py lifespan) so the DB is always ready.
    """
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with _connect(db_path) as conn:
        conn.executescript(sql)
        # Lightweight migration: older DBs created before the `details` column
        # existed won't get it from CREATE TABLE IF NOT EXISTS. Add it if missing.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(issues)")}
        if "details" not in cols:
            conn.execute("ALTER TABLE issues ADD COLUMN details TEXT")
    logger.info("Initialized database at %s", db_path or DEFAULT_DB_PATH)


# --- Save -----------------------------------------------------------------

def save_scan(scan: ScanResult, db_path: Path | str | None = None) -> int:
    """
    Persist a completed ScanResult and return the new scan_id.

    Everything for one scan goes into a single transaction so partial
    saves can't happen — either the scan + all its pages and issues are
    there, or nothing is.
    """
    if scan.score is None:
        raise ValueError("Cannot save a scan with no score. Compute the score first.")

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    avg_rt = scan.average_response_time

    with _connect(db_path) as conn:
        cur = conn.cursor()

        # 1. The scan row itself.
        cur.execute(
            """
            INSERT INTO scans (
                root_url, scanned_at, score, grade,
                pages_count, issues_count,
                high_count, medium_count, low_count,
                avg_response_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan.root_url,
                now_iso,
                scan.score.score,
                scan.score.grade,
                scan.pages_scanned,
                scan.issues_found,
                scan.score.high_count,
                scan.score.medium_count,
                scan.score.low_count,
                avg_rt,
            ),
        )
        scan_id = cur.lastrowid

        # 2. All pages.
        if scan.pages:
            cur.executemany(
                """
                INSERT INTO pages (scan_id, url, status_code, response_time, error)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (scan_id, p.url, p.status_code, p.response_time, p.error)
                    for p in scan.pages
                ],
            )

        # 3. All issues.
        if scan.issues:
            cur.executemany(
                """
                INSERT INTO issues (
                    scan_id, url, issue_type, severity, category,
                    description, recommendation,
                    status_code, response_time, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        scan_id,
                        i.url,
                        i.issue_type,
                        i.severity,
                        i.category,
                        i.description,
                        i.recommendation,
                        i.status_code,
                        i.response_time,
                        json.dumps(i.details) if getattr(i, "details", None) else None,
                    )
                    for i in scan.issues
                ],
            )

        # 4. Per-category sub-scores (one row each).
        if scan.score.category_scores:
            cur.executemany(
                """
                INSERT INTO category_scores (scan_id, category, score)
                VALUES (?, ?, ?)
                """,
                [
                    (scan_id, category, sub_score)
                    for category, sub_score in scan.score.category_scores.items()
                ],
            )

        conn.commit()

    logger.info(
        "Saved scan #%d for %s — score %d, %d pages, %d issues",
        scan_id, scan.root_url, scan.score.score,
        scan.pages_scanned, scan.issues_found,
    )
    return scan_id


# --- Read API -------------------------------------------------------------

@dataclass
class ScanSummary:
    """
    Lightweight summary of a saved scan — what the History page lists.

    We expose this small object instead of a full ScanResult because the
    History page doesn't need every page and issue; only the headline numbers.
    """
    id: int
    root_url: str
    scanned_at: str
    score: int
    grade: str
    pages_count: int
    issues_count: int
    high_count: int
    medium_count: int
    low_count: int
    avg_response_time: Optional[float]


def list_scans(
    root_url: Optional[str] = None,
    limit: int = 100,
    db_path: Path | str | None = None,
) -> list[ScanSummary]:
    """
    Return saved scans, newest first.

    Pass `root_url` to filter the history for one specific site.
    """
    # We sort by (scanned_at, id) so that two scans saved within the same
    # second still keep their insertion order in the listing — newest id
    # wins ties. This matters in tests; in real use the timestamps differ.
    if root_url:
        sql = """
            SELECT * FROM scans
            WHERE root_url = ?
            ORDER BY scanned_at DESC, id DESC
            LIMIT ?
        """
        args = (root_url, limit)
    else:
        sql = """
            SELECT * FROM scans
            ORDER BY scanned_at DESC, id DESC
            LIMIT ?
        """
        args = (limit,)

    with _connect(db_path) as conn:
        rows = conn.execute(sql, args).fetchall()

    return [
        ScanSummary(
            id=r["id"],
            root_url=r["root_url"],
            scanned_at=r["scanned_at"],
            score=r["score"],
            grade=r["grade"],
            pages_count=r["pages_count"],
            issues_count=r["issues_count"],
            high_count=r["high_count"],
            medium_count=r["medium_count"],
            low_count=r["low_count"],
            avg_response_time=r["avg_response_time"],
        )
        for r in rows
    ]


def get_scan(scan_id: int, db_path: Path | str | None = None) -> Optional[ScanResult]:
    """
    Reconstruct a full ScanResult from the DB.

    Returns None if the scan_id doesn't exist.

    Note that we lose `html` on the way to disk — we never stored it. The
    AI Assistant won't have page context for historical scans, only for
    the current one. That's a deliberate trade-off: HTML blobs would blow
    up the DB very quickly.
    """
    with _connect(db_path) as conn:
        # Scan row
        scan_row = conn.execute(
            "SELECT * FROM scans WHERE id = ?", (scan_id,)
        ).fetchone()
        if scan_row is None:
            return None

        # Pages
        page_rows = conn.execute(
            "SELECT * FROM pages WHERE scan_id = ? ORDER BY url", (scan_id,)
        ).fetchall()
        pages = [
            PageResult(
                url=p["url"],
                status_code=p["status_code"],
                response_time=p["response_time"],
                html=None,        # not persisted
                links=[],         # not persisted
                error=p["error"],
            )
            for p in page_rows
        ]

        # Issues
        issue_rows = conn.execute(
            "SELECT * FROM issues WHERE scan_id = ? ORDER BY severity, url",
            (scan_id,),
        ).fetchall()
        issues = []
        for ir in issue_rows:
            category = ir["category"] if ir["category"] in VALID_CATEGORIES else CATEGORY_SEO
            # `details` is JSON (or NULL). Guard for legacy rows / bad JSON.
            details = None
            raw_details = ir["details"] if "details" in ir.keys() else None
            if raw_details:
                try:
                    details = json.loads(raw_details)
                except (ValueError, TypeError):
                    details = None
            issues.append(Issue(
                url=ir["url"],
                issue_type=ir["issue_type"],
                severity=ir["severity"],
                category=category,
                description=ir["description"],
                recommendation=ir["recommendation"],
                status_code=ir["status_code"],
                response_time=ir["response_time"],
                details=details,
            ))

        # Per-category sub-scores (empty for scans saved before this existed).
        cat_rows = conn.execute(
            "SELECT category, score FROM category_scores WHERE scan_id = ?",
            (scan_id,),
        ).fetchall()
        category_scores = {r["category"]: r["score"] for r in cat_rows}

        score = ScoreResult(
            score=scan_row["score"],
            grade=scan_row["grade"],
            high_count=scan_row["high_count"],
            medium_count=scan_row["medium_count"],
            low_count=scan_row["low_count"],
            category_scores=category_scores,
        )

    return ScanResult(
        root_url=scan_row["root_url"],
        pages=pages,
        issues=issues,
        score=score,
    )


def delete_scan(scan_id: int, db_path: Path | str | None = None) -> bool:
    """
    Delete a scan and all its pages/issues. Returns True if a row was
    actually removed (False if scan_id didn't exist).

    The ON DELETE CASCADE in the schema takes care of pages and issues.
    """
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
        conn.commit()
        return cur.rowcount > 0


# --- Diff -----------------------------------------------------------------

@dataclass
class ScanDiff:
    """
    The shape of a comparison between two scans.

    The newer scan is `to`, the older is `from`. "Fixed" issues existed
    in `from` but not in `to`; "new" issues are the reverse.

    Two issues are considered "the same" if they have the same
    (url, issue_type) pair. We deliberately ignore description differences
    (rare and noisy) and severity changes (rule-based; they don't drift).
    """
    from_scan: ScanSummary
    to_scan: ScanSummary
    fixed_issues: list[Issue]    # were in old, gone in new
    new_issues: list[Issue]      # in new but not old
    unchanged_issues: list[Issue]  # in both

    score_delta: int             # to.score - from.score


def _issue_key(issue: Issue) -> tuple[str, str]:
    """Identity used for issue equality across scans."""
    return (issue.url, issue.issue_type)


def get_diff(
    from_scan_id: int,
    to_scan_id: int,
    db_path: Path | str | None = None,
) -> Optional[ScanDiff]:
    """
    Compare two scans. Returns None if either doesn't exist.

    Convention: 'from' is the older scan, 'to' is the newer one. We don't
    actually require this — caller can compare in either direction — but
    the field names (`fixed_issues`, `new_issues`) only make sense if you
    follow it.
    """
    from_scan = get_scan(from_scan_id, db_path)
    to_scan = get_scan(to_scan_id, db_path)
    if from_scan is None or to_scan is None:
        return None

    from_keys = {_issue_key(i): i for i in from_scan.issues}
    to_keys = {_issue_key(i): i for i in to_scan.issues}

    fixed = [issue for k, issue in from_keys.items() if k not in to_keys]
    new = [issue for k, issue in to_keys.items() if k not in from_keys]
    unchanged = [issue for k, issue in to_keys.items() if k in from_keys]

    # Fetch the lightweight summaries so the UI can show metadata
    # (when scanned, score) without re-querying.
    with _connect(db_path) as conn:
        from_meta = conn.execute(
            "SELECT * FROM scans WHERE id = ?", (from_scan_id,)
        ).fetchone()
        to_meta = conn.execute(
            "SELECT * FROM scans WHERE id = ?", (to_scan_id,)
        ).fetchone()

    def _to_summary(r) -> ScanSummary:
        return ScanSummary(
            id=r["id"],
            root_url=r["root_url"],
            scanned_at=r["scanned_at"],
            score=r["score"],
            grade=r["grade"],
            pages_count=r["pages_count"],
            issues_count=r["issues_count"],
            high_count=r["high_count"],
            medium_count=r["medium_count"],
            low_count=r["low_count"],
            avg_response_time=r["avg_response_time"],
        )

    return ScanDiff(
        from_scan=_to_summary(from_meta),
        to_scan=_to_summary(to_meta),
        fixed_issues=fixed,
        new_issues=new,
        unchanged_issues=unchanged,
        score_delta=to_meta["score"] - from_meta["score"],
    )
