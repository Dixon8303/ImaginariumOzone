"""
BGF Pipeline Orchestrator — 18-stage state machine.

Stages (matching NPOS §I·03):
  01 topic_scoring
  02 research
  03 script
  04 seo
  05 voice_ssml
  06 asset_planning
  07 generation
  08 ken_burns         ← waits for user asset approval in ASSISTED mode
  09 assembly
  10 shorts            ← waits for user video review before upload
  11 upload            ← triggered manually by user

Operating modes:
  ASSISTED  — pauses at script_review, asset_review, video_review gates
  SEMI_AUTO — pauses only at video_review gate
  FULL_AUTO — runs end-to-end, only pauses at video_review gate
"""

import asyncio
import json
from pathlib import Path
from typing import Callable, Any
import config
import database as db

# Per-episode SSE event queues
_queues: dict[str, asyncio.Queue] = {}

def get_queue(episode_id: str) -> asyncio.Queue:
    if episode_id not in _queues:
        _queues[episode_id] = asyncio.Queue()
    return _queues[episode_id]

async def emit(episode_id: str, event: dict):
    await get_queue(episode_id).put(event)

async def run_pipeline(episode_id: str, start_from: str | None = None):
    episode = await db.get_episode(episode_id)
    if not episode:
        raise ValueError(f"Episode {episode_id} not found")

    mode = episode.get("mode", "ASSISTED")
    output_dir = config.OUTPUT_BASE_DIR / episode_id
    output_dir.mkdir(parents=True, exist_ok=True)

    await db.update_episode(episode_id, status="running")
    await emit(episode_id, {"type": "pipeline_start", "mode": mode})

    stages = [
        ("topic_scoring",  _stage_topic_scoring),
        ("research",       _stage_research),
        ("script",         _stage_script),
        ("seo",            _stage_seo),
        ("voice_ssml",     _stage_voice_ssml),
        ("asset_planning", _stage_asset_planning),
        ("generation",     _stage_generation),
        ("ken_burns",      _stage_ken_burns),
        ("assembly",       _stage_assembly),
        ("shorts",         _stage_shorts),
    ]

    # ASSISTED mode: pause after script for human review
    # Gate handlers will re-signal the pipeline when user approves
    human_gates = {
        "ASSISTED":  ["script", "generation", "assembly"],
        "SEMI_AUTO": ["assembly"],
        "FULL_AUTO": ["assembly"],
    }
    gate_stages = set(human_gates.get(mode, ["assembly"]))

    skip = start_from is not None
    for stage_name, stage_fn in stages:
        if skip:
            if stage_name == start_from:
                skip = False
            else:
                continue

        await db.upsert_stage(episode_id, stage_name, "running")
        await emit(episode_id, {"type": "stage_start", "stage": stage_name})

        try:
            result = await stage_fn(episode_id, output_dir, mode)
            await db.upsert_stage(episode_id, stage_name, "done", output=result)
            await emit(episode_id, {"type": "stage_done", "stage": stage_name, "data": result})
        except Exception as e:
            await db.upsert_stage(episode_id, stage_name, "failed", error_message=str(e))
            await db.update_episode(episode_id, status="failed")
            await emit(episode_id, {"type": "stage_failed", "stage": stage_name, "error": str(e)})
            return

        # Human gate — set episode to review status and pause
        if stage_name in gate_stages:
            gate_status = f"{stage_name}_review"
            await db.update_episode(episode_id, status=gate_status)
            await emit(episode_id, {"type": "gate", "stage": stage_name,
                                     "message": f"Awaiting human review of {stage_name}"})
            return  # Pipeline will resume via POST /pipeline/resume/{id}

    await db.update_episode(episode_id, status="review")
    await emit(episode_id, {"type": "pipeline_paused",
                             "message": "Pipeline complete. Review video before upload."})

# ─── Stage Implementations ─────────────────────────────────────────────────

async def _stage_topic_scoring(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services import claude_client
    episode = await db.get_episode(episode_id)
    topic = episode["topic"]
    # Quick scoring prompt
    system = "You are a YouTube analytics expert for Black history documentary content."
    user = (
        f"Score this topic for The Black Genius Files channel on a 100-point scale.\n"
        f"Topic: {topic}\n\n"
        f"Scoring: Virality (30pts), Retention Potential (20pts), Emotional Impact (20pts), "
        f"Monetization (15pts), Brand Alignment (15pts).\n\n"
        f"Also suggest: primary_keyword, three title options, and keyword_volume_estimate.\n"
        f"Output JSON: {{score, breakdown, primary_keyword, title_options, keyword_volume_estimate, approved}}"
    )
    raw = await claude_client.complete(system, user, max_tokens=800)
    result = claude_client._parse_json(raw, "topic_scoring")
    await db.update_episode(episode_id,
                             score=result.get("score", 0),
                             keyword=result.get("primary_keyword", ""),
                             title_options=json.dumps(result.get("title_options", [])))
    return result

async def _stage_research(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services import claude_client
    episode = await db.get_episode(episode_id)
    result = await claude_client.research(episode["topic"])
    (output_dir / "research.json").write_text(json.dumps(result, indent=2))
    return result

async def _stage_script(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services import claude_client
    episode = await db.get_episode(episode_id)
    research = await db.get_stage_output(episode_id, "research")
    if not research:
        research = json.loads((output_dir / "research.json").read_text())
    title_options = json.loads(episode.get("title_options") or "[]")
    title = title_options[0] if title_options else episode["topic"]
    scenes = await claude_client.generate_script(title, research)
    result = {"title": title, "scenes": scenes}
    (output_dir / "script.json").write_text(json.dumps(result, indent=2))
    return result

async def _stage_seo(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services import claude_client
    episode = await db.get_episode(episode_id)
    script_data = await db.get_stage_output(episode_id, "script")
    if not script_data:
        script_data = json.loads((output_dir / "script.json").read_text())
    scenes = script_data.get("scenes", [])
    summary = " ".join(s.get("narration", "")[:200] for s in scenes[:3])
    result = await claude_client.generate_seo(
        episode["topic"], summary, episode.get("keyword", episode["topic"])
    )
    (output_dir / "seo.json").write_text(json.dumps(result, indent=2))
    return result

async def _stage_voice_ssml(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services import claude_client
    script_data = await db.get_stage_output(episode_id, "script")
    if not script_data:
        script_data = json.loads((output_dir / "script.json").read_text())
    scenes = script_data.get("scenes", [])
    narration = "\n\n".join(
        f"[Scene {s['scene_number']}]\n{s.get('narration', '')}"
        for s in scenes
    )
    ssml_text = await claude_client.generate_ssml(narration, mode)
    (output_dir / "voice_ssml.txt").write_text(ssml_text)
    return {"ssml_text": ssml_text, "scene_count": len(scenes)}

async def _stage_asset_planning(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services import claude_client
    script_data = await db.get_stage_output(episode_id, "script")
    if not script_data:
        script_data = json.loads((output_dir / "script.json").read_text())
    title = script_data.get("title", "")
    scenes = script_data.get("scenes", [])
    asset_plan = await claude_client.plan_assets(title, scenes)
    # Persist each asset to DB
    for asset_spec in asset_plan:
        await db.create_asset(
            episode_id=episode_id,
            scene_index=asset_spec.get("scene_index", 0),
            asset_type=asset_spec.get("asset_type", "ai_image"),
            prompt=asset_spec.get("comfyui_prompt", ""),
            negative_prompt=asset_spec.get("negative_prompt", ""),
            motion_notes=asset_spec.get("motion_notes", "zoom_in")
        )
    (output_dir / "asset_plan.json").write_text(json.dumps(asset_plan, indent=2))
    return {"asset_count": len(asset_plan), "plan": asset_plan}

async def _stage_generation(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services.comfyui_client import generate_asset
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    assets = await db.get_assets(episode_id)
    pending = [a for a in assets if a["status"] == "pending"]
    semaphore = asyncio.Semaphore(2)  # max 2 concurrent on M1 Max
    total = len(pending)
    done = 0

    async def _gen_one(asset: dict):
        nonlocal done
        async with semaphore:
            ext = ".mp4" if asset["asset_type"] == "ai_video" else ".png"
            dest = assets_dir / f"scene_{asset['scene_index']:03d}{ext}"
            await db.update_asset(asset["id"], status="generating",
                                   comfyui_prompt_id="queued")
            try:
                await generate_asset(
                    asset_type=asset["asset_type"],
                    positive_prompt=asset["prompt"],
                    negative_prompt=asset.get("negative_prompt", ""),
                    seed=hash(asset["id"]) % (2**31),
                    dest_path=dest
                )
                await db.update_asset(asset["id"], status="done", file_path=str(dest))
            except Exception as e:
                await db.update_asset(asset["id"], status="failed")
                await emit(episode_id, {"type": "asset_failed",
                                         "scene": asset["scene_index"], "error": str(e)})
            finally:
                done += 1
                await emit(episode_id, {"type": "generation_progress",
                                         "done": done, "total": total})

    await asyncio.gather(*[_gen_one(a) for a in pending])
    completed = await db.get_assets(episode_id)
    return {"total": total, "done": sum(1 for a in completed if a["status"] == "done")}

async def _stage_ken_burns(episode_id: str, output_dir: Path, mode: str) -> dict:
    from ffmpeg.ken_burns import apply_ken_burns
    assets = await db.get_assets(episode_id)
    # Only apply Ken Burns to approved image assets
    image_assets = [a for a in assets
                    if a["asset_type"] == "ai_image"
                    and a["status"] in ("done", "approved")
                    and a.get("file_path")]
    kb_dir = output_dir / "ken_burns"
    kb_dir.mkdir(exist_ok=True)
    processed = []
    for asset in image_assets:
        src = Path(asset["file_path"])
        dest = kb_dir / f"scene_{asset['scene_index']:03d}_kb.mp4"
        motion = asset.get("motion_notes", "zoom_in")
        duration = 7  # default 7s per still
        await apply_ken_burns(src, dest, motion, duration)
        await db.update_asset(asset["id"], file_path=str(dest))
        processed.append(str(dest))
    return {"processed": len(processed)}

async def _stage_assembly(episode_id: str, output_dir: Path, mode: str) -> dict:
    from ffmpeg.assembler import (
        upscale_clip, generate_narration, normalize_audio,
        assemble_episode, extract_thumbnail
    )
    from services import claude_client

    script_data = await db.get_stage_output(episode_id, "script")
    if not script_data:
        script_data = json.loads((output_dir / "script.json").read_text())
    scenes = script_data.get("scenes", [])

    assets = await db.get_assets(episode_id)
    asset_by_scene = {a["scene_index"]: a for a in assets if a.get("file_path")}

    audio_dir = output_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    final_dir = output_dir / "final"
    final_dir.mkdir(exist_ok=True)

    scene_clips = []
    narration_clips = []

    for scene in scenes:
        idx = scene.get("scene_number", 1) - 1
        asset = asset_by_scene.get(idx)

        # Prepare video clip
        if asset and asset.get("file_path"):
            p = Path(asset["file_path"])
            if asset["asset_type"] == "ai_video" and p.suffix == ".mp4":
                upscaled = output_dir / "upscaled" / p.name
                upscaled.parent.mkdir(exist_ok=True)
                await upscale_clip(p, upscaled)
                scene_clips.append(upscaled)
            else:
                scene_clips.append(p)
        else:
            continue

        # Generate narration for scene
        narration_text = scene.get("narration", "")
        if narration_text:
            # Strip SSML markers for TTS
            clean = narration_text.replace("[PAUSE]", "").replace("[BEAT]", ""). \
                replace("[SLOW]", "").replace("[EMPHASIS]", "")
            raw_audio = audio_dir / f"scene_{idx:03d}_raw.mp3"
            norm_audio = audio_dir / f"scene_{idx:03d}.mp3"
            await generate_narration(clean, raw_audio)
            await normalize_audio(raw_audio, norm_audio)
            narration_clips.append(norm_audio)
        else:
            continue

    final_video = final_dir / "episode.mp4"
    music_path = config.MUSIC_DIR / "background.mp3" if config.MUSIC_DIR.exists() else None
    await assemble_episode(scene_clips, narration_clips, final_video, music_path)
    thumbnail = final_dir / "thumbnail.jpg"
    await extract_thumbnail(final_video, thumbnail)
    return {"final_video": str(final_video), "thumbnail": str(thumbnail)}

async def _stage_shorts(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services import claude_client
    from ffmpeg.shorts_cutter import extract_shorts_from_episode

    script_data = await db.get_stage_output(episode_id, "script")
    if not script_data:
        script_data = json.loads((output_dir / "script.json").read_text())

    # Generate shorts scripts
    shorts_data = await claude_client.generate_shorts(
        script_data.get("title", ""), script_data.get("scenes", [])
    )
    (output_dir / "shorts.json").write_text(json.dumps(shorts_data, indent=2))

    # Extract from assembled video
    assembly = await db.get_stage_output(episode_id, "assembly")
    if assembly and assembly.get("final_video"):
        final_video = Path(assembly["final_video"])
        shorts_dir = output_dir / "shorts"
        paths = await extract_shorts_from_episode(final_video, shorts_data, shorts_dir)
        return {"shorts_count": len(paths), "paths": [str(p) for p in paths]}
    return {"shorts_count": 0, "shorts_data": shorts_data}
