#!/bin/bash
# BGF Production OS — startup script
# Usage: ./start.sh
# Runs backend (port 8001) + frontend (port 5173) in parallel

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

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
  source "$BACKEND/.venv/bin/activate"
  pip install -q -r "$BACKEND/requirements.txt"
else
  source "$BACKEND/.venv/bin/activate"
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
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT INT TERM

echo ""
echo "  BGF Production OS running."
echo "  Dashboard → http://localhost:5173"
echo "  API       → http://localhost:8001/api/health"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

wait
