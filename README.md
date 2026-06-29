# SitePulse — Web Health & SEO Crawler (with AI Assistant)

A local web application that scans a website for technical SEO, accessibility,
performance, security, privacy, and schema issues, then uses **Google Gemini**
to explain each issue in plain language and suggest a copy-paste fix.

The architecture is a **Python backend** (crawler + rule-based analyzers + AI +
SQLite history) exposed through a **FastAPI** layer, with a **React + Vite**
single-page frontend on top.

Built as a final BSc project in Computer Science.

---

## What it does

You enter a website URL. The application:

1. **Crawls** internal pages on the same domain — BFS, depth-limited,
   politely concurrent, respects `robots.txt`.
2. **Analyzes** each page with rule-based analyzers across eight audit areas:
   SEO, accessibility, performance, transport security (TLS), security headers,
   cookies, information disclosure, privacy/trackers, and schema.org markup.
3. **Scores** the site 0–100 with an explainable per-page formula, plus a
   sub-score for each category.
4. **Explains** each issue with a Gemini-powered assistant — plain-language
   summary, why it matters, and a ready-to-paste fix. Includes a grounded
   chatbot and a scan-to-scan "root cause" diff explainer.
5. **Stores** every scan in a local SQLite database so you can browse history
   and diff two scans over time.
6. **Exports** results to CSV (issues + pages) and to a print-ready PDF report.

Separation of concerns is deliberate: the **analyzers** decide what counts as a
problem, and the **AI** only explains and fixes. This keeps the system
predictable, testable, and easy to defend.

---

## Tech stack

| Layer        | Choice                                    | Why                                       |
|--------------|-------------------------------------------|-------------------------------------------|
| Language     | **Python 3.10+**                          | Mature ecosystem, fast iteration          |
| API          | **FastAPI** + **uvicorn**                 | Thin, typed JSON layer over the backend   |
| Frontend     | **React 18** + **Vite** + **React Router**| Real SPA matching the product mockup      |
| Charts       | **Recharts**                              | Score gauges and history charts           |
| Crawling     | **requests** + **BeautifulSoup4** + **lxml** | Standard, well-understood, easy to test|
| Concurrency  | **concurrent.futures.ThreadPoolExecutor** | Network-bound work, simple model          |
| AI           | **google-generativeai** (Gemini)          | Generous free tier, fast responses        |
| Storage      | **SQLite** (stdlib `sqlite3`)             | Zero-config local scan history            |
| Reports      | **reportlab**                             | Print-quality PDFs, no headless browser   |
| Tests        | **pytest**                                | Industry standard                         |
| Config       | **python-dotenv**                         | Keeps the API key out of source control   |

---

## Features

- BFS crawler with configurable max-pages, max-depth, timeout, workers, and polite delay
- `robots.txt` honored by default; opt-out available
- Same-domain crawl with extension filtering (skips PDFs, images, archives)
- URL normalization that collapses `/`, `/index.html`, etc. to a canonical URL
- Cross-page broken-link detection — flags the *linking* page, with optional live re-verification to drop transient anti-bot 404s
- Eight analyzers: SEO, accessibility, performance, TLS/transport security, security headers, cookies, information disclosure, privacy/trackers, and schema.org
- Health score with per-page model and per-category sub-scores, plus four grade bands (Excellent / Good / Needs Improvement / Critical)
- AI Assistant powered by Gemini:
  - per-issue page-context passed into the prompt
  - structured JSON output for predictable rendering
  - grounded chatbot and scan-diff root-cause explainer
  - graceful deterministic fallback when no API key is set or the API fails
- Local SQLite scan history with two-scan diff
- React SPA: dashboard, score gauge, category cards, issue board, AI drawer, history, reports
- CSV export (issues + pages) and print-ready PDF report
- **369 unit tests** across crawler, analyzers, scoring, AI, database, serializers, and the API
- Bundled local test site with intentionally seeded bugs for stable demos

---

## Project structure

```
Web Health & SEO Crawler/
├── api/                     # FastAPI layer (thin wrapper over the backend)
│   ├── main.py              # Endpoints: scan, history, diff, reports, AI
│   └── serializers.py       # Dataclass -> JSON
│
├── crawler/                 # Site crawler
│   ├── crawler.py           # BFS + concurrency + robots.txt
│   └── url_utils.py         # normalize, is_internal, extract_links, ...
│
├── analyzer/                # Rule-based issue detection
│   ├── seo_analyzer.py      # Orchestrates all analyzers
│   ├── accessibility.py     # Accessibility checks
│   ├── performance.py       # Page weight / response-time checks
│   ├── tls.py               # Live TLS / certificate checks
│   ├── security.py          # Security headers, cookies, info disclosure
│   ├── privacy.py           # Third-party trackers
│   ├── exposed_paths.py     # Sensitive-path probing (opt-in)
│   ├── schema_org.py        # schema.org structured-data checks
│   └── scoring.py           # 0-100 health score + per-category sub-scores
│
├── ai/                      # AI Assistant (Gemini + deterministic fallback)
│   ├── ai_assistant.py      # Per-issue explain + fix
│   ├── chatbot.py           # Grounded chatbot
│   ├── root_cause.py        # Scan-diff explanation
│   └── prompts.py           # Prompt templates
│
├── database/                # SQLite scan history
│   ├── db.py                # save_scan, get_scan, list_scans, get_diff
│   └── schema.sql
│
├── reports/                 # Export
│   ├── csv_exporter.py      # Issues + Pages CSV
│   └── pdf_exporter.py      # Print-ready PDF
│
├── models/                  # Shared dataclasses
│   └── result_models.py     # PageResult, Issue, ScoreResult, ScanResult
│
├── frontend/                # React + Vite SPA (see frontend/README.md)
│   ├── vite.config.js       # dev server + /api proxy to :8001
│   └── src/
│       ├── App.jsx          # routes + dashboard shell
│       ├── api.js           # API client
│       ├── screens/         # Landing, Overview, Scan, Issues, Chat,
│       │                    #   Reports, History, Settings
│       ├── components/      # Sidebar, ScoreGauge, AiFixDrawer, ...
│       ├── state/           # ScanContext (shared scan result)
│       ├── lib/             # categoryMeta, humanize helpers
│       └── styles/theme.css # design system
│
├── sample_sites/            # Local test site + documented ground truth
│   └── test_site/           # HTML pages with intentional issues
│
├── tests/                   # 369 unit tests
├── serve_test_site.py       # Local test-site server (port 8000)
├── run_dev.sh               # Start API + test site + frontend together
├── run_api.sh               # Start just the API
├── requirements.txt
├── pytest.ini
├── conftest.py
└── .env.example             # Template — copy to .env and add your key
```

---

## Setup

### 1. Python backend

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
```

### 2. Frontend

```bash
cd frontend
npm install
cd ..
```

### 3. Configure the Gemini API key (optional)

Get a free key at https://aistudio.google.com/app/apikey, then:

```bash
cp .env.example .env
# Open .env and paste the key after GEMINI_API_KEY=
```

If you skip this step the app still runs — the AI features return a
deterministic built-in answer instead of calling Gemini.

---

## Running the app

The simplest way is the all-in-one dev script, which starts the API
(:8001), the bundled test site (:8000), and the frontend (:5173):

```bash
./run_dev.sh
```

Then open **http://localhost:5173**.

To run pieces individually:

```bash
./run_api.sh                          # API only, on :8001
python serve_test_site.py             # bundled test site, on :8000
cd frontend && npm run dev            # frontend, on :5173
```

The API is documented interactively at http://localhost:8001/docs.

---

## Frontend

The UI is a React 18 + Vite single-page app under `frontend/`, routed with
React Router. In development the Vite server (:5173) proxies `/api/*` to the
FastAPI backend (:8001), so the frontend uses relative URLs and there's no CORS
setup needed. See `frontend/README.md` for full details.

| Path        | Screen   | What it does                                          |
|-------------|----------|-------------------------------------------------------|
| `/`         | Landing  | Marketing landing page (full-bleed, no sidebar)       |
| `/app`      | Overview | Score gauge, metric cards, health-by-category, action plan |
| `/scan`     | Scan     | Configure and run a scan (URL, depth, TLS toggles)    |
| `/issues`   | Issues   | Searchable/filterable issue board + AI "Explain & Fix" drawer |
| `/ai`       | Chat     | Grounded "Ask Your Site" AI chat                      |
| `/reports`  | Reports  | Download Issues CSV, Pages CSV, and the PDF report    |
| `/history`  | History  | Score-over-time chart + two-scan compare with AI root cause |
| `/settings` | Settings | System / AI status                                    |

The design makes the architecture explicit with "Detected by SitePulse
Analyzer · Explained by AI" trust labels — deterministic detection, AI only
explains.

To build the frontend for production:

```bash
cd frontend
npm run build       # outputs to frontend/dist/
npm run preview     # preview the production build locally
```

---

## Running the bundled test site

To work offline and get a stable demo:

1. Start everything with `./run_dev.sh`.
2. In the UI, scan `http://localhost:8000`.

The test site lives in `sample_sites/test_site/` and contains pages with
intentionally seeded bugs documented in `sample_sites/README.md`.

---

## Running the tests

```bash
pytest -q
```

Expected: **369 passed** in a few seconds. The tests use in-memory HTML
fixtures and do not require the test site or the API to be running.

---

## How the health score is computed

The score uses an explainable per-page model:

```
For each page:
    penalty    = 10×High + 5×Medium + 2×Low   (that page's issues)
    penalty    = min(penalty, 100)
    page_score = 100 - penalty
overall_score  = average(page_score over all pages)
```

The same method restricted to one category at a time yields a per-category
sub-score (SEO, Accessibility, Performance, Security, Schema, ...).

| Score range | Grade               |
|-------------|---------------------|
| 90 – 100    | Excellent           |
| 75 – 89     | Good                |
| 50 – 74     | Needs Improvement   |
|  0 – 49     | Critical            |

No black-box ML in the scoring — a user can always point at the dashboard and
say "I lost N points because of these M issues."

---

## Authors

- Kamil Sason
- Dan Swirsky
