from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import aiosqlite
import database as db
import config
from analytics.decisions import evaluate, interventions_to_dict

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

class PerformanceInput(BaseModel):
    ctr_24h: float = 0.0
    ctr_48h: float = 0.0
    retention_30: float = 0.0
    retention_70: float = 0.0
    watch_time_sec: int = 0
    session_depth: float = 0.0
    shorts_views: int = 0

@router.post("/performance/{episode_id}")
async def record_performance(episode_id: str, body: PerformanceInput):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as conn:
        await conn.execute("""
            INSERT INTO performances
            (episode_id, ctr_24h, ctr_48h, ctr_7d, retention_pct, watch_time_sec, session_depth, shorts_views, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (episode_id, body.ctr_24h, body.ctr_48h, body.ctr_48h,
              body.retention_30, body.watch_time_sec, body.session_depth,
              body.shorts_views, now))
        await conn.commit()
    # Run decision engine
    metrics = body.dict()
    interventions = evaluate(metrics)
    for iv in interventions:
        await db.log_intervention(episode_id, iv.issue, iv.action)
    return {
        "recorded": True,
        "interventions": interventions_to_dict(interventions)
    }

@router.get("/performance/{episode_id}")
async def get_performance(episode_id: str):
    async with aiosqlite.connect(config.DATABASE_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM performances WHERE episode_id = ? ORDER BY recorded_at DESC",
            (episode_id,)
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
    return rows

@router.get("/interventions/{episode_id}")
async def get_interventions(episode_id: str):
    async with aiosqlite.connect(config.DATABASE_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM interventions WHERE episode_id = ? ORDER BY created_at DESC",
            (episode_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

@router.get("/war-room")
async def war_room_summary():
    """Aggregated metrics for the War Room dashboard."""
    async with aiosqlite.connect(config.DATABASE_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("""
            SELECT e.id, e.topic, e.status,
                   p.ctr_48h, p.retention_pct, p.session_depth, p.shorts_views
            FROM episodes e
            LEFT JOIN performances p ON p.episode_id = e.id
            ORDER BY e.created_at DESC
            LIMIT 10
        """) as cur:
            episodes = [dict(r) for r in await cur.fetchall()]
        async with conn.execute(
            "SELECT AVG(ctr_48h), AVG(retention_pct), AVG(session_depth) FROM performances"
        ) as cur:
            row = await cur.fetchone()
            averages = {
                "avg_ctr": round(row[0] or 0, 2),
                "avg_retention": round(row[1] or 0, 2),
                "avg_session_depth": round(row[2] or 0, 2)
            }
    return {"episodes": episodes, "averages": averages}
