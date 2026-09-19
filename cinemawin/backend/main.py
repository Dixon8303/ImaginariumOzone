"""
CinemaWin backend — FastAPI app.

Run from inside cinemawin/backend:
    uvicorn main:app --port 8002

Mounts /api/* routers, GET /api/health, and — when ../dist exists — serves the
built frontend as a SPA (static assets + index.html fallback for any non-/api
path).
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import config
import database
from routers import app as app_router
from routers import auth, functions, projects
from services import providers

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("cinemawin")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await database.init_db()
    provider = providers.status()
    log.info(
        "CinemaWin backend ready — provider=%s model=%s configured=%s demo_mode=%s smtp=%s db=%s",
        provider["provider"] or "(none)",
        provider["craft_model"],
        provider["configured"],
        config.DEMO_MODE,
        config.SMTP_CONFIGURED,
        config.DATABASE_PATH,
    )
    if not provider["configured"] and not config.DEMO_MODE:
        log.warning(
            "No LLM provider is configured and demo mode is off — the four story "
            "functions will return 503. Set a provider key in .env (several have a "
            "free tier; see README) or set CINEMAWIN_DEMO_MODE=1."
        )
    if config.SECRET_KEY_EPHEMERAL:
        log.warning(
            "CINEMAWIN_SECRET_KEY is unset — generated a random key for this boot. "
            "All sessions will reset when the server restarts. Set it in .env."
        )
    yield


app = FastAPI(title=config.APP_NAME, lifespan=lifespan)

# CINEMAWIN_CORS_ORIGINS="*" is the common case for a static frontend hosted
# somewhere else (GitHub Pages) calling this backend. Credentials are off in
# that mode because "*" and allow_credentials are incompatible — and CinemaWin
# does not need them: the session rides on an Authorization header our own
# code sets, not on a cookie.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if config.CORS_ALLOW_ALL else config.CORS_ORIGINS,
    allow_credentials=not config.CORS_ALLOW_ALL,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(functions.router, prefix=API_PREFIX)
app.include_router(app_router.router, prefix=API_PREFIX)


@app.get(f"{API_PREFIX}/health")
async def health() -> dict:
    return {
        "ok": True,
        "demo_mode": config.DEMO_MODE,
        "llm_configured": providers.is_configured(),
        "provider": providers.status()["provider"],
    }


# ── SPA static mount (production) ───────────────────────────────────────────

DIST_DIR: Path = config.DIST_DIR
INDEX_FILE = DIST_DIR / "index.html"

if DIST_DIR.is_dir() and INDEX_FILE.is_file():
    assets_dir = DIST_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="not_found")
        candidate = (DIST_DIR / full_path).resolve()
        # Serve a real file from dist (favicon, manifest…) if it exists and is inside dist.
        if full_path and candidate.is_file() and DIST_DIR in candidate.parents:
            return FileResponse(str(candidate))
        return FileResponse(str(INDEX_FILE))

    log.info("Serving SPA from %s", DIST_DIR)
else:
    log.info("No frontend build at %s — API only (run vite build to enable the SPA).", DIST_DIR)
