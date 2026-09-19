"""
/api/functions/* — the four LLM functions.

developStory is public (the intake runs before sign-up) and IP rate-limited.
The other three require auth. Every function: truncate inputs → demo or Claude
→ deterministic post-processing → contract shape.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, HTTPException, Request

import config
import database
import security
from services import demo_responses, llm, postprocess

log = logging.getLogger("cinemawin.functions")
router = APIRouter(prefix="/functions", tags=["functions"])


# ── In-memory sliding-window rate limiter (per client IP) ───────────────────

class SlidingWindowLimiter:
    def __init__(self, limit: int, window_sec: int):
        self.limit = limit
        self.window = window_sec
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._hits[key]
            cutoff = now - self.window
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


develop_limiter = SlidingWindowLimiter(config.DEVELOP_RATE_LIMIT, config.DEVELOP_RATE_WINDOW_SEC)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


# ── Input handling ──────────────────────────────────────────────────────────

_LIMITS = {"title": config.FUNCTION_TITLE_MAX, "logline": config.FUNCTION_LOGLINE_MAX}


def _truncate(value: Any, key: str) -> str:
    if value is None:
        return ""
    return str(value)[: _LIMITS.get(key, config.FUNCTION_TEXT_MAX)]


async def _fields(request: Request, keys: tuple[str, ...]) -> dict:
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid_json")
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="body_must_be_object")
    return {k: _truncate(body.get(k), k) for k in keys}


# ── Dispatch: demo → Claude → postprocess ───────────────────────────────────

async def _run(
    fields: dict,
    demo_fn: Callable[[dict], dict],
    llm_fn: Callable[[dict], Awaitable[dict]],
    post_fn: Callable[[dict], dict],
) -> dict:
    if config.DEMO_MODE:
        result = post_fn(demo_fn(fields))
        # The client renders a banner off this flag so canned output is never
        # mistaken for a real read of the user's film.
        result["demo"] = True
        return result
    if not llm.is_configured():
        raise HTTPException(status_code=503, detail="llm_not_configured")
    try:
        raw = await llm_fn(fields)
    except llm.LLMNotConfigured:
        raise HTTPException(status_code=503, detail="llm_not_configured")
    except llm.LLMRefused:
        raise HTTPException(status_code=502, detail="llm_refused")
    except llm.LLMError as exc:
        log.error("LLM error: %s", exc)
        raise HTTPException(status_code=502, detail="llm_error")
    return post_fn(raw)


@router.post("/developStory")
async def develop_story(request: Request) -> dict:
    if not develop_limiter.allow(client_ip(request)):
        raise HTTPException(status_code=429, detail="rate_limited")
    fields = await _fields(request, ("title", "logline", "genre", "track"))
    if not fields["logline"].strip():
        raise HTTPException(status_code=400, detail="logline_required")
    return await _run(
        fields, demo_responses.develop_story, llm.develop_story, postprocess.process_develop_story
    )


@router.post("/buildStructure")
async def build_structure(request: Request, user: dict = security.CurrentUser) -> dict:
    fields = await _fields(
        request, ("title", "logline", "premise", "protagonist", "central_question", "theme", "genre")
    )
    return await _run(
        fields, demo_responses.build_structure, llm.build_structure, postprocess.process_build_structure
    )


@router.post("/scoreStory")
async def score_story(request: Request, user: dict = security.CurrentUser) -> dict:
    fields = await _fields(
        request,
        ("title", "logline", "premise", "protagonist", "central_question", "theme", "genre", "track"),
    )
    return await _run(
        fields, demo_responses.score_story, llm.score_story, postprocess.process_score_story
    )


@router.post("/buildFinance")
async def build_finance(request: Request, user: dict = security.CurrentUser) -> dict:
    fields = await _fields(
        request, ("title", "logline", "genre", "premise", "story_score", "story_verdict")
    )
    # The deck and the waterfall are Premium. Gate them here, not just in the
    # UI: a blurred div still ships the real text to the browser.
    deck_unlocked = database.derive_plan_flags(user["plan"])["pitch_deck_unlocked"]
    return await _run(
        fields,
        demo_responses.build_finance,
        llm.build_finance,
        lambda raw: postprocess.process_build_finance(raw, deck_unlocked=deck_unlocked),
    )
