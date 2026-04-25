import asyncio
import json
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import database as db
from pipeline.orchestrator import run_pipeline, get_queue, emit

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

class UploadRequest(BaseModel):
    privacy: str = "private"

@router.post("/start/{episode_id}", status_code=202)
async def start_pipeline(episode_id: str, background_tasks: BackgroundTasks):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    if ep["status"] == "running":
        raise HTTPException(status_code=409, detail="Pipeline already running")
    background_tasks.add_task(run_pipeline, episode_id)
    return {"status": "started", "episode_id": episode_id}

@router.post("/resume/{episode_id}", status_code=202)
async def resume_pipeline(episode_id: str, background_tasks: BackgroundTasks,
                           from_stage: str | None = None):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    # If in a review gate, determine which stage to resume from
    status = ep["status"]
    stage_map = {
        "script_review": "seo",
        "generation_review": "ken_burns",
        "assembly_review": "shorts",
        "failed": None,
    }
    resume_from = from_stage or stage_map.get(status)
    if resume_from is None and status == "failed":
        # Find last failed stage
        stages = ep.get("stages", [])
        failed = [s for s in stages if s["status"] == "failed"]
        resume_from = failed[-1]["stage_name"] if failed else None
    background_tasks.add_task(run_pipeline, episode_id, resume_from)
    return {"status": "resumed", "from_stage": resume_from, "episode_id": episode_id}

@router.post("/upload/{episode_id}", status_code=202)
async def trigger_upload(episode_id: str, body: UploadRequest,
                          background_tasks: BackgroundTasks):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")

    async def _upload():
        from youtube.uploader import upload_episode
        from pathlib import Path
        import config
        output_dir = config.OUTPUT_BASE_DIR / episode_id
        seo_path = output_dir / "seo.json"
        seo = json.loads(seo_path.read_text()) if seo_path.exists() else {}
        assembly = await db.get_stage_output(episode_id, "assembly")
        if not assembly or not assembly.get("final_video"):
            await emit(episode_id, {"type": "upload_failed",
                                     "error": "No final video found"})
            return
        video_path = Path(assembly["final_video"])
        thumb_path = Path(assembly.get("thumbnail", ""))
        try:
            url = await upload_episode(video_path, seo, thumb_path, body.privacy)
            await db.update_episode(episode_id, status="done")
            await emit(episode_id, {"type": "upload_done", "url": url})
        except Exception as e:
            await db.update_episode(episode_id, status="upload_failed")
            await emit(episode_id, {"type": "upload_failed", "error": str(e)})

    background_tasks.add_task(_upload)
    return {"status": "upload_started", "episode_id": episode_id}

@router.get("/status/{episode_id}")
async def pipeline_status_stream(episode_id: str):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")

    async def event_generator():
        # Send current state immediately
        yield f"data: {json.dumps({'type': 'current_state', 'episode': ep})}\n\n"
        queue = get_queue(episode_id)
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ("upload_done", "upload_failed"):
                    break
            except asyncio.TimeoutError:
                yield "data: {\"type\": \"heartbeat\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"}
    )
