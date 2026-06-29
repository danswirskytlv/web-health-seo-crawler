-- ============================================================
-- SitePulse AI — Database Schema
-- ============================================================
--
-- Three tables that mirror the in-memory dataclasses:
--   scans   — one row per completed scan
--   pages   — one row per URL visited during a scan
--   issues  — one row per detected problem
--
-- Foreign keys + ON DELETE CASCADE ensure that deleting a scan
-- cleans up everything that belongs to it — no orphan rows.
-- ============================================================

-- Enable foreign-key enforcement (SQLite needs this per connection).
PRAGMA foreign_keys = ON;


-- ------------------------------------------------------------
-- scans: the top-level record. One row per scan run.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scans (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,

    -- The root URL the user scanned (normalized form).
    root_url        TEXT    NOT NULL,

    -- When the scan completed (ISO 8601, UTC).
    scanned_at      TEXT    NOT NULL,

    -- Health score 0-100 and its grade label.
    -- Stored as plain integers/strings so they're easy to query and chart.
    score           INTEGER NOT NULL,
    grade           TEXT    NOT NULL,

    -- Quick-access counters so the History page doesn't have to JOIN
    -- and aggregate on every page load.
    pages_count     INTEGER NOT NULL,
    issues_count    INTEGER NOT NULL,
    high_count      INTEGER NOT NULL DEFAULT 0,
    medium_count    INTEGER NOT NULL DEFAULT 0,
    low_count       INTEGER NOT NULL DEFAULT 0,

    -- Average response time across pages that succeeded; NULL if
    -- nothing could be fetched.
    avg_response_time REAL
);


-- ------------------------------------------------------------
-- pages: one row per URL that the crawler attempted.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Which scan this page belongs to. Cascade-delete keeps the
    -- table tidy when the user removes an old scan.
    scan_id         INTEGER NOT NULL
                    REFERENCES scans(id) ON DELETE CASCADE,

    url             TEXT    NOT NULL,

    -- All three may be NULL: a connection failure leaves us with
    -- nothing but an error message.
    status_code     INTEGER,
    response_time   REAL,
    error           TEXT
);


-- ------------------------------------------------------------
-- issues: one row per detected problem.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS issues (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,

    scan_id         INTEGER NOT NULL
                    REFERENCES scans(id) ON DELETE CASCADE,

    url             TEXT    NOT NULL,

    -- The classifier output: type + severity, plus the human
    -- description and recommendation that the AI / UI need.
    issue_type      TEXT    NOT NULL,
    severity        TEXT    NOT NULL CHECK(severity IN ('High','Medium','Low')),

    -- Category groups issues so the UI can show "SEO", "Accessibility",
    -- "Performance", "Security", "Schema". Defaults to "SEO" for the
    -- existing analyzer — later stages will populate other values.
    category        TEXT    NOT NULL DEFAULT 'SEO',

    description     TEXT    NOT NULL,
    recommendation  TEXT    NOT NULL,

    -- Convenience snapshot copied from the page at scan time.
    status_code     INTEGER,
    response_time   REAL,

    -- Optional structured payload as JSON (e.g. the grouped 404 note's full
    -- list of URLs). NULL for ordinary issues.
    details         TEXT
);


-- ------------------------------------------------------------
-- category_scores: one row per (scan, audit category) sub-score.
-- Added in the per-page scoring stage. Because this is CREATE TABLE
-- IF NOT EXISTS, init_db() adds it transparently to older databases.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS category_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,

    scan_id         INTEGER NOT NULL
                    REFERENCES scans(id) ON DELETE CASCADE,

    -- e.g. "SEO", "Accessibility", "Security", "Schema".
    category        TEXT    NOT NULL,

    -- 0-100 sub-score for this category on this scan.
    score           INTEGER NOT NULL
);


-- ------------------------------------------------------------
-- Indices for the queries we actually run.
-- ------------------------------------------------------------

-- "Show recent scans for a given site" — used by the History page.
CREATE INDEX IF NOT EXISTS idx_scans_url_time
    ON scans(root_url, scanned_at DESC);

-- "All pages / issues that belong to scan X" — used everywhere.
CREATE INDEX IF NOT EXISTS idx_pages_scan
    ON pages(scan_id);
CREATE INDEX IF NOT EXISTS idx_issues_scan
    ON issues(scan_id);

-- "Look up issues by type" — used by diff computation and trends.
CREATE INDEX IF NOT EXISTS idx_issues_scan_type
    ON issues(scan_id, issue_type, url);

-- "All category sub-scores for scan X" — used when rebuilding a ScanResult.
CREATE INDEX IF NOT EXISTS idx_category_scores_scan
    ON category_scores(scan_id);
