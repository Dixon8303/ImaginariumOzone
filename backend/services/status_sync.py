"""
Mission Control sync — mirrors production state to GitHub.

After every pipeline event or episode status change, a debounced task
commits status/production_status.json to the repo via the GitHub Contents
API. The public dashboard at docs/bgf/ reads that file client-side.

Requires GITHUB_SYNC_TOKEN in .env (fine-grained PAT, Contents R/W on the
repo). Without it every call is a silent no-op — sync must never break
the pipeline, so all failures are swallowed after a single retry.

Payload contains production METADATA only: topics, stage states, gate
verdicts, scores, timestamps. Never scripts, research text, or keys.
"""

import asyncio
import base64
import json
from datetime import datetime
import config
import database as db

try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False

STATUS_PATH = "status/production_status.json"
DEBOUNCE_SECONDS = 5.0

# Canonical stage order — mirrors orchestrator.py's stages list
STAGE_ORDER = [
    # Pipeline Order v2 — must match orchestrator.stages and the dashboard's
    # STAGES array in docs/bgf/index.html.
    "batch_primer", "topic_scoring", "research", "outline", "script",
    "storyboard", "generation", "ken_burns",
    "voice_ssml", "audio_prod",
    "titles_seo",
    "assembly", "qa_gates", "shorts", "upload",
]

_pending_task: asyncio.Task | None = None
_dirty = False


def is_configured() -> bool:
    return bool(config.GITHUB_SYNC_TOKEN) and _AIOHTTP_AVAILABLE


def request_sync():
    """Debounced entry point — safe to call from anywhere, any rate.
    Coalesces bursts of state changes into one commit ~5s later."""
    global _pending_task, _dirty
    if not is_configured():
        return
    _dirty = True
    if _pending_task is None or _pending_task.done():
        try:
            _pending_task = asyncio.get_running_loop().create_task(_debounced_sync())
        except RuntimeError:
            pass  # no running loop (e.g. sync context) — skip


async def _debounced_sync():
    global _dirty
    while _dirty:
        _dirty = False
        await asyncio.sleep(DEBOUNCE_SECONDS)
    try:
        await sync_now()
    except Exception:
        pass


async def build_payload() -> dict:
    """Production metadata snapshot for the public dashboard."""
    episodes = await db.list_episodes()
    out = []
    for ep in episodes:
        eid = ep["id"]
        stage_rows = {s["stage_name"]: s for s in await _list_pipeline_stages(eid)}
        stages = [
            {"name": name, "status": stage_rows.get(name, {}).get("status", "pending")}
            for name in STAGE_ORDER
        ]
        gates = {}
        for gd in await db.list_gate_decisions(eid):
            gid = gd["gate_id"]
            if gid not in gates:  # list is newest-first; keep latest per gate
                gates[gid] = {"result": gd["result"], "score": gd.get("score"),
                              "max_score": gd.get("max_score")}
        out.append({
            "id": eid,
            "topic": ep["topic"],
            "mode": ep["mode"],
            "status": ep["status"],
            "production_stage": ep.get("production_stage"),
            "keyword": ep.get("keyword"),
            "score": ep.get("score"),
            "stages": stages,
            "gates": gates,
            "created_at": ep.get("created_at"),
            "updated_at": ep.get("updated_at"),
        })
    return {
        "last_synced": datetime.utcnow().isoformat() + "Z",
        "app": "BGF Production OS v1.0",
        "episodes": out,
    }


async def _list_pipeline_stages(episode_id: str) -> list[dict]:
    import aiosqlite
    async with aiosqlite.connect(db.DB) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT stage_name, status FROM pipeline_stages WHERE episode_id = ?",
            (episode_id,))
        return [dict(r) for r in await cur.fetchall()]


async def sync_now() -> bool:
    """Build payload and commit it. Returns True on success."""
    if not is_configured():
        return False
    payload = await build_payload()
    content_b64 = base64.b64encode(
        json.dumps(payload, indent=2).encode()).decode()
    url = (f"https://api.github.com/repos/{config.GITHUB_SYNC_REPO}"
           f"/contents/{STATUS_PATH}")
    headers = {
        "Authorization": f"Bearer {config.GITHUB_SYNC_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with aiohttp.ClientSession() as session:
        for attempt in range(2):
            sha = await _get_sha(session, url, headers)
            body = {
                "message": "sync: production status from studio",
                "content": content_b64,
            }
            if sha:
                body["sha"] = sha
            async with session.put(
                url, json=body, headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status in (200, 201):
                    return True
                if resp.status not in (409, 422):  # sha conflict → retry once
                    return False
    return False


async def _get_sha(session, url: str, headers: dict) -> str | None:
    try:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                return None
            return (await resp.json()).get("sha")
    except Exception:
        return None
