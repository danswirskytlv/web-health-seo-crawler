# SitePulse — Presentation Guide

**Web Health & SEO Crawler with AI Assistant**
Authors: Kamil Sason, Dan Swirsky

---

## Part 1 — How to Run the Project (Step by Step)

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and **npm** (for the React frontend)
- A terminal (macOS / Linux; on Windows use WSL or Git Bash)
- *(Optional)* A free **Google Gemini API key** — https://aistudio.google.com/app/apikey

The app runs fully **without** an API key: the AI features fall back to a built-in deterministic answer instead of calling Gemini. Nothing crashes.

### Step 1 — Set up the Python backend

From the project root:

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
```

This creates an isolated virtual environment and installs the backend dependencies (FastAPI, requests, BeautifulSoup, reportlab, google-generativeai, pytest, etc.).

### Step 2 — Install the frontend

```bash
cd frontend
npm install
cd ..
```

### Step 3 — (Optional) Add the Gemini API key

```bash
cp .env.example .env
# open .env and paste your key after GEMINI_API_KEY=
```

Skip this if you want to demo the deterministic AI fallback.

### Step 4 — Start everything with one command

```bash
./run_dev.sh
```

This single script starts three processes together:

| Process | Port | URL |
|---|---|---|
| FastAPI backend (uvicorn) | 8001 | http://localhost:8001 |
| Bundled demo test site | 8000 | http://localhost:8000 |
| React frontend (Vite) | 5173 | http://localhost:5173 |

Press **Ctrl+C** once to stop all three cleanly.

Then open **http://localhost:5173** in the browser.

### Step 5 — Run a scan (the live demo)

1. Go to the **Scan** screen.
2. Enter a URL to audit. For a stable, offline demo use the bundled test site: **`http://localhost:8000`** (it has intentionally seeded bugs). For a real site you can use e.g. `https://ilaynoy.com`.
3. Configure options if you want (max pages, depth, TLS check, exposed-path probing).
4. Run the scan and walk through the results: **Overview** (health score + category cards), **Issues** (filterable issue board + the AI "Explain & Fix" drawer), **Chat** (grounded "Ask Your Site" AI), **Reports** (CSV + PDF export), **History** (score-over-time + two-scan compare with AI root-cause).

### Running pieces individually (optional)

```bash
./run_api.sh                 # API only, on :8001
python serve_test_site.py    # bundled test site, on :8000
cd frontend && npm run dev   # frontend, on :5173
```

The API has interactive Swagger docs at **http://localhost:8001/docs**.

### Running the tests

```bash
pytest -q
```

Expected: **369 passing** in a few seconds. Tests use in-memory HTML fixtures and require **neither** the test site nor the API to be running — a good point to mention to the lecturer.

---

## Part 2 — Architecture, Libraries & Technologies

### Architectural overview

SitePulse is a **layered pipeline** with a strict separation of concerns. The central design decision — and the thing worth emphasizing to the lecturer — is the boundary between **deterministic detection** and **AI explanation**:

> The **rule-based analyzers** decide *what counts as a problem*. The **AI** only *explains and fixes* problems that were already detected. The AI never detects issues itself.

This boundary is what makes the system **predictable, testable, and defensible**. Every issue on screen can be traced back to a concrete rule, not to a black-box model. The UI even makes this explicit with "Detected by SitePulse Analyzer · Explained by AI" trust labels.

### The data pipeline

Data flows through the system in one direction, carried by typed dataclasses:

```
URL
 │
 ▼
Crawler ─────────────►  List[PageResult]     (BFS over internal pages)
 │
 ▼
Analyzers ───────────►  List[Issue]          (8 audit areas, rule-based)
 │
 ▼
Scorer ──────────────►  ScoreResult          (0–100 + per-category sub-scores)
 │
 ▼
Database (SQLite) ───►  persisted scan history
 │
 ├──► FastAPI ──► React SPA   (interactive UI)
 ├──► AI layer  (Gemini)      (explain / fix / chat / root-cause)
 └──► Reports   (CSV + PDF)
```

Each stage consumes the previous stage's output and produces the next. Because every boundary is a **typed dataclass** (`PageResult`, `Issue`, `ScoreResult`, `ScanResult` in `models/result_models.py`) rather than a loose dict, the shape of the data is enforced across the whole codebase — mistyped fields raise errors instead of silently returning `None`, and each module can be unit-tested in isolation.

### The layers in detail

**1. Crawler (`crawler/`)**
Given a root URL, it walks every internal page on the same domain using **BFS** (breadth-first), depth-limited and page-count-limited. Design choices worth defending:

- **BFS over DFS** — pages closer to the root are usually more important, so if the page limit is hit, shallow coverage beats deep coverage of one branch.
- **Concurrency via `ThreadPoolExecutor`** — the work is almost entirely network I/O, so threads are cheap and effective. `asyncio` was deliberately avoided to keep the code readable at this scale (50–200 pages).
- **`robots.txt` is respected** by default (opt-out available), with a polite configurable delay between requests.
- **Errors never crash the crawl** — every fetch is wrapped in try/except; failures become `PageResult` entries with an `error` field, and the BFS continues.
- `url_utils.py` handles URL **normalization** (collapsing `/`, `/index.html`, etc. to a canonical URL), same-domain checks, link extraction, and extension filtering (skips PDFs, images, archives).

**2. Analyzers (`analyzer/`)**
Rule-based issue detection across **eight audit areas**, orchestrated by `seo_analyzer.py` (`analyze_pages`):

- **SEO** — titles, meta descriptions, headings, broken links (flags the *linking* page, with optional live re-verification to drop transient anti-bot 404s)
- **Accessibility** — alt text, labels, structure
- **Performance** — page weight / response-time checks
- **Transport Security (TLS)** — live certificate checks
- **Security Headers** — CSP, HSTS, etc.
- **Cookies** — secure/HttpOnly flags
- **Information Disclosure** — leaked server info, and opt-in sensitive-path probing (`exposed_paths.py`)
- **Privacy** — third-party trackers detected from the page's own markup (GDPR-relevant)
- **Schema.org** — structured-data / rich-result markup

Each analyzer emits `Issue` objects with a **severity** (High / Medium / Low) and a **category**.

**3. Scorer (`analyzer/scoring.py`)**
An **explainable, non-ML** health score. Per page:

```
penalty    = 10×High + 5×Medium + 2×Low   (that page's issues)
penalty    = min(penalty, 100)
page_score = 100 - penalty
overall    = average(page_score across all pages)
```

The same method restricted to one category yields a **per-category sub-score**. Grade bands: 90–100 Excellent, 75–89 Good, 50–74 Needs Improvement, 0–49 Critical. The selling point: *a user can always point at the dashboard and say "I lost N points because of these M issues."* No black box.

**4. AI layer (`ai/`)**
Powered by **Google Gemini** via `google-generativeai`. Three capabilities:

- `ai_assistant.py` — per-issue **explain & fix** (plain-language summary, why it matters, a copy-paste fix), with the relevant page context injected into the prompt.
- `chatbot.py` — a **grounded** "Ask Your Site" chatbot (answers are grounded in the actual scan data, not open-ended).
- `root_cause.py` — a scan-to-scan **diff explainer** ("why did the score drop between these two scans?").

Prompts live in `prompts.py`. The AI requests **structured JSON output** for predictable rendering, and **degrades gracefully**: no API key, a network failure, or malformed JSON all return a usable deterministic fallback — the user never sees a stack trace.

**5. Persistence (`database/`)**
Plain **SQLite** via the stdlib `sqlite3` (zero-config, no server). `db.py` exposes `save_scan`, `get_scan`, `list_scans`, and `get_diff`. Every scan is stored, enabling history browsing and two-scan diffs over time. Schema in `schema.sql`.

**6. API layer (`api/`)**
A **thin FastAPI** wrapper — it contains *no* analysis logic. Every endpoint just calls a backend function and serializes the result to JSON (`serializers.py` converts dataclasses → dict). **Pydantic** models validate incoming requests (e.g. `ScanRequest`). Endpoints include `/api/scan`, `/api/scans`, `/api/diff`, the three report exports, and `/api/ai/{fix,chat,root-cause}`. The schema exists on startup via a FastAPI **lifespan** hook.

**7. Reports (`reports/`)**
`csv_exporter.py` produces Issues + Pages CSVs; `pdf_exporter.py` builds a print-ready PDF with **reportlab** — chosen so there's **no headless browser dependency** (no Puppeteer/Chromium to install).

**8. Frontend (`frontend/`)**
A **React 18 + Vite** single-page app, routed with **React Router**, with **Recharts** for the score gauges and history charts. In development, the Vite dev server (:5173) **proxies `/api/*`** to the FastAPI backend (:8001), so the frontend uses relative URLs and needs **no CORS setup**. Shared scan state lives in a React Context (`ScanContext`). Screens: Landing, Overview, Scan, Issues, Chat, Reports, History, Settings.

### Technology & library summary

| Layer | Choice | Why this choice |
|---|---|---|
| Language | **Python 3.10+** | Mature ecosystem, fast iteration |
| API | **FastAPI** + **uvicorn** | Thin, typed JSON layer; auto Swagger docs |
| Validation | **Pydantic** | Request-model validation on the API boundary |
| Frontend | **React 18** + **Vite** + **React Router** | Real SPA, fast dev server, client routing |
| Charts | **Recharts** | Score gauges + history charts |
| Crawling | **requests** + **BeautifulSoup4** + **lxml** | Standard, well-understood, easy to test |
| Concurrency | **ThreadPoolExecutor** | Network-bound work; simpler than asyncio |
| TLS | **certifi** CA bundle | Live certificate verification |
| AI | **google-generativeai** (Gemini) | Generous free tier, fast, structured JSON |
| Storage | **SQLite** (stdlib `sqlite3`) | Zero-config local scan history |
| Reports | **reportlab** | Print-quality PDFs, no headless browser |
| Config | **python-dotenv** | Keeps the API key out of source control |
| Tests | **pytest** (369 tests) | Industry standard; run in seconds |

### Points worth emphasizing to the lecturer

1. **Deterministic detection vs. AI explanation** — the core architectural boundary; makes the whole system testable and defensible.
2. **Typed dataclasses at every layer boundary** — a single predictable data shape flows through crawler → analyzer → scorer → UI/reports.
3. **Explainable scoring** — no black-box ML; every point lost is traceable to specific issues.
4. **Graceful degradation** — the app is fully functional with no API key and never surfaces a crash to the user.
5. **369 unit tests** with in-memory fixtures — no external services needed to run the suite.
6. **Thin API principle** — FastAPI adds zero business logic; it only exposes the backend, so the backend stays independently usable and testable.
