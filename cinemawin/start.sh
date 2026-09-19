#!/bin/bash
# CinemaWin — startup script
# Usage: ./start.sh            (from the cinemawin/ folder)
# Runs the FastAPI backend + Vite frontend together. Ports come from
# backend/.env (CINEMAWIN_PORT, CINEMAWIN_FRONTEND_PORT); defaults 8002/5174.
#
# First run: creates backend/.env from backend/.env.example and stops so you
# can add an AI provider key. Several providers have a free tier — see the
# README. Set CINEMAWIN_DEMO_MODE=1 in that file to try the whole app with
# sample output and no key at all.

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"

# Ports come from backend/.env so the documented CINEMAWIN_PORT is real: the
# backend, the port we clear, and the Vite dev proxy all follow the same value.
read_env() {
  local key="$1" default="$2" value=""
  [ -f "$BACKEND/.env" ] && value="$(grep -E "^${key}=" "$BACKEND/.env" | tail -1 | cut -d= -f2- | tr -d '"'"'"'\r' | xargs || true)"
  echo "${value:-$default}"
}

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
BACKEND_PORT="$(read_env CINEMAWIN_PORT 8002)"
FRONTEND_PORT="$(read_env CINEMAWIN_FRONTEND_PORT 5174)"

free_port "$BACKEND_PORT" "backend"
free_port "$FRONTEND_PORT" "frontend"

# ── Backend ──────────────────────────────────────────────────────────────────
if [ ! -f "$BACKEND/.env" ]; then
  echo "⚠  No backend/.env found. Creating it from the template..."
  cp "$BACKEND/.env.example" "$BACKEND/.env"
  echo ""
  echo "  → Open $BACKEND/.env, set CINEMAWIN_LLM_PROVIDER and paste a key,"
  echo "    then re-run ./start.sh. Free options (no credit card):"
  echo "      gemini  → https://aistudio.google.com/apikey"
  echo "      groq    → https://console.groq.com/keys"
  echo "      ollama  → https://ollama.com/download  (local, no key at all)"
  echo "    Or set CINEMAWIN_DEMO_MODE=1 to explore with sample output first."
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

echo "→ Starting backend on http://localhost:$BACKEND_PORT ..."
(cd "$BACKEND" && exec uvicorn main:app --host 127.0.0.1 --port "$BACKEND_PORT" --reload) &
BACKEND_PID=$!

echo "→ Starting frontend on http://localhost:$FRONTEND_PORT ..."
# CINEMAWIN_PORT reaches vite.config.js, which points the /api proxy at it.
(cd "$ROOT" && CINEMAWIN_PORT="$BACKEND_PORT" exec npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT") &
FRONTEND_PID=$!

echo ""
echo "  CinemaWin is running:"
echo "    App:      http://localhost:$FRONTEND_PORT"
echo "    API docs: http://localhost:$BACKEND_PORT/docs"
echo ""
echo "  Press Ctrl+C to stop both servers."
wait
