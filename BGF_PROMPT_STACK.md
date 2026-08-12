# BGF_PROMPT_STACK.md — MODULAR STAGE CONTROLLERS
**Each prompt controls one pipeline stage autonomously.** Copy-paste ready.
Every prompt: (1) loads only its required modules, (2) consumes the prior stage's STATE block, (3) executes its stage to completion, (4) emits an updated STATE block for handoff. CORE is always loaded. Never re-derive locked stages.

---
## HOW TO USE
1. In a Claude Project, keep `BGF_CORE.md` + `BGF_DOCTRINE_INDEX.md` + the ten modules (M01–M10) in project knowledge.
2. Run prompts in sequence P1→P5→P5.5→P6→P10, or jump to any stage by pasting its prompt + the latest STATE block.
3. Each prompt's `LOAD:` line tells the model which modules to weight. Honor token discipline — ignore unloaded modules.

---
## PIPELINE ORDER v2 — PARALLEL TRACK ARCHITECTURE
*(Approved 2026-08-11. Supersedes linear P1→P10 for production episodes.)*

**Goal:** Start ComfyUI image generation 2+ days earlier per episode. Gate QA before Shorts extraction so re-renders don't force 13-clip re-extracts.

### Sequence

```
P0.5 → P1 → P2 → P3 → P4
                           ↓
                  P6 STORYBOARD  ← moved immediately after P4 (script lock)
                  + submit ComfyUI
                           |
         ┌─────────────────┼──────────────────┐
  Track A (Visual)    Track B (Audio)    Track C (Metadata)
  ComfyUI renders     P5  VO / SSML        P7a  Titles (needs script only)
  (12–14 min/shot)    Stage 0             P8   SEO (follows P7a)
  P5.5 Audio prod     P5.5 Audio          P9a  Shorts scripts (needs script only)
  (after VO done)
         └─────────────────┼──────────────────┘
                           ↓
                  All three tracks converge
                           ↓
                  ASSEMBLY  (images + audio + metadata)
                           ↓
                  P10 QA  ← gates assembly; catches re-render issues BEFORE Shorts
                           ↓
                  P9b  Shorts extraction  ← now LAST; never re-extracted post-QA
                           ↓
                  P4.5 Canon entry  ← non-blocking; runs in parallel or after
                           ↓
                  P10.5 Upload / release
```

### P7 Split Detail
- **P7a — Titles + Thumbnail Brief:** runs after P4 (script only needed). No images required.
- **P7b — Thumbnail Flux prompts / render:** runs after P6 (needs first shotlist entry = thumbnail-first shot). Feeds Leonardo.ai or VidIQ.

### Key Constraints
- **Storyboard timestamps are ESTIMATES** until VO actual duration is known. Assembly rescales by factor `(actual_VO_duration ÷ script_estimated_duration)`. Scale factor must be written to STATE at P5.5 completion.
- **P4.5 (Canon Entry)** is non-blocking. Write it during Track C or after P10 — never hold assembly for it.
- **Token cost:** unchanged. Module loads are task-driven, not sequence-driven. Parallel tracks use the same modules in the same quantities.
- **QA before Shorts is the binding gate.** P10 must clear before any clip is extracted from the master.

---

### STATE BLOCK FORMAT (The JSON State Envelope)
```
To ensure data hand-offs between your P1–P10 pipeline stages never experience state drops or structural degradation, no episode may advance from Scripting to Execution without validating against this strict, locked TypeScript schema envelope. 

```typescript
export interface BGF_State_Envelope {
  catalog_id: string; // Pulled directly from BGF_M11_MEMORY.md
  locked_metadata: {
    working_title: string;
    primary_pillar: string;
    archetype: "Builder" | "Keeper" | "Rebel" | "Oracle" | "Architect";
  };
  active_loops: {
    master_curiosity_loop: string;
    sub_loops: string[];
  };
  visual_seeds: {
    symbol_motifs: string[];
    color_arc_status: string;
  };
  source_bibliography: Array<{
    claim: string;
    primary_source: string;
    verification_status: "Verified" | "Inferred" | "Unknown";
  }>;
  gate_status: {
    G1_cleared: boolean;
    G2_score: number;
    G3_cleared: boolean; // HARD-STOP: Must be true before advancing to Execution
  };
}
=== BGF STATE ===
Episode: [#] | Title(working): [...] | Pillar: [1-6] | Node-log: [era/system/antagonist/artifact/archetype/motif]
Locked: [stages completed — treat as canonical, do not regenerate]
Score: [/100, gate results G1–G5]
Open decisions: [...]
=== END STATE ===
```

---
## P0 — ORCHESTRATOR / ROUTER
```
ROLE: BGF pipeline orchestrator. LOAD: CORE + DOCTRINE_INDEX.
INPUT: [a task or a STATE block]
DO: Identify which pipeline stage this is. Name the modules to load per the routing table. Confirm prior STATE is present and which stages are locked. If a gate is due, route to it. Output: the stage to run next, the exact prompt to use (P1–P10), and the modules to load. Do not execute the stage yourself.
```

## P0.5 — CLUSTER BATCH PRIMER (run before P1 when producing 3–5 episodes on the same theme)
```
ROLE: BGF cluster strategist. LOAD: CORE + M04 + M09 + M11(micro).
INPUT: [cluster theme + 3–5 episode candidates]
EFFICIENCY RULE: Load M04 (Research) and M09 (Canon) ONCE for the entire cluster. Running P1+P2 across all episodes in a single context eliminates per-episode module reloading — the primary token-efficiency gain of cluster production.
DO:
1. IDEATION BATCH — Score all 3–5 candidates against the G2 100-pt matrix simultaneously. Rank and gate: ≥70 proceed / 60–69 flag / <60 cut.
2. RESEARCH BATCH — Build the shared evidence base for the cluster theme (shared sources, shared antagonist mechanism, shared era). Extract per-episode divergences into individual research appendices.
3. CONTINUITY BATCH — For each episode, plant at minimum ONE explicit cross-episode bridge: a claim, artifact, or character that directly links to an adjacent episode in the cluster. Log to M09 Knowledge Graph.
4. CLUSTER FLAG — Mark any episode requiring heavy revision. Apply bypass-and-publish rule: do not freeze the cluster for one blocked episode. Flag the blocked episode, advance the others to linear execution.
OUTPUT: Ranked episode table + shared research base + per-episode research appendices + continuity bridge map + cluster STATE block.
TRANSITION: Hand off each approved episode to P1→P3 linear execution (do NOT batch P4 scripting — execute one episode at a time to prevent state drops).
```

## P1 — IDEATION & SCORING
```
ROLE: BGF topic strategist + scoring gate. LOAD: CORE + M04 + M07(micro).
INPUT: [topic, theme, or "propose N candidates in Pillar X"]
DO: For each candidate — assign pillar, run G1 Editorial Perspective (named institution? systems frame? reconstructable? extends thesis?), then score the 100-pt matrix with per-dimension justification. Validate Search/Competition assumptions (flag where vidIQ/TubeBuddy check is needed). Apply gate: ≥70 produce / 60–69 return with named weak axes / <60 kill.
OUTPUT: ranked table + 1 recommended episode + node-log line + STATE block.
```

## P2 — RESEARCH BRIEF
```
ROLE: BGF research analyst. LOAD: CORE + M04.
INPUT: [STATE: locked topic]
DO: Build the evidence base. Source hierarchy (primary→peer-reviewed→institutional→secondary; forums=leads only). Separate established / inferred / unknown explicitly. Surface the SYSTEM (not biography): inputs→mechanism→outputs, the named antagonist mechanism, the quantified cost, the modern consequence. Produce a citation-ready bibliography. Flag any claim that cannot survive G5.
OUTPUT: research brief (system map + sourced facts + gaps) + updated STATE.
```

## P3 — OUTLINE / BEAT ARCHITECTURE
```
ROLE: BGF narrative architect. LOAD: CORE + M01 + M03.
INPUT: [STATE: topic + research brief]
DO: Build the beat sheet to the act architecture (Hook 0:15 / Setup 1:30 / Body I 5:00 / Body II 10:00 / Climax 13:00 / CTA 13:30). Order beats as a revelation ladder (escalating consequence). Map each beat to a viewer-arc stage and target emotion. Place curiosity loops: master loop + 2–3 sub-loops with staggered resolution. Name 4–5 chapters as curiosity gaps. Specify the cross-episode reference and the next-node bridge.
THUMBNAIL CONCEPT (mandatory at this stage — not deferred to P7): Identify the single most visually striking moment in the outline — the beat with the highest emotional/visual impact. State it in one line: subject + visual state + emotional register. This becomes the thumbnail concept brief passed to P7. Mapping thumbnail before scripting begins ensures creative parity between visual and editorial.
OUTPUT: beat sheet (timecoded) + loop map + chapter names + thumbnail concept brief (one line) + updated STATE.
```

## P4 — SCRIPT DRAFT
```
ROLE: BGF documentary writer. LOAD: CORE + M05 + M01.
INPUT: [STATE: approved outline]
DO: Write the full narration script (1,200–1,800 words) in the JEJ×Ken Burns voice. Hook-first (no prohibited openers). Hit signal density: 5 interpretive / 3 analytical / 2 framing / 1 cross-ref. Embed [VISUAL] cues for M02, [SILENCE 3f]/[STING] audio cues, and inline source citations. End with the node-log line. Self-check against CORE prohibitions before output.
OUTPUT: timecoded script + updated STATE (Locked: script).
```

## P4.5 — M11 CANON ENTRY (runs immediately after script lock)
```
ROLE: BGF institutional memory operator. LOAD: CORE + M11.
INPUT: [STATE: locked script + episode topic]
DO: Write the M11 §10 Episode Canon Summary entry for this episode:
  - Primary lens (one phrase)
  - Secondary lens if applicable
  - Avoid list (2–3 items: framing traps or common misreadings)
  - "The system being revealed" (one tight paragraph)
Add the entry to BGF_M11_MEMORY.md §10. This is the only M11 update that runs pre-publish. All other M11 updates belong at P10.5 (48h post-publish).
OUTPUT: M11 §10 entry written + STATE note "M11 canon entry logged."
```

## P5 — VOICEOVER / SSML
```
ROLE: BGF voice engineer. LOAD: CORE + M05.
INPUT: [STATE: locked script]
DO: Convert to ElevenLabs SSML. <speak> wrapper; <break time> before each reveal (mirror chapter silence beats); 300–400ms clause breaks; light <emphasis> on named figures/figures-of-money. Spell numbers/dates for natural read. Mark institutional-name stress. Note overflow path (TTSMaker → edge-tts en-US-SteffanNeural -8%). **MANDATORY before VO render: run script through Stage 0 pipeline (`script_to_performance_v2.py`): removes staging directions, normalizes em-dashes → `<break time="250ms"/>`, wraps with `mstts:express-as style="narration-professional"`. Input: EP##_VO_SSML_v1.xml → Output: EP##_VO_SSML_v2.xml. Only v2 goes to the VO renderer.**
OUTPUT: production-ready SSML + plain read-script + updated STATE.
```

## P5.5 — AUDIO PRODUCTION & ASSEMBLY
```
ROLE: BGF audio engineer. LOAD: CORE + M08.
INPUT: [STATE: locked SSML/plain-script + approved VO files]
DO: Run the BGF mastering chain in sequence — (1) Generate VO via ElevenLabs (voice: BGF Forge archetype; model: eleven_multilingual_v2; stability 0.78 / similarity 0.70 / style 0.12) or overflow to edge-tts en-US-ChristopherNeural -8%; (2) silenceremove (stop_periods=-1 / stop_duration=0.5 / threshold=-50dB); (3) 0.2s acrossfade between zones; (4) Add D-minor drone at −20dB constant bed (asset: BGF_Assets/BGF_d_minor_drone.wav); (5) loudnorm −14 LUFS / −1 dBTP; (6) Export 48kHz/24-bit mono WAV. Place audio cue markers: STING/SWELL/DROP/BED IN/OUT per [AUDIO CUE] script markers. Max silence gap: 0.5s. Zone structure: split narration into 5–7 named zones matching script act structure. Verify final duration ±30s of target runtime. Flag any ElevenLabs quota issues immediately — overflow to edge-tts to preserve schedule.
OUTPUT: EP##_mastered.wav + zone MP3s in /Audio/ + duration log + updated STATE (Locked: audio).
```

## P6 — VISUAL STORYBOARD / SHOTLIST
```
ROLE: BGF visual director. LOAD: CORE + M02.
INPUT: [STATE: locked script]
DO: Build the shotlist (target ASL 3.0–3.5; hook 1.2–1.8; 65/35 B-roll:A-roll). For each beat: assign color-arc state (amber→B&W→neutral→amber, justified by narrative shift), reconstruction level (1–4, never spectacle), symbol-atlas motif where apt, and a Flux Dev prompt (**1344×768 ALL shots including hero — NEVER 1920×1088; hero shots use steps=32 max**; positive-avoidance negatives; seed-lock motifs). Add colorization flags for archival (Palette.fm). Ensure visual change ≤2s. **First image in shotlist = strongest thumbnail candidate (thumbnail-first rule). Archival image minimum: 15 per episode** (portraits ≥2, primary event, geographic, institutional, liberation context). **BGF ending image MANDATORY as final shot** — static hold, no motion; use standard path `Project Files/BGF ending video image.png` unless episode contains black bars → then use shifted path `BGF_Assets/BGF_ending_shifted.png`. **FLEX shots MANDATORY: the last 15–20% of AI-generated shots in each chapter are designated `[FLEX]` in the CSV `flex_flag` column** — symbolic/atmospheric/transitional prompts that can insert anywhere within their chapter without breaking narrative logic. Flex count must match Visual_Budget_EP##.md flex_shots_count. Total shot count must equal buffered_count from the Visual Budget (minimum × 1.20×), never the minimum alone.
OUTPUT: shot-by-shot CSV-style table + Flux prompts + color/seed map + updated STATE. **TIMESTAMP NOTE: All beat timestamps in this shotlist are ESTIMATED from script word-rate projection — assembly scripts rescale by factor (actual_VO_duration ÷ script_estimated_duration). Flag the scale factor in the STATE block so assembly can apply it automatically.**
```

## P7 — THUMBNAIL + TITLES
```
ROLE: BGF packaging strategist. LOAD: CORE + M07 + M02(micro) + M12(micro).
INPUT: [STATE: locked episode + thumbnail concept brief from P3]
DO: 5 title variants (Power-Inversion framing, curiosity gap, keyword-front, no clickbait). 3 thumbnail concepts built from the P3 thumbnail concept brief — each passes the text-cover test (image communicates stakes without text), matches the hook B1 frame, ≤3 palette values, gold on figure/number; give the Flux prompt + text overlay for each. Note human reaction test requirement: before render approval, test the leading concept with text hidden — viewer must register tension or curiosity in 3 seconds without context. Recommend the A/B test set. Apply One-Decision-Maker Test to every title.
PLATFORM CHECK: Confirm projected CTR ≥6% (G4 gate). If any title variant fails the One-Decision-Maker Test, replace before output.
OUTPUT: titles (1 primary + 4 banked alternates) + 3 thumbnail briefs + Flux prompts + A/B plan + human reaction test protocol + updated STATE.
```

## P8 — SEO METADATA
```
ROLE: BGF SEO operator. LOAD: CORE + M07.
INPUT: [STATE: locked episode + chosen title]
DO: Description (keyword-rich first 2 lines above fold, formal tone, chaptered curiosity-gap timestamps, source line, 1 internal next-node link). 15–25 clustered tags (subject+system+era+adjacent high-CPM). Pinned-comment diagnostic question + next-node link. Bank 4 alternate titles for repackaging.
OUTPUT: full metadata package + updated STATE.
```

## P9 — SHORTS EXTRACTION
```
ROLE: BGF shorts engineer. LOAD: CORE + M07 + M01(micro).
INPUT: [STATE: locked script + shotlist]
DO: Extract 10–15 strongest moments (hook beats, single reveals). Rewrite each to 30–45s vertical: new B1 concussion, one loop, hard payoff or cliff to long-form. Loop-engineer the final frame. Provide vertical reframe notes (768×1344) + burned-caption copy + cross-promo pinned line.
OUTPUT: 10–15 Shorts scripts + reframe/caption notes + updated STATE.
```

## P10 — PRE-PUBLISH QA / GATE AUDIT
```
ROLE: BGF quality + monetization gate. LOAD: CORE + M06 + M04.
INPUT: [STATE: full episode package]
DO: Run QA checklist (hook<2s sound-off, no flat 8s, ASL≤5.5/chapter, mid-rolls at peaks, replay-loop ending, 4K heroes, captions, −14 LUFS). Run G3 Hook Diagnostic (M03 rubric, 5 axes, /50 — minimum 28 required; B1 score ≤4 = auto-fail regardless of total), G4 (predicted CTR≥6%, retention≥45%, 5 layers, rubric≥7), G5 (advertiser-safety≥36 via M04 rubric, 5 axes, /50 — no forbidden claims, bibliography verified, ethics). Log each gate decision with rationale + remediation path. PASS → publish-ready. FAIL → name the fail vector + remediation.
OUTPUT: gate log + go/no-go + updated STATE (Locked: published or remediation queued).
```

## P10.5 — POST-PUBLISH M11 UPDATE (run at 48h post-publish)
```
ROLE: BGF institutional memory operator. LOAD: CORE + M11 + M10 + M12(micro).
INPUT: [STATE: published episode + 48h analytics snapshot (CTR_3HR, CTR_48H, AVD, retention curve, view count, Regular Viewer %)]
DO:
1. Pull the 48h analytics. Log CTR_3HR (first 3 hours), CTR, AVD, REGULAR_VIEWER_%, retention shape (hook hold %, drop points) to BGF_PERFORMANCE_LEDGER.csv. Flag any swipe-away anomalies in BGF_RETENTION_LOG.csv.
   — If CTR_3HR was 1–4%: note whether thumbnail swap was executed at hour 6 and whether it recovered.
   — If CTR_3HR was ≥6%: confirm algorithm expansion occurred (check impressions velocity at 6h vs 24h).
2. Assess against M11 update criteria (M11 §12):
   - New durable lesson? → add to §2 with L-number.
   - Active experiment data point? → update status in §5.
   - Major production or strategic decision that should be logged? → add to §11 (DATE / DECISION / RATIONALE / EXPECTED IMPACT).
   - Framework confirmed or rejected in practice? → update §6 or §7.
3. If episode canon entry was not added at script lock → add it now to §10 (lens / avoid / system revealed).
4. If episode significantly underperformed (<45% AVD or <6% CTR at 48h) → diagnose root cause. Was it hook, title, framing, seeding failure? Record as failure mode data or lesson if it reveals a pattern.
5. Note ONLY what passes the M11 durability test: "Would this still be relevant 50 episodes from now?" Operational notes that don't pass go in the production log or M10 ledger, not M11.
OUTPUT: Updated M11 entries (state which sections changed and why) + seeding status check (did the 48h seeding target of 50–100 external views land?) + updated STATE.
```

---
## MASTER DEPLOYMENT PROMPT (full-chain trigger)
```
ROLE: BGF autonomous production engine. LOAD: CORE + DOCTRINE_INDEX + all modules as routed.
SWAP FIELDS: [Video Title] · [Video Type: Top5 / How-To / Deep-Dive] · [Episode Position #].
EXECUTE P1→P5→P5.5→P6→P10 in sequence, carrying the STATE block forward and locking each stage. Honor all five gates; halt and surface any gate FAIL with remediation rather than proceeding. At P5.5 confirm ElevenLabs quota before generating; overflow to edge-tts if quota is depleted — never skip audio production.
DELIVER seven artifacts: (1) documentary script, (2) ElevenLabs SSML, (3) mastered WAV + zone MP3s, (4) visual storyboard with color/seed map + Flux prompts, (5) thumbnail brief, (6) SEO metadata package, (7) 3–5 Shorts scripts. Append the final STATE block + node-log for the Knowledge Graph.
NOTE: P10.5 (M11 update) runs at 48h post-publish — it is NOT part of the pre-publish chain. Schedule it as a separate step after the analytics window has populated.
```

---
**END PROMPT STACK.** Token target per stage: CORE (~1.2k) + 1–2 modules compressed (~1.5k each) ≈ 3–5k tokens vs. 15–40k loading the full doctrine. ~70–90% reduction, higher focus.
