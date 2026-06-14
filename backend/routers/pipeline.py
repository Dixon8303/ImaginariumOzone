import asyncio
import json
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import database as db
from pipeline.orchestrator import run_pipeline, get_queue, emit, ROUTING

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
        "script_review":      "seo",
        "outline_review":     "script",
        "generation_review":  "ken_burns",
        "assembly_review":    "shorts",
        "qa_gates_review":    None,
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

# ── Gate + Stage Run Endpoints ────────────────────────────────────────────────

@router.get("/gates/{episode_id}")
async def list_gates(episode_id: str):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    gates = await db.list_gate_decisions(episode_id)
    remediations = await db.list_remediations(episode_id)
    return {"gates": gates, "remediations": remediations}

@router.get("/stage-runs/{episode_id}")
async def list_stage_runs(episode_id: str):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    runs = await db.list_stage_runs(episode_id)
    return {"stage_runs": runs, "routing": ROUTING}

@router.get("/mutation-log/{episode_id}")
async def get_mutation_log(episode_id: str, limit: int = 50):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    log = await db.get_mutation_log(episode_id, limit=limit)
    return {"mutations": log}

@router.get("/title-variants/{episode_id}")
async def get_title_variants(episode_id: str):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    variants = await db.get_title_variants(episode_id)
    return {"variants": variants}

class GateOverrideRequest(BaseModel):
    result: str      # "PASS" or "FAIL"
    rationale: str
    advance_to: str | None = None

@router.post("/gate-override/{episode_id}/{gate_id}", status_code=202)
async def gate_override(episode_id: str, gate_id: str, body: GateOverrideRequest,
                        background_tasks: BackgroundTasks):
    """Operator override for a gate decision (CHECKPOINT approval or remediation bypass)."""
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    await db.write_gate_decision(
        episode_id, gate_id, body.result,
        rationale=f"[OPERATOR OVERRIDE] {body.rationale}",
        decided_by="operator",
    )
    await db.log_mutation(episode_id, "gate_decisions", episode_id,
                          "OPERATOR_OVERRIDE", {"gate": gate_id, "result": body.result})
    if body.result == "PASS" and body.advance_to:
        background_tasks.add_task(run_pipeline, episode_id, body.advance_to)
        return {"status": "override_applied_advancing", "gate": gate_id, "advance_to": body.advance_to}
    return {"status": "override_applied", "gate": gate_id}
