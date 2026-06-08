# SitePulse — Frontend (React + Vite)

The premium dashboard UI for SitePulse. It talks to the Python API
(`api/main.py`) over HTTP/JSON.

## Architecture

```
  React (Vite, :5173)  ──/api──▶  FastAPI (:8001)  ──▶  crawler / analyzer / AI / DB
```

The Vite dev server proxies `/api/*` to `http://localhost:8001`, so the
frontend uses relative URLs and there's no CORS hassle in development.

## Run it (two terminals)

**Terminal 1 — the API** (from the project root):

```bash
cd ..                 # project root
source venv/bin/activate
./run_api.sh          # FastAPI on http://localhost:8001
```

**Terminal 2 — the frontend** (from this `frontend/` folder):

```bash
npm install           # first time only — installs React, Vite, etc.
npm run dev           # Vite on http://localhost:5173
```

Then open **http://localhost:5173**.

> For a full demo, also run the bundled test site in a third terminal
> (`python serve_test_site.py` from the project root) and scan
> `http://localhost:8000`.

## Project structure

```
frontend/
├─ index.html              app entry HTML
├─ package.json            deps + scripts
├─ vite.config.js          dev server + /api proxy
└─ src/
   ├─ main.jsx             React entry
   ├─ App.jsx              routes + app shell
   ├─ api.js               typed-ish client for the SitePulse API
   ├─ styles/theme.css     design system (navy/cyan glassmorphism)
   ├─ components/          Sidebar, Logo, PageHeader, …
   └─ screens/             one file per screen (Overview, Issues, …)
```

## Screens

All screens are live and wired to the API:

- **Overview** — health-score gauge, metric cards with trends, Health by
  Category, and the Recommended Action Plan.
- **Scan** — configure and run a scan (URL, depth, TLS / exposed-path toggles).
- **Issues** — searchable, filterable issue board with the slide-in AI Fix
  drawer ("Explain & Fix").
- **Ask Your Site** — the grounded AI chat.
- **Reports** — download Issues CSV, Pages CSV, and the PDF health report.
- **History** — score-over-time chart, recent scans, and the Compare view with
  AI root-cause insights.
- **Settings** — system/AI status and the architecture note.

The design follows the SitePulse mockup: deep-navy glassmorphism, electric-cyan
accent, and the "Detected by SitePulse Analyzer · Explained by AI" trust labels
that make the architecture (deterministic detection, AI only explains) explicit.
