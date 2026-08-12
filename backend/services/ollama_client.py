"""
Ollama client — local model, $0 marginal cost.
Used for: candidate title generation, shot-row drafts, caption drafts, SEO tags.
Gracefully degrades if Ollama is not running.
"""

import json
import asyncio
import config

try:
    import aiohttp
    from services import http as _http
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False


async def complete(prompt: str, model: str = None, max_tokens: int = 512) -> str | None:
    if not _AIOHTTP_AVAILABLE:
        return None
    m = model or config.OLLAMA_MODEL
    payload = {
        "model": m,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    try:
        async with _http.session() as session:
            async with session.post(
                f"{config.OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("response", "").strip()
    except Exception:
        return None


async def generate_title_candidates(topic: str, n: int = 10) -> list[str]:
    """Generate N candidate titles via local Ollama before Opus scoring."""
    prompt = (
        f"You are a YouTube title expert for Black history documentary content.\n"
        f"Generate {n} compelling YouTube video titles for this topic: {topic}\n\n"
        f"Rules: hook in first 4 words, name real institutions/people, under 60 chars.\n"
        f"Output ONLY a JSON array of strings: [\"title1\", \"title2\", ...]"
    )
    raw = await complete(prompt, max_tokens=800)
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1:
        try:
            titles = json.loads(raw[start:end + 1])
            return [t for t in titles if isinstance(t, str)][:n]
        except json.JSONDecodeError:
            pass
    lines = [l.strip().lstrip("0123456789.-) ").strip('"') for l in raw.split("\n") if l.strip()]
    return [l for l in lines if len(l) > 5][:n]


async def draft_shot_rows(scenes: list) -> list[dict]:
    """Draft storyboard shot rows for Sonnet P6 to refine."""
    prompt = (
        f"You are a documentary storyboard artist.\n"
        f"Draft visual shot descriptions for these {len(scenes)} scenes.\n"
        f"Scenes: {json.dumps(scenes[:4], indent=2)}\n\n"
        f"For each scene, output a shot_type (wide/medium/close/archive), "
        f"visual_description (1 sentence), and color_palette (3 words).\n"
        f"Output JSON array: [{{\"scene_index\": int, \"shot_type\": str, "
        f"\"visual_description\": str, \"color_palette\": str}}, ...]"
    )
    raw = await complete(prompt, max_tokens=1200)
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass
    return []


async def draft_captions(narration_text: str) -> str:
    """Draft burned caption text for Shorts."""
    prompt = (
        f"Write short, punchy caption text for a YouTube Short (9:16 video).\n"
        f"Narration: {narration_text[:500]}\n\n"
        f"Output 3-5 caption lines, max 6 words each, all caps.\n"
        f"No JSON, just the caption lines separated by newlines."
    )
    raw = await complete(prompt, max_tokens=200)
    return raw or ""


async def generate_seo_tags(title: str, topic: str, keyword: str) -> list[str]:
    """Generate SEO tag pool for Haiku/P8 to finalize."""
    prompt = (
        f"Generate 20 YouTube SEO tags for a Black history documentary.\n"
        f"Title: {title}\nTopic: {topic}\nPrimary keyword: {keyword}\n\n"
        f"Mix: broad terms, specific names/events, long-tail phrases.\n"
        f"Output JSON array of strings only."
    )
    raw = await complete(prompt, max_tokens=400)
    if not raw:
        return []
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass
    return [l.strip().strip('"') for l in raw.split("\n") if l.strip() and len(l) > 2][:20]
