"""Provider layer: JSON extraction, preset resolution, and paywall gating."""

import pytest

import config
from services import postprocess, providers


# ── extract_json: weaker free-tier models wrap JSON in prose or fences ───────

def test_extract_plain_json():
    assert providers.extract_json('{"a": 1}') == {"a": 1}


def test_extract_fenced_json():
    assert providers.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert providers.extract_json("```\n{\"a\": 1}\n```") == {"a": 1}


def test_extract_json_with_surrounding_prose():
    text = 'Sure! Here is the JSON you asked for:\n\n{"a": 1, "b": "x"}\n\nLet me know.'
    assert providers.extract_json(text) == {"a": 1, "b": "x"}


def test_extract_json_nested_braces():
    text = 'preamble {"outer": {"inner": [1, 2]}} trailer'
    assert providers.extract_json(text) == {"outer": {"inner": [1, 2]}}


def test_extract_json_rejects_non_object():
    for bad in ("", "   ", "not json at all", "[1, 2, 3]"):
        with pytest.raises(providers.LLMError):
            providers.extract_json(bad)


# ── Presets ─────────────────────────────────────────────────────────────────

def test_every_preset_is_complete():
    for name, p in providers.PRESETS.items():
        assert p["protocol"] in ("anthropic", "openai"), name
        assert p["craft_model"] and p["judge_model"], name
        assert p["key_url"].startswith("http"), name
        assert p["label"], name
        if p["protocol"] == "openai":
            assert p["base_url"].startswith("http"), name


def test_free_presets_exist():
    # The free path is the point; if this list empties, the README lies.
    assert set(providers.FREE_PRESETS) >= {"gemini", "groq", "ollama"}


def test_unknown_preset_falls_back_to_anthropic():
    assert providers.preset("nope")["protocol"] == "anthropic"


def test_status_never_leaks_the_key():
    assert "key" not in " ".join(providers.status().keys()).lower().replace("key_url", "")
    assert config.LLM_API_KEY not in str(providers.status()) or not config.LLM_API_KEY


# ── Paywall gating happens on the server, not in CSS ─────────────────────────

def _stack(percents):
    return [
        {"layer": n, "source": "s", "percent": p, "note": "n", "evidence": "INDUSTRY RANGE"}
        for n, p in zip(config.CAPITAL_LAYERS, percents)
    ]


def _slides(n=12):
    return [{"title": f"t{i}", "content": f"real slide body {i}"} for i in range(n)]


def test_locked_deck_withholds_content_past_the_preview():
    slides = postprocess.pad_deck_slides(_slides(), deck_unlocked=False)
    assert len(slides) == 12
    # Titles always visible — the user must see what they would be buying.
    assert [s["title"] for s in slides] == config.DECK_SLIDE_TITLES
    preview = postprocess.DECK_PREVIEW_SLIDES
    assert all("real slide body" in s["content"] for s in slides[:preview])
    assert all(s["content"] == postprocess.LOCKED_SLIDE_CONTENT for s in slides[preview:])


def test_unlocked_deck_returns_everything():
    slides = postprocess.pad_deck_slides(_slides(), deck_unlocked=True)
    assert all("real slide body" in s["content"] for s in slides)


def test_locked_finance_withholds_waterfall_and_flags_itself():
    raw = {"budget_ceiling": 4_200_000, "capital_stack": _stack([30, 22, 10, 38]), "deck_slides": _slides()}
    locked = postprocess.process_build_finance(raw, deck_unlocked=False)
    assert locked["waterfall"] == []
    assert locked["deck_unlocked"] is False

    unlocked = postprocess.process_build_finance(raw, deck_unlocked=True)
    assert len(unlocked["waterfall"]) == len(config.WATERFALL_STEPS)
    assert unlocked["deck_unlocked"] is True


def test_locked_finance_still_returns_the_free_numbers():
    # Budget, stack and comps are not paywalled — only the deck body and
    # the waterfall are.
    raw = {"budget_ceiling": 4_200_000, "capital_stack": _stack([30, 22, 10, 38]), "deck_slides": _slides()}
    locked = postprocess.process_build_finance(raw, deck_unlocked=False)
    assert locked["budget_ceiling"] == 4_200_000
    assert sum(l["percent"] for l in locked["capital_stack"]) == 100
    assert locked["equity_gap"] == 1_596_000


# ── doctrine.json is the shared source of truth ──────────────────────────────

def test_doctrine_file_drives_config():
    assert config.DOCTRINE_FILE is not None and config.DOCTRINE_FILE.is_file()
    assert config.SCORE_TOTAL_MAX == 100
    assert len(config.SCORE_CATEGORIES) == 12
    assert len(config.DECK_SLIDE_TITLES) == 12
    assert len(config.CAPITAL_LAYERS) == 4
    assert config.EQUITY_GAP_LAYER in config.CAPITAL_LAYERS
