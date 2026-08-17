#!/usr/bin/env bash
# Builds the frontend and starts the backend, which serves both the UI and
# the API from a single process on a single port (http://localhost:8000).
# See backend/app/main.py -- it mounts frontend/dist and falls back to
# index.html for client-side routes, so there's no separate `npm run dev`
# needed for a normal run.
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8000}"

echo "==> Installing/building frontend..."
(cd frontend && npm install --no-audit --no-fund && npm run build)

echo "==> Setting up backend virtualenv..."
cd backend
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt

echo "==> Starting NeuroLLM on http://localhost:${PORT}"
echo "    (frontend + API both served from this one process)"
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
