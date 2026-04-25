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

async def complete(system: str, user: str, max_tokens: int = 4096) -> str:
    client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    for attempt in range(3):
        try:
            msg = await client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}]
            )
            return msg.content[0].text
        except anthropic.RateLimitError:
            wait = 2 ** attempt * 5
            await asyncio.sleep(wait)
        except anthropic.APIError as e:
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt * 2)
    raise RuntimeError("Claude API failed after 3 retries")

async def research(topic: str) -> dict:
    system = _load_bible()
    user = _load_prompt("research", topic=topic)
    raw = await complete(system, user, max_tokens=4096)
    return _parse_json(raw, "research")

async def generate_script(title: str, research_json: dict) -> list:
    system = _load_bible()
    user = _load_prompt("script", title=title, research_json=json.dumps(research_json, indent=2))
    raw = await complete(system, user, max_tokens=6000)
    return _parse_json(raw, "script")

async def generate_seo(topic: str, summary: str, keyword: str) -> dict:
    system = _load_bible()
    user = _load_prompt("seo", topic=topic, summary=summary, keyword=keyword)
    raw = await complete(system, user, max_tokens=2000)
    return _parse_json(raw, "seo")

async def plan_assets(title: str, script_json: list) -> list:
    system = _load_bible()
    user = _load_prompt("asset_planning", title=title, script_json=json.dumps(script_json, indent=2))
    raw = await complete(system, user, max_tokens=5000)
    return _parse_json(raw, "asset_planning")

async def generate_ssml(narration_text: str, mode: str) -> str:
    system = _load_bible()
    user = _load_prompt("voice", narration_text=narration_text, mode=mode)
    return await complete(system, user, max_tokens=3000)

async def generate_shorts(title: str, script_json: list) -> list:
    system = _load_bible()
    user = _load_prompt("shorts", title=title, script_json=json.dumps(script_json, indent=2))
    raw = await complete(system, user, max_tokens=5000)
    return _parse_json(raw, "shorts")

async def analyze_performance(title: str, topic: str, metrics: dict) -> dict:
    system = _load_bible()
    user = _load_prompt("performance", title=title, topic=topic, **metrics)
    raw = await complete(system, user, max_tokens=2000)
    return _parse_json(raw, "performance")

def _parse_json(raw: str, stage: str) -> dict | list:
    raw = raw.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        # Attempt to extract JSON substring
        start = raw.find("[") if raw.find("[") != -1 else raw.find("{")
        end = raw.rfind("]") if raw.rfind("]") != -1 else raw.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Claude returned non-JSON for stage '{stage}': {e}\nRaw: {raw[:500]}")
