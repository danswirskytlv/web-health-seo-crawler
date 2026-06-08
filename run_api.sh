#!/usr/bin/env bash
# Start the sitePulse API (FastAPI + uvicorn) on port 8001.
#
# Usage:
#   ./run_api.sh
#
# The React dev server (Vite, port 5173) calls http://localhost:8001/api/...
set -euo pipefail

cd "$(dirname "$0")"

# Activate the venv if present.
if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

exec uvicorn api.main:app --reload --port 8001
