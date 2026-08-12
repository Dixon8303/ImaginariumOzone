#!/bin/bash
# BGF Production OS — startup script
# Usage: ./start.sh
# Runs backend (port 8001) + frontend (port 5173) in parallel

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── Clear stale servers from a previous run ──────────────────────────────────
# uvicorn --reload runs a reloader plus a worker, and `npm run dev` runs vite
# as a child. Killing only the launcher leaves the real server alive holding
# the port, so closing the terminal (or an incomplete Ctrl+C) strands them and
# the next run fails with "Address already in use". Clear our own ports first.
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

free_port 8001 "backend"
free_port 5173 "frontend"

# ── Backend ──────────────────────────────────────────────────────────────────
BACKEND="$ROOT/backend"

if [ ! -f "$BACKEND/.env" ]; then
  echo "⚠  No .env found. Creating from template..."
  cp "$BACKEND/.env.example" "$BACKEND/.env"
  # Patch paths for this machine
  sed -i '' "s|./backend/outputs|$BACKEND/outputs|g" "$BACKEND/.env"
  sed -i '' "s|./backend/bgf.db|$BACKEND/bgf.db|g" "$BACKEND/.env"
  sed -i '' "s|YOUR_USERNAME|$(whoami)|g" "$BACKEND/.env"
  echo ""
  echo "  → Open $BACKEND/.env and add your ANTHROPIC_API_KEY, then re-run."
  echo ""
  exit 1
fi

if [ ! -d "$BACKEND/.venv" ]; then
  echo "→ Creating Python virtual environment..."
  python3 -m venv "$BACKEND/.venv"
fi
source "$BACKEND/.venv/bin/activate"

# Always sync dependencies. This used to run only when the venv was first
# created, which meant any package added to requirements.txt afterwards never
# reached an existing install — the feature just silently didn't work. pip is
# fast and does nothing when everything is already satisfied.
echo "→ Checking Python dependencies..."
if ! pip install -q -r "$BACKEND/requirements.txt"; then
  echo ""
  echo "⚠  Could not install Python dependencies."
  echo "   Try:  cd backend && .venv/bin/pip install -r requirements.txt"
  echo ""
  exit 1
fi

echo "→ Starting backend on http://localhost:8001"
cd "$BACKEND"
uvicorn main:app --port 8001 --reload &
BACKEND_PID=$!

# ── Frontend ─────────────────────────────────────────────────────────────────
cd "$ROOT"

if [ ! -d "node_modules" ]; then
  echo "→ Installing npm dependencies..."
  npm install --silent
fi

echo "→ Starting frontend on http://localhost:5173"
npm run dev &
FRONTEND_PID=$!

# ── Cleanup on exit ──────────────────────────────────────────────────────────
# Kill the children too. uvicorn --reload's worker and npm's vite process are
# what actually hold the ports; killing only the launchers orphans them, which
# is what left ports 8001/5173 occupied between runs.
cleanup() {
  for pid in $BACKEND_PID $FRONTEND_PID; do
    [ -n "$pid" ] || continue
    pkill -P "$pid" 2>/dev/null || true
    kill "$pid" 2>/dev/null || true
  done
  echo 'Stopped.'
}
trap cleanup EXIT INT TERM

echo ""
echo "  BGF Production OS running."
echo "  Dashboard → http://localhost:5173"
echo "  API       → http://localhost:8001/api/health"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

wait
