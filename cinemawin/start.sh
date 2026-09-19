#!/bin/bash
# CinemaWin — startup script
# Usage: ./start.sh            (from the cinemawin/ folder)
# Runs the FastAPI backend (port 8002) + Vite frontend (port 5174) together.
#
# First run: creates backend/.env from backend/.env.example and stops so you
# can add your ANTHROPIC_API_KEY. Set CINEMAWIN_DEMO_MODE=1 in that file to
# try the whole app with canned story/score/finance output and no API key.

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"

# ── Clear stale servers from a previous run ──────────────────────────────────
free_port() {
  local port="$1" label="$2" pids
  command -v lsof >/dev/null 2>&1 || return 0
  pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  [ -n "$pids" ] || return 0
  echo "→ Port $port ($label) still held by an earlier run — stopping it..."
  echo "$pids" | xargs kill 2>/dev/null || true
  sleep 1
  pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
}
free_port 8002 "backend"
free_port 5174 "frontend"

# ── Backend ──────────────────────────────────────────────────────────────────
if [ ! -f "$BACKEND/.env" ]; then
  echo "⚠  No backend/.env found. Creating it from the template..."
  cp "$BACKEND/.env.example" "$BACKEND/.env"
  echo ""
  echo "  → Open $BACKEND/.env and add your ANTHROPIC_API_KEY, then re-run ./start.sh"
  echo "    (or set CINEMAWIN_DEMO_MODE=1 to explore with sample output first)."
  echo ""
  exit 1
fi

if [ ! -d "$BACKEND/.venv" ]; then
  echo "→ Creating Python virtual environment..."
  python3 -m venv "$BACKEND/.venv"
fi
# shellcheck disable=SC1091
source "$BACKEND/.venv/bin/activate"

echo "→ Checking Python dependencies..."
if ! pip install -q -r "$BACKEND/requirements.txt"; then
  echo ""
  echo "✗ pip install failed. Fix the error above and re-run ./start.sh"
  exit 1
fi

# ── Frontend ─────────────────────────────────────────────────────────────────
if [ ! -d "$ROOT/node_modules" ]; then
  echo "→ Installing frontend dependencies (first run only)..."
  (cd "$ROOT" && npm install)
fi

# ── Launch both ──────────────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo "→ Shutting down..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "→ Starting backend on http://localhost:8002 ..."
(cd "$BACKEND" && exec uvicorn main:app --host 127.0.0.1 --port 8002 --reload) &
BACKEND_PID=$!

echo "→ Starting frontend on http://localhost:5174 ..."
(cd "$ROOT" && exec npm run dev -- --host 127.0.0.1 --port 5174) &
FRONTEND_PID=$!

echo ""
echo "  CinemaWin is running:"
echo "    App:      http://localhost:5174"
echo "    API docs: http://localhost:8002/docs"
echo ""
echo "  Press Ctrl+C to stop both servers."
wait
