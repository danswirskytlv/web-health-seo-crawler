#!/usr/bin/env bash
# ============================================================================
# SitePulse — one-command setup & run
#
#   ./start.sh
#
# Does EVERYTHING from a fresh clone:
#   1. Checks that python3 and npm exist
#   2. Creates the Python venv (if missing) and installs backend deps
#   3. Installs the frontend deps (if missing)
#   4. Creates .env from .env.example (if missing)
#   5. Starts the API (:8001), the test site (:8000) and the frontend (:5173)
#
# Safe to run repeatedly — it skips steps that are already done.
# Press Ctrl+C once to stop all three servers.
# ============================================================================
set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"

# --- Pretty output ----------------------------------------------------------
info()  { printf "\033[1;34m▶ %s\033[0m\n" "$1"; }
ok()    { printf "\033[1;32m✓ %s\033[0m\n" "$1"; }
warn()  { printf "\033[1;33m! %s\033[0m\n" "$1"; }
die()   { printf "\033[1;31m✗ %s\033[0m\n" "$1"; exit 1; }

# --- 0. Prerequisite checks -------------------------------------------------
info "Checking prerequisites…"
command -v python3 >/dev/null 2>&1 || die "python3 not found. Install Python 3.10+ and retry."
command -v npm     >/dev/null 2>&1 || die "npm not found. Install Node.js 18+ and retry."
ok "python3: $(python3 --version)   npm: $(npm --version)"

# --- 1. Python venv + backend deps -----------------------------------------
if [ ! -d "venv" ]; then
  info "Creating Python virtual environment (venv)…"
  python3 -m venv venv
  ok "venv created"
else
  ok "venv already exists"
fi

# shellcheck disable=SC1091
source venv/bin/activate

# Install backend deps only if a key package is missing (fast on re-runs).
if ! python -c "import fastapi" >/dev/null 2>&1; then
  info "Installing Python dependencies…"
  pip install --quiet --upgrade pip
  pip install --quiet -r requirements.txt
  ok "Python dependencies installed"
else
  ok "Python dependencies already installed"
fi

# --- 2. Frontend deps -------------------------------------------------------
if [ ! -d "frontend/node_modules" ]; then
  info "Installing frontend dependencies (npm install)…"
  ( cd frontend && npm install --silent )
  ok "Frontend dependencies installed"
else
  ok "Frontend dependencies already installed"
fi

# --- 3. .env ----------------------------------------------------------------
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  warn "Created .env from template. AI runs in fallback mode until you add a"
  warn "Gemini key (GEMINI_API_KEY=) — the app works fine without it."
else
  ok ".env present"
fi

# --- 4. Start the three servers --------------------------------------------
PIDS=()
cleanup() {
  echo ""
  info "Stopping SitePulse…"
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
  ok "Stopped."
}
trap cleanup INT TERM EXIT

echo ""
info "Starting API on :8001"
uvicorn api.main:app --reload --port 8001 &
PIDS+=($!)

info "Starting test site on :8000"
python serve_test_site.py &
PIDS+=($!)

info "Starting frontend on :5173"
( cd frontend && npm run dev ) &
PIDS+=($!)

echo ""
echo "──────────────────────────────────────────────"
echo "  SitePulse is starting up:"
echo "    Frontend : http://localhost:5173"
echo "    API docs : http://localhost:8001/docs"
echo "    Test site: http://localhost:8000"
echo ""
echo "  Open http://localhost:5173 in your browser."
echo "  Press Ctrl+C to stop everything."
echo "──────────────────────────────────────────────"

wait
