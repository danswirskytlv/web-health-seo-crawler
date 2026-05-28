# Web Health & SEO Crawler (with AI Assistant)

A local desktop application that scans websites for technical SEO and web
health issues, then uses **Google Gemini** to explain each issue in plain
language and suggest a copy-paste fix.

Built as a final BSc project in Computer Science.

---

## What it does

You enter a website URL. The application:

1. **Crawls** internal pages on the same domain — BFS, depth-limited,
   politely concurrent, respects `robots.txt`.
2. **Detects** seven kinds of issues with a rule-based analyzer:
   missing `<title>`, missing `<h1>`, missing meta description, images
   without `alt`, broken links, slow responses, server errors.
3. **Scores** the site from 0 to 100 with an explainable formula
   (High = -10, Medium = -5, Low = -2).
4. **Explains** each issue with a Google Gemini-powered assistant —
   plain-language summary, why it matters, and a ready-to-paste HTML fix.
5. **Exports** results to CSV (issues + pages) and to a print-ready PDF
   report with the health score, summary cards, and a colored issues table.

Separation of concerns is deliberate: the **analyzer** decides what counts
as a problem, and the **AI** only explains and fixes. This makes the system
predictable, testable, and easy to defend.

---

## Tech stack

| Layer        | Choice                                  | Why                                      |
|--------------|-----------------------------------------|------------------------------------------|
| Language     | **Python 3.10+**                        | Fast iteration, mature ecosystem         |
| UI           | **Streamlit**                           | Lets us stay in Python — no JS framework |
| Crawling     | **requests** + **BeautifulSoup4**       | Standard, well-understood, easy to test  |
| Concurrency  | **concurrent.futures.ThreadPoolExecutor** | Network-bound work, simple model       |
| AI           | **google-generativeai** (Gemini)        | Generous free tier, fast responses       |
| Reports      | **reportlab**                           | Print-quality PDFs, no headless browser  |
| Tests        | **pytest**                              | Industry standard                        |
| Config       | **python-dotenv**                       | Keeps the API key out of source control  |

---

## Features

- BFS crawler with configurable max-pages, max-depth, and timeout
- Multi-threaded fetching (configurable workers + polite delay)
- `robots.txt` honored by default; opt-out available
- Same-domain crawl with extension filtering (skips PDFs, images, archives)
- URL normalization that collapses `/`, `/index.html`, etc., to a single canonical URL
- Issue detection that **skips error pages** so 404s don't get double-flagged as "missing meta description"
- Cross-page broken-link detection — flags the *linking* page, not just the broken target
- Health score with four explainable grade bands (Excellent / Good / Needs Improvement / Critical)
- AI Assistant powered by Gemini, with:
  - per-issue page-context (current title, H1, meta) passed into the prompt
  - structured JSON output schema for predictable rendering
  - in-session cache so re-clicking doesn't burn quota
  - per-session call limit (cost guardrail, configurable in `.env`)
  - graceful fallback when the API key is missing or the API fails
- Streamlit UI with dashboard cards, visual health-score gauge,
  severity filtering, color-coded issues table, and a working AI panel
- CSV export (issues + pages)
- Print-ready PDF report
- **88 unit tests** covering URL utilities, the analyzer, scoring, and reports
- Bundled local test site with intentionally seeded bugs for stable demos

---

## Project structure

```
web-health-seo-crawler/
├── app.py                   # Streamlit UI (entry point)
├── serve_test_site.py       # Local test site server (port 8000)
├── requirements.txt
├── pytest.ini
├── conftest.py
├── .env.example             # Template — copy to .env and add your key
├── .gitignore
├── README.md
│
├── crawler/                 # Site crawler
│   ├── crawler.py           # BFS + concurrency + robots.txt
│   └── url_utils.py         # normalize, is_internal, extract_links, ...
│
├── analyzer/                # Rule-based issue detection
│   ├── seo_analyzer.py      # 7 SEO / health checks
│   └── scoring.py           # 0-100 health score
│
├── ai/                      # AI Assistant
│   ├── ai_assistant.py      # Gemini integration + fallback
│   └── prompts.py           # Prompt templates
│
├── reports/                 # Export
│   ├── csv_exporter.py      # Issues + Pages CSV
│   └── pdf_exporter.py      # Print-ready PDF
│
├── models/                  # Shared dataclasses
│   └── result_models.py     # PageResult, Issue, ScoreResult, ScanResult
│
├── sample_sites/            # Local test site + ground truth
│   ├── README.md            # Documents the seeded bugs (ground truth)
│   └── test_site/           # 8 HTML pages with intentional issues
│
└── tests/                   # 88 unit tests
    ├── test_url_utils.py
    ├── test_analyzer.py
    ├── test_scoring.py
    └── test_reports.py
```

---

## Setup

### 1. Clone

```bash
git clone https://github.com/<your-user>/web-health-seo-crawler.git
cd web-health-seo-crawler
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Gemini API key

Get a free key at https://aistudio.google.com/app/apikey, then:

```bash
cp .env.example .env
# Open .env in your editor and paste the key after GEMINI_API_KEY=
```

If you skip this step the app still runs — the AI Assistant just returns
a deterministic built-in answer instead of calling Gemini.

---

## Running the app

```bash
streamlit run app.py
```

The UI opens at http://localhost:8501.

---

## Running the bundled test site

To work offline (and to get a stable demo for the project defense):

```bash
# In one terminal:
python serve_test_site.py

# In another terminal:
streamlit run app.py
# then scan http://localhost:8000 from the sidebar
```

The test site lives in `sample_sites/test_site/` and contains 8 pages with
intentionally seeded bugs documented in `sample_sites/README.md`.

Expected scan results: 9 pages crawled (8 reachable + 1 broken link to a
non-existent `/portfolio.html`), **11 issues**, **Health Score 34/100
(Critical)**.

---

## Running the tests

```bash
pytest
```

Expected: **88 passed** in < 1 second. The tests do not require the test
site to be running — every test uses in-memory HTML fixtures.

---

## How the scan results are computed

The health score uses a deliberately simple, explainable formula:

```
score = 100
      - 10 × (number of High-severity issues)
      -  5 × (number of Medium-severity issues)
      -  2 × (number of Low-severity issues)
clamped to [0, 100]
```

| Score range | Grade               |
|-------------|---------------------|
| 90 – 100    | Excellent           |
| 75 – 89     | Good                |
| 50 – 74     | Needs Improvement   |
|  0 – 49     | Critical            |

A user can always point at the dashboard and say "I lost N points because
of these M issues" — no black-box ML inside the scoring.

---

## Demo flow (suggested for the project defense)

1. Start the test site (`python serve_test_site.py`).
2. Start Streamlit (`streamlit run app.py`).
3. In the sidebar, enter `http://localhost:8000` and click **Scan**.
4. Walk through the dashboard cards and the health-score gauge.
5. Open the issues table, sort by severity, filter to High only.
6. In the AI Assistant, pick **Missing Title — /about.html** and click
   **Ask AI for Fix**. Show the simple explanation, why-it-matters, and
   the ready-to-paste `<title>` snippet.
7. Click **Issues CSV** and **PDF Report** to demonstrate export.

Talking points:
- The crawler detects the technical issue.
- The analyzer classifies it (severity, type).
- The AI explains how to fix it in plain language.
- The report lets the user keep working after the scan is over.

---

## Out of scope (Future improvements)

The prototype intentionally does **not** include:
- User accounts / authentication
- Persistent database / scan history
- Cloud hosting / SaaS
- Scheduled scans
- Auto-fix that actually modifies the target site
- Direct integrations with WordPress / Wix / Shopify

Adding any of these would be a natural next step after the prototype.

---

## Authors

- Kamil Sason
- Dan Swirsky
