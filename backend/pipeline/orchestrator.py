"""
BGF Pipeline Orchestrator — Pipeline Order v2.

Doctrine: BGF_PROMPT_STACK.md (stage contracts, v2 order) and
BGF_PACING_CONSTITUTION.md (§3 pacing curve, §6 Flux specs, §14 gates).

Order (15 stages). Pre-production is linear; storyboard is pulled ahead of
voiceover so ComfyUI starts days earlier; QA gates the master BEFORE Shorts
extraction so a re-render never forces a 13-clip re-extract.

  P0.5 Batch Primer -> P1 Score -> P2 Research -> P3 Outline -> P4 Script
       -> [G0.25 VO pilot] [G0.5 visual budget] -> P6 Storyboard
       -> Track A: Generation, Ken Burns
          Track B: P5 Voiceover, P5.5 Audio Prod
          Track C: P7a/P8 Titles + SEO
       -> Assembly -> P10 QA -> P9b Shorts -> P10.5 Upload

Tiers: Opus 4.8 (score/outline/script/QA) · Fable 5 (research) ·
Sonnet 4.6 (storyboard/VO/shorts) · Haiku 4.5 (titles+SEO) ·
ComfyUI Flux Dev (generation) · ffmpeg (motion/audio/assembly).

Gates:
  G0.25 VO Pilot      — calibrates real VO duration; blocks ComfyUI queuing
  G0.5  Visual Budget — buffered shot count (1.20x, or 1.25x un-piloted)
  G1/G2 at P1         — editorial perspective, 100-pt score (CHECKPOINT)
  G3/G4/G5 at P10     — hook, predictive, monetization+ethics (CHECKPOINT)
  Any FAIL -> HardHalt, remediation row, pipeline stops.

Upload is a CHECKPOINT in every mode. There is no unattended-publish path.
"""

import asyncio
import json
import math
from pathlib import Path
import config
import database as db

# Per-episode SSE event queues
_queues: dict[str, asyncio.Queue] = {}

ROUTING = {
    # ── Pre-production (linear) ──────────────────────────────────────────
    "batch_primer":   {"tier": config.MODEL_OPUS,   "pre": None,              "autonomy": "AUTO"},
    "topic_scoring":  {"tier": config.MODEL_OPUS,   "pre": "ollama_titles",   "autonomy": "CHECKPOINT"},
    "research":       {"tier": config.MODEL_FABLE,  "pre": None,              "autonomy": "AUTO"},
    "outline":        {"tier": config.MODEL_OPUS,   "pre": None,              "autonomy": "AUTO"},
    "script":         {"tier": config.MODEL_OPUS,   "pre": None,              "autonomy": "AUTO_REVIEW"},
    # ── Track A · Visual (storyboard moved ahead of VO; carries G0.25/G0.5) ──
    "storyboard":     {"tier": config.MODEL_SONNET, "pre": "ollama_shots",    "autonomy": "AUTO"},
    "generation":     {"tier": "comfyui",           "pre": None,              "autonomy": "AUTO"},
    "ken_burns":      {"tier": "ffmpeg",            "pre": None,              "autonomy": "AUTO"},
    # ── Track B · Audio ──────────────────────────────────────────────────
    "voice_ssml":     {"tier": config.MODEL_SONNET, "pre": None,              "autonomy": "AUTO"},
    "audio_prod":     {"tier": "ffmpeg",            "pre": None,              "autonomy": "AUTO"},
    # ── Track C · Metadata (needs script only) ───────────────────────────
    "titles_seo":     {"tier": config.MODEL_HAIKU,  "pre": "ollama_tags",     "autonomy": "AUTO"},
    # ── Post-production (tracks converge) ────────────────────────────────
    "assembly":       {"tier": "ffmpeg",            "pre": None,              "autonomy": "AUTO"},
    "qa_gates":       {"tier": config.MODEL_OPUS,   "pre": "code_checks",     "autonomy": "CHECKPOINT"},
    "shorts":         {"tier": config.MODEL_SONNET, "pre": "ollama_captions", "autonomy": "AUTO"},
    "upload":         {"tier": "youtube",           "pre": None,              "autonomy": "CHECKPOINT"},
}

def get_queue(episode_id: str) -> asyncio.Queue:
    if episode_id not in _queues:
        _queues[episode_id] = asyncio.Queue()
    return _queues[episode_id]

async def emit(episode_id: str, event: dict):
    await get_queue(episode_id).put(event)
    # Every pipeline event = a state change worth mirroring to Mission Control
    from services import status_sync
    status_sync.request_sync()

async def run_pipeline(episode_id: str, start_from: str | None = None):
    episode = await db.get_episode(episode_id)
    if not episode:
        raise ValueError(f"Episode {episode_id} not found")

    mode = episode.get("mode", "ASSISTED")
    output_dir = config.OUTPUT_BASE_DIR / episode_id
    output_dir.mkdir(parents=True, exist_ok=True)

    await db.update_episode(episode_id, status="running")
    await emit(episode_id, {"type": "pipeline_start", "mode": mode})

    # Pipeline Order v2 (BGF_PROMPT_STACK.md). Execution is sequential; the
    # Track A/B/C grouping is the doctrine's concurrency model and is honoured
    # in ordering (visual work front-loaded so ComfyUI starts as early as
    # possible). Running the tracks truly concurrently is a later change —
    # the stage outputs are identical either way.
    stages = [
        # Pre-production — linear. P1 scores before P2 researches: G2 kills
        # sub-60 topics, and P2's own spec requires a locked topic.
        ("batch_primer",   _stage_batch_primer),
        ("topic_scoring",  _stage_topic_scoring),
        ("research",       _stage_research),
        ("outline",        _stage_outline),
        ("script",         _stage_script),
        # Track A — visual. storyboard runs G0.25 + G0.5 before any shot.
        ("storyboard",     _stage_storyboard),
        ("generation",     _stage_generation),
        ("ken_burns",      _stage_ken_burns),
        # Track B — audio.
        ("voice_ssml",     _stage_voice_ssml),
        ("audio_prod",     _stage_audio_prod),
        # Track C — metadata.
        ("titles_seo",     _stage_titles_seo),
        # Post — QA gates the master BEFORE Shorts, so a re-render never
        # forces a 13-clip re-extract.
        ("assembly",       _stage_assembly),
        ("qa_gates",       _stage_qa_gates),
        ("shorts",         _stage_shorts),
        ("upload",         _stage_upload),
    ]

    # 'upload' is a CHECKPOINT in every mode — there is no unattended-publish
    # path. See CLAUDE.md hard rules.
    human_gates = {
        "ASSISTED":  ["script", "generation", "assembly", "qa_gates", "upload"],
        "SEMI_AUTO": ["assembly", "qa_gates", "upload"],
        "FULL_AUTO": ["qa_gates", "upload"],
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

async def _stage_batch_primer(episode_id: str, output_dir: Path, mode: str) -> dict:
    """
    P0.5 Cluster Batch Primer (BGF_PROMPT_STACK.md).

    Only meaningful when producing 3-5 episodes on a shared theme: it loads
    the research and canon modules once for the whole cluster instead of per
    episode, which is the main token saving of cluster production.

    A single-episode run has no cluster to prime, so this passes through and
    records why. It never blocks — the bypass-and-publish rule says one
    blocked episode must not freeze the others.
    """
    episode = await db.get_episode(episode_id)
    cluster_theme = (episode.get("production_notes") or "").strip() if episode else ""
    result = {
        "cluster": False,
        "reason": "single-episode run — no cluster batch to prime",
        "topic": episode["topic"] if episode else None,
    }
    (output_dir / "batch_primer.json").write_text(json.dumps(result, indent=2))
    await db.update_episode(episode_id, production_stage="P0_5_BATCH_PRIMER")
    return result


async def _stage_topic_scoring(episode_id: str, output_dir: Path, mode: str) -> dict:
    from services import claude_client
    from services import ollama_client
    from services import vidiq_client
    episode = await db.get_episode(episode_id)
    topic = episode["topic"]

    # Pre-work: Ollama + vidIQ generate candidate titles
    candidates = await ollama_client.generate_title_candidates(topic, n=8)
    if candidates:
        await db.save_title_variants(episode_id, candidates, source="ollama")
        await db.log_mutation(episode_id, "title_variants", episode_id,
                              "INSERT", {"source": "ollama", "count": len(candidates)}, "topic_scoring")

    vidiq_titles = await vidiq_client.generate_titles(topic, n=5)
    if vidiq_titles:
        await db.save_title_variants(episode_id, vidiq_titles, source="vidiq")
        candidates = candidates + vidiq_titles

    # Real keyword data replaces Opus's volume estimate
    keyword_data = await vidiq_client.keyword_research(topic)

    # Opus: G1 + G2 evaluation
    result = await claude_client.ideate_and_score(topic, candidates, keyword_data)

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

    # Save Opus title variants, CTR-scored by vidIQ when available
    if result.get("title_variants"):
        from services import vidiq_client as _vq
        scored = await _vq.score_titles(result["title_variants"])
        if scored:
            await db.save_title_variants(episode_id, scored, source="opus")
            result["title_scores"] = scored
        else:
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


async def _stage_titles_seo(episode_id: str, output_dir: Path, mode: str) -> dict:
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
    await db.update_episode(episode_id, production_stage="P7_P8_TITLES_SEO")
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


def _script_words(script_data: dict) -> str:
    """Flatten a script's narration to a single string."""
    return " ".join(
        s.get("narration", "") for s in script_data.get("scenes", [])
    ).strip()


async def _gate_g0_25_vo_pilot(episode_id: str, output_dir: Path,
                                script_data: dict) -> dict:
    """
    G0.25 — VO PILOT RENDER (BGF_PACING_CONSTITUTION.md §14).

    Renders the first ~250 words, measures the real duration, and derives the
    scale factor between estimated and actual VO. ComfyUI queuing is blocked
    until this closes: without it, image counts are computed against an
    estimate that ran 27% short on EP40, which is what forced re-generation.

    Never hard-halts. If the render is impossible the gate closes as
    ESTIMATED, which promotes the buffer from 1.20x to 1.25x downstream.
    """
    from ffmpeg import assembler

    full_text = _script_words(script_data)
    total_words = len(full_text.split())
    pilot_text = " ".join(full_text.split()[:config.BGF_PILOT_WORD_TARGET])
    pilot_words = len(pilot_text.split())

    if not pilot_words:
        raise ValueError("G0.25: script has no narration to pilot")

    estimated_seg_sec = pilot_words / config.BGF_WORDS_PER_SECOND
    scale, actual_seg_sec, method = None, None, "ESTIMATED"

    try:
        pilot_path = output_dir / "audio" / "vo_pilot.mp3"
        await assembler.generate_narration(pilot_text, pilot_path)
        actual_seg_sec = await assembler.get_duration(pilot_path)
        if actual_seg_sec and estimated_seg_sec > 0:
            scale = actual_seg_sec / estimated_seg_sec
            method = "PILOT_RENDER"
    except Exception:
        scale = None  # TTS unavailable — fall through to ESTIMATED

    if scale is None:
        scale = 1.0
        buffer_mult = config.BGF_BUFFER_NO_PILOT
    else:
        buffer_mult = config.BGF_BUFFER_WITH_PILOT

    calibrated_vo_sec = (total_words / config.BGF_WORDS_PER_SECOND) * scale

    result = {
        "pilot_scale_factor": round(scale, 3) if method == "PILOT_RENDER" else "ESTIMATED",
        "calibrated_VO_sec": round(calibrated_vo_sec, 1),
        "buffer_multiplier": buffer_mult,
        "method": method,
        "pilot_words": pilot_words,
        "total_words": total_words,
        "estimated_seg_sec": round(estimated_seg_sec, 2),
        "actual_seg_sec": round(actual_seg_sec, 2) if actual_seg_sec else None,
    }

    await db.write_gate_decision(
        episode_id, "G0.25", "PASS",
        rationale=(
            f"{method}: scale {result['pilot_scale_factor']}, "
            f"calibrated VO {result['calibrated_VO_sec']}s from {total_words} words, "
            f"buffer {buffer_mult}x"
        ),
        decided_by="pipeline",
    )
    (output_dir / "g0_25_vo_pilot.json").write_text(json.dumps(result, indent=2))
    await emit(episode_id, {"type": "gate_passed", "gate": "G0.25", "data": result})
    return result


async def _gate_g0_5_visual_budget(episode_id: str, output_dir: Path,
                                    pilot: dict) -> dict:
    """
    G0.5 — VISUAL BUDGET (BGF_PACING_CONSTITUTION.md §14).

    Per §3 phase, derives minimum visual events from the calibrated VO
    duration and the phase ASL midpoint, then applies the buffer. The buffer
    is non-negotiable doctrine — it absorbs VO variance, assembly retiming,
    and shot-level quality failures without a second ComfyUI pass.
    """
    calibrated = pilot["calibrated_VO_sec"]
    buffer_mult = pilot["buffer_multiplier"]

    per_phase, min_total, buffered_total = [], 0, 0
    for phase in config.BGF_PHASES:
        duration = calibrated * phase["pct"]
        min_events = math.ceil(duration / phase["asl"])
        buffered = math.ceil(min_events * buffer_mult)
        flex = math.ceil(buffered * config.BGF_FLEX_PCT)
        per_phase.append({
            "phase": phase["name"],
            "duration_sec": round(duration, 1),
            "asl": phase["asl"],
            "min_visual_events": min_events,
            "buffered_count": buffered,
            "flex_count": flex,
        })
        min_total += min_events
        buffered_total += buffered

    flex_total = math.ceil(buffered_total * config.BGF_FLEX_PCT)
    ai_shots = max(0, buffered_total - config.BGF_ARCHIVAL_MINIMUM)

    budget = {
        "target_runtime_sec": calibrated,
        "pilot_scale_factor": pilot["pilot_scale_factor"],
        "min_visual_events_total": min_total,
        "buffered_shot_count": buffered_total,
        "flex_shots_count": flex_total,
        "archival_minimum": config.BGF_ARCHIVAL_MINIMUM,
        "AI_shots_needed": ai_shots,
        "buffer_multiplier": buffer_mult,
        "per_phase": per_phase,
    }

    # The constitution requires Visual_Budget_EP##.md to exist as an artifact.
    lines = [
        f"# Visual Budget — {episode_id}", "",
        f"- target_runtime_sec: {calibrated}",
        f"- pilot_scale_factor: {pilot['pilot_scale_factor']}",
        f"- min_visual_events_total: {min_total}",
        f"- buffered_shot_count: {buffered_total}  ({buffer_mult}x buffer)",
        f"- flex_shots_count: {flex_total}",
        f"- archival_minimum: {config.BGF_ARCHIVAL_MINIMUM}",
        f"- AI_shots_needed: {ai_shots}", "",
        "## Per-beat allocation", "",
        "| Phase | Duration | ASL | Min | Buffered | FLEX |",
        "|-------|----------|-----|-----|----------|------|",
    ] + [
        f"| {p['phase']} | {p['duration_sec']}s | {p['asl']}s | "
        f"{p['min_visual_events']} | {p['buffered_count']} | {p['flex_count']} |"
        for p in per_phase
    ]
    (output_dir / f"Visual_Budget_{episode_id[:8]}.md").write_text("\n".join(lines))

    await db.write_gate_decision(
        episode_id, "G0.5", "PASS",
        score=buffered_total, max_score=buffered_total,
        rationale=(
            f"{buffered_total} shots ({min_total} min x {buffer_mult}), "
            f"{flex_total} FLEX, {ai_shots} AI after {config.BGF_ARCHIVAL_MINIMUM} archival"
        ),
        decided_by="pipeline",
    )
    (output_dir / "g0_5_visual_budget.json").write_text(json.dumps(budget, indent=2))
    await emit(episode_id, {"type": "gate_passed", "gate": "G0.5", "data": budget})
    return budget


async def _stage_audio_prod(episode_id: str, output_dir: Path, mode: str) -> dict:
    """
    P5.5 Audio Production (BGF_PROMPT_STACK.md).

    Renders per-scene narration, runs the BGF mastering chain, and — the part
    assembly depends on — measures the ACTUAL VO duration and writes the
    rescale factor to state. Storyboard timestamps are estimates until this
    runs; assembly multiplies by this factor to retime beats.
    """
    from ffmpeg import assembler

    script_data = await db.get_stage_output(episode_id, "script")
    if not script_data:
        script_data = json.loads((output_dir / "script.json").read_text())
    scenes = script_data.get("scenes", [])
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    drone = config.MUSIC_DIR / "BGF_d_minor_drone.wav"
    rendered, total_sec = [], 0.0
    for scene in scenes:
        idx = scene.get("scene_number", 1) - 1
        text = (scene.get("narration") or "")
        for marker in ("[PAUSE]", "[BEAT]", "[SLOW]", "[EMPHASIS]"):
            text = text.replace(marker, "")
        if not text.strip():
            continue
        raw = audio_dir / f"scene_{idx:03d}_raw.mp3"
        out = audio_dir / f"scene_{idx:03d}.mp3"
        try:
            await assembler.generate_narration(text.strip(), raw)
            await assembler.master_narration(raw, out, drone_path=drone)
            dur = await assembler.get_duration(out)
            total_sec += dur or 0.0
            rendered.append({"scene": idx, "path": str(out), "duration_sec": dur})
        except Exception as e:
            rendered.append({"scene": idx, "error": str(e)})

    # Reconcile against G0.25's projection so assembly can retime.
    pilot_path = output_dir / "g0_25_vo_pilot.json"
    calibrated = None
    if pilot_path.exists():
        calibrated = json.loads(pilot_path.read_text()).get("calibrated_VO_sec")
    assembly_scale = (total_sec / calibrated) if calibrated else 1.0

    result = {
        "scenes_rendered": len([r for r in rendered if "path" in r]),
        "actual_VO_duration_sec": round(total_sec, 1),
        "calibrated_VO_sec": calibrated,
        "assembly_scale_factor": round(assembly_scale, 3),
        "loudness_target": "-14 LUFS / -1 dBTP",
        "clips": rendered,
    }
    (output_dir / "audio_prod.json").write_text(json.dumps(result, indent=2))
    await db.update_episode(episode_id, production_stage="P5_5_AUDIO_PROD")
    return result


async def _stage_upload(episode_id: str, output_dir: Path, mode: str) -> dict:
    """
    P10.5 Upload / release.

    Assembles the release package and stops. This stage is a CHECKPOINT in
    every operating mode — it never publishes on its own. Publishing happens
    only when the operator confirms from the Upload Panel.
    """
    final_dir = output_dir / "final"
    episode = await db.get_episode(episode_id)
    seo = await db.get_stage_output(episode_id, "titles_seo") or {}
    video = final_dir / "episode.mp4"
    thumb = final_dir / "thumbnail.jpg"

    result = {
        "ready_for_upload": video.exists(),
        "awaiting_operator_approval": True,
        "video_path": str(video) if video.exists() else None,
        "thumbnail_path": str(thumb) if thumb.exists() else None,
        "title": seo.get("title") or (episode or {}).get("topic"),
        "description": seo.get("description"),
        "tags": seo.get("tags", []),
    }
    (output_dir / "upload_package.json").write_text(json.dumps(result, indent=2))
    await db.update_episode(episode_id, production_stage="P10_5_UPLOAD")
    return result


async def _stage_storyboard(episode_id: str, output_dir: Path, mode: str) -> dict:
    """P6 Storyboard — runs immediately after script lock, ahead of VO, so
    ComfyUI starts days earlier. G0.25 and G0.5 close before any shot is
    planned; the shotlist is sized to the buffered count, never the minimum."""
    from services import claude_client
    from services import ollama_client
    script_data = await db.get_stage_output(episode_id, "script")
    if not script_data:
        script_data = json.loads((output_dir / "script.json").read_text())
    title = script_data.get("title", "")
    scenes = script_data.get("scenes", [])

    # G0.25 → G0.5 must both close before ComfyUI is queued.
    pilot = await _gate_g0_25_vo_pilot(episode_id, output_dir, script_data)
    budget = await _gate_g0_5_visual_budget(episode_id, output_dir, pilot)

    # Pre-work: Ollama shot row drafts
    shot_drafts = await ollama_client.draft_shot_rows(scenes)

    asset_plan = await claude_client.plan_assets(
        title, scenes, shot_target=budget["AI_shots_needed"])
    # FLEX designation: the last 15-20% of the shotlist. These are symbolic /
    # atmospheric and can be dropped in anywhere within their chapter, so
    # assembly can absorb VO overrun without a second ComfyUI pass. They are
    # rendered in the primary batch — never a second pass — and unused ones
    # are simply discarded.
    flex_start = max(0, len(asset_plan) - budget["flex_shots_count"])
    for i, asset_spec in enumerate(asset_plan):
        asset_spec["flex_flag"] = i >= flex_start
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
    return {
        "asset_count": len(asset_plan),
        "flex_count": sum(1 for a in asset_plan if a.get("flex_flag")),
        "budget": budget,
        "pilot": pilot,
        "plan": asset_plan,
        "shot_drafts": shot_drafts,
    }


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
            # P5.5 already mastered this scene — don't re-render it.
            if not norm_audio.exists():
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

    # Real CTR-predictive signals for G4: vidIQ score on the final title
    from services import vidiq_client
    vidiq_benchmarks = None
    title_score = await vidiq_client.score_title(script_data.get("title", ""))
    if title_score:
        vidiq_benchmarks = {"title_ctr_score": title_score}

    result = await claude_client.evaluate_qa_gates(
        episode_id, script_data, research_data, seo_data, vidiq_benchmarks)

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
