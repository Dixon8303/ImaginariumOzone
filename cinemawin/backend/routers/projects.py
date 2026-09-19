"""/api/projects/* — the Project entity (owner-scoped)."""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

import config
import database
import security

router = APIRouter(prefix="/projects", tags=["projects"])

_TEXT_FIELDS = set(database.PROJECT_TEXT_FIELDS)
_JSON_FIELDS = set(database.PROJECT_JSON_FIELDS)
_VERDICTS = {"RECOMMEND", "CONSIDER", "PASS"}
# Derived from the owner's plan on every read; client writes are ignored.
_DERIVED = {"score_locked", "pitch_deck_unlocked", "id", "owner_id", "created_date", "updated_date"}


def _cap(value: Any, limit: int) -> str:
    if value is None:
        return ""
    return str(value)[:limit]


def _opt_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def sanitize(body: dict, *, creating: bool) -> dict:
    """Keep known fields only, cap text lengths, coerce types. Unknown keys are ignored."""
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="body_must_be_object")
    out: dict[str, Any] = {}
    for key, value in body.items():
        if key in _DERIVED:
            continue
        if key == "title":
            title = _cap(value, config.PROJECT_TITLE_MAX).strip()
            if creating and not title:
                raise HTTPException(status_code=422, detail="title_required")
            if title:
                out["title"] = title
        elif key == "track":
            out["track"] = value if value in config.VALID_TRACKS else "Writer"
        elif key == "genre":
            out["genre"] = _cap(value, config.PROJECT_TITLE_MAX)
        elif key == "current_module":
            out["current_module"] = value if value in config.VALID_MODULES else "develop"
        elif key == "maturity_level":
            out["maturity_level"] = max(0, min(7, _opt_int(value) or 0))
        elif key == "story_score":
            score = _opt_int(value)
            out["story_score"] = None if score is None else max(0, min(100, score))
        elif key == "story_verdict":
            out["story_verdict"] = value if value in _VERDICTS else None
        elif key == "budget_ceiling":
            out["budget_ceiling"] = _opt_int(value)
        elif key == "paywall_email_captured":
            out["paywall_email_captured"] = bool(value)
        elif key in _TEXT_FIELDS:
            if key in ("story_verdict_label", "story_headline"):
                out[key] = None if value is None else _cap(value, config.PROJECT_TEXT_MAX)
            else:
                out[key] = _cap(value, config.PROJECT_TEXT_MAX)
        elif key in _JSON_FIELDS:
            out[key] = value if isinstance(value, (list, dict)) or value is None else None
        # else: unknown field, ignored
    if creating and "title" not in out:
        raise HTTPException(status_code=422, detail="title_required")
    return out


async def _json_body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid_json")
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="body_must_be_object")
    return body


async def _load(project_id: str, user: dict) -> dict:
    row = await database.get_project(project_id, user["id"])
    if row is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    return database.row_to_project(row, user["plan"])


@router.get("")
async def list_projects(
    sort: str = Query("-updated_date"),
    limit: int = Query(50, ge=1, le=200),
    user: dict = security.CurrentUser,
) -> list[dict]:
    if sort not in database.PROJECT_SORTS:
        sort = "-updated_date"
    rows = await database.list_projects(user["id"], sort, limit)
    return [database.row_to_project(r, user["plan"]) for r in rows]


@router.post("", status_code=201)
async def create_project(request: Request, user: dict = security.CurrentUser) -> JSONResponse:
    fields = sanitize(await _json_body(request), creating=True)
    pid = await database.create_project(user["id"], fields)
    return JSONResponse(status_code=201, content=await _load(pid, user))


@router.get("/{project_id}")
async def get_project(project_id: str, user: dict = security.CurrentUser) -> dict:
    return await _load(project_id, user)


@router.patch("/{project_id}")
async def patch_project(
    project_id: str, request: Request, user: dict = security.CurrentUser
) -> dict:
    fields = sanitize(await _json_body(request), creating=False)
    if not await database.update_project(project_id, user["id"], fields):
        raise HTTPException(status_code=404, detail="project_not_found")
    return await _load(project_id, user)


@router.delete("/{project_id}")
async def delete_project(project_id: str, user: dict = security.CurrentUser) -> dict:
    if not await database.delete_project(project_id, user["id"]):
        raise HTTPException(status_code=404, detail="project_not_found")
    return {"ok": True}
