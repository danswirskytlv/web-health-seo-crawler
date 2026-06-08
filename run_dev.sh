#!/usr/bin/env bash
# SitePulse — start the whole dev stack with one command.
#
#   ./run_dev.sh
#
# Starts three processes:
#   1. The API        (FastAPI / uvicorn) on http://localhost:8001
#   2. The test site  (bundled demo site)  on http://localhost:8000
#   3. The frontend   (Vite / React)       on http://localhost:5173
#
# Press Ctrl+C once to stop all three.
set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"

# Activate the Python venv if present.
if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

PIDS=()
cleanup() {
  echo ""
  echo "Stopping SitePulse dev stack…"
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  # Also stop the Vite child if it lingers.
  wait 2>/dev/null || true
  echo "Done."
}
trap cleanup INT TERM EXIT

echo "▶ Starting API on :8001"
uvicorn api.main:app --reload --port 8001 &
PIDS+=($!)

echo "▶ Starting test site on :8000"
python serve_test_site.py &
PIDS+=($!)

echo "▶ Starting frontend on :5173"
( cd frontend && npm run dev ) &
PIDS+=($!)

echo ""
echo "──────────────────────────────────────────────"
echo " SitePulse dev stack is starting up:"
echo "   Frontend : http://localhost:5173"
echo "   API      : http://localhost:8001/api/health"
echo "   Test site: http://localhost:8000"
echo ""
echo " Press Ctrl+C to stop everything."
echo "──────────────────────────────────────────────"

# Wait on all background jobs.
wait
