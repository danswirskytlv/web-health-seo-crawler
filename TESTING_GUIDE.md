# SitePulse — Testing Guide

How to verify the project works end to end. Three parts, in order of
importance: the automated suite is the most important.

---

## Part 1 — Automated tests (~5 seconds)

**1. Activate the virtual environment:**

```bash
cd "/Users/danswir/Documents/Claude/Projects/Web Health & SEO Crawler"
source venv/bin/activate
```

**2. Run the whole suite:**

```bash
pytest -q
```

Expected: **369 passed**.

(If a stale cache ever gives a wrong count, force a clean run:
`pytest -q -p no:cacheprovider`.)

**3. Per-file counts** (handy when working on one area):

| File                          | Tests | Covers                                  |
|-------------------------------|------:|-----------------------------------------|
| `test_url_utils.py`           |   41  | URL normalize / is-internal / skip      |
| `test_analyzer.py`            |   28  | SEO checks orchestration                |
| `test_accessibility.py`       |   31  | Accessibility checks                    |
| `test_performance.py`         |   26  | Page weight / response-time checks      |
| `test_security.py`            |   55  | Security headers, cookies, disclosure   |
| `test_tls.py`                 |   20  | TLS / certificate logic (mocked)        |
| `test_privacy.py`             |   12  | Third-party trackers                    |
| `test_exposed_paths.py`       |    9  | Sensitive-path probing                  |
| `test_schema.py`              |   24  | schema.org structured data              |
| `test_scoring.py`             |   29  | Health score + per-category sub-scores  |
| `test_chatbot.py`             |   11  | Grounded chatbot                        |
| `test_root_cause.py`          |   15  | Scan-diff explanation                   |
| `test_database.py`            |   28  | SQLite save / get / list / diff         |
| `test_serializers.py`         |   16  | Dataclass → JSON                        |
| `test_reports.py`             |   12  | CSV + PDF export                        |
| `test_api.py`                 |   12  | FastAPI endpoints                       |

Every test uses in-memory HTML fixtures and mocks — no network, no running
server required.

---

## Part 2 — Manual end-to-end on the test site (~2 minutes)

Confirms the crawler really collects pages, headers, and cookies from a live
site.

**1. Terminal #1 — start the bundled test site (leave it running):**

```bash
python serve_test_site.py
```

**2. Terminal #2 (also `source venv/bin/activate`) — run the e2e check:**

```bash
python test_e2e_manual.py
```

Expected: a scan of `http://localhost:8000` with `[PASS]` lines.

> Note: the test site runs over **http**, so every page is correctly flagged
> "Site Not Served Over HTTPS", and the dev server's version shows up under
> Information Disclosure. That is expected behaviour, not a bug.

There are two other manual scripts for spot checks:

- `python test_crawler_manual.py` — crawler behaviour against the test site.
- `python test_tls_manual.py` — see the TLS section below.

---

## Part 3 — Live TLS / certificate checks (~1 minute)

The unit tests mock TLS; this script runs the real inspector against live
hosts, including deliberately-broken ones, so you see both a healthy result
and a correct failure.

```bash
python test_tls_manual.py
```

What proves it works:

- **www.google.com** / **github.com** → `handshake: OK`, `TLSv1.3 (current)`,
  and a real days-until-expiry number.
- **expired.badssl.com** → `handshake: FAILED` ("certificate has expired").
  This is CORRECT — the scanner flags it as "TLS Handshake Failed".
- **wrong.host.badssl.com** / **self-signed.badssl.com** → `FAILED`, as expected.
- **nonexistent.invalid…** → `FAILED` with a DNS error → fails gracefully
  instead of crashing.

> badssl.com is a public service built specifically for testing broken TLS.
> TLS runs only on real HTTPS hosts during a live scan; localhost is skipped
> on purpose (no real certificate).

---

## Part 4 — Visual check in the React UI (~3 minutes)

Shows the categories rendering in the dashboard.

**1. Start the whole stack:**

```bash
./run_dev.sh
```

This starts the API (:8001), the test site (:8000), and the frontend (:5173).
Open **http://localhost:5173**.

**2. Scan the test site:** enter `http://localhost:8000` and run a scan.

**3. What to look for:**

- The score gauge and per-category cards populate.
- The Issues board shows categories: Transport Security, Security Headers,
  Cookies, Information Disclosure, Accessibility, Performance, Privacy, SEO,
  Schema. Filtering by category updates the board.
- **"Slow Response Time"** appears under **Performance** (from `/faq.html`,
  which simulates a 3-second delay).

**4. To see TLS detect a real problem**, scan `https://expired.badssl.com` —
a "TLS Handshake Failed" issue should appear under Transport Security. Scan a
healthy HTTPS site for contrast: no TLS issues, proving it doesn't cry wolf.

---

## If something is off

- **Wrong test count** → stale cache: `pytest -q -p no:cacheprovider`.
- **`ModuleNotFoundError`** → the venv isn't active; re-run
  `source venv/bin/activate`.
- **Port already in use** → another server is still running; stop it (Ctrl+C)
  or change the port.
- **Frontend can't reach the API** → make sure the API is up on :8001
  (`./run_api.sh`) and check http://localhost:8001/api/health.
- **No security issues on an HTTPS site** → that can be correct! A
  well-configured site passes these checks. Scan the local http test site to
  see them fire.

All parts green = everything works end to end.
