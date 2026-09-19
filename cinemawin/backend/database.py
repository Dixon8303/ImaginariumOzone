"""
CinemaWin database — aiosqlite schema and helpers.

Tables: users, otp_codes, reset_tokens, projects. Projects keep scalar columns
for indexed/simple fields and a `data_json` column for the rest; `row_to_project`
flattens both into the API's Project shape.
"""

import json
import secrets
from datetime import datetime, timezone
from typing import Any, Optional

import aiosqlite

import config

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    plan TEXT NOT NULL DEFAULT 'entry',
    role TEXT NOT NULL DEFAULT 'user',
    email_verified INTEGER NOT NULL DEFAULT 0,
    created_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS otp_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    code TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_otp_email ON otp_codes(email);

CREATE TABLE IF NOT EXISTS reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    title TEXT NOT NULL,
    track TEXT NOT NULL DEFAULT 'Writer',
    genre TEXT NOT NULL DEFAULT '',
    current_module TEXT NOT NULL DEFAULT 'develop',
    maturity_level INTEGER NOT NULL DEFAULT 0,
    story_score INTEGER,
    story_verdict TEXT,
    data_json TEXT NOT NULL DEFAULT '{}',
    created_date TEXT NOT NULL,
    updated_date TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_id);
"""

# Project fields stored in data_json (everything not a scalar column).
PROJECT_TEXT_FIELDS = (
    "logline",
    "premise",
    "protagonist",
    "core_need",
    "emotional_wound",
    "central_question",
    "theme",
    "story_verdict_label",
    "story_headline",
    "first_step",
    "production_notes",
    "paywall_email",
)
PROJECT_JSON_FIELDS = ("score_breakdown", "structure", "finance", "top_fixes")
PROJECT_SCALAR_COLUMNS = (
    "title",
    "track",
    "genre",
    "current_module",
    "maturity_level",
    "story_score",
    "story_verdict",
)
PROJECT_DATA_DEFAULTS: dict[str, Any] = {
    "logline": "",
    "premise": "",
    "protagonist": "",
    "core_need": "",
    "emotional_wound": "",
    "central_question": "",
    "theme": "",
    "story_verdict_label": None,
    "story_headline": None,
    "first_step": "",
    "score_breakdown": None,
    "structure": None,
    "finance": None,
    "top_fixes": None,
    "production_notes": "",
    "budget_ceiling": None,
    "paywall_email": "",
    "paywall_email_captured": False,
}

PROJECT_SORTS = {
    "updated_date": "updated_date ASC",
    "-updated_date": "updated_date DESC",
    "created_date": "created_date ASC",
    "-created_date": "created_date DESC",
    "title": "title COLLATE NOCASE ASC",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def connect() -> aiosqlite.Connection:
    return aiosqlite.connect(str(config.DATABASE_PATH))


async def init_db() -> None:
    config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with connect() as db:
        await db.executescript(CREATE_SQL)
        await db.commit()


# ── Users ───────────────────────────────────────────────────────────────────

def row_to_user(row: aiosqlite.Row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "plan": row["plan"],
        "role": row["role"],
        "email_verified": bool(row["email_verified"]),
        "created_date": row["created_date"],
    }


async def create_user(email: str, password_hash: str, verified: bool) -> dict:
    uid = new_id("usr")
    created = now_iso()
    plan = config.DEFAULT_PLAN if config.DEFAULT_PLAN in config.VALID_PLANS else "entry"
    async with connect() as db:
        await db.execute(
            "INSERT INTO users (id, email, password_hash, plan, role, email_verified, created_date) "
            "VALUES (?, ?, ?, ?, 'user', ?, ?)",
            (uid, email, password_hash, plan, 1 if verified else 0, created),
        )
        await db.commit()
    return {
        "id": uid,
        "email": email,
        "plan": plan,
        "role": "user",
        "email_verified": verified,
        "created_date": created,
    }


async def get_user_by_email(email: str) -> Optional[aiosqlite.Row]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE email = ?", (email,))
        return await cur.fetchone()


async def get_user_by_id(user_id: str) -> Optional[aiosqlite.Row]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return await cur.fetchone()


async def mark_user_verified(email: str) -> None:
    async with connect() as db:
        await db.execute("UPDATE users SET email_verified = 1 WHERE email = ?", (email,))
        await db.commit()


async def set_user_password(user_id: str, password_hash: str) -> None:
    async with connect() as db:
        await db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id)
        )
        await db.commit()


# ── OTP codes ───────────────────────────────────────────────────────────────

async def create_otp(email: str, code: str, expires_at: str) -> None:
    async with connect() as db:
        # Invalidate any outstanding codes for this email so only the newest works.
        await db.execute(
            "UPDATE otp_codes SET used = 1 WHERE email = ? AND used = 0", (email,)
        )
        await db.execute(
            "INSERT INTO otp_codes (email, code, expires_at, used, created_at) VALUES (?, ?, ?, 0, ?)",
            (email, code, expires_at, now_iso()),
        )
        await db.commit()


async def consume_otp(email: str, code: str) -> bool:
    """Returns True and marks the code used if a live, unused code matches."""
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id FROM otp_codes WHERE email = ? AND code = ? AND used = 0 AND expires_at > ? "
            "ORDER BY id DESC LIMIT 1",
            (email, code, now_iso()),
        )
        row = await cur.fetchone()
        if row is None:
            return False
        await db.execute("UPDATE otp_codes SET used = 1 WHERE id = ?", (row["id"],))
        await db.commit()
        return True


# ── Reset tokens ────────────────────────────────────────────────────────────

async def create_reset_token(user_id: str, token: str, expires_at: str) -> None:
    async with connect() as db:
        await db.execute(
            "INSERT INTO reset_tokens (user_id, token, expires_at, used, created_at) VALUES (?, ?, ?, 0, ?)",
            (user_id, token, expires_at, now_iso()),
        )
        await db.commit()


async def consume_reset_token(token: str) -> Optional[str]:
    """Returns the user_id and marks the token used if live and unused."""
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id, user_id FROM reset_tokens WHERE token = ? AND used = 0 AND expires_at > ?",
            (token, now_iso()),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        await db.execute("UPDATE reset_tokens SET used = 1 WHERE id = ?", (row["id"],))
        await db.commit()
        return row["user_id"]


# ── Projects ────────────────────────────────────────────────────────────────

def derive_plan_flags(plan: str) -> dict:
    """score_locked / pitch_deck_unlocked are derived from the owner's plan on every read."""
    return {
        "score_locked": plan == "entry",
        "pitch_deck_unlocked": plan == "premium",
    }


def row_to_project(row: aiosqlite.Row, owner_plan: str) -> dict:
    try:
        data = json.loads(row["data_json"] or "{}")
    except (TypeError, ValueError):
        data = {}
    project: dict[str, Any] = {
        "id": row["id"],
        "owner_id": row["owner_id"],
        "created_date": row["created_date"],
        "updated_date": row["updated_date"],
        "title": row["title"],
        "track": row["track"],
        "genre": row["genre"],
        "current_module": row["current_module"],
        "maturity_level": row["maturity_level"],
        "story_score": row["story_score"],
        "story_verdict": row["story_verdict"],
    }
    for key, default in PROJECT_DATA_DEFAULTS.items():
        project[key] = data.get(key, default)
    project.update(derive_plan_flags(owner_plan))
    return project


def _split_fields(fields: dict) -> tuple[dict, dict]:
    scalars = {k: v for k, v in fields.items() if k in PROJECT_SCALAR_COLUMNS}
    data = {k: v for k, v in fields.items() if k in PROJECT_DATA_DEFAULTS}
    return scalars, data


async def create_project(owner_id: str, fields: dict) -> str:
    """`fields` must already be sanitized (see routers/projects.py)."""
    pid = new_id("prj")
    ts = now_iso()
    scalars, data = _split_fields(fields)
    async with connect() as db:
        await db.execute(
            "INSERT INTO projects (id, owner_id, title, track, genre, current_module, maturity_level, "
            "story_score, story_verdict, data_json, created_date, updated_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                pid,
                owner_id,
                scalars.get("title", ""),
                scalars.get("track", "Writer"),
                scalars.get("genre", ""),
                scalars.get("current_module", "develop"),
                scalars.get("maturity_level", 0),
                scalars.get("story_score"),
                scalars.get("story_verdict"),
                json.dumps(data),
                ts,
                ts,
            ),
        )
        await db.commit()
    return pid


async def get_project(project_id: str, owner_id: str) -> Optional[aiosqlite.Row]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM projects WHERE id = ? AND owner_id = ?", (project_id, owner_id)
        )
        return await cur.fetchone()


async def list_projects(owner_id: str, sort: str, limit: int) -> list[aiosqlite.Row]:
    order = PROJECT_SORTS.get(sort, PROJECT_SORTS["-updated_date"])
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            f"SELECT * FROM projects WHERE owner_id = ? ORDER BY {order} LIMIT ?",
            (owner_id, limit),
        )
        return list(await cur.fetchall())


async def update_project(project_id: str, owner_id: str, fields: dict) -> bool:
    """Merge sanitized `fields` into the project. Returns False if not found/not owner."""
    scalars, data_updates = _split_fields(fields)
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT data_json FROM projects WHERE id = ? AND owner_id = ?", (project_id, owner_id)
        )
        row = await cur.fetchone()
        if row is None:
            return False
        try:
            data = json.loads(row["data_json"] or "{}")
        except (TypeError, ValueError):
            data = {}
        data.update(data_updates)

        sets = [f"{col} = ?" for col in scalars]
        params: list[Any] = list(scalars.values())
        sets.append("data_json = ?")
        params.append(json.dumps(data))
        sets.append("updated_date = ?")
        params.append(now_iso())
        params.extend([project_id, owner_id])
        await db.execute(
            f"UPDATE projects SET {', '.join(sets)} WHERE id = ? AND owner_id = ?", params
        )
        await db.commit()
        return True


async def delete_project(project_id: str, owner_id: str) -> bool:
    async with connect() as db:
        cur = await db.execute(
            "DELETE FROM projects WHERE id = ? AND owner_id = ?", (project_id, owner_id)
        )
        await db.commit()
        return cur.rowcount > 0
