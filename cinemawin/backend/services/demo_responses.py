"""
CinemaWin demo mode — deterministic canned responses.

Used when CINEMAWIN_DEMO_MODE is on (or "auto" with no API key) so the whole
UI works without an Anthropic key. Content is a "The Last Archivist"-style
sample parameterized by the request's title / logline / genre, and is shaped
exactly like the model output the post-processors expect (they still run on
top of it, so the returned shapes always match the contract).
"""

import hashlib

import config


def _seed(*parts: str) -> int:
    h = hashlib.sha256("|".join(p or "" for p in parts).encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _title(fields: dict) -> str:
    return (fields.get("title") or "").strip() or "The Last Archivist"


def _genre(fields: dict) -> str:
    return (fields.get("genre") or "").strip() or "Drama"


def _logline(fields: dict) -> str:
    return (fields.get("logline") or "").strip() or (
        "A municipal archivist discovers the city is quietly deleting the records "
        "of a neighborhood it intends to erase."
    )


# ── developStory ─────────────────────────────────────────────────────────────

def develop_story(fields: dict) -> dict:
    title = _title(fields)
    genre = _genre(fields)
    logline = _logline(fields)
    return {
        "premise": (
            f"{title} is a {genre.lower()} about what a person owes to a record no one else "
            f"wants kept. Logline as received: \"{logline}\" The engine is Desire → Obstacle → "
            "Action → Consequence: the protagonist wants one file preserved, the institution wants "
            "it gone, and every move to save it costs them a piece of the life the institution gave them."
        ),
        "protagonist": (
            "A mid-career civil servant who has built an identity on being the person who never "
            "loses anything. Surface want: keep the job, keep the order. The contradiction: they "
            "are meticulous about paper and careless about people."
        ),
        "core_need": (
            "To be witnessed rather than useful — to matter to someone as a person and not as the "
            "keeper of their records."
        ),
        "emotional_wound": (
            "A family history that was itself misfiled and lost, which they have never forgiven "
            "anyone for and never spoken about. The Lie Believed: if everything is kept, nothing can "
            "be taken."
        ),
        "central_question": (
            "Will they destroy the one record that would save the neighborhood, or the career that "
            "makes them who they are — and is there a version where neither survives?"
        ),
        "theme": (
            "Memory is not preservation; it is a choice about who gets to be remembered, made by "
            "people who would rather not be seen making it."
        ),
        "first_step": (
            "Run DEVELOP with the PROTECT-THE-DNA lens: write the 8-sequence storyline, locking the "
            "midpoint reversal where the archivist realizes the deletion order has their own "
            "signature on it."
        ),
        "maturity_level": 1 if logline and len(logline) > 40 else 0,
    }


# ── buildStructure ───────────────────────────────────────────────────────────

def build_structure(fields: dict) -> dict:
    title = _title(fields)
    prot = (fields.get("protagonist") or "").strip() or "the archivist"
    prot_short = prot.split(".")[0][:60]
    seqs = [
        ("The Ordinary Record",
         f"{prot_short} runs the archive with quiet, absolute control. A routine deletion order arrives for a block of neighborhood files.",
         "They notice one name on the order that should not be there."),
        ("The Wrong File",
         "They pull the file, quietly, telling themselves it is procedure. A junior colleague notices and says nothing — yet.",
         "A second order arrives: the entire neighborhood collection, scheduled for shredding in ten days."),
        ("Lines of Custody",
         "They begin tracing who signed the orders and why. The paper trail leads toward a redevelopment deal and a name they know socially.",
         "The colleague reports the irregular access. An audit is opened on the archivist."),
        ("Midpoint: The Signature",
         "Under audit, they discover a prior deletion — of records tied to their own family — bears their signature from years ago. They kept everything except this.",
         "They choose to copy the neighborhood collection illegally rather than lose it twice."),
        ("Countermeasures",
         "The institution tightens access; a resident organizer wants the copies made public now. The archivist refuses — timing is control, and control is all they have left.",
         "The organizer leaks part of the archive without them; the story breaks wrong."),
        ("What the Paper Knows",
         "Publicly discredited, they read the family file at last. It says less than they feared and more than they can hold. They stop protecting the institution.",
         "They deliver the full record — with their own signature on the old deletion — to the one reporter who will print all of it."),
        ("The Hearing",
         "The city holds a hearing. The archive is entered as evidence; the archivist is entered as the person who once destroyed one. Both are true and neither is deniable.",
         "The redevelopment is halted. The archivist is dismissed."),
        ("A Record Kept by Others",
         f"Weeks later. The neighborhood keeps its own archive now, imperfectly, in a church basement. {prot_short} visits and is not in charge of anything. The title card: {title}.",
         "They are asked to help — as a volunteer — and, for the first time, hesitate before saying yes."),
    ]
    return {
        "sequences": [{"name": n, "summary": s, "turn": t} for n, s, t in seqs]
    }


# ── scoreStory ───────────────────────────────────────────────────────────────

def score_story(fields: dict) -> dict:
    title = _title(fields)
    seed = _seed(title, _logline(fields), _genre(fields))
    # Deterministic per-project variation: pattern of -0/-1/-2 offsets by category.
    offsets = [(seed >> (i * 2)) & 0b11 for i in range(len(config.SCORE_CATEGORIES))]
    notes = [
        "Clear institutional antagonist and a hook that can be spoken in one breath. Originality above the civic-drama median.",
        "Causality holds through the midpoint; the third act needs a harder external clock than a scheduled hearing.",
        "Wound and contradiction are dramatized, not declared. Supporting cast still thin beyond the colleague and organizer.",
        "Subtext exists on the page; the organizer risks becoming a thesis mouthpiece under AHAG Question 2.",
        "Theme emerges from action (the old signature) rather than dialogue. Thematic climax is earned.",
        "Paper, basements, shredders — sound-driven and blockable. Few images yet that a trailer would open on.",
        "Comps in the contained civic-thriller lane perform to budget, not beyond it. Trailerability moderate.",
        "One marquee lead role with a strong arc; Tier-2 SVOD trigger plausible, Tier-1 foreign trigger unlikely.",
        "Two to three hubs, mostly interiors, no VFX. Highly shootable within a contained footprint.",
        "Ceiling defensible in the Contained Indie Tier; equity gap leverage depends on jurisdiction incentive.",
        "Director-driven material; sales-agent appeal contingent on lead attachment.",
        "Festival-first (TIFF / SXSW) into SVOD acquisition is a credible, well-trodden lane.",
    ]
    breakdown = []
    for (category, mx), off, note in zip(config.SCORE_CATEGORIES, offsets, notes):
        # Baseline one point below the maximum (9/10 or 4/5), then a small
        # deterministic deduction so different projects score differently.
        score = max(0, (mx - 1) - (off % 3))
        breakdown.append({"category": category, "score": score, "max": mx, "note": note})
    return {
        "breakdown": breakdown,
        "headline": f"{title}: a contained, castable civic {_genre(fields).lower()} whose third act needs a harder clock.",
        "top_fixes": [
            "Replace the scheduled hearing with an irreversible deadline the antagonist controls (shred date moved up, not announced).",
            "Give the organizer a private want that conflicts with the archivist's — remove every line that explains the theme.",
            "Seed three trailer-grade images in Sequences 1–3 (the shredder room, the signature, the basement archive).",
        ],
    }


# ── buildFinance ─────────────────────────────────────────────────────────────

def build_finance(fields: dict) -> dict:
    title = _title(fields)
    genre = _genre(fields)
    try:
        score = int(fields.get("story_score") or 0)
    except (TypeError, ValueError):
        score = 0
    ceiling = 2_400_000 if score < 80 else 4_200_000
    tax_pct = 28
    presale_pct = 20 if score >= 80 else 16
    brand_pct = 6
    equity_pct = 100 - tax_pct - presale_pct - brand_pct
    equity_gap = round(ceiling * equity_pct / 100)

    slides = [
        f"{title}. Logline: {_logline(fields)} Budget ceiling ${ceiling:,}; equity gap ${equity_gap:,} ({equity_pct}%); soft-money offset {tax_pct}%.",
        f"A contained {genre.lower()} about who controls memory — timely as civic records digitize and neighborhoods contest redevelopment.",
        "Municipal interiors, fluorescent and paper-dense; 1.85:1 for grounded intimacy; sound palette of shredders, HVAC hum, and church-basement silence.",
        "Protagonist defined by contradiction (meticulous with paper, careless with people); colleague and organizer as opposing mirrors.",
        "One Tier-2 SVOD-trigger lead (45–60, any gender); two Tier-3 festival-prestige supporting roles. LOIs sought pay-or-play with escrow contingency.",
        "Three primary hubs (archive, city hall, church basement); 22-day schedule target; no VFX; company moves ≤1 per day.",
        "Comps: contained civic dramas/thrillers 2021–2025 acquired by streamers at or slightly above budget. Historic ROI modest and consistent, not explosive.",
        f"Tax Incentives / Soft Money {tax_pct}% · Foreign Pre-Sales & MGs {presale_pct}% · Brand Integration & Grants {brand_pct}% · Equity Gap {equity_pct}%.",
        "Festival premiere (TIFF / SXSW) → domestic SVOD acquisition; international via sales agent at market following premiere.",
        "Gross → sales commission + delivery → bridge/senior debt payoff → equity recoupment + 115% preferred (pari-passu) → 50/50 net profits split.",
        "Completion bond, escrowed LOIs, E&O insurance, 10% contingency; jurisdiction selected for a certified, monetizable credit.",
        "Producer of record, director attached, line producer with regional incentive experience; 9-month timeline from close to picture lock; capital call on subscription.",
    ]
    return {
        "budget_ceiling": ceiling,
        "budget_rationale": (
            f"Scored {score or 'unscored'} on the Greenlight Scorecard; contained footprint and one marquee role "
            "place the defendable ceiling in the Contained Indie Tier for comparable streamer buyouts. Ceiling is a MODEL ASSUMPTION pending a top sheet."
        ),
        "comps": [
            {"title": "Contained civic drama A", "year": 2023, "budget_note": "Reported low-single-digit millions", "relevance": "Institutional antagonist, single lead, interiors-heavy."},
            {"title": "Paper-trail thriller B", "year": 2022, "budget_note": "Reported $3–5M range", "relevance": "Document-driven suspense with a public hearing climax."},
            {"title": "Neighborhood ensemble C", "year": 2024, "budget_note": "Festival acquisition, undisclosed", "relevance": "Community archive as narrative object; festival-to-SVOD path."},
        ],
        "capital_stack": [
            {"layer": "Tax Incentives / Soft Money", "source": "Georgia or Illinois 30% transferable credit, monetized via bridge at $0.90", "percent": tax_pct, "note": "Net of monetization discount.", "evidence": "INDUSTRY RANGE"},
            {"layer": "Foreign Pre-Sales & MGs", "source": "UK, Germany/Benelux, LATAM MGs contingent on lead LOI", "percent": presale_pct, "note": "Requires Tier-2 attachment.", "evidence": "INDUSTRY RANGE"},
            {"layer": "Brand Integration & Grants", "source": "Regional arts foundation grant + camera/hardware sponsorship", "percent": brand_pct, "note": "Low-dilution, slow to close.", "evidence": "INDUSTRY RANGE"},
            {"layer": "Equity Gap", "source": "Private equity subscription", "percent": equity_pct, "note": "Net request after non-dilutive layers.", "evidence": "MODEL ASSUMPTION"},
        ],
        "waterfall": list(config.WATERFALL_STEPS),
        "deck_slides": [
            {"title": t, "content": c} for t, c in zip(config.DECK_SLIDE_TITLES, slides)
        ],
        "assumptions": [
            {"claim": "30% transferable credit in Georgia/Illinois for qualifying in-state spend.", "tag": "INDUSTRY RANGE"},
            {"claim": "Bridge monetization at $0.88–$0.92 on the dollar.", "tag": "INDUSTRY RANGE"},
            {"claim": f"Budget ceiling of ${ceiling:,} for this project.", "tag": "MODEL ASSUMPTION"},
            {"claim": "Foreign MGs achievable without a Tier-1 attachment.", "tag": "PROJECT-SPECIFIC ASSUMPTION"},
            {"claim": "Comp titles are illustrative placeholders in demo mode.", "tag": "SCENARIO"},
        ],
        "headline": f"{title} finances as a contained ${ceiling/1_000_000:.1f}M streamer-buyout candidate with a {equity_pct}% equity ask.",
    }
