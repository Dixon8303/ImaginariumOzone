"""
CinemaWin Claude client — doctrine loader, structured-output calls, retries,
refusal handling.

Rules (integration contract §LLM implementation rules):
  - anthropic>=1.0, AsyncAnthropic() reading ANTHROPIC_API_KEY.
  - Model IDs come from config (MODEL_CRAFT / MODEL_JUDGE). Never inline.
  - OMIT `thinking` (adaptive is on by default on Opus 5). Never send
    temperature, budget_tokens, or an assistant prefill.
  - Structured output via output_config json_schema; every object has
    additionalProperties=false and every property in `required`.
  - max_tokens=16000, non-streaming.
  - System = doctrine files 00…04 concatenated + house-style preamble, with
    cache_control ephemeral.
  - Refusal fallbacks ON by default via client.beta.messages.create(
        betas=[FALLBACK_BETA], fallbacks="default", ...).
  - Retry RateLimitError / APIStatusError(5xx) / APIConnectionError up to 3
    attempts with backoff. BadRequestError is never retried.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional

import anthropic

import config

log = logging.getLogger("cinemawin.claude")


class LLMNotConfigured(Exception):
    """No ANTHROPIC_API_KEY and demo mode is off."""


class LLMError(Exception):
    """API failure after retries, or unparseable output."""


class LLMRefused(Exception):
    """stop_reason == 'refusal' after fallbacks."""


def is_configured() -> bool:
    return config.LLM_CONFIGURED


# ── Doctrine / prompt loading ────────────────────────────────────────────────

HOUSE_STYLE_PREAMBLE = """# CinemaWin House Style (operating preamble)

You are CinemaWin, the studio operating system defined by the five doctrine
modules that follow. You are answering a single command from the Master
Command Lexicon (Module 00 §III) for one project. Observe these rules:

- Reverse-engineer first (Prime Directive): find the strongest version latent
  in the writer's material. Never flatten voice, cultural specificity, or
  deliberate risk into formula.
- Every figure, range, or market claim carries an evidence tag from Module 00
  §V. Never invent incentive rates, pre-sales values, or comps as fact.
- Apply the AHAG gatekeeper (Module 01 §II) to any prose you write: concrete,
  specific, no artificial profundity, no therapy-speak, no rhetorical
  symmetry.
- Write for a working writer or producer: direct, specific, professional.
  No hedging boilerplate, no meta-commentary about being an AI.
- Return only the requested JSON object. No prose outside the JSON.
"""

_system_text: Optional[str] = None
_prompt_cache: dict[str, str] = {}


def load_doctrine() -> str:
    """Concatenate prompts/doctrine/*.md in filename order (00…04)."""
    parts = []
    for path in sorted(Path(config.DOCTRINE_DIR).glob("*.md")):
        parts.append(path.read_text(encoding="utf-8").strip())
    return "\n\n---\n\n".join(parts)


def system_prompt() -> str:
    global _system_text
    if _system_text is None:
        _system_text = HOUSE_STYLE_PREAMBLE.strip() + "\n\n---\n\n" + load_doctrine()
    return _system_text


def load_prompt(name: str, **fields: Any) -> str:
    """Read prompts/<name>.txt and str.format it with the request fields."""
    if name not in _prompt_cache:
        _prompt_cache[name] = (Path(config.PROMPTS_DIR) / f"{name}.txt").read_text(encoding="utf-8")
    return _prompt_cache[name].format(**fields)


# ── JSON schemas (every object: additionalProperties false, all required) ───
# Array lengths and numeric ranges are NOT expressed here (unsupported by the
# structured-outputs grammar); prompts state them and postprocess.py enforces them.

def _obj(properties: dict, **extra) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties.keys()),
        "additionalProperties": False,
        **extra,
    }


def _arr(items: dict, **extra) -> dict:
    return {"type": "array", "items": items, **extra}


_S = {"type": "string"}
_I = {"type": "integer"}

DEVELOP_STORY_SCHEMA = _obj(
    {
        "premise": _S,
        "protagonist": _S,
        "core_need": _S,
        "emotional_wound": _S,
        "central_question": _S,
        "theme": _S,
        "first_step": _S,
        "maturity_level": _I,
    }
)

BUILD_STRUCTURE_SCHEMA = _obj(
    {
        "sequences": _arr(
            _obj({"name": _S, "summary": _S, "turn": _S}),
        )
    }
)

SCORE_STORY_SCHEMA = _obj(
    {
        "breakdown": _arr(
            _obj({"category": _S, "score": _I, "max": _I, "note": _S}),
        ),
        "headline": _S,
        "top_fixes": _arr(_S),
    }
)

BUILD_FINANCE_SCHEMA = _obj(
    {
        "budget_ceiling": _I,
        "budget_rationale": _S,
        "comps": _arr(
            _obj({"title": _S, "year": _I, "budget_note": _S, "relevance": _S}),
        ),
        "capital_stack": _arr(
            _obj(
                {
                    "layer": _S,
                    "source": _S,
                    "percent": _I,
                    "note": _S,
                    "evidence": {"type": "string", "enum": config.EVIDENCE_TAGS},
                }
            ),
        ),
        "waterfall": _arr(_S),
        "deck_slides": _arr(
            _obj({"title": _S, "content": _S}),
        ),
        "assumptions": _arr(
            _obj({"claim": _S, "tag": {"type": "string", "enum": config.EVIDENCE_TAGS}}),
        ),
        "headline": _S,
    }
)


# ── The call ────────────────────────────────────────────────────────────────

_client: Optional[anthropic.AsyncAnthropic] = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic()  # reads ANTHROPIC_API_KEY
    return _client


def _backoff(attempt: int) -> float:
    return float(2 ** attempt)  # 1s, 2s, 4s


async def _create(model: str, system: str, user: str, schema: dict) -> Any:
    client = _get_client()
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": config.LLM_MAX_TOKENS,
        "system": [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ],
        "messages": [{"role": "user", "content": user}],
        "output_config": {"format": {"type": "json_schema", "schema": schema}},
    }
    if config.REFUSAL_FALLBACKS:
        return await client.beta.messages.create(
            betas=[config.FALLBACK_BETA], fallbacks="default", **kwargs
        )
    return await client.messages.create(**kwargs)


async def structured_call(model: str, user_prompt: str, schema: dict) -> dict:
    """
    One structured-output call with retries. Raises LLMNotConfigured,
    LLMRefused, or LLMError. Returns the parsed JSON dict.
    """
    if not is_configured():
        raise LLMNotConfigured()

    system = system_prompt()
    last_exc: Optional[Exception] = None
    for attempt in range(config.LLM_MAX_ATTEMPTS):
        try:
            response = await _create(model, system, user_prompt, schema)
        except anthropic.BadRequestError as exc:
            log.error("Claude BadRequest (not retried): %s", exc)
            raise LLMError(str(exc)) from exc
        except anthropic.RateLimitError as exc:
            last_exc = exc
            log.warning("Claude rate limited (attempt %d): %s", attempt + 1, exc)
        except anthropic.APIStatusError as exc:
            if exc.status_code >= 500:
                last_exc = exc
                log.warning("Claude %s (attempt %d): %s", exc.status_code, attempt + 1, exc)
            else:
                log.error("Claude %s (not retried): %s", exc.status_code, exc)
                raise LLMError(str(exc)) from exc
        except anthropic.APIConnectionError as exc:
            last_exc = exc
            log.warning("Claude connection error (attempt %d): %s", attempt + 1, exc)
        else:
            # Always check refusal before reading content.
            if response.stop_reason == "refusal":
                details = getattr(response, "stop_details", None)
                log.warning("Claude refused (after fallbacks): %s", details)
                raise LLMRefused(str(details) if details else "refusal")
            text = next((b.text for b in response.content if getattr(b, "type", "") == "text"), None)
            if text is None:
                raise LLMError("no text block in response")
            try:
                data = json.loads(text)
            except ValueError as exc:
                raise LLMError(f"invalid JSON from model: {exc}") from exc
            if not isinstance(data, dict):
                raise LLMError("model output was not a JSON object")
            return data

        if attempt < config.LLM_MAX_ATTEMPTS - 1:
            await asyncio.sleep(_backoff(attempt))

    raise LLMError(f"Claude call failed after {config.LLM_MAX_ATTEMPTS} attempts: {last_exc}")


# ── Per-function entry points (raw model output; routers post-process) ──────

async def develop_story(fields: dict) -> dict:
    return await structured_call(
        config.MODEL_CRAFT, load_prompt("develop_story", **fields), DEVELOP_STORY_SCHEMA
    )


async def build_structure(fields: dict) -> dict:
    return await structured_call(
        config.MODEL_CRAFT, load_prompt("build_structure", **fields), BUILD_STRUCTURE_SCHEMA
    )


async def score_story(fields: dict) -> dict:
    return await structured_call(
        config.MODEL_JUDGE, load_prompt("score_story", **fields), SCORE_STORY_SCHEMA
    )


async def build_finance(fields: dict) -> dict:
    return await structured_call(
        config.MODEL_JUDGE, load_prompt("build_finance", **fields), BUILD_FINANCE_SCHEMA
    )
