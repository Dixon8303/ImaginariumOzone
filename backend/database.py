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
    script_body TEXT,
    production_stage TEXT DEFAULT 'P0_ROUTE',
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

CREATE TABLE IF NOT EXISTS episode_stage_runs (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    tier TEXT NOT NULL,
    autonomy TEXT NOT NULL DEFAULT 'AUTO',
    status TEXT NOT NULL DEFAULT 'NOT_STARTED',
    pre_work_tier TEXT,
    started_at TEXT,
    completed_at TEXT,
    artifact_json TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS gate_decisions (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    gate_id TEXT NOT NULL,
    stage_run_id TEXT,
    result TEXT NOT NULL,
    score INTEGER,
    max_score INTEGER,
    rationale TEXT,
    decided_by TEXT NOT NULL DEFAULT 'opus',
    decided_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gate_remediations (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    gate_id TEXT NOT NULL,
    gate_decision_id TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    operator_notes TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS mutation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id TEXT NOT NULL,
    stage TEXT,
    table_name TEXT NOT NULL,
    row_id TEXT NOT NULL,
    mutation_type TEXT NOT NULL,
    payload_json TEXT,
    logged_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS title_variants (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'ollama',
    score INTEGER,
    selected INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    url TEXT,
    title TEXT,
    author TEXT,
    publication_year INTEGER,
    source_type TEXT,
    verified INTEGER DEFAULT 0,
    verified_by TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS research_claims (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    claim TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Unknown',
    confidence REAL,
    verified_by TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS claim_sources (
    claim_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    PRIMARY KEY (claim_id, source_id)
);

CREATE TABLE IF NOT EXISTS script_beats (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    beat_index INTEGER NOT NULL,
    beat_type TEXT,
    narration TEXT,
    visual_direction TEXT,
    curiosity_hook TEXT,
    duration_sec INTEGER,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS shorts_candidates (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    clip_type TEXT NOT NULL,
    start_sec INTEGER,
    end_sec INTEGER,
    hook TEXT,
    caption_draft TEXT,
    file_path TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    views INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS ab_tests (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    test_type TEXT NOT NULL,
    variant_a TEXT,
    variant_b TEXT,
    winner TEXT,
    metric TEXT,
    started_at TEXT,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS performance_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id TEXT NOT NULL,
    snapshot_hour INTEGER NOT NULL,
    ctr REAL,
    retention_pct REAL,
    views INTEGER,
    watch_time_sec INTEGER,
    session_depth REAL,
    shorts_views INTEGER,
    recorded_at TEXT
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

# ── Stage Runs ──────────────────────────────────────────────────────────────

async def create_stage_run(episode_id: str, stage: str, tier: str,
                           autonomy: str = "AUTO", pre_work_tier: str = None) -> str:
    run_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """INSERT INTO episode_stage_runs
               (id, episode_id, stage, tier, autonomy, pre_work_tier, status, started_at)
               VALUES (?, ?, ?, ?, ?, ?, 'RUNNING', ?)""",
            (run_id, episode_id, stage, tier, autonomy, pre_work_tier, now)
        )
        await db.commit()
    return run_id

async def complete_stage_run(run_id: str, artifact: dict = None, error: str = None):
    now = datetime.utcnow().isoformat()
    status = "FAILED" if error else "COMPLETED"
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """UPDATE episode_stage_runs SET status=?, completed_at=?, artifact_json=?, error_message=?
               WHERE id=?""",
            (status, now, json.dumps(artifact) if artifact else None, error, run_id)
        )
        await db.commit()

async def list_stage_runs(episode_id: str) -> list:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM episode_stage_runs WHERE episode_id=? ORDER BY started_at",
            (episode_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

# ── Gates ───────────────────────────────────────────────────────────────────

async def write_gate_decision(episode_id: str, gate_id: str, result: str,
                               score: int = None, max_score: int = None,
                               rationale: str = None, decided_by: str = "opus",
                               stage_run_id: str = None) -> str:
    gd_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """INSERT INTO gate_decisions
               (id, episode_id, gate_id, stage_run_id, result, score, max_score,
                rationale, decided_by, decided_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (gd_id, episode_id, gate_id, stage_run_id, result, score, max_score,
             rationale, decided_by, now)
        )
        await db.commit()
    return gd_id

async def list_gate_decisions(episode_id: str) -> list:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM gate_decisions WHERE episode_id=? ORDER BY decided_at",
            (episode_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

async def create_remediation(episode_id: str, gate_id: str,
                              gate_decision_id: str, description: str) -> str:
    rem_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """INSERT INTO gate_remediations
               (id, episode_id, gate_id, gate_decision_id, description, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'open', ?)""",
            (rem_id, episode_id, gate_id, gate_decision_id, description, now)
        )
        await db.commit()
    return rem_id

async def list_remediations(episode_id: str) -> list:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM gate_remediations WHERE episode_id=? ORDER BY created_at",
            (episode_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

# ── Mutation Log ─────────────────────────────────────────────────────────────

async def log_mutation(episode_id: str, table_name: str, row_id: str,
                       mutation_type: str, payload: dict = None, stage: str = None):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """INSERT INTO mutation_log
               (episode_id, stage, table_name, row_id, mutation_type, payload_json, logged_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (episode_id, stage, table_name, row_id, mutation_type,
             json.dumps(payload) if payload else None, now)
        )
        await db.commit()

async def get_mutation_log(episode_id: str, limit: int = 50) -> list:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM mutation_log WHERE episode_id=? ORDER BY logged_at DESC LIMIT ?",
            (episode_id, limit)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

# ── Title Variants ───────────────────────────────────────────────────────────

async def save_title_variants(episode_id: str, titles: list, source: str = "ollama"):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB) as db:
        for title in titles:
            tid = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO title_variants (id, episode_id, title, source, created_at) VALUES (?,?,?,?,?)",
                (tid, episode_id, title if isinstance(title, str) else title.get("title",""), source, now)
            )
        await db.commit()

async def select_title_variant(episode_id: str, title_id: str):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE title_variants SET selected=0 WHERE episode_id=?", (episode_id,))
        await db.execute("UPDATE title_variants SET selected=1 WHERE id=?", (title_id,))
        await db.commit()

async def get_title_variants(episode_id: str) -> list:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM title_variants WHERE episode_id=? ORDER BY created_at",
            (episode_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

# ── Research Sources + Claims ────────────────────────────────────────────────

async def save_sources(episode_id: str, sources: list) -> list:
    now = datetime.utcnow().isoformat()
    ids = []
    async with aiosqlite.connect(DB) as db:
        for s in sources:
            sid = str(uuid.uuid4())
            await db.execute(
                """INSERT INTO sources
                   (id, episode_id, url, title, author, publication_year, source_type, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (sid, episode_id, s.get("url"), s.get("title"), s.get("author"),
                 s.get("publication_year"), s.get("source_type"), now)
            )
            ids.append(sid)
        await db.commit()
    return ids

async def save_research_claims(episode_id: str, claims: list):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB) as db:
        for c in claims:
            cid = str(uuid.uuid4())
            await db.execute(
                """INSERT INTO research_claims
                   (id, episode_id, claim, status, confidence, created_at)
                   VALUES (?,?,?,?,?,?)""",
                (cid, episode_id, c.get("claim", ""),
                 c.get("status", "Unknown"), c.get("confidence"), now)
            )
        await db.commit()

# ── Script Beats ─────────────────────────────────────────────────────────────

async def save_script_beats(episode_id: str, beats: list):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB) as db:
        for i, b in enumerate(beats):
            bid = str(uuid.uuid4())
            await db.execute(
                """INSERT INTO script_beats
                   (id, episode_id, beat_index, beat_type, narration, visual_direction,
                    curiosity_hook, duration_sec, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (bid, episode_id, i, b.get("beat_type"), b.get("narration"),
                 b.get("visual_direction"), b.get("curiosity_hook"),
                 b.get("duration_sec"), now)
            )
        await db.commit()

async def get_script_beats(episode_id: str) -> list:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM script_beats WHERE episode_id=? ORDER BY beat_index",
            (episode_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]
