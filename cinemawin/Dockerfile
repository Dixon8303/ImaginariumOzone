# CinemaWin — one container running the whole app.
#
# The FastAPI backend serves the built frontend, so this single image is the
# entire product: no separate web host, no CORS to configure.
#
# Build:  docker build -t cinemawin ./cinemawin
# Run:    docker run -p 8002:8002 -e GEMINI_API_KEY=... cinemawin
#
# It also deploys as-is to any host that takes a Dockerfile and sets $PORT
# (Render, Fly.io, Railway) and to Hugging Face Spaces (which uses 7860).
# See README.md → "Put it online for free".

# ── Stage 1: build the frontend ─────────────────────────────────────────────
FROM node:22-slim AS frontend

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci

COPY index.html vite.config.js tailwind.config.js postcss.config.js jsconfig.json ./
COPY doctrine.json ./
COPY public ./public
COPY src ./src
RUN npm run build

# ── Stage 2: the app ────────────────────────────────────────────────────────
FROM python:3.12-slim

# Keeps the image small and the logs unbuffered so hosted log tails are live.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY doctrine.json ./doctrine.json
COPY backend ./backend
COPY --from=frontend /build/dist ./dist

# The database defaults to a path inside the container. On a host with
# ephemeral disk (Hugging Face Spaces free tier, Render free tier) this resets
# whenever the container restarts — mount a volume or point
# CINEMAWIN_DATABASE_PATH at persistent storage if the data matters.
ENV CINEMAWIN_DATABASE_PATH=/app/data/cinemawin.db
RUN mkdir -p /app/data

# Hosted platforms hand the port over in $PORT; 8002 is the local default.
ENV PORT=8002
EXPOSE 8002

WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8002}"]
