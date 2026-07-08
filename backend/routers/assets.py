from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import database as db

router = APIRouter(prefix="/api/assets", tags=["assets"])

class AssetUpdate(BaseModel):
    status: str  # approved | rejected

@router.get("/episode/{episode_id}")
async def list_assets(episode_id: str):
    return await db.get_assets(episode_id)

@router.patch("/{asset_id}")
async def update_asset(asset_id: str, body: AssetUpdate):
    asset = await db.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if body.status not in ("approved", "rejected", "pending"):
        raise HTTPException(status_code=400, detail="Invalid status")
    await db.update_asset(asset_id, status=body.status)
    return await db.get_asset(asset_id)

@router.post("/{asset_id}/regenerate", status_code=202)
async def regenerate_asset(asset_id: str):
    asset = await db.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    await db.update_asset(asset_id, status="pending", file_path=None)
    # Re-trigger generation for this asset
    import asyncio
    from services.comfyui_client import generate_asset
    import config

    episode_id = asset["episode_id"]
    output_dir = config.OUTPUT_BASE_DIR / episode_id / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)
    ext = ".mp4" if asset["asset_type"] == "ai_video" else ".png"
    dest = output_dir / f"scene_{asset['scene_index']:03d}_regen{ext}"

    async def _regen():
        try:
            await generate_asset(
                asset_type=asset["asset_type"],
                positive_prompt=asset["prompt"],
                negative_prompt=asset.get("negative_prompt", ""),
                seed=hash(asset_id + "_regen") % (2**31),
                dest_path=dest
            )
            await db.update_asset(asset_id, status="done", file_path=str(dest))
        except Exception as e:
            await db.update_asset(asset_id, status="failed")

    asyncio.create_task(_regen())
    return {"status": "regenerating", "asset_id": asset_id}

@router.get("/{asset_id}/file")
async def get_asset_file(asset_id: str):
    asset = await db.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if not asset.get("file_path"):
        raise HTTPException(status_code=404, detail="Asset file not generated yet")
    path = Path(asset["file_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Asset file missing from disk")
    return FileResponse(path)

@router.get("/episode/{episode_id}/final")
async def get_final_video(episode_id: str):
    import config
    final_path = config.OUTPUT_BASE_DIR / episode_id / "final" / "episode.mp4"
    if not final_path.exists():
        raise HTTPException(status_code=404, detail="Final video not ready")
    return FileResponse(final_path, media_type="video/mp4")

@router.get("/episode/{episode_id}/thumbnail")
async def get_thumbnail(episode_id: str):
    import config
    thumb = config.OUTPUT_BASE_DIR / episode_id / "final" / "thumbnail.jpg"
    if not thumb.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not ready")
    return FileResponse(thumb, media_type="image/jpeg")
