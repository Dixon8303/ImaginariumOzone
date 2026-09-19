"""
CinemaWin LLM providers.

CinemaWin does not require Anthropic. It speaks two wire protocols:

  * ``anthropic``  — the Anthropic Messages API (Claude).
  * ``openai``     — the OpenAI-compatible ``/chat/completions`` shape, which
                     nearly every other provider also speaks: Google Gemini
                     (via its OpenAI-compatible endpoint), Groq, OpenRouter,
                     Together, Cerebras, a local Ollama or LM Studio, and
                     OpenAI itself.

That second protocol is the point: several providers offer a genuinely free
tier, so CinemaWin can run on real models at no cost. Presets below fill in
the base URL and a sensible default model for each, so `.env` usually needs
only a preset name and a key.

Structured output is requested with ``json_schema`` where the provider
supports it and falls back to ``json_object`` where it does not; either way
``postprocess.py`` is the real guarantee of shape, so a weaker free model
still produces a valid response.
"""

import asyncio
import json
import logging
import re
from typing import Any, Optional

import httpx

import config

log = logging.getLogger("cinemawin.providers")


class LLMNotConfigured(Exception):
    """No provider credentials, and demo mode is off."""


class LLMError(Exception):
    """API failure after retries, or unparseable output."""


class LLMRefused(Exception):
    """The provider declined the request on policy grounds."""


# ── Presets ──────────────────────────────────────────────────────────────────
# `free` marks providers with a no-credit-card free tier at the time of
# writing. Free tiers change; treat it as a pointer, not a promise.

PRESETS: dict[str, dict] = {
    "anthropic": {
        "protocol": "anthropic",
        "base_url": "",  # the SDK's default
        "craft_model": "claude-opus-5",
        "judge_model": "claude-opus-5",
        "key_url": "https://console.anthropic.com/settings/keys",
        "free": False,
        "label": "Anthropic (Claude)",
    },
    "gemini": {
        "protocol": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "craft_model": "gemini-2.5-flash",
        "judge_model": "gemini-2.5-flash",
        "key_url": "https://aistudio.google.com/apikey",
        "free": True,
        "label": "Google Gemini (free tier, no card)",
    },
    "groq": {
        "protocol": "openai",
        "base_url": "https://api.groq.com/openai/v1",
        "craft_model": "llama-3.3-70b-versatile",
        "judge_model": "llama-3.3-70b-versatile",
        "key_url": "https://console.groq.com/keys",
        "free": True,
        "label": "Groq (free tier, no card)",
    },
    "openrouter": {
        "protocol": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "craft_model": "meta-llama/llama-3.3-70b-instruct:free",
        "judge_model": "meta-llama/llama-3.3-70b-instruct:free",
        "key_url": "https://openrouter.ai/keys",
        "free": True,
        "label": "OpenRouter (has :free models)",
    },
    "together": {
        "protocol": "openai",
        "base_url": "https://api.together.xyz/v1",
        "craft_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "judge_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "key_url": "https://api.together.ai/settings/api-keys",
        "free": False,
        "label": "Together AI",
    },
    "cerebras": {
        "protocol": "openai",
        "base_url": "https://api.cerebras.ai/v1",
        "craft_model": "llama-3.3-70b",
        "judge_model": "llama-3.3-70b",
        "key_url": "https://cloud.cerebras.ai/",
        "free": True,
        "label": "Cerebras (free tier)",
    },
    "openai": {
        "protocol": "openai",
        "base_url": "https://api.openai.com/v1",
        "craft_model": "gpt-4o",
        "judge_model": "gpt-4o",
        "key_url": "https://platform.openai.com/api-keys",
        "free": False,
        "label": "OpenAI",
    },
    "ollama": {
        "protocol": "openai",
        "base_url": "http://localhost:11434/v1",
        "craft_model": "llama3.1",
        "judge_model": "llama3.1",
        "key_url": "https://ollama.com/download",
        "free": True,
        "label": "Ollama (local, unlimited, no key)",
        "keyless": True,
    },
}

FREE_PRESETS = [name for name, p in PRESETS.items() if p.get("free")]


def preset(name: str) -> dict:
    return PRESETS.get(name, PRESETS["anthropic"])


# ── Resolved active configuration ────────────────────────────────────────────

def active() -> dict:
    """The provider CinemaWin will actually call, after env resolution."""
    p = preset(config.LLM_PROVIDER)
    return {
        "name": config.LLM_PROVIDER,
        "label": p["label"],
        "protocol": p["protocol"],
        "base_url": (config.LLM_BASE_URL or p["base_url"]).rstrip("/"),
        "craft_model": config.MODEL_CRAFT or p["craft_model"],
        "judge_model": config.MODEL_JUDGE or p["judge_model"],
        "keyless": bool(p.get("keyless")),
        "key_url": p["key_url"],
        "free": bool(p.get("free")),
    }


def is_configured() -> bool:
    """True when the active provider has everything it needs to be called."""
    a = active()
    if a["keyless"]:
        return bool(a["base_url"])
    return bool(config.LLM_API_KEY)


def status() -> dict:
    """Safe-to-publish description of the provider. Never includes the key."""
    a = active()
    return {
        "provider": a["name"],
        "label": a["label"],
        "protocol": a["protocol"],
        "craft_model": a["craft_model"],
        "judge_model": a["judge_model"],
        "configured": is_configured(),
        "free_tier": a["free"],
    }


# ── JSON extraction (weaker models wrap output in prose or fences) ───────────

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json(text: str) -> dict:
    """Parse a JSON object out of a model response. Raises LLMError."""
    if not text or not text.strip():
        raise LLMError("empty response from model")
    candidates = [text]
    fenced = _FENCE.search(text)
    if fenced:
        candidates.insert(0, fenced.group(1))
    # Last resort: the outermost {...} span.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(data, dict):
            return data
    raise LLMError("model did not return a JSON object")


# ── Anthropic transport ──────────────────────────────────────────────────────

_anthropic_client = None


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic  # imported lazily so the package is optional

        _anthropic_client = anthropic.AsyncAnthropic(api_key=config.LLM_API_KEY or None)
    return _anthropic_client


async def _anthropic_call(model: str, system: str, user: str, schema: dict) -> dict:
    import anthropic

    client = _get_anthropic()
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": config.LLM_MAX_TOKENS,
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": user}],
        "output_config": {"format": {"type": "json_schema", "schema": schema}},
    }
    try:
        if config.REFUSAL_FALLBACKS:
            response = await client.beta.messages.create(
                betas=[config.FALLBACK_BETA], fallbacks="default", **kwargs
            )
        else:
            response = await client.messages.create(**kwargs)
    except anthropic.BadRequestError as exc:
        raise LLMError(str(exc)) from exc
    except anthropic.APIStatusError as exc:
        if exc.status_code >= 500:
            raise _Retryable(str(exc)) from exc
        raise LLMError(str(exc)) from exc
    except (anthropic.RateLimitError, anthropic.APIConnectionError) as exc:
        raise _Retryable(str(exc)) from exc

    # Always check refusal before reading content.
    if response.stop_reason == "refusal":
        raise LLMRefused(str(getattr(response, "stop_details", None) or "refusal"))
    text = next((b.text for b in response.content if getattr(b, "type", "") == "text"), None)
    if text is None:
        raise LLMError("no text block in response")
    return extract_json(text)


# ── OpenAI-compatible transport ──────────────────────────────────────────────

class _Retryable(Exception):
    """Internal marker: this failure is worth another attempt."""


def _openai_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if config.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {config.LLM_API_KEY}"
    # OpenRouter attributes traffic with these; harmless elsewhere.
    headers["HTTP-Referer"] = config.PUBLIC_URL or "https://localhost"
    headers["X-Title"] = config.APP_NAME
    return headers


async def _openai_post(url: str, payload: dict) -> dict:
    timeout = httpx.Timeout(config.LLM_TIMEOUT_SEC)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=_openai_headers())
    except httpx.RequestError as exc:
        raise _Retryable(f"connection error: {exc}") from exc

    if response.status_code == 429:
        raise _Retryable(f"rate limited: {response.text[:300]}")
    if response.status_code >= 500:
        raise _Retryable(f"{response.status_code}: {response.text[:300]}")
    if response.status_code >= 400:
        body = response.text[:600]
        # Providers signal a policy block in various ways; treat the common
        # shapes as a refusal so the UI can say something useful.
        if any(w in body.lower() for w in ("content_filter", "safety", "blocked", "policy")):
            raise LLMRefused(body)
        raise LLMError(f"{response.status_code}: {body}")
    try:
        return response.json()
    except ValueError as exc:
        raise LLMError(f"non-JSON response body: {response.text[:300]}") from exc


async def _openai_call(model: str, system: str, user: str, schema: dict) -> dict:
    base = active()["base_url"]
    url = f"{base}/chat/completions"
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    base_payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": config.LLM_MAX_TOKENS,
    }

    # Prefer a strict schema; fall back to plain JSON mode, then to no format
    # hint at all. postprocess.py is what actually guarantees the shape.
    attempts = [
        {
            **base_payload,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "cinemawin_response", "strict": True, "schema": schema},
            },
        },
        {**base_payload, "response_format": {"type": "json_object"}},
        base_payload,
    ]

    last_error: Optional[Exception] = None
    for i, payload in enumerate(attempts):
        try:
            data = await _openai_post(url, payload)
        except LLMError as exc:
            # A 400 here usually means "this provider doesn't support that
            # response_format" — try the simpler one rather than giving up.
            last_error = exc
            if i < len(attempts) - 1:
                log.info("response_format attempt %d rejected, falling back: %s", i + 1, exc)
                continue
            raise
        choices = data.get("choices") or []
        if not choices:
            raise LLMError(f"no choices in response: {json.dumps(data)[:300]}")
        message = choices[0].get("message") or {}
        if choices[0].get("finish_reason") == "content_filter":
            raise LLMRefused("content filtered by provider")
        content = message.get("content") or ""
        if isinstance(content, list):  # some providers return content parts
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return extract_json(content)

    raise LLMError(str(last_error) if last_error else "no response")


# ── Public entry point ───────────────────────────────────────────────────────

async def complete_json(role: str, system: str, user: str, schema: dict) -> dict:
    """
    Call the active provider and return a parsed JSON object.

    `role` is "craft" (develop / structure) or "judge" (score / finance);
    it selects which configured model to use.
    """
    if not is_configured():
        raise LLMNotConfigured()

    a = active()
    model = a["judge_model"] if role == "judge" else a["craft_model"]
    call = _anthropic_call if a["protocol"] == "anthropic" else _openai_call

    last: Optional[Exception] = None
    for attempt in range(config.LLM_MAX_ATTEMPTS):
        try:
            return await call(model, system, user, schema)
        except _Retryable as exc:
            last = exc
            log.warning(
                "%s attempt %d/%d failed: %s",
                a["name"], attempt + 1, config.LLM_MAX_ATTEMPTS, exc,
            )
            if attempt < config.LLM_MAX_ATTEMPTS - 1:
                await asyncio.sleep(2 ** attempt)
        except LLMError as exc:
            # Malformed output is worth one more shot; a bad request is not.
            if "JSON" in str(exc) and attempt < config.LLM_MAX_ATTEMPTS - 1:
                last = exc
                log.warning("unparseable output, retrying: %s", exc)
                await asyncio.sleep(1)
                continue
            raise
    raise LLMError(f"{a['name']} failed after {config.LLM_MAX_ATTEMPTS} attempts: {last}")
