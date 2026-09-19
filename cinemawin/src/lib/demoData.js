// Demo-mode output for the browser-only build.
//
// When CinemaWin runs as a static site (GitHub Pages) there is no server to
// call, so the four story functions are answered here. The shapes match what
// the FastAPI backend returns AFTER post-processing, because there is no
// post-processing step in the browser — what this file returns is what the UI
// renders. Every response carries `demo: true` so the UI can say plainly that
// the words are a sample and not a reading of the user's film.

import {
  SCORE_CATEGORIES,
  CAPITAL_LAYERS,
  DECK_SLIDE_TITLES,
  WATERFALL_STEPS,
  MATURITY_LABELS,
  verdictForTotal,
  tierForCeiling,
} from "@/lib/doctrine";

// Small deterministic hash so the same project always gets the same numbers.
function seedOf(...parts) {
  const text = parts.map((p) => p || "").join("|");
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

const titleOf = (f) => (f.title || "").trim() || "The Last Archivist";
const genreOf = (f) => (f.genre || "").trim() || "Drama";
const loglineOf = (f) =>
  (f.logline || "").trim() ||
  "A municipal archivist discovers the city is quietly deleting the records of a neighborhood it intends to erase.";

export function developStory(fields) {
  const title = titleOf(fields);
  const genre = genreOf(fields);
  const logline = loglineOf(fields);
  const level = logline.length > 40 ? 1 : 0;
  return {
    demo: true,
    premise:
      `${title} is a ${genre.toLowerCase()} about what a person owes to a record no one else ` +
      `wants kept. Logline as received: "${logline}" The engine is Desire → Obstacle → Action → ` +
      `Consequence: the protagonist wants one file preserved, the institution wants it gone, and ` +
      `every move to save it costs them a piece of the life the institution gave them.`,
    protagonist:
      "A mid-career civil servant who has built an identity on being the person who never loses " +
      "anything. Surface want: keep the job, keep the order. The contradiction: they are meticulous " +
      "about paper and careless about people.",
    core_need:
      "To be witnessed rather than useful — to matter to someone as a person and not as the keeper " +
      "of their records.",
    emotional_wound:
      "A family history that was itself misfiled and lost, which they have never forgiven anyone for " +
      "and never spoken about. The Lie Believed: if everything is kept, nothing can be taken.",
    central_question:
      "Will they destroy the one record that would save the neighborhood, or the career that makes " +
      "them who they are — and is there a version where neither survives?",
    theme:
      "Memory is not preservation; it is a choice about who gets to be remembered, made by people " +
      "who would rather not be seen making it.",
    first_step:
      "Run DEVELOP with the PROTECT-THE-DNA lens: write the 8-sequence storyline, locking the " +
      "midpoint reversal where the archivist realises the deletion order has their own signature on it.",
    maturity_level: level,
    maturity_label: MATURITY_LABELS[String(level)],
  };
}

export function buildStructure(fields) {
  const title = titleOf(fields);
  const prot = ((fields.protagonist || "").trim() || "the archivist").split(".")[0].slice(0, 60);
  const rows = [
    [
      "The Ordinary Record",
      `${prot} runs the archive with quiet, absolute control. A routine deletion order arrives for a block of neighbourhood files.`,
      "They notice one name on the order that should not be there.",
    ],
    [
      "The Wrong File",
      "They pull the file, quietly, telling themselves it is procedure. A junior colleague notices and says nothing — yet.",
      "A second order arrives: the entire neighbourhood collection, scheduled for shredding in ten days.",
    ],
    [
      "Lines of Custody",
      "They begin tracing who signed the orders and why. The paper trail leads toward a redevelopment deal and a name they know socially.",
      "The colleague reports the irregular access. An audit is opened on the archivist.",
    ],
    [
      "Midpoint: The Signature",
      "Under audit, they discover a prior deletion — of records tied to their own family — bears their signature from years ago. They kept everything except this.",
      "They choose to copy the neighbourhood collection illegally rather than lose it twice.",
    ],
    [
      "Countermeasures",
      "The institution tightens access; a resident organiser wants the copies made public now. The archivist refuses — timing is control, and control is all they have left.",
      "The organiser leaks part of the archive without them; the story breaks wrong.",
    ],
    [
      "What the Paper Knows",
      "Publicly discredited, they read the family file at last. It says less than they feared and more than they can hold. They stop protecting the institution.",
      "They deliver the full record — with their own signature on the old deletion — to the one reporter who will print all of it.",
    ],
    [
      "The Hearing",
      "The city holds a hearing. The archive is entered as evidence; the archivist is entered as the person who once destroyed one. Both are true and neither is deniable.",
      "The redevelopment is halted. The archivist is dismissed.",
    ],
    [
      "A Record Kept by Others",
      `Weeks later. The neighbourhood keeps its own archive now, imperfectly, in a church basement. ${prot} visits and is not in charge of anything. The title card: ${title}.`,
      "They are asked to help — as a volunteer — and, for the first time, hesitate before saying yes.",
    ],
  ];
  return { demo: true, sequences: rows.map(([name, summary, turn]) => ({ name, summary, turn })) };
}

const SCORE_NOTES = [
  "Clear institutional antagonist and a hook that can be spoken in one breath. Originality above the civic-drama median.",
  "Causality holds through the midpoint; the third act needs a harder external clock than a scheduled hearing.",
  "Wound and contradiction are dramatised, not declared. Supporting cast still thin beyond the colleague and organiser.",
  "Subtext exists on the page; the organiser risks becoming a thesis mouthpiece under AHAG Question 2.",
  "Theme emerges from action (the old signature) rather than dialogue. Thematic climax is earned.",
  "Paper, basements, shredders — sound-driven and blockable. Few images yet that a trailer would open on.",
  "Comps in the contained civic-thriller lane perform to budget, not beyond it. Trailerability moderate.",
  "One marquee lead role with a strong arc; Tier-2 SVOD trigger plausible, Tier-1 foreign trigger unlikely.",
  "Two to three hubs, mostly interiors, no VFX. Highly shootable within a contained footprint.",
  "Ceiling defensible in the Contained Indie Tier; equity gap leverage depends on jurisdiction incentive.",
  "Director-driven material; sales-agent appeal contingent on lead attachment.",
  "Festival-first (TIFF / SXSW) into SVOD acquisition is a credible, well-trodden lane.",
];

export function scoreStory(fields) {
  const title = titleOf(fields);
  const seed = seedOf(title, loglineOf(fields), genreOf(fields));
  const breakdown = SCORE_CATEGORIES.map(([category, max], i) => {
    const offset = (seed >> (i * 2)) & 0b11;
    const score = Math.max(0, max - 1 - (offset % 3));
    return { category, score, max, note: SCORE_NOTES[i] };
  });
  const total = breakdown.reduce((sum, row) => sum + row.score, 0);
  const { verdict, label } = verdictForTotal(total);
  return {
    demo: true,
    total,
    verdict,
    verdict_label: label,
    breakdown,
    headline: `${title}: a contained, castable civic ${genreOf(fields).toLowerCase()} whose third act needs a harder clock.`,
    top_fixes: [
      "Replace the scheduled hearing with an irreversible deadline the antagonist controls (shred date moved up, not announced).",
      "Give the organiser a private want that conflicts with the archivist's — remove every line that explains the theme.",
      "Seed three trailer-grade images in Sequences 1–3 (the shredder room, the signature, the basement archive).",
    ],
  };
}

const DECK_BODIES = (title, genre, logline, ceiling, equityGap, equityPct, taxPct, presalePct, brandPct) => [
  `${title}. Logline: ${logline} Budget ceiling $${ceiling.toLocaleString()}; equity gap $${equityGap.toLocaleString()} (${equityPct}%); soft-money offset ${taxPct}%.`,
  `A contained ${genre.toLowerCase()} about who controls memory — timely as civic records digitise and neighbourhoods contest redevelopment.`,
  "Municipal interiors, fluorescent and paper-dense; 1.85:1 for grounded intimacy; sound palette of shredders, HVAC hum, and church-basement silence.",
  "Protagonist defined by contradiction (meticulous with paper, careless with people); colleague and organiser as opposing mirrors.",
  "One Tier-2 SVOD-trigger lead (45–60, any gender); two Tier-3 festival-prestige supporting roles. LOIs sought pay-or-play with escrow contingency.",
  "Three primary hubs (archive, city hall, church basement); 22-day schedule target; no VFX; company moves ≤1 per day.",
  "Comps: contained civic dramas/thrillers 2021–2025 acquired by streamers at or slightly above budget. Historic ROI modest and consistent, not explosive.",
  `Tax Incentives / Soft Money ${taxPct}% · Foreign Pre-Sales & MGs ${presalePct}% · Brand Integration & Grants ${brandPct}% · Equity Gap ${equityPct}%.`,
  "Festival premiere (TIFF / SXSW) → domestic SVOD acquisition; international via sales agent at market following premiere.",
  "Gross → sales commission + delivery → bridge/senior debt payoff → equity recoupment + 115% preferred (pari-passu) → 50/50 net profits split.",
  "Completion bond, escrowed LOIs, E&O insurance, 10% contingency; jurisdiction selected for a certified, monetisable credit.",
  "Producer of record, director attached, line producer with regional incentive experience; 9-month timeline from close to picture lock; capital call on subscription.",
];

const LOCKED_SLIDE_CONTENT = "Unlock with Premium to see this slide.";
const DECK_PREVIEW_SLIDES = 6;

export function buildFinance(fields, { deckUnlocked = false } = {}) {
  const title = titleOf(fields);
  const genre = genreOf(fields);
  const score = Number(fields.story_score) || 0;
  const ceiling = score < 80 ? 2_400_000 : 4_200_000;
  const taxPct = 28;
  const presalePct = score >= 80 ? 20 : 16;
  const brandPct = 6;
  const equityPct = 100 - taxPct - presalePct - brandPct;
  const equityGap = Math.round((ceiling * equityPct) / 100);
  const percents = [taxPct, presalePct, brandPct, equityPct];
  const sources = [
    "Georgia or Illinois 30% transferable credit, monetised via bridge at $0.90",
    "UK, Germany/Benelux, LATAM MGs contingent on lead LOI",
    "Regional arts foundation grant + camera/hardware sponsorship",
    "Private equity subscription",
  ];
  const notes = [
    "Net of monetisation discount.",
    "Requires Tier-2 attachment.",
    "Low-dilution, slow to close.",
    "Net request after non-dilutive layers.",
  ];
  const bodies = DECK_BODIES(
    title, genre, loglineOf(fields), ceiling, equityGap, equityPct, taxPct, presalePct, brandPct,
  );

  return {
    demo: true,
    budget_ceiling: ceiling,
    budget_tier: tierForCeiling(ceiling),
    budget_rationale:
      `Scored ${score || "unscored"} on the Greenlight Scorecard; a contained footprint and one marquee role ` +
      "place the defendable ceiling in this tier for comparable streamer buyouts. The ceiling is a MODEL " +
      "ASSUMPTION pending a departmental top sheet.",
    comps: [
      { title: "Contained civic drama A", year: 2023, budget_note: "Reported low-single-digit millions", relevance: "Institutional antagonist, single lead, interiors-heavy." },
      { title: "Paper-trail thriller B", year: 2022, budget_note: "Reported $3–5M range", relevance: "Document-driven suspense with a public hearing climax." },
      { title: "Neighbourhood ensemble C", year: 2024, budget_note: "Festival acquisition, undisclosed", relevance: "Community archive as narrative object; festival-to-SVOD path." },
    ],
    capital_stack: CAPITAL_LAYERS.map((layer, i) => ({
      layer,
      source: sources[i],
      percent: percents[i],
      note: notes[i],
      evidence: i === 3 ? "MODEL ASSUMPTION" : "INDUSTRY RANGE",
    })),
    equity_gap: equityGap,
    equity_gap_percent: equityPct,
    waterfall: deckUnlocked ? [...WATERFALL_STEPS] : [],
    deck_slides: DECK_SLIDE_TITLES.map((title_, i) => ({
      title: title_,
      content: deckUnlocked || i < DECK_PREVIEW_SLIDES ? bodies[i] : LOCKED_SLIDE_CONTENT,
    })),
    deck_unlocked: deckUnlocked,
    assumptions: [
      { claim: "30% transferable credit in Georgia/Illinois for qualifying in-state spend.", tag: "INDUSTRY RANGE" },
      { claim: "Bridge monetisation at $0.88–$0.92 on the dollar.", tag: "INDUSTRY RANGE" },
      { claim: `Budget ceiling of $${ceiling.toLocaleString()} for this project.`, tag: "MODEL ASSUMPTION" },
      { claim: "Foreign MGs achievable without a Tier-1 attachment.", tag: "PROJECT-SPECIFIC ASSUMPTION" },
      { claim: "Comp titles are illustrative placeholders in demo mode.", tag: "SCENARIO" },
    ],
    headline: `${title} finances as a contained $${(ceiling / 1e6).toFixed(1)}M streamer-buyout candidate with a ${equityPct}% equity ask.`,
  };
}

export const DEMO_FUNCTIONS = {
  developStory,
  buildStructure,
  scoreStory,
  buildFinance,
};
