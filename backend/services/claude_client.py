"""
BGF Claude Client — multi-tier model routing.

Tier routing (BGF Orchestration Spec):
  Fable 5  (claude-fable-5)              → P2 research, bibliography verification
  Opus 4.8 (claude-opus-4-8)             → P1 ideation/score, P3 outline, P4 script, P10 QA + G1-G5
  Sonnet 4.6 (claude-sonnet-4-6)         → P5 SSML, P6 storyboard, P7 thumbnails, P9 shorts
  Haiku 4.5 (claude-haiku-4-5-20251001)  → P8 SEO metadata, packaging QC
"""

import asyncio
import json
from pathlib import Path
import anthropic
import config

_bible_text: str | None = None

def _load_bible() -> str:
    global _bible_text
    if _bible_text is None:
        bible_path = config.PROMPTS_DIR / "production_bible.txt"
        _bible_text = bible_path.read_text()
    return _bible_text

def _load_prompt(name: str, **kwargs) -> str:
    path = config.PROMPTS_DIR / f"{name}.txt"
    template = path.read_text()
    return template.format(**kwargs) if kwargs else template

async def complete_with_model(model: str, system: str, user: str, max_tokens: int = 4096) -> str:
    client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    for attempt in range(3):
        try:
            msg = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}]
            )
            return msg.content[0].text
        except anthropic.RateLimitError:
            await asyncio.sleep(2 ** attempt * 5)
        except anthropic.APIError:
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt * 2)
    raise RuntimeError(f"Claude API ({model}) failed after 3 retries")

async def complete(system: str, user: str, max_tokens: int = 4096) -> str:
    return await complete_with_model(config.MODEL_SONNET, system, user, max_tokens)

# ── P1 Ideation + Score (Opus) ───────────────────────────────────────────────

async def ideate_and_score(topic: str, candidate_titles: list[str] = None) -> dict:
    """G1 Editorial Perspective + G2 100-pt Score — both evaluated by Opus."""
    system = _load_bible()
    candidates_block = ""
    if candidate_titles:
        candidates_block = "\n\nCandidate titles from pre-work:\n" + "\n".join(
            f"  {i+1}. {t}" for i, t in enumerate(candidate_titles)
        )
    user = (
        f"Topic: {topic}{candidates_block}\n\n"
        "Run the full P1 Ideation gate sequence:\n\n"
        "G1 EDITORIAL PERSPECTIVE — binary check:\n"
        "  - Names a real institution or documented individual (not archetype)?\n"
        "  - Frames through systems, not exceptional-individual narrative?\n"
        "  - Reconstructable from primary sources?\n"
        "  - Extends the BGF thesis on structural wealth + genius?\n\n"
        "G2 100-PT SCORE:\n"
        "  Virality (30) · Retention Potential (20) · Emotional Impact (20)\n"
        "  Monetization Safety (15) · Brand Alignment (15)\n"
        "  ≥70 → PRODUCE · 60-69 → REVISE TOPIC · <60 → KILL\n\n"
        "Also output: primary_keyword, top 3 title variants (ranked), keyword_volume_estimate.\n\n"
        "Return JSON:\n"
        "{\n"
        "  \"g1\": {\"result\": \"PASS\"|\"FAIL\", \"rationale\": str},\n"
        "  \"g2\": {\"score\": int, \"breakdown\": {...}, \"decision\": \"PRODUCE\"|\"REVISE\"|\"KILL\", \"rationale\": str},\n"
        "  \"primary_keyword\": str,\n"
        "  \"title_variants\": [str, str, str],\n"
        "  \"keyword_volume_estimate\": str\n"
        "}"
    )
    raw = await complete_with_model(config.MODEL_OPUS, system, user, max_tokens=1200)
    return _parse_json(raw, "ideation")

# ── P2 Research (Fable) ───────────────────────────────────────────────────────

async def research(topic: str) -> dict:
    """Deep research with per-claim verification — routed to Fable 5."""
    system = _load_bible()
    user = _load_prompt("research", topic=topic)
    raw = await complete_with_model(config.MODEL_FABLE, system, user, max_tokens=8000)
    return _parse_json(raw, "research")

# ── P3 Outline (Opus) ────────────────────────────────────────────────────────

async def generate_outline(title: str, research_json: dict) -> dict:
    system = _load_bible()
    user = (
        f"Title: {title}\n\n"
        f"Research brief:\n{json.dumps(research_json, indent=2)}\n\n"
        "Generate a structured episode outline with:\n"
        "- 6-8 script beats (beat_type, narration_hook, visual_direction, curiosity_loop, duration_sec)\n"
        "- Opening curiosity loop (question posed in first 30s)\n"
        "- Closing loop resolution\n"
        "- Transition notes between beats\n\n"
        "Return JSON: {\"beats\": [...], \"curiosity_loops\": [...], \"arc_notes\": str}"
    )
    raw = await complete_with_model(config.MODEL_OPUS, system, user, max_tokens=3000)
    return _parse_json(raw, "outline")

# ── P4 Script (Opus) ─────────────────────────────────────────────────────────

async def generate_script(title: str, research_json: dict) -> list:
    system = _load_bible()
    user = _load_prompt("script", title=title, research_json=json.dumps(research_json, indent=2))
    raw = await complete_with_model(config.MODEL_OPUS, system, user, max_tokens=6000)
    return _parse_json(raw, "script")

# ── P5 SSML / Voiceover (Sonnet) ─────────────────────────────────────────────

async def generate_ssml(narration_text: str, mode: str) -> str:
    system = _load_bible()
    user = _load_prompt("voice", narration_text=narration_text, mode=mode)
    return await complete_with_model(config.MODEL_SONNET, system, user, max_tokens=3000)

# ── P6 Storyboard (Sonnet) ───────────────────────────────────────────────────

async def plan_assets(title: str, script_json: list) -> list:
    system = _load_bible()
    user = _load_prompt("asset_planning", title=title, script_json=json.dumps(script_json, indent=2))
    raw = await complete_with_model(config.MODEL_SONNET, system, user, max_tokens=5000)
    return _parse_json(raw, "asset_planning")

# ── P7 Thumbnails / Packaging (Sonnet) ───────────────────────────────────────

async def plan_thumbnails(title: str, summary: str) -> dict:
    system = _load_bible()
    user = _load_prompt("thumbnail", title=title, summary=summary)
    raw = await complete_with_model(config.MODEL_SONNET, system, user, max_tokens=2000)
    return _parse_json(raw, "thumbnails")

# ── P8 SEO Metadata (Haiku) ──────────────────────────────────────────────────

async def generate_seo(topic: str, summary: str, keyword: str) -> dict:
    system = _load_bible()
    user = _load_prompt("seo", topic=topic, summary=summary, keyword=keyword)
    raw = await complete_with_model(config.MODEL_HAIKU, system, user, max_tokens=2000)
    return _parse_json(raw, "seo")

# ── P9 Shorts (Sonnet) ───────────────────────────────────────────────────────

async def generate_shorts(title: str, script_json: list) -> list:
    system = _load_bible()
    user = _load_prompt("shorts", title=title, script_json=json.dumps(script_json, indent=2))
    raw = await complete_with_model(config.MODEL_SONNET, system, user, max_tokens=5000)
    return _parse_json(raw, "shorts")

# ── P10 QA Gates G3-G5 (Opus) ────────────────────────────────────────────────

async def evaluate_qa_gates(episode_id: str, script_data: dict,
                             research_data: dict, seo_data: dict) -> dict:
    """G3 Hook Diagnostic + G4 Predictive + G5 Monetization/Ethics — decided by Opus."""
    system = _load_bible()
    user = (
        f"Run P10 Quality Assurance gate evaluation.\n\n"
        f"Script title: {script_data.get('title', '')}\n"
        f"Opening beat: {json.dumps(script_data.get('scenes', [{}])[0], indent=2)}\n\n"
        f"Research claim count: {len(research_data.get('claims', []))}\n"
        f"Bibliography entries: {len(research_data.get('sources', []))}\n\n"
        f"SEO package: {json.dumps(seo_data, indent=2)}\n\n"
        "Evaluate:\n\n"
        "G3 HOOK DIAGNOSTIC (/50, ≥28 to pass):\n"
        "  B1 cold_open_hook (/15) — auto-fail if ≤4\n"
        "  B2 first_question_posed (/10)\n"
        "  B3 stakes_established (/10)\n"
        "  B4 visual_hook_clarity (/15)\n\n"
        "G4 PREDICTIVE PERFORMANCE:\n"
        "  Estimate CTR_likelihood (0-10), retention_likelihood (0-10)\n"
        "  vs. BGF benchmarks: CTR ≥6% threshold, retention ≥30% first-mark\n\n"
        "G5 MONETIZATION + ETHICS:\n"
        "  advertiser_safety_score (/50) — ≥36 to pass\n"
        "  ethics_check: sensitive_content?, historical_accuracy_risk?, exploitative_framing?\n\n"
        "Return JSON:\n"
        "{\n"
        "  \"g3\": {\"result\": \"PASS\"|\"FAIL\", \"score\": int, \"max_score\": 50,\n"
        "           \"breakdown\": {...}, \"auto_fail_triggered\": bool, \"rationale\": str},\n"
        "  \"g4\": {\"result\": \"PASS\"|\"FAIL\", \"ctr_likelihood\": int, \"retention_likelihood\": int, \"rationale\": str},\n"
        "  \"g5\": {\"result\": \"PASS\"|\"FAIL\", \"advertiser_safety_score\": int,\n"
        "           \"ethics_flags\": [...], \"rationale\": str}\n"
        "}"
    )
    raw = await complete_with_model(config.MODEL_OPUS, system, user, max_tokens=2000)
    return _parse_json(raw, "qa_gates")

# ── Performance Analysis (Fable) ─────────────────────────────────────────────

async def analyze_performance(title: str, topic: str, metrics: dict) -> dict:
    system = _load_bible()
    user = _load_prompt("performance", title=title, topic=topic, **metrics)
    raw = await complete_with_model(config.MODEL_FABLE, system, user, max_tokens=2000)
    return _parse_json(raw, "performance")

# ── Utilities ─────────────────────────────────────────────────────────────────

def _parse_json(raw: str, stage: str) -> dict | list:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        start = raw.find("[") if raw.find("[") != -1 else raw.find("{")
        end = raw.rfind("]") if raw.rfind("]") != -1 else raw.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Claude returned non-JSON for stage '{stage}': {e}\nRaw: {raw[:500]}")
