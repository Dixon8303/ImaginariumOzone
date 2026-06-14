"""
BGF Pipeline Orchestrator — multi-tier model routing + G1-G5 gate system.

Stage → Tier mapping (BGF Orchestration Spec):
  P1 Ideation/Score  → Opus 4.8   (pre-work: Ollama title candidates)
  P2 Research        → Fable 5
  P3 Outline         → Opus 4.8
  P4 Script          → Opus 4.8    (AUTO + async review flag)
  P5 SSML/Voice      → Sonnet 4.6  (then: ElevenLabs/say + Whisper)
  P6 Storyboard      → Sonnet 4.6  (pre-work: Ollama shot drafts → Flux/ComfyUI)
  P7 Thumbnails      → Sonnet 4.6  (pre-work: Ollama title pool)
  P8 SEO             → Haiku 4.5
  P9 Shorts          → Sonnet 4.6  (pre-work: Ollama captions)
  P10 QA + Gates     → Opus 4.8   (G3, G4, G5 — CHECKPOINT)

Gate autonomy:
  CHECKPOINT → P1 (topic lock), P10 (go/no-go)
  HARD_HALT  → any gate FAIL
  AUTO       → all other stages
"""

import asyncio
import json
from pathlib import Path
import config
import database as db

# Per-episode SSE event queues
_queues: dict[str, asyncio.Queue] = {}

ROUTING = {
    "topic_scoring":  {"tier": config.MODEL_OPUS,   "pre": "ollama_titles",   "autonomy": "CHECKPOINT"},
    "research":       {"tier": config.MODEL_FABLE,  "pre": None,              "autonomy": "AUTO"},
    "outline":        {"tier": config.MODEL_OPUS,   "pre": None,              "autonomy": "AUTO"},
    "script":         {"tier": config.MODEL_OPUS,   "pre": None,              "autonomy": "AUTO_REVIEW"},
    "seo":            {"tier": config.MODEL_HAIKU,  "pre": "ollama_tags",     "autonomy": "AUTO"},
    "voice_ssml":     {"tier": config.MODEL_SONNET, "pre": None,              "autonomy": "AUTO"},
    "asset_planning": {"tier": config.MODEL_SONNET, "pre": "ollama_shots",    "autonomy": "AUTO"},
    "generation":     {"tier": "comfyui",           "pre": None,              "autonomy": "AUTO"},
    "ken_burns":      {"tier": "ffmpeg",            "pre": None,              "autonomy": "AUTO"},
    "assembly":       {"tier": "ffmpeg",            "pre": None,              "autonomy": "AUTO"},
    "shorts":         {"tier": config.MODEL_SONNET, "pre": "ollama_captions", "autonomy": "AUTO"},
    "qa_gates":       {"tier": config.MODEL_OPUS,   "pre": "code_checks",     "autonomy": "CHECKPOINT"},
}

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
        ("outline",        _stage_outline),
        ("script",         _stage_script),
        ("seo",            _stage_seo),
        ("voice_ssml",     _stage_voice_ssml),
        ("asset_planning", _stage_asset_planning),
        ("generation",     _stage_generation),
        ("ken_burns",      _stage_ken_burns),
        ("assembly",       _stage_assembly),
        ("shorts",         _stage_shorts),
        ("qa_gates",       _stage_qa_gates),
    ]

    human_gates = {
        "ASSISTED":  ["script", "generation", "assembly", "qa_gates"],
        "SEMI_AUTO": ["assembly", "qa_gates"],
        "FULL_AUTO": ["qa_gates"],
    }
    gate_stages = set(human_gates.get(mode, ["qa_gates"]))

    skip = start_from is not None
    for stage_name, stage_fn in stages:
        if skip:
            if stage_name == start_from:
                skip = False
            else:
                continue

        routing = ROUTING.get(stage_name, {})
        tier = routing.get("tier", config.MODEL_SONNET)
        autonomy = routing.get("autonomy", "AUTO")

        run_id = await db.create_stage_run(
            episode_id, stage_name, tier, autonomy,
            pre_work_tier=routing.get("pre")
        )
        await db.upsert_stage(episode_id, stage_name, "running")
        await emit(episode_id, {
            "type": "stage_start",
            "stage": stage_name,
            "tier": tier,
            "autonomy": autonomy,
        })

        try:
            result = await stage_fn(episode_id, output_dir, mode)
            await db.complete_stage_run(run_id, artifact=result)
            await db.upsert_stage(episode_id, stage_name, "done", output=result)
            await db.log_mutation(episode_id, "pipeline_stages", episode_id,
                                  "STAGE_COMPLETE", {"stage": stage_name, "tier": tier}, stage_name)
            await emit(episode_id, {
                "type": "stage_done",
                "stage": stage_name,
                "tier": tier,
                "data": result,
            })
        except HardHalt as e:
            await db.complete_stage_run(run_id, error=str(e))
            await db.upsert_stage(episode_id, stage_name, "halted", error_message=str(e))
            await db.update_episode(episode_id, status="halted")
            await emit(episode_id, {
                "type": "hard_halt",
                "stage": stage_name,
                "gate": e.gate_id,
                "remediation": e.remediation_id,
                "message": str(e),
            })
            return
        except Exception as e:
            await db.complete_stage_run(run_id, error=str(e))
            await db.upsert_stage(episode_id, stage_name, "failed", error_message=str(e))
            await db.update_episode(episode_id, status="failed")
            await emit(episode_id, {"type": "stage_failed", "stage": stage_name, "error": str(e)})
            return

        if stage_name in gate_stages:
            gate_status = f"{stage_name}_review"
            await db.update_episode(episode_id, status=gate_status)
            await emit(episode_id, {
                "type": "gate",
                "stage": stage_name,
                "message": f"Awaiting human review of {stage_name}",
            })
            return

    await db.update_episode(episode_id, status="review")
    await emit(episode_id, {"type": "pipeline_paused",
                             "message": "Pipeline complete. Review before upload."})


class HardHalt(Exception):
    def __init__(self, gate_id: str, remediation_id: str, message: str):
        self.gate_id = gate_id
        self.remediation_id = remediation_id
        super().__init__(message)


async def _hard_halt(episode_id: str, gate_id: str, rationale: str,
                     run_id: str = None, score: int = None, max_score: int = None) -> None:
    """Write gate FAIL, create remediation, raise HardHalt."""
    gd_id = await db.write_gate_decision(
        episode_id, gate_id, "FAIL",
        score=score, max_score=max_score,
        rationale=rationale, decided_by="opus",
        stage_run_id=run_id,
    )
    rem_id = await db.create_remediation(episode_id, gate_id, gd_id, rationale)
    await db.log_mutation(episode_id, "gate_decisions", gd_id,
                          "GATE_FAIL", {"gate": gate_id, "rationale": rationale})
    raise HardHalt(gate_id, rem_id, f"Gate {gate_id} FAILED — {rationale}")


# ─── Stage Implementations ────────────────────────────────────────────────────

async def _stage_topic_scoring(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services import claude_client
    from services import ollama_client
    episode = await db.get_episode(episode_id)
    topic = episode["topic"]

    # Pre-work: Ollama generates candidate titles
    candidates = await ollama_client.generate_title_candidates(topic, n=8)
    if candidates:
        await db.save_title_variants(episode_id, candidates, source="ollama")
        await db.log_mutation(episode_id, "title_variants", episode_id,
                              "INSERT", {"source": "ollama", "count": len(candidates)}, "topic_scoring")

    # Opus: G1 + G2 evaluation
    result = await claude_client.ideate_and_score(topic, candidates)

    g1 = result.get("g1", {})
    g2 = result.get("g2", {})

    await db.write_gate_decision(
        episode_id, "G1", g1.get("result", "FAIL"),
        rationale=g1.get("rationale"), decided_by="opus",
    )
    await db.write_gate_decision(
        episode_id, "G2", g2.get("result", "PASS") if g2.get("decision") == "PRODUCE" else "FAIL",
        score=g2.get("score"), max_score=100,
        rationale=g2.get("rationale"), decided_by="opus",
    )

    if g1.get("result") == "FAIL":
        await _hard_halt(episode_id, "G1", g1.get("rationale", "G1 editorial check failed"))

    if g2.get("decision") == "KILL":
        await _hard_halt(episode_id, "G2",
                         f"Score {g2.get('score')}/100 — below 60 kill threshold. {g2.get('rationale', '')}")

    # Save Opus-scored title variants
    if result.get("title_variants"):
        await db.save_title_variants(episode_id, result["title_variants"], source="opus")

    await db.update_episode(
        episode_id,
        score=g2.get("score", 0),
        keyword=result.get("primary_keyword", ""),
        title_options=json.dumps(result.get("title_variants", [])),
        production_stage="P1_IDEATION",
    )
    return result


async def _stage_research(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services import claude_client
    episode = await db.get_episode(episode_id)
    result = await claude_client.research(episode["topic"])

    # Persist structured research artifacts
    if result.get("sources"):
        source_ids = await db.save_sources(episode_id, result["sources"])
        await db.log_mutation(episode_id, "sources", episode_id, "INSERT",
                              {"count": len(source_ids)}, "research")

    if result.get("claims"):
        await db.save_research_claims(episode_id, result["claims"])
        await db.log_mutation(episode_id, "research_claims", episode_id, "INSERT",
                              {"count": len(result["claims"])}, "research")

    (output_dir / "research.json").write_text(json.dumps(result, indent=2))
    await db.update_episode(episode_id, production_stage="P2_RESEARCH")
    return result


async def _stage_outline(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services import claude_client
    episode = await db.get_episode(episode_id)
    research = await db.get_stage_output(episode_id, "research")
    if not research:
        research = json.loads((output_dir / "research.json").read_text())

    title_options = json.loads(episode.get("title_options") or "[]")
    title = title_options[0] if title_options else episode["topic"]

    result = await claude_client.generate_outline(title, research)

    if result.get("beats"):
        await db.save_script_beats(episode_id, result["beats"])
        await db.log_mutation(episode_id, "script_beats", episode_id, "INSERT",
                              {"count": len(result["beats"])}, "outline")

    (output_dir / "outline.json").write_text(json.dumps(result, indent=2))
    await db.update_episode(episode_id, production_stage="P3_OUTLINE")
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
    await db.update_episode(episode_id,
                             script_body=json.dumps(scenes),
                             production_stage="P4_SCRIPT")
    return result


async def _stage_seo(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services import claude_client
    from services import ollama_client
    episode = await db.get_episode(episode_id)
    script_data = await db.get_stage_output(episode_id, "script")
    if not script_data:
        script_data = json.loads((output_dir / "script.json").read_text())
    scenes = script_data.get("scenes", [])
    summary = " ".join(s.get("narration", "")[:200] for s in scenes[:3])
    kw = episode.get("keyword", episode["topic"])

    # Pre-work: Ollama tag drafts
    tag_drafts = await ollama_client.generate_seo_tags(script_data.get("title", ""), episode["topic"], kw)

    result = await claude_client.generate_seo(episode["topic"], summary, kw)
    # Merge Ollama draft tags
    existing = result.get("tags", [])
    merged = list(dict.fromkeys(existing + tag_drafts))[:30]
    result["tags"] = merged
    (output_dir / "seo.json").write_text(json.dumps(result, indent=2))
    await db.update_episode(episode_id, production_stage="P8_SEO")
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
    await db.update_episode(episode_id, production_stage="P5_VOICEOVER")
    return {"ssml_text": ssml_text, "scene_count": len(scenes)}


async def _stage_asset_planning(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services import claude_client
    from services import ollama_client
    script_data = await db.get_stage_output(episode_id, "script")
    if not script_data:
        script_data = json.loads((output_dir / "script.json").read_text())
    title = script_data.get("title", "")
    scenes = script_data.get("scenes", [])

    # Pre-work: Ollama shot row drafts
    shot_drafts = await ollama_client.draft_shot_rows(scenes)

    asset_plan = await claude_client.plan_assets(title, scenes)
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
    await db.update_episode(episode_id, production_stage="P6_VISUAL")
    return {"asset_count": len(asset_plan), "plan": asset_plan, "shot_drafts": shot_drafts}


async def _stage_generation(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services.comfyui_client import generate_asset
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    assets = await db.get_assets(episode_id)
    pending = [a for a in assets if a["status"] == "pending"]
    semaphore = asyncio.Semaphore(2)
    total = len(pending)
    done = 0

    async def _gen_one(asset: dict):
        nonlocal done
        async with semaphore:
            ext = ".mp4" if asset["asset_type"] == "ai_video" else ".png"
            dest = assets_dir / f"scene_{asset['scene_index']:03d}{ext}"
            await db.update_asset(asset["id"], status="generating", comfyui_prompt_id="queued")
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
                await emit(episode_id, {"type": "generation_progress", "done": done, "total": total})

    await asyncio.gather(*[_gen_one(a) for a in pending])
    completed = await db.get_assets(episode_id)
    return {"total": total, "done": sum(1 for a in completed if a["status"] == "done")}


async def _stage_ken_burns(episode_id: str, output_dir: Path, mode: str) -> dict:
    from ffmpeg.ken_burns import apply_ken_burns
    assets = await db.get_assets(episode_id)
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
        await apply_ken_burns(src, dest, motion, duration=7)
        await db.update_asset(asset["id"], file_path=str(dest))
        processed.append(str(dest))
    return {"processed": len(processed)}


async def _stage_assembly(episode_id: str, output_dir: Path, mode: str) -> dict:
    from ffmpeg.assembler import (
        upscale_clip, generate_narration, normalize_audio,
        assemble_episode, extract_thumbnail
    )
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

    scene_clips, narration_clips = [], []
    for scene in scenes:
        idx = scene.get("scene_number", 1) - 1
        asset = asset_by_scene.get(idx)
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
        narration_text = scene.get("narration", "")
        if narration_text:
            clean = narration_text.replace("[PAUSE]","").replace("[BEAT]",""). \
                replace("[SLOW]","").replace("[EMPHASIS]","")
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
    await db.update_episode(episode_id, production_stage="P_ASSEMBLY")
    return {"final_video": str(final_video), "thumbnail": str(thumbnail)}


async def _stage_shorts(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services import claude_client
    from services import ollama_client
    from ffmpeg.shorts_cutter import extract_shorts_from_episode

    script_data = await db.get_stage_output(episode_id, "script")
    if not script_data:
        script_data = json.loads((output_dir / "script.json").read_text())

    # Pre-work: Ollama caption drafts
    narration_sample = " ".join(
        s.get("narration", "")[:200] for s in script_data.get("scenes", [])[:2]
    )
    caption_draft = await ollama_client.draft_captions(narration_sample)

    shorts_data = await claude_client.generate_shorts(
        script_data.get("title", ""), script_data.get("scenes", [])
    )
    if caption_draft:
        for s in shorts_data:
            s.setdefault("caption_draft", caption_draft)
    (output_dir / "shorts.json").write_text(json.dumps(shorts_data, indent=2))

    assembly = await db.get_stage_output(episode_id, "assembly")
    if assembly and assembly.get("final_video"):
        final_video = Path(assembly["final_video"])
        shorts_dir = output_dir / "shorts"
        paths = await extract_shorts_from_episode(final_video, shorts_data, shorts_dir)
        await db.update_episode(episode_id, production_stage="P9_SHORTS")
        return {"shorts_count": len(paths), "paths": [str(p) for p in paths]}
    return {"shorts_count": 0, "shorts_data": shorts_data}


async def _stage_qa_gates(episode_id: str, output_dir: Path, mode: str) -> dict:
    """P10 — G3 Hook + G4 Predictive + G5 Ethics/Monetization (all Opus)."""
    from services import claude_client

    script_data = await db.get_stage_output(episode_id, "script")
    if not script_data:
        script_data = json.loads((output_dir / "script.json").read_text())

    research_data = await db.get_stage_output(episode_id, "research")
    if not research_data:
        try:
            research_data = json.loads((output_dir / "research.json").read_text())
        except FileNotFoundError:
            research_data = {}

    seo_data = await db.get_stage_output(episode_id, "seo")
    if not seo_data:
        try:
            seo_data = json.loads((output_dir / "seo.json").read_text())
        except FileNotFoundError:
            seo_data = {}

    result = await claude_client.evaluate_qa_gates(episode_id, script_data, research_data, seo_data)

    # Write all gate decisions
    for gate_id in ("g3", "g4", "g5"):
        g = result.get(gate_id, {})
        gd_result = g.get("result", "FAIL")
        await db.write_gate_decision(
            episode_id, gate_id.upper(),
            gd_result,
            score=g.get("score") or g.get("advertiser_safety_score"),
            max_score=g.get("max_score") or (50 if gate_id == "g3" else None),
            rationale=g.get("rationale"),
            decided_by="opus",
        )

    # Check for failures — HARD HALT on any
    failures = []
    g3 = result.get("g3", {})
    g4 = result.get("g4", {})
    g5 = result.get("g5", {})

    if g3.get("result") == "FAIL" or g3.get("auto_fail_triggered"):
        failures.append(("G3", f"Hook score {g3.get('score')}/50 — {g3.get('rationale', '')}"))
    if g4.get("result") == "FAIL":
        failures.append(("G4", g4.get("rationale", "Predictive performance below threshold")))
    if g5.get("result") == "FAIL":
        failures.append(("G5", f"Advertiser safety {g5.get('advertiser_safety_score')}/50 — {g5.get('rationale', '')}"))

    if failures:
        gate_id, rationale = failures[0]
        await _hard_halt(episode_id, gate_id, rationale)

    await db.update_episode(episode_id, production_stage="P10_QA", status="review")
    return {"g3": g3, "g4": g4, "g5": g5, "all_passed": not failures}
