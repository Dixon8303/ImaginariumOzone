import aiosqlite
import json
import uuid
from datetime import datetime
from config import DATABASE_PATH

DB = DATABASE_PATH

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'ASSISTED',
    status TEXT NOT NULL DEFAULT 'draft',
    keyword TEXT,
    score INTEGER,
    title_options TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS pipeline_stages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id TEXT NOT NULL,
    stage_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT,
    output_json TEXT,
    UNIQUE(episode_id, stage_name)
);

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    scene_index INTEGER NOT NULL,
    asset_type TEXT NOT NULL,
    prompt TEXT,
    negative_prompt TEXT,
    motion_notes TEXT,
    file_path TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    comfyui_prompt_id TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS performances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id TEXT NOT NULL,
    ctr_24h REAL,
    ctr_48h REAL,
    ctr_7d REAL,
    retention_pct REAL,
    watch_time_sec INTEGER,
    session_depth REAL,
    shorts_views INTEGER,
    recorded_at TEXT
);

CREATE TABLE IF NOT EXISTS thumbnails (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    version TEXT NOT NULL,
    file_path TEXT,
    ctr REAL,
    is_winner INTEGER DEFAULT 0,
    deployed_at TEXT
);

CREATE TABLE IF NOT EXISTS shorts (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    short_type TEXT NOT NULL,
    file_path TEXT,
    views INTEGER DEFAULT 0,
    velocity REAL DEFAULT 0,
    recycled INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS interventions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id TEXT NOT NULL,
    issue TEXT,
    action TEXT,
    result TEXT,
    insight TEXT,
    created_at TEXT
);
"""

async def init_db():
    async with aiosqlite.connect(DB) as db:
        for stmt in CREATE_SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                await db.execute(stmt)
        await db.commit()

async def create_episode(topic: str, mode: str = "ASSISTED") -> dict:
    ep_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO episodes (id, topic, mode, status, created_at, updated_at) VALUES (?, ?, ?, 'draft', ?, ?)",
            (ep_id, topic, mode, now, now)
        )
        await db.commit()
    return {"id": ep_id, "topic": topic, "mode": mode, "status": "draft", "created_at": now}

async def get_episode(episode_id: str) -> dict | None:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            ep = dict(row)
        async with db.execute(
            "SELECT stage_name, status, started_at, completed_at, error_message, output_json FROM pipeline_stages WHERE episode_id = ?",
            (episode_id,)
        ) as cur:
            ep["stages"] = [dict(r) for r in await cur.fetchall()]
    return ep

async def list_episodes() -> list:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM episodes ORDER BY created_at DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]

async def update_episode(episode_id: str, **kwargs):
    kwargs["updated_at"] = datetime.utcnow().isoformat()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [episode_id]
    async with aiosqlite.connect(DB) as db:
        await db.execute(f"UPDATE episodes SET {sets} WHERE id = ?", vals)
        await db.commit()

async def upsert_stage(episode_id: str, stage_name: str, status: str,
                       error_message: str = None, output: dict = None):
    now = datetime.utcnow().isoformat()
    started_at = now if status == "running" else None
    completed_at = now if status in ("done", "failed") else None
    output_json = json.dumps(output) if output else None
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            INSERT INTO pipeline_stages (episode_id, stage_name, status, started_at, completed_at, error_message, output_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(episode_id, stage_name) DO UPDATE SET
                status = excluded.status,
                started_at = COALESCE(excluded.started_at, started_at),
                completed_at = excluded.completed_at,
                error_message = excluded.error_message,
                output_json = COALESCE(excluded.output_json, output_json)
        """, (episode_id, stage_name, status, started_at, completed_at, error_message, output_json))
        await db.commit()

async def get_stage_output(episode_id: str, stage_name: str) -> dict | None:
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT output_json FROM pipeline_stages WHERE episode_id = ? AND stage_name = ?",
            (episode_id, stage_name)
        ) as cur:
            row = await cur.fetchone()
            if row and row[0]:
                return json.loads(row[0])
    return None

async def create_asset(episode_id: str, scene_index: int, asset_type: str,
                       prompt: str, negative_prompt: str = None, motion_notes: str = None) -> str:
    asset_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """INSERT INTO assets (id, episode_id, scene_index, asset_type, prompt, negative_prompt, motion_notes, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (asset_id, episode_id, scene_index, asset_type, prompt, negative_prompt, motion_notes, now)
        )
        await db.commit()
    return asset_id

async def update_asset(asset_id: str, **kwargs):
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [asset_id]
    async with aiosqlite.connect(DB) as db:
        await db.execute(f"UPDATE assets SET {sets} WHERE id = ?", vals)
        await db.commit()

async def get_assets(episode_id: str) -> list:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM assets WHERE episode_id = ? ORDER BY scene_index",
            (episode_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

async def get_asset(asset_id: str) -> dict | None:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def log_intervention(episode_id: str, issue: str, action: str, result: str = None, insight: str = None):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO interventions (episode_id, issue, action, result, insight, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (episode_id, issue, action, result, insight, now)
        )
        await db.commit()
