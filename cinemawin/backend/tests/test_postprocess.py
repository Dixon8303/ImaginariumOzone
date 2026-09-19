import config
from services import demo_responses, postprocess


# ── Capital stack re-balancing ───────────────────────────────────────────────

def _stack(percents, names=None):
    names = names or config.CAPITAL_LAYERS
    return [
        {"layer": n, "source": "s", "percent": p, "note": "n", "evidence": "INDUSTRY RANGE"}
        for n, p in zip(names, percents)
    ]


def test_rebalance_sums_to_100_and_equity_absorbs_remainder():
    layers = postprocess.rebalance_capital_stack(_stack([30, 20, 5, 40]))  # sums to 95
    assert [l["layer"] for l in layers] == config.CAPITAL_LAYERS
    assert sum(l["percent"] for l in layers) == 100
    assert layers[3]["percent"] == 45  # 100 - (30+20+5)


def test_rebalance_over_100_shrinks_equity():
    layers = postprocess.rebalance_capital_stack(_stack([30, 25, 10, 50]))  # 115
    assert sum(l["percent"] for l in layers) == 100
    assert layers[3]["percent"] == 35


def test_rebalance_reorders_by_name_and_rounds():
    shuffled = [
        {"layer": "Equity gap (private)", "percent": 44.6},
        {"layer": "Brand integration and grants", "percent": 5.4},
        {"layer": "Foreign pre-sales / MGs", "percent": 20.2},
        {"layer": "Tax credits & soft money", "percent": 29.8},
    ]
    layers = postprocess.rebalance_capital_stack(shuffled)
    assert [l["layer"] for l in layers] == config.CAPITAL_LAYERS
    assert [l["percent"] for l in layers][:3] == [30, 20, 5]
    assert layers[3]["percent"] == 45
    assert sum(l["percent"] for l in layers) == 100


def test_rebalance_non_equity_exceeding_100_never_negative():
    layers = postprocess.rebalance_capital_stack(_stack([60, 50, 20, 10]))
    assert sum(l["percent"] for l in layers) == 100
    assert all(l["percent"] >= 0 for l in layers)


def test_rebalance_missing_layers_padded():
    layers = postprocess.rebalance_capital_stack([])
    assert len(layers) == 4
    assert layers[3]["percent"] == 100


# ── Verdict boundaries ───────────────────────────────────────────────────────

def test_verdict_boundaries():
    cases = {
        59: ("PASS", "PASS — Not Ready"),
        60: ("CONSIDER", "CONSIDER — Major Revision Required"),
        69: ("CONSIDER", "CONSIDER — Major Revision Required"),
        70: ("CONSIDER", "CONSIDER — Viable with Development"),
        79: ("CONSIDER", "CONSIDER — Viable with Development"),
        80: ("RECOMMEND", "RECOMMEND — Strong / Packaging Candidate"),
        89: ("RECOMMEND", "RECOMMEND — Strong / Packaging Candidate"),
        90: ("RECOMMEND", "RECOMMEND — Market-Ready / Exceptional"),
        100: ("RECOMMEND", "RECOMMEND — Market-Ready / Exceptional"),
        0: ("PASS", "PASS — Not Ready"),
    }
    for total, expected in cases.items():
        assert postprocess.verdict_for_total(total) == expected, total


def test_score_story_enforces_categories_clamps_and_recomputes_total():
    raw = {
        "breakdown": [
            {"category": "wrong name", "score": 99, "max": 3, "note": "clamped"},
            {"category": "x", "score": -4, "max": 10, "note": ""},
            {"category": "x", "score": 7.6, "max": 10, "note": ""},
        ],
        "headline": "h",
        "top_fixes": ["a"],
    }
    out = postprocess.process_score_story(raw)
    assert [r["category"] for r in out["breakdown"]] == [c for c, _ in config.SCORE_CATEGORIES]
    assert [r["max"] for r in out["breakdown"]] == [m for _, m in config.SCORE_CATEGORIES]
    assert out["breakdown"][0]["score"] == 10
    assert out["breakdown"][1]["score"] == 0
    assert out["breakdown"][2]["score"] == 8
    assert out["total"] == sum(r["score"] for r in out["breakdown"]) == 18
    assert out["verdict"] == "PASS"
    assert len(out["top_fixes"]) == 3


# ── Deck slide padding ───────────────────────────────────────────────────────

def test_pad_deck_slides_to_12_with_forced_titles():
    slides = postprocess.pad_deck_slides([{"title": "Whatever", "content": "Slide one body"}])
    assert len(slides) == 12
    assert [s["title"] for s in slides] == config.DECK_SLIDE_TITLES
    assert slides[0]["content"] == "Slide one body"
    assert all(s["content"] == "To be developed." for s in slides[1:])


def test_pad_deck_slides_truncates_extra():
    slides = postprocess.pad_deck_slides([{"title": "t", "content": f"c{i}"} for i in range(20)])
    assert len(slides) == 12
    assert slides[11]["content"] == "c11"


# ── Tier snapping / ceiling clamp / equity gap ───────────────────────────────

def test_tier_snapping():
    assert postprocess.tier_for_ceiling(499_999) == "Micro / Ultra-Low"
    assert postprocess.tier_for_ceiling(500_000) == "Contained Indie Tier"
    assert postprocess.tier_for_ceiling(3_499_999) == "Contained Indie Tier"
    assert postprocess.tier_for_ceiling(3_500_000) == "Mid-Tier Indie / Streamer Buyout"
    assert postprocess.tier_for_ceiling(8_499_999) == "Mid-Tier Indie / Streamer Buyout"
    assert postprocess.tier_for_ceiling(8_500_000) == "Studio Independent / Prestige"
    assert postprocess.tier_for_ceiling(50_000_000) == "Studio Independent / Prestige"


def test_ceiling_clamp_and_equity_gap():
    out = postprocess.process_build_finance(
        {"budget_ceiling": 5, "capital_stack": _stack([30, 20, 5, 45])}
    )
    assert out["budget_ceiling"] == 100_000
    assert out["budget_tier"] == "Micro / Ultra-Low"
    assert out["equity_gap_percent"] == 45
    assert out["equity_gap"] == 45_000

    out = postprocess.process_build_finance({"budget_ceiling": 999_999_999, "capital_stack": []})
    assert out["budget_ceiling"] == 50_000_000
    assert out["budget_tier"] == "Studio Independent / Prestige"

    out = postprocess.process_build_finance(
        {"budget_ceiling": 4_200_000, "capital_stack": _stack([30, 22, 10, 38])}
    )
    assert out["budget_tier"] == "Mid-Tier Indie / Streamer Buyout"
    assert out["equity_gap_percent"] == 38
    assert out["equity_gap"] == 1_596_000
    assert len(out["deck_slides"]) == 12
    assert out["waterfall"]  # defaults when the model omits it


# ── Structure + demo mode shapes ─────────────────────────────────────────────

def test_structure_padded_to_8():
    out = postprocess.process_build_structure({"sequences": [{"name": "A", "summary": "s", "turn": "t"}]})
    assert len(out["sequences"]) == 8
    assert out["sequences"][0]["name"] == "A"
    assert set(out["sequences"][7]) == {"name", "summary", "turn"}


def test_demo_responses_survive_postprocess():
    fields = {"title": "The Last Archivist", "logline": "A municipal archivist finds the city deleting a neighborhood.", "genre": "Drama", "track": "Writer"}
    dev = postprocess.process_develop_story(demo_responses.develop_story(fields))
    assert dev["maturity_label"].startswith("LEVEL")
    seq = postprocess.process_build_structure(demo_responses.build_structure(fields))
    assert len(seq["sequences"]) == 8
    sc = postprocess.process_score_story(demo_responses.score_story(fields))
    assert sc["total"] == sum(r["score"] for r in sc["breakdown"])
    assert len(sc["breakdown"]) == 12
    fin = postprocess.process_build_finance(
        demo_responses.build_finance({**fields, "story_score": sc["total"], "story_verdict": sc["verdict"]})
    )
    assert sum(l["percent"] for l in fin["capital_stack"]) == 100
    assert len(fin["deck_slides"]) == 12
    assert fin["equity_gap"] == round(fin["budget_ceiling"] * fin["equity_gap_percent"] / 100)
