# sitePulse — Plan to Rebuild the UI as a Real Web App (Path 1)

Goal: a frontend that matches the mockup (radial gauge, category cards, issue
board, AI drawer, history charts) **and** runs on the real backend you've
already built and tested. Streamlit stays as a working backup.

---

## The architecture (what changes, what doesn't)

```
            BEFORE (now)                       AFTER (Path 1)
   ┌─────────────────────────┐       ┌──────────────┐   HTTP/JSON   ┌──────────────────┐
   │   Streamlit (app.py)    │       │  Frontend    │ ───────────▶ │   FastAPI (API)  │
   │  UI  +  calls backend   │       │ HTML/CSS/JS  │ ◀─────────── │  thin wrapper    │
   └─────────────────────────┘       │ (the mockup) │   results    └────────┬─────────┘
            │                        └──────────────┘                       │ calls
            ▼                                                                ▼
   crawler / analyzer / AI / DB  ◀────────── UNCHANGED ──────────▶  crawler / analyzer / AI / DB
```

- **Backend logic** (crawler, analyzer, scoring, AI, DB): **untouched.** All
  309 tests keep passing.
- **New: a thin API layer** (FastAPI) that calls those existing functions and
  returns JSON. ~150–250 lines total.
- **New: a real frontend** (HTML/CSS/JS) that looks like the mockup and talks
  to the API.
- **Streamlit** stays runnable as a backup the whole time.

---

## Guiding principles

1. **Don't break the backend.** The API only *calls* existing functions; it
   never reimplements logic. Tests stay green throughout.
2. **One screen at a time.** Build the API + one full screen, see it work
   end-to-end, then add the next. If we stop early, what exists still works.
3. **Real data from step one.** Every screen we build is wired to the real
   crawler/analyzer via the API — not mock data.
4. **Streamlit is the safety net.** It keeps working until the new UI fully
   replaces it (your call, later).

---

## Phase A — The API layer (foundation)

Wrap the existing backend in a small FastAPI service. No new logic.

**Endpoints (first set):**

| Method | Path | Calls (existing) | Returns |
|---|---|---|---|
| `POST` | `/api/scan` | `crawl_site` → `analyze_pages` → `calculate_score` → `save_scan` | full scan result JSON |
| `GET` | `/api/scans` | `list_scans` | scan history list |
| `GET` | `/api/scans/{id}` | `get_scan` | one stored scan |
| `GET` | `/api/diff?from=&to=` | `get_diff` | diff between two scans |
| `POST` | `/api/ai/fix` | `generate_ai_fix` | AI explanation + fix for one issue |
| `POST` | `/api/ai/root-cause` | `analyze_diff` | root-cause insight |
| `POST` | `/api/ai/chat` | `chatbot.answer` | chat reply |

**Work items:**
- A1. Add `fastapi` + `uvicorn` to requirements.
- A2. Create `api/` package: `api/main.py` (app + routes), `api/serializers.py`
  (dataclass → JSON helpers).
- A3. A serializer that turns `ScanResult` / `Issue` / `ScoreResult` into clean
  JSON (the shape the frontend wants: score, grade, category_scores, metrics,
  issues with severity/category/url/description).
- A4. CORS enabled (so the frontend can call it during dev).
- A5. `tests/test_api.py` — hits each endpoint with a mocked/seeded backend so
  it runs offline.
- A6. A run script: `run_api.sh` (`uvicorn api.main:app --reload`).

**Done when:** `curl localhost:8001/api/scan` against the local test site
returns the full JSON. No frontend yet.

---

## Phase B — Frontend foundation + design system

Set up the look-and-feel once, so every screen is consistent with the mockup.

- B1. Choose the stack. **Recommended: plain HTML + CSS + vanilla JS** (no
  build step, easy to run and submit) — or React/Vite if you prefer. Decide
  before starting.
- B2. `frontend/` folder. Global stylesheet implementing the mockup's design
  tokens: deep-navy background, glassmorphism panels, cyan glow, the exact
  colors (green/amber/red status), rounded cards, spacing, typography.
- B3. App shell: the **left nav rail** (Overview, Scan, Issues, AI Fix,
  Reports, History, Settings) + top bar, exactly like the mockup.
- B4. sitePulse logo (the pulse-wave mark) and brand wordmark in the rail.
- B5. A tiny API client (`api.js`) that calls the Phase-A endpoints.

**Done when:** the empty shell (nav rail + header + empty content area) renders
and looks like the mockup's chrome.

---

## Phase C — Screen 1: Overview Dashboard (the centerpiece)

The screen from the mockup's center. Build it fully, wired to `/api/scan`.

- C1. URL bar card: input + "Run Health Scan" + "Compare with Previous Scan".
- C2. **Radial health-score gauge** (SVG) — 68/100 with color by grade. This is
  the signature visual.
- C3. AI summary panel next to the gauge.
- C4. Metric cards row (Pages, Issues, Broken links, Avg response, Critical,
  AI fixes) with trend vs. previous scan.
- C5. **Health by Category** grid — one card per category (SEO, Performance,
  Security Headers, Accessibility, etc.) with score, mini progress bar, issue
  count, "View issues".
- C6. "Scan in progress" state: the stepper (Crawling → Analyzing → Checking
  links → AI) + animated pulse + progress bar.
- C7. Empty state: the welcome screen with the 3 feature cards.

**Done when:** you enter a URL, click Run Health Scan, and the real scan result
renders in this dashboard with the gauge and category cards.

---

## Phase D — Screen 2: Issues board

The smart, filterable issue list (not a raw table).

- D1. Search bar + filter chips (All / Critical / High / … / by category).
- D2. Sort controls (severity, page, category).
- D3. Issue rows/cards: severity badge, category, title, URL, plain-language
  explanation, "Explain with AI" / "Generate Fix" buttons.
- D4. Clicking an issue opens the **AI Fix drawer** (right side): what was
  found, why it matters, suggested HTML, copy button, and the trust label
  "Detected by sitePulse Analyzer · Explained by AI". Wired to `/api/ai/fix`.

**Done when:** issues from a real scan are filterable, and the AI drawer
explains a selected issue.

---

## Phase E — Screen 3: History & Compare

The long-term maintenance story.

- E1. Health-score-over-time line chart (from `/api/scans`).
- E2. Issue-trend-by-severity chart.
- E3. Recent scans table with "Compare".
- E4. Compare view: new / resolved / still-open issues + "Get AI Insights"
  (wired to `/api/ai/root-cause`).

**Done when:** history renders with charts and two scans can be compared.

---

## Phase F — Remaining screens

- F1. Reports screen (CSV / PDF download cards via the existing reports module).
- F2. AI Chat screen (wired to `/api/ai/chat`).
- F3. Settings screen (scan parameters).
- F4. "Recommended Action Plan" section on the overview.

---

## Phase G — Polish & wrap-up

- G1. Microcopy pass (friendly, non-technical language from the prompt).
- G2. Trust labels / architecture tooltips throughout.
- G3. Responsive tidy-up.
- G4. A single run script that starts API + frontend together.
- G5. README + screenshots; decide whether to retire or keep Streamlit.

---

## Effort & sequencing (honest estimate)

| Phase | What you get | Relative size |
|---|---|---|
| A — API | Backend reachable over HTTP/JSON | Small (logic exists) |
| B — Frontend shell | The mockup's look + nav | Medium |
| C — Overview | The signature dashboard, real data | **Largest single screen** |
| D — Issues | Filterable board + AI drawer | Medium-large |
| E — History | Trends + compare | Medium |
| F — Reports/Chat/Settings | Remaining screens | Medium |
| G — Polish | Production feel | Small-medium |

After **A + B + C** you already have a real, impressive, working product that
looks like the mockup for the main flow. Everything after that is additive.

---

## Two decisions to confirm before Phase A

1. **Frontend stack:** plain HTML/CSS/JS (no build step, simplest to run and
   submit) vs. React/Vite (more powerful, needs Node tooling).
2. **API port / run model:** run API and frontend as two local processes
   (simple) — fine for a project demo.

Once those are set, we start with **Phase A: the API layer.**
