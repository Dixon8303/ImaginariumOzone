"""
CinemaWin post-processing — deterministic enforcement of the contract shapes.

Every function here is pure: it takes the (possibly imperfect) model or demo
output and returns exactly the response shape the frontend expects. All
doctrine numbers come from config (never inline).
"""

from typing import Any, Optional

import config


# ── Small coercion helpers ───────────────────────────────────────────────────

def _str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip() or default
    return str(value)


def _int(value: Any, default: int = 0) -> int:
    try:
        if isinstance(value, bool):
            return int(value)
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def _list(value: Any) -> list:
    return list(value) if isinstance(value, (list, tuple)) else []


def _dict(value: Any) -> dict:
    return dict(value) if isinstance(value, dict) else {}


# ── developStory ─────────────────────────────────────────────────────────────

def maturity_label(level: int) -> str:
    return config.MATURITY_LABELS.get(level, config.MATURITY_LABELS[0])


def process_develop_story(raw: dict) -> dict:
    raw = _dict(raw)
    level = _clamp(_int(raw.get("maturity_level"), 0), 0, max(config.MATURITY_LABELS))
    return {
        "premise": _str(raw.get("premise")),
        "protagonist": _str(raw.get("protagonist")),
        "core_need": _str(raw.get("core_need")),
        "emotional_wound": _str(raw.get("emotional_wound")),
        "central_question": _str(raw.get("central_question")),
        "theme": _str(raw.get("theme")),
        "first_step": _str(raw.get("first_step")),
        "maturity_level": level,
        "maturity_label": maturity_label(level),
    }


# ── buildStructure ───────────────────────────────────────────────────────────

def process_build_structure(raw: dict) -> dict:
    raw = _dict(raw)
    sequences = []
    for i in range(config.STRUCTURE_SEQUENCE_COUNT):
        src = _dict(_list(raw.get("sequences"))[i]) if i < len(_list(raw.get("sequences"))) else {}
        sequences.append(
            {
                "name": _str(src.get("name"), f"Sequence {i + 1}"),
                "summary": _str(src.get("summary"), config.DECK_PLACEHOLDER_CONTENT),
                "turn": _str(src.get("turn"), config.DECK_PLACEHOLDER_CONTENT),
            }
        )
    return {"sequences": sequences}


# ── scoreStory ───────────────────────────────────────────────────────────────

def verdict_for_total(total: int) -> tuple[str, str]:
    """Returns (verdict, verdict_label) for a 0–100 total (Module 04 §II)."""
    for minimum, verdict, label in config.VERDICT_THRESHOLDS:
        if total >= minimum:
            return verdict, label
    # Unreachable given the 0 floor, but keep a defined answer.
    _, verdict, label = config.VERDICT_THRESHOLDS[-1]
    return verdict, label


def process_score_story(raw: dict) -> dict:
    raw = _dict(raw)
    model_rows = _list(raw.get("breakdown"))
    breakdown = []
    for i, (category, max_points) in enumerate(config.SCORE_CATEGORIES):
        src = _dict(model_rows[i]) if i < len(model_rows) else {}
        score = _clamp(_int(src.get("score"), 0), 0, max_points)
        breakdown.append(
            {
                "category": category,
                "score": score,
                "max": max_points,
                "note": _str(src.get("note")),
            }
        )
    total = sum(row["score"] for row in breakdown)
    verdict, label = verdict_for_total(total)

    fixes = [_str(f) for f in _list(raw.get("top_fixes")) if _str(f)]
    fixes = fixes[: config.TOP_FIXES_COUNT]
    while len(fixes) < config.TOP_FIXES_COUNT:
        fixes.append(config.DECK_PLACEHOLDER_CONTENT)

    return {
        "total": total,
        "verdict": verdict,
        "verdict_label": label,
        "breakdown": breakdown,
        "headline": _str(raw.get("headline")),
        "top_fixes": fixes,
    }


# ── buildFinance ─────────────────────────────────────────────────────────────

def clamp_budget_ceiling(value: Any) -> int:
    return _clamp(_int(value, config.BUDGET_CEILING_MIN), config.BUDGET_CEILING_MIN, config.BUDGET_CEILING_MAX)


def tier_for_ceiling(ceiling: int) -> str:
    for upper, tier in config.BUDGET_TIERS:
        if upper is None or ceiling < upper:
            return tier
    return config.BUDGET_TIERS[-1][1]


def _evidence_tag(value: Any, default: str = "MODEL ASSUMPTION") -> str:
    tag = _str(value).upper()
    return tag if tag in config.EVIDENCE_TAGS else default


def rebalance_capital_stack(raw_layers: list) -> list[dict]:
    """
    Force exactly 4 layers in config.CAPITAL_LAYERS order, rounded integer
    percents summing to exactly 100 with Equity Gap absorbing the remainder.

    Model layers are matched by name (case-insensitive substring heuristics),
    then by position for anything unmatched.
    """
    src_layers = [_dict(l) for l in _list(raw_layers)]

    def matches(name: str, target: str) -> bool:
        n = name.lower()
        t = target.lower()
        if n == t:
            return True
        keywords = {
            "Tax Incentives / Soft Money": ("tax", "soft money", "incentive"),
            "Foreign Pre-Sales & MGs": ("pre-sale", "presale", "pre sale", "minimum guarantee", "mg"),
            "Brand Integration & Grants": ("brand", "grant", "sponsor", "subsid"),
            "Equity Gap": ("equity",),
        }[target]
        return any(k in n for k in keywords)

    assigned: dict[str, dict] = {}
    used: set[int] = set()
    for target in config.CAPITAL_LAYERS:
        for idx, layer in enumerate(src_layers):
            if idx in used:
                continue
            if matches(_str(layer.get("layer")), target):
                assigned[target] = layer
                used.add(idx)
                break
    # Positional fill for anything still unmatched.
    remaining = [l for i, l in enumerate(src_layers) if i not in used]
    for target in config.CAPITAL_LAYERS:
        if target not in assigned:
            assigned[target] = remaining.pop(0) if remaining else {}

    layers = []
    for target in config.CAPITAL_LAYERS:
        src = assigned[target]
        layers.append(
            {
                "layer": target,
                "source": _str(src.get("source")),
                "percent": max(0, _int(src.get("percent"), 0)),
                "note": _str(src.get("note")),
                "evidence": _evidence_tag(src.get("evidence"), "INDUSTRY RANGE"),
            }
        )

    non_equity = [l for l in layers if l["layer"] != config.EQUITY_GAP_LAYER]
    equity = next(l for l in layers if l["layer"] == config.EQUITY_GAP_LAYER)

    # If the non-equity layers alone exceed 100, scale them down proportionally
    # so Equity Gap can never go negative.
    non_equity_sum = sum(l["percent"] for l in non_equity)
    if non_equity_sum > 100:
        scale = 100 / non_equity_sum
        for l in non_equity:
            l["percent"] = int(l["percent"] * scale)  # floor keeps sum <= 100
        non_equity_sum = sum(l["percent"] for l in non_equity)

    equity["percent"] = 100 - non_equity_sum
    return layers


def pad_deck_slides(raw_slides: list) -> list[dict]:
    """Exactly 12 slides, titles forced to the spec titles, content kept by position."""
    src = [_dict(s) for s in _list(raw_slides)]
    slides = []
    for i, title in enumerate(config.DECK_SLIDE_TITLES):
        content = _str(src[i].get("content")) if i < len(src) else ""
        slides.append({"title": title, "content": content or config.DECK_PLACEHOLDER_CONTENT})
    return slides


def process_build_finance(raw: dict) -> dict:
    raw = _dict(raw)
    ceiling = clamp_budget_ceiling(raw.get("budget_ceiling"))
    tier = tier_for_ceiling(ceiling)

    comps = []
    for c in _list(raw.get("comps"))[: config.COMPS_MAX]:
        c = _dict(c)
        comps.append(
            {
                "title": _str(c.get("title")),
                "year": _int(c.get("year"), 0),
                "budget_note": _str(c.get("budget_note")),
                "relevance": _str(c.get("relevance")),
            }
        )

    layers = rebalance_capital_stack(raw.get("capital_stack"))
    equity_pct = next(l["percent"] for l in layers if l["layer"] == config.EQUITY_GAP_LAYER)
    equity_gap = round(ceiling * equity_pct / 100)

    waterfall = [_str(w) for w in _list(raw.get("waterfall")) if _str(w)]
    if not waterfall:
        waterfall = list(config.WATERFALL_STEPS)

    assumptions = []
    for a in _list(raw.get("assumptions")):
        a = _dict(a)
        claim = _str(a.get("claim"))
        if claim:
            assumptions.append({"claim": claim, "tag": _evidence_tag(a.get("tag"))})

    return {
        "budget_ceiling": ceiling,
        "budget_tier": tier,
        "budget_rationale": _str(raw.get("budget_rationale")),
        "comps": comps,
        "capital_stack": layers,
        "equity_gap": equity_gap,
        "equity_gap_percent": equity_pct,
        "waterfall": waterfall,
        "deck_slides": pad_deck_slides(raw.get("deck_slides")),
        "assumptions": assumptions,
        "headline": _str(raw.get("headline")),
    }
