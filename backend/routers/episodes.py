from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import database as db

router = APIRouter(prefix="/api/episodes", tags=["episodes"])

class EpisodeCreate(BaseModel):
    topic: str
    mode: str = "ASSISTED"

class EpisodeUpdate(BaseModel):
    topic: str | None = None
    mode: str | None = None
    keyword: str | None = None
    script_json: str | None = None

@router.get("")
async def list_episodes():
    return await db.list_episodes()

@router.post("", status_code=201)
async def create_episode(body: EpisodeCreate):
    return await db.create_episode(body.topic, body.mode)

@router.get("/{episode_id}")
async def get_episode(episode_id: str):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return ep

@router.patch("/{episode_id}")
async def update_episode(episode_id: str, body: EpisodeUpdate):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if updates:
        await db.update_episode(episode_id, **updates)
    return await db.get_episode(episode_id)

@router.delete("/{episode_id}", status_code=204)
async def delete_episode(episode_id: str):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    import aiosqlite
    import config
    async with aiosqlite.connect(config.DATABASE_PATH) as db_conn:
        await db_conn.execute("DELETE FROM pipeline_stages WHERE episode_id = ?", (episode_id,))
        await db_conn.execute("DELETE FROM assets WHERE episode_id = ?", (episode_id,))
        await db_conn.execute("DELETE FROM episodes WHERE id = ?", (episode_id,))
        await db_conn.commit()
