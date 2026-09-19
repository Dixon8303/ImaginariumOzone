"""
CinemaWin LLM layer — doctrine loading, JSON schemas, per-function calls.

Provider-agnostic: the transport lives in providers.py, which speaks both the
Anthropic and the OpenAI-compatible protocols. This module owns what is sent
(the doctrine system prompt and the per-stage user prompt) and what shape is
asked for; postprocess.py owns what is guaranteed to come back.
"""

import logging
from pathlib import Path
from typing import Any, Optional

import config
from services import providers
from services.providers import LLMError, LLMNotConfigured, LLMRefused  # re-exported

log = logging.getLogger("cinemawin.llm")

__all__ = [
    "LLMError",
    "LLMNotConfigured",
    "LLMRefused",
    "is_configured",
    "system_prompt",
    "develop_story",
    "build_structure",
    "score_story",
    "build_finance",
]


def is_configured() -> bool:
    return providers.is_configured()


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
- Return only the requested JSON object. No prose outside the JSON, and no
  markdown code fences around it.
"""

_system_text: Optional[str] = None
_prompt_cache: dict[str, str] = {}


def load_doctrine() -> str:
    """Concatenate prompts/doctrine/*.md in filename order (00…04)."""
    parts = [
        path.read_text(encoding="utf-8").strip()
        for path in sorted(Path(config.DOCTRINE_DIR).glob("*.md"))
    ]
    if not parts:
        raise LLMError(f"no doctrine documents found in {config.DOCTRINE_DIR}")
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


# ── JSON schemas ─────────────────────────────────────────────────────────────
# Every object sets additionalProperties=false and lists all properties in
# `required`, which strict structured-output modes demand. Array lengths and
# numeric ranges are stated in the prompts and enforced by postprocess.py.

def _obj(properties: dict) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties.keys()),
        "additionalProperties": False,
    }


def _arr(items: dict) -> dict:
    return {"type": "array", "items": items}


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
    {"sequences": _arr(_obj({"name": _S, "summary": _S, "turn": _S}))}
)

SCORE_STORY_SCHEMA = _obj(
    {
        "breakdown": _arr(_obj({"category": _S, "score": _I, "max": _I, "note": _S})),
        "headline": _S,
        "top_fixes": _arr(_S),
    }
)

BUILD_FINANCE_SCHEMA = _obj(
    {
        "budget_ceiling": _I,
        "budget_rationale": _S,
        "comps": _arr(_obj({"title": _S, "year": _I, "budget_note": _S, "relevance": _S})),
        "capital_stack": _arr(
            _obj(
                {
                    "layer": _S,
                    "source": _S,
                    "percent": _I,
                    "note": _S,
                    "evidence": {"type": "string", "enum": config.EVIDENCE_TAGS},
                }
            )
        ),
        "waterfall": _arr(_S),
        "deck_slides": _arr(_obj({"title": _S, "content": _S})),
        "assumptions": _arr(
            _obj({"claim": _S, "tag": {"type": "string", "enum": config.EVIDENCE_TAGS}})
        ),
        "headline": _S,
    }
)


# ── Per-function entry points (raw provider output; routers post-process) ────

async def _run(role: str, prompt_name: str, schema: dict, fields: dict) -> dict:
    return await providers.complete_json(
        role, system_prompt(), load_prompt(prompt_name, **fields), schema
    )


async def develop_story(fields: dict) -> dict:
    return await _run("craft", "develop_story", DEVELOP_STORY_SCHEMA, fields)


async def build_structure(fields: dict) -> dict:
    return await _run("craft", "build_structure", BUILD_STRUCTURE_SCHEMA, fields)


async def score_story(fields: dict) -> dict:
    return await _run("judge", "score_story", SCORE_STORY_SCHEMA, fields)


async def build_finance(fields: dict) -> dict:
    return await _run("judge", "build_finance", BUILD_FINANCE_SCHEMA, fields)
