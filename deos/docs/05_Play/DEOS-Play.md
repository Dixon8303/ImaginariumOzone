# Specification: Player Loop, Catalyst Interface, Chronicle & Retention Systems (DEOS-PLAY)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | DEOS-PLAY |
| **Semantic Version** | v0.1.0 |
| **Status** | Draft |
| **Dependencies** | DEOS, DEOS-F01, DEOS-F02, DEOS-F03, DEOS-F04, DEOS-F05, DEOS-F06, DEOS-CORE, DEOS-ECS, DEOS-RT, DEOS-PROTO |
| **Supersedes** | None (new module; absorbs Pillar 4 and ROADMAP Phase 6 intent) |
| **Reserved Prefixes** | `PLAY`, `CAT`, `SES` (from DEOS section 3.2) |

---

## 1. Purpose

DEOS-Play is the module that makes *Emergence: The Digital Rise* a game people play compulsively, for months, without being deceived. It owns the player's role and loops (`PLAY`), the Catalyst interface and Budget (`CAT`), and sessions, catch-up, sharing, and challenges (`SES`). Every mechanism here is derived from one sentence, **shape the probabilities, not the people** (research/INTERFACE_INSPIRATION.md, commitment C1), and every reward is information or consequence, never a payout. Pacing is tuned only through the constants DEOS-CORE and DEOS-PROTO expose (GI-7), and retention is earned by novelty and agency (GI-8).

Player-facing consequence: this document is the player's experience end to end, from the first 90 seconds to the thirtieth day, with a number on every promise.

## 2. Scope

**Included.** The fantasy and the five-verb loop; the 30-second, session, daily, and meta loops with triggers, actions, rewards, and return hooks; the first five minutes and seed curation; cadence and surprise targets; the `CatalystAction` kind table, payload semantics, cost formula, validation ranges, expansion table for composites, Host-side settings that are not logged, and the Catalyst Budget; Chronicle presentation, story rendering, the why drill-down, Epoch summaries, rewind and branch; the Observation View layers and Affective Signals mapping; World Phases presentation; sessions, offline catch-up, the seed code, world sharing, Challenges, rivalry; retention metrics and telemetry; engagement ethics.

**Excluded.** Rendering technology, audio synthesis, input devices, platform stores (Host implementation); every Kernel rule this module tunes (DEOS-CORE, DEOS-PROTO); how the Kernel validates and applies Catalyst Actions (DEOS-RT REQ-LOOP-003, which consumes the tables here).

## 3. Dependencies

| Document | Used for |
| :--- | :--- |
| DEOS sections 1, 4, 5, 6 | identity; vocabulary; `TICKS_PER_DAY`, `TICKS_PER_EPOCH`, `SPEED_LEVELS`, `OFFLINE_RATE`, `MAX_OFFLINE_TICKS`, `SNAPSHOT_INTERVAL`; `CatalystAction`, `CatalystLedger`, `NotableEvent`; GI-2, GI-5, GI-6, GI-7, GI-8 |
| DEOS-F01 section 3.5, DEOS-F03 Pillars 4 and 5, DEOS-F05 sections 1.2 and 1.3 | World Phases; commitments; the metrics this module must meet |
| DEOS-CORE | `FX_CELL_ENERGY_CAP`, `FX_ELEV_MAX`, `mutation_bias` range, `FX_WORLD_ENERGY_MAX`; `LAT` (for the Climate family's display) |
| DEOS-ECS | `IngressWrite` fields and ops (REQ-MUT-011); the read view's component layouts for the Observation View; `Decision` and `DecisionTrace` (REQ-CMP-006) |
| DEOS-RT | the ABI (REQ-ARCH-003, 005); Stage 1 validation (REQ-LOOP-003); Input Log records and Checkpoints (REQ-LOOP-004); egress (REQ-LOOP-008); Snapshots, replay, verification, Acceleration (REQ-SNAP-002 … 006) |
| DEOS-PROTO | the event taxonomy and story templates (REQ-EVT-002); World Phase thresholds (REQ-EVT-004); pacing constants (section 8.5); `WorldMood` (REQ-SOC-009) |
| `research/INTERFACE_INSPIRATION.md` | commitments C1 through C9 |

## 4. Definitions

| Term | Definition |
| :--- | :--- |
| **Session** | The span between the Host's foreground and background transitions (or launch and quit) for one world. |
| **Check-in** | A Session under 5 real minutes. **Deep session:** a Session of 20 real minutes or more. |
| **Absence** | Real time between the end of one Session and the start of the next for the same world. |
| **Catch-up** | The Acceleration run the Host performs at Session start to cover an Absence (REQ-SES-001). |
| **Pinned subject** | An EntityID or Cell the player marked in the Host so the Chronicle ranks its rows first. Host state, never logged. |
| **Seed code** | The 16-character encoding of (DEOS version, scale, Master Seed) of REQ-SES-003. |
| **Challenge** | A tuple (seed code, objective, tick budget, allowed kinds, starting Budget) published by the Host service (REQ-SES-005). |
| **Ghost mode** | Rewind that restores a Snapshot and steps read-only: the original Input Log is replayed, no new actions are accepted. **Branch mode:** rewind that forks a Seed Lineage child at a Snapshot. |
| **Legacy trait** | The one Meme-Vector dimension a Seed Lineage child carries forward (REQ-PLAY-005). |
| **Family** | One of Climate, Resource, Mutation, Cosmic: the four groups of the Catalyst Palette (commitment C3). |

## 5. Assumptions

1. The Host renders at a frame rate independent of the tick rate; at speed 1× it calls `deos_tick` 60 times per real second (`TICK_RATE_HZ`), at 4× 240 times, and so on, dropping frames rather than ticks; when the Host cannot sustain a speed level it displays the achieved multiplier honestly (GI-8).
2. A world has one player in v0.1.0; the `CatalystLedger` is per world. Multiplayer is future expansion.
3. The Host has persistent storage for the Input Log, a Snapshot ring, and Host settings; and network access for the share and Challenge services, which are optional: every loop in this document except REQ-SES-005 works offline.
4. Every wall-clock figure is a Host measurement; nothing in this module enters the Kernel except the constants compiled into `cat_kind_table`, `cat_cost`, and `cat_expand` (DEOS-RT section 9).

---

## 6. Requirements

### 6.1 Player role and loops (`PLAY`)

### REQ-PLAY-001: The fantasy

The player is the Catalyst: a presence above a world that is not theirs to command. They can warm a coast, drown a valley, raise the mutation rate of a forest, whisper an idea into a village, or drop a meteor, and then they must wait and read what a population of autonomous agents makes of it. The satisfaction is authorship of conditions and the reading of consequences, never control of outcomes. Every mechanic in this document is derived from that sentence: the Palette offers conditions (REQ-CAT-001), the Budget paces them (REQ-CAT-004), the Chronicle reads consequences (REQ-PLAY-006), and the meta loop lets the player carry one idea from a world they have finished into a world they are starting (REQ-PLAY-005). Formally (commitment C1): no `CatalystAction` kind writes `Decision`, `Needs`, `Memory`, or `TrustEdges`; the legal targets are the Cell fields and population-level Meme deltas of DEOS-ECS REQ-MUT-011, and nothing else.

Why it retains: the player is never finished because they never finish anything; they start things, and the world answers in its own time.

### REQ-PLAY-002: The core loop (30 seconds)

The five verbs, in this order, are the loop (commitment C2), and the Host's primary regions map one-to-one:

| Verb | Region | What happens | Target timing at 1× |
| :--- | :--- | :--- | :--- |
| **Observe** | Observation View | the player reads the Particles, Living Diagram, or Network Map layer, or opens an inspect panel | 5–10 s |
| **Influence** | Catalyst Palette | the player sets a family, a region, and a magnitude with sliders, sees the cost, and commits; `deos_push_action` stamps it for `current_tick + 1` | 5–10 s |
| **Wait** | Time Control | the player chooses a `SPEED_LEVELS` multiplier; the Kernel ticks; the Affective Signals play | 10–20 s |
| **Adapt** | Observation View | the world visibly responds: fields change in the same tick, agents move within seconds, a Notable Event lands | within 30 s (REQ-PLAY-003) |
| **History** | Chronicle | the row appears; the player opens its cause | 5 s |

Target: one full loop in 30 to 60 real seconds at speed 1×; the Host measures it as telemetry `loop_seconds` (REQ-PLAY-008).

Why it retains: each loop ends with a row that raises a question the next loop answers.

### REQ-PLAY-003: Agency and consequence

Every accepted Catalyst Action produces a consequence the player can perceive within the same Session: the Cell fields it writes change in the Observation View in the tick it lands (REQ-CAT-003 magnitudes are large enough to be visible at the Particles layer's colour scale), and at least one Notable Event attributable to it (`CATALYST_APPLIED` kind 5 immediately; a domain event whose `cell` lies within the affected square within `TICKS_PER_DAY` ticks in at least 80 of 100 seed-sample worlds for the reference actions of section 8.3) follows. The Host measures `consequence_ticks` per action (REQ-PLAY-008). Actions may be undone only by the world, never by a button: there is no revert (GI-2, the log is the save).

Why it retains: the player learns that they matter, and that they cannot take it back.

### REQ-PLAY-004: Session and daily loops

| Loop | Trigger | Action | Reward | Return hook |
| :--- | :--- | :--- | :--- | :--- |
| **Check-in** (≤ 5 min) | app opened after an Absence | read the "while you were away" summary (REQ-SES-002); spend the regenerated Budget on one or two actions; set a speed; leave | the summary's top rows and one visible change | the Budget is full again after `capacity / regen_per_tick` ticks = 3,840 ticks ≈ 1.07 simulated days (REQ-CAT-004), which the Host shows as a countdown in simulated time |
| **Deep session** (≥ 20 min) | the player stays past the check-in | steer a region or an Institution through several loops at 4× to 16×; inspect agents; pin subjects | a World Phase, a founding, a war, a discovery | an unresolved arc: a pinned Institution under threat, a lineage the player is watching |
| **Daily** | the first Session of a player-local day | catch-up (REQ-SES-001) streams an Epoch's worth of history if the Absence allows; the Epoch summary (REQ-PLAY-007) if a boundary passed | the summary, the phase ladder position, the day's firsts | the next Epoch boundary, shown as simulated time remaining |

Why it retains: the Budget refills on the world's clock, the world moves on the world's clock, and the player's day has a reason to include it at each scale of attention.

### REQ-PLAY-005: The meta loop, Seed Lineage, and the legacy trait

1. **Seed Lineage.** A world's lineage is the chain of (parent seed code, branch tick) pairs from which it was created: a world started from a seed code has no parent; a world started by branch mode (REQ-PLAY-007) records its parent's seed code and the branch tick; a world started by "carry forward" (below) records its parent and `tick = 0`.
2. **Carry forward.** At any Epoch boundary the player may start a child world from a new seed code with one **legacy trait**: they choose one Meme-Vector dimension `d` in `[0, 31]` and the child's world generation applies, at tick 0, an `IngressWrite` `{ field 6 MEME_DELTA, op ADD, dim d, value = +0.5, x = GRID_W/2, y = GRID_H/2, radius = GRID_W }` (every Agent), recorded as the first Input Log entry with `kind = 13 LEGACY` (REQ-CAT-001) and `cost = 0`. Because it is an Input Log entry, the child is still `F(MasterSeed, InputLog)` and shareable (GI-1, GI-2); a world with a legacy trait is displayed with its parent's name.
3. **Prestige.** The Host counts lineage depth and shows it; nothing in the Kernel changes with depth.

Why it retains: finishing a world is starting the next one with something from it, and the chain is visible.

### REQ-PLAY-006: Chronicle presentation and the why drill-down

1. Every `NotableEvent` polled from the Kernel is rendered as one row: simulated time (`day = tick / TICKS_PER_DAY`, `hour = (tick mod TICKS_PER_DAY) × 24 / TICKS_PER_DAY`), the DEOS-PROTO story template with names substituted, and a chevron.
2. **Names.** An entity's display name is a deterministic function of its EntityID and `born_tick`: `name = SYLLABLE[(index × 7 + born_tick) mod 128] ‖ SYLLABLE[(index × 13 + generation) mod 128] ‖ (generation ≥ 1 ? " " ‖ ROMAN[generation mod 40] : "")` over a fixed 128-syllable table shipped with the Host; Institutions use the founder's second syllable plus one of 32 house suffixes indexed by `founded_tick mod 32`. The same entity has the same name on every device (GI-1).
3. **The drill-down.** The chevron opens the cause chain: the row's `cause` is a slot index; the Host reads that slot's `Decision` from the read view when the row is from the current tick, and otherwise reconstructs it by ghost-mode rewind (REQ-PLAY-007 rule 3) to the row's tick, then shows the action, the three contributors with signed weights, the Perception summary, and the newest Memory entries (DEOS-ECS REQ-CMP-006, 004, 005). A row with `cause = 0` opens the subject's inspect panel at that tick instead.
4. **Ranking.** Rows are shown newest first; rows whose subject, object, or cell matches a pinned subject are pinned to the top of their day; first-order kinds are visually distinct from second-order kinds; reserved kinds 1, 2, 7, 8 are shown in a "Kernel" filter that is off by default and one tap away (never hidden, GI-8).
5. **Filters** by family of cause, by Institution, by Cell region, and by World Phase; every filter is Host state.

Why it retains: every row is a question with an answer one tap away, and the answer is always true.

### REQ-PLAY-007: Epoch summary, rewind, and branch

1. **Epoch summary.** At each `EPOCH_BOUNDARY` (kind 4) the Host composes a summary from the Epoch's Chronicle: the top `K = 12` first-order rows by `magnitude` with at most 3 per kind (ties: earlier tick), the World Phase reached, population and Institution counts at the boundary, `e_sun` and `e_rad` totals as "the world's breath", Budget spent, and the player's own `CATALYST_APPLIED` count. The selection is deterministic over the Chronicle so two devices show the same summary.
2. **Snapshot ring.** The Host keeps the Snapshots of the last 4 `SNAPSHOT_INTERVAL` boundaries and of every Epoch boundary (DEOS-RT REQ-SNAP-002); older interval Snapshots are deleted, Epoch Snapshots are kept for the life of the world.
3. **Ghost mode.** Rewind to tick `r` restores the nearest earlier retained Snapshot in a private Kernel, imports the world's Input Log, steps to `r` (at most `SNAPSHOT_INTERVAL` ticks, under 2 s at MVS scale), and lets the player scrub forward in read-only mode with the Observation View and inspect panels live; `deos_push_action` is disabled. The live world is untouched.
4. **Branch mode.** From ghost mode at tick `r`, "branch here" creates a Seed Lineage child: a new world whose Input Log is the parent's entries with `tick ≤ r` followed by a `SNAPSHOT_MARK`, whose Snapshot is the ghost Kernel's Snapshot at `r`, and whose lineage records (parent seed code, `r`). The child's seed code is the parent's (same Master Seed); the Host displays the branch tick alongside it.

Why it retains: "how did this war start?" has an exact answer, and "what if I had done otherwise?" is a new world rather than a wish.

### REQ-PLAY-008: Cadence, surprise, and the first five minutes

1. **Cadence band.** First-order Notable Events (DEOS-PROTO section 8.4) per simulated day, measured over the seed sample at MVS scale with an empty Input Log, must fall within the band per World Phase: Phase 1–2: 4 to 40 per day; Phase 3: 8 to 80; Phase 4: 12 to 120. A simulated day is 60 real seconds at speed 1×, so 4 per day is one first-order row every 15 s and 120 per day is two per second, the noise ceiling. DEOS-F05 P5 tests this band.
2. **Surprise rate.** Over an Epoch of attended play with the reference action script of section 8.3, at least 50 % of first-order rows must have a `cell` outside every affected square of the player's actions in the preceding day, measured by the Host as `surprise_rate` (REQ-PLAY-009). Below 50 % the world is a puppet; above 95 % the player is a spectator. Both are tuning failures for the DEOS-PROTO pacing constants, never occasions for scripts (GI-7).
3. **First five minutes.** From world creation at speed 1×: a first-order row within 90 s (DEOS-F05 P1, `FIRST_OF_KIND` for the first `FED` fires in the first day in every seed); the Palette tutorial is one accepted action of each family in the first 3 minutes, each with its `CATALYST_APPLIED` row and a visible field change; World Phase 2 (Life) is reached in ≥ 95 of 100 seeds within 5 simulated days (ROADMAP Phase 3 target); the first Institution by day 10 in ≥ 80 of 100 seeds (P2).
4. **Seed curation.** When the player asks for a new world without a seed code, the Host draws a candidate Master Seed, runs a private headless probe of `PROBE_TICKS` = 5,400 ticks (90 s at 1×; under 3 s at `MIN_ACCELERATION`) with an empty Input Log, and accepts the seed when the probe shows at least one first-order row and `population ≥ 0.9 × tick-0 population` at the end; otherwise it tries the next candidate (at most 8). The accepted seed is the world's seed and is shareable; the world itself is untouched by the probe (the probe Kernel is discarded). Curation is legitimate because it selects a world, never edits one (GI-7).

Why it retains: the first minute promises something will happen, the first three minutes prove the player can make things happen, and the first ten days deliver a society to watch.

### REQ-PLAY-009: Observation View and Affective Signals

1. **Layers** (commitment C7), each bound to the DEOS-RT read view and nothing else (GI-6): **Particles** renders every live Physical entity at `Position2D` coloured by archetype and `EnergyState.ef`, over the Cell fields (`energy` as ground brightness, `temperature` as hue, `moisture` as saturation, `material_id` as texture, `mutation_bias` as a shimmer when ≠ 1.0); **Living Diagram** renders Institutions as nodes at their `Position2D` sized by `member_count`, members linked by `Affiliation`, and `TrustEdges` as lines weighted by `weight`; **Network Map** renders agents clustered by Meme-Vector similarity (DEOS-ECS REQ-CMP-007 rule 3) and coloured by the dominant dimension group. Each layer is one tap from the others; the inspect panel opens from any of them and shows every component field of the selected entity in the words of the specifications.
2. **Affective Signals** (commitment C8): the Host maps the per-tick `WorldMood` to sound: `cooperation` to consonance (chord density and major intervals), `conflict` to dissonance (minor seconds, tempo), `growth` to register and brightness, `entropy` to noise floor; `population` to voice count; a World Phase reached adds an instrument permanently. The mapping is Host art; the inputs are Kernel state, so two devices hear the same world.

Why it retains: the player hears a war before reading it and sees a belief spread before understanding it, which is what makes them open the Chronicle.

### REQ-PLAY-010: World Phases presentation

The Host displays the four-rung ladder (DEOS-F01 section 3.5) with the world's position, the tick each rung was reached (from the `WORLD_PHASE_REACHED` rows), and, for the next rung, the DEOS-PROTO condition in plain words ("an Institution has not yet been founded"). A rung reached during a Session is celebrated once, with its row pinned for the Session; the Epoch summary repeats it. Nothing about the ladder changes any Kernel value (GI-7).

### 6.2 Catalyst interface (`CAT`)

### REQ-CAT-001: Catalyst Action kinds

`CatalystAction.kind` values below `0x8000`. All region kinds use `target_kind = 1` and `target` = the centre Cell index; `payload[0]` = magnitude `m` (Q32.32, signed where stated), `payload[1]` = radius `r` as a Q32.32 integer in `[0, 8]` (Chebyshev, so the square has `(2r + 1)²` Cells, at most 289), `payload[2]` = parameter `q`, `payload[3]` = 0. Ranges are validated by DEOS-RT REQ-LOOP-003 rule 3.

| Kind | Name | Family | `m` range | `q` | Effect (primitive `IngressWrite`, DEOS-ECS REQ-MUT-011) |
| ---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `WARM` | Climate | (0, 32.0] | — | `CELL_TEMPERATURE ADD +m`, radius `r` |
| 2 | `COOL` | Climate | (0, 32.0] | — | `CELL_TEMPERATURE ADD −m` (clamped at 0 per Cell), radius `r` |
| 3 | `RAIN` | Climate | (0, 1.0] | — | `CELL_MOISTURE ADD +m`, radius `r` (a Catalyst moisture credit, `m_cat`) |
| 4 | `DROUGHT` | Climate | (0, 1.0] | — | `CELL_MOISTURE ADD −m`, radius `r` |
| 5 | `ENRICH` | Resource | (0, 256.0] | — | `CELL_ENERGY ADD +m`, radius `r` (a Catalyst energy credit, `e_cat`) |
| 6 | `BLIGHT` | Resource | (0, 256.0] | — | `CELL_ENERGY ADD −m`, radius `r` (a Catalyst debit; the energy leaves the world through `e_cat`) |
| 7 | `RAISE` | Resource | (0, 512.0] | — | `CELL_ELEVATION ADD +m`, radius `r` |
| 8 | `LOWER` | Resource | (0, 512.0] | — | `CELL_ELEVATION ADD −m`, radius `r` |
| 9 | `TRANSMUTE` | Resource | 1 | material id 0–2 (WATER, SOIL, ROCK) | `CELL_MATERIAL SET q`, radius `r` |
| 10 | `VOLATILITY` | Mutation | [1.0, 4.0] | — | `CELL_MUTATION_BIAS MUL m`, radius `r` (clamped to 4.0) |
| 11 | `STABILITY` | Mutation | [0.25, 1.0] | — | `CELL_MUTATION_BIAS MUL m`, radius `r` (clamped to 0.25) |
| 12 | `WHISPER` | Mutation | [−0.5, 0.5] | dimension 0–31 | `MEME_DELTA ADD m` on dimension `q`, radius `r` (scaled by each Agent's receptivity, DEOS-ECS REQ-MUT-011 rule 2) |
| 13 | `LEGACY` | Mutation | +0.5 (fixed) | dimension 0–31 | as `WHISPER` with radius `GRID_W`; legal only at tick 0 as the first entry (REQ-PLAY-005); cost 0 |
| 16 | `METEOR` | Cosmic | (0, 1.0] | — | composite (REQ-CAT-002) |
| 17 | `SOLAR_FLARE` | Cosmic | (0, 1.0] | — | composite |
| 18 | `MONSOON` | Cosmic | (0, 1.0] | — | composite |
| 19 | `VOLCANO` | Cosmic | (0, 1.0] | — | composite |
| 20 | `EPIPHANY` | Cosmic | (0, 1.0] | — | composite |
| 21 | `ICE_WIND` | Cosmic | (0, 1.0] | — | composite |
| 14, 15, 22–0x7FFF | reserved | — | — | — | rejected |

Player-facing consequence: eleven primitive verbs and six composite events are the whole vocabulary of influence, all of them conditions and none of them orders (commitment C1, C3).

### REQ-CAT-002: Composite expansion

A composite kind expands in DEOS-RT Stage 1, in the table order, into primitive writes that share the entry's `seq`; `m` is the entry's magnitude in `(0, 1]` and `r` its radius. No draw is used in v0.1.0; the SystemID 1 Stream is reserved for future stochastic composites.

| Kind | Writes, in order |
| :--- | :--- |
| `METEOR` | `CELL_ENERGY ADD +256·m` radius `r`; `CELL_TEMPERATURE ADD +64·m` radius `r`; `CELL_ELEVATION ADD −256·m` radius `max(0, r/2)`; `CELL_MATERIAL SET ROCK` radius 0 |
| `SOLAR_FLARE` | `CELL_TEMPERATURE ADD +16·m` radius `min(8, r + 4)`; `CELL_MOISTURE ADD −0.25·m` radius `min(8, r + 4)` |
| `MONSOON` | `CELL_MOISTURE ADD +0.75·m` radius `min(8, r + 4)`; `CELL_TEMPERATURE ADD −8·m` radius `min(8, r + 4)` |
| `VOLCANO` | `CELL_ELEVATION ADD +512·m` radius `max(0, r/2)`; `CELL_TEMPERATURE ADD +96·m` radius `r`; `CELL_MATERIAL SET ROCK` radius `max(0, r/2)`; `CELL_ENERGY ADD +64·m` radius `min(8, r + 2)` |
| `EPIPHANY` | `MEME_DELTA ADD +0.5·m` dimension 23 (progress) radius `r`; `MEME_DELTA ADD +0.5·m` dimension 18 (agency) radius `r`; `CELL_MUTATION_BIAS MUL (1 + m)` radius `r` |
| `ICE_WIND` | `CELL_TEMPERATURE ADD −24·m` radius `min(8, r + 4)`; `CELL_MOISTURE ADD +0.25·m` radius `r` |

Products are Q32.32 (`fx_mul(256.0, m)` and so on) computed by the Kernel's `cat_expand`; the Input Log stores only the composite record.

Player-facing consequence: a meteor is one tap and one row, and the crater, the heat, the scorched rock, and the buried energy are its four visible consequences (commitment C3).

### REQ-CAT-003: Cost

```
area  = (2r + 1)²                                          -- integer, 1 … 289
af    = fx_div(fx_from_int(area), fx_from_int(81))         -- Q32.32; 1.0 at r = 4
unit  = fx_div(fx_abs(m), MAG_UNIT[kind])                  -- magnitude in units of the kind's reference
cost  = fx_mul(BASE[kind], fx_mul(fx_max(unit, FX_ONE >> 2), af))   -- at least a quarter unit is charged
```

| Kind | `BASE` | `MAG_UNIT` | Cost at `m = MAG_UNIT`, `r = 4` |
| :--- | :--- | :--- | :--- |
| `WARM`, `COOL` | 6.0 | 8.0 | 6 |
| `RAIN`, `DROUGHT` | 6.0 | 0.5 | 6 |
| `ENRICH`, `BLIGHT` | 10.0 | 64.0 | 10 |
| `RAISE`, `LOWER` | 8.0 | 128.0 | 8 |
| `TRANSMUTE` | 12.0 | 1.0 | 12 |
| `VOLATILITY`, `STABILITY` | 5.0 | 2.0 (for `STABILITY`: `1/m` is the unit) | 5 |
| `WHISPER` | 8.0 | 0.25 | 8 |
| `LEGACY` | 0 | — | 0 |
| `METEOR`, `VOLCANO` | 40.0 | 1.0 | 40 |
| `SOLAR_FLARE`, `MONSOON`, `ICE_WIND` | 24.0 | 1.0 | 24 |
| `EPIPHANY` | 30.0 | 1.0 | 30 |

The Host displays `cost` before commit and the Kernel recomputes it (DEOS-RT REQ-LOOP-003 rule 3.4). Costs are Play constants (section 8.2); a change is scored under DEOS-F06.

Player-facing consequence: the price of an action is on the slider before the player commits, it never changes after, and bigger regions cost more in a way the player can predict (GI-8).

### REQ-CAT-004: The Catalyst Budget

The `CatalystLedger` (DEOS section 5.4) is Kernel state with the constants `capacity = CAT_CAPACITY = 120.0`, `regen_per_tick = CAT_REGEN = 2^-5` (0.03125 per tick: 112.5 per simulated day, a full refill from empty in 3,840 ticks, 64 real seconds at 1×), initial `balance = CAT_CAPACITY`. Regeneration is applied by DEOS-RT REQ-LOOP-003 rule 1 every tick, including in Acceleration, so the balance a returning player finds is the same on every device. Rules:
1. The balance, the capacity, the regeneration rate, and the time to full are always displayed; there is no hidden timer (GI-8).
2. Nothing but simulated ticks regenerates the Budget; nothing purchasable adds to it (REQ-PLAY-011).
3. The `reserved` field's bits 0–3 and 8–15 are DEOS-PROTO's World Phase and first-of-kind masks (DEOS-PROTO section 8.2); the remaining bits are zero.
4. Because the Budget is hashed and replayed, a Challenge verifier can prove a submitted log never overspent (REQ-SES-005).

Player-facing consequence: the Budget is a metronome for the loop, not a wall: a check-in always has something to spend, a deep session must choose (GI-8).

### REQ-CAT-005: Host-side settings that are not logged

Speed level, pinned subjects, layer selection, filters, and audio settings are Host state and never Input Log entries, because they do not change `F(MasterSeed, InputLog)` (GI-4, DEOS-CORE REQ-TICK-001). The Host shows the achieved speed multiplier when it falls short of the selected one.

### 6.3 Sessions, catch-up, sharing, challenges (`SES`)

### REQ-SES-001: Offline catch-up

At Session start after an Absence of `A` real seconds:

```
ticks_due = min( floor(A × TICK_RATE_HZ × OFFLINE_RATE), MAX_OFFLINE_TICKS )      -- OFFLINE_RATE = 1/16: 8 h → 108,000 ticks, one Epoch
```

The Host sets `EGRESS_REDUCED`, steps `ticks_due` in batches of `CATCHUP_BATCH` = 600 ticks (10 simulated minutes) with `deos_step`, polling the Chronicle after each batch and rendering the rows as they arrive with a progress line "day 12 of 30", then returns to `EGRESS_FULL`. At `MIN_ACCELERATION` an Epoch streams in ≤ 60 s (DEOS-F05 P3) with the first rows within 1 s; the player may begin observing and inspecting during catch-up but `deos_push_action` is held until it completes (an action stamped mid-catch-up would land in a tick the player has not seen). Absences shorter than `TICKS_PER_DAY / (TICK_RATE_HZ × OFFLINE_RATE)` = 16 real minutes produce no catch-up. Hosting-neutral: a server-stepped world (DEOS-RT REQ-SNAP-006) performs the same computation on its own clock and hands the Host the Snapshot and Chronicle instead.

Why it retains: the world lived while the player slept, at a rate the player can read on screen, and it greets them with what happened.

### REQ-SES-002: The "while you were away" summary

After catch-up, the Host shows: simulated time elapsed, the World Phase change if any, population and Institution deltas, the top 6 first-order rows by `magnitude` with the pinned subjects' rows first, any `INGRESS_REJECTED` or `EVENT_OVERFLOW` rows, and the Budget now available. One push notification per completed catch-up and one per Epoch boundary reached during it are permitted (REQ-PLAY-011); none otherwise.

### REQ-SES-003: Seed code

A seed code encodes 80 bits as 16 characters of Crockford base32 (alphabet `0123456789ABCDEFGHJKMNPQRSTVWXYZ`), displayed as four groups of four separated by hyphens and accepted case-insensitively with `O → 0`, `I, L → 1`:

```
bits 79..72  : DEOS minor version (8 bits; 1 for v0.1.x)
bits 71..68  : scale (4 bits; 0 = SCALE_MVS, 1 = SCALE_V1)
bits 67..4   : Master Seed (64 bits, big-endian in the bit string)
bits 3..0    : check = XOR of the nineteen preceding 4-bit nibbles
```

Characters are emitted most-significant 5-bit group first. A code with a wrong check or an unknown version is refused with a message. The Host's world-creation screen accepts a seed code or draws one by curation (REQ-PLAY-008 rule 4).

Player-facing consequence: "try 9F3A-K2M7-…" is sixteen characters that any player can type, and it names the same coastlines, the same founding population, and the same first ten days everywhere (GI-1).

### REQ-SES-004: World sharing and rivalry

1. **Share a world.** Export = seed code + the Input Log (`deos_input_log_export`) + optionally the latest Epoch Snapshot; the receiver imports and either replays from tick 0 (verifying every Checkpoint as it goes) or restores the Snapshot. A shared world opens in ghost mode by default; "branch" makes it the receiver's own Seed Lineage child.
2. **Rivalry.** Two players who start from the same seed code can compare Chronicles day by day: the Host service aligns the two Input Logs and Chronicles by tick and shows where they diverged and what each did; the comparison is Host presentation over two verified logs.

Why it retains: a world is a thing you can hand to a friend, and a seed is a race you can run twice.

### REQ-SES-005: Challenges and leaderboards

1. **Definition.** A Challenge is `{ seed code, objective, tick_budget, allowed_kinds (bitmask over kinds 1–21), start_budget (≤ CAT_CAPACITY), created_at }`, published by the Host service. Objectives are predicates over the read view at a tick, from a fixed list: `PHASE(n)` (World Phase `n` reached), `POPULATION(≥ p)`, `INSTITUTIONS(≥ k)`, `DISCOVERY(d)`, `SURVIVE(no EXTINCTION)`, `PEACE(no CONTEST rows for two days)`, each evaluated by the Kernel state the verifier reaches.
2. **Submission** is the player's Input Log. **Verification** is `deos_verify` (DEOS-RT REQ-SNAP-004) followed by evaluation of the objective at every Checkpoint tick up to `tick_budget`; a log that overspends the Budget, uses a disallowed kind, or fails a Checkpoint is rejected with the tick.
3. **Leaderboard key**, ascending: `(objective not met, tick at which met, Budget spent, log length, submission time)`.
4. **Anti-cheat properties** follow from GI-1 and GI-3 without any additional mechanism: there is no score to forge, only a log to replay; the Budget is Kernel state; the Kernel version is in the seed code.

Why it retains: a leaderboard entry is a story someone else can watch, not a number.

### REQ-SES-006: Time control

`SPEED_LEVELS` = {1, 4, 16, 64} are Host tick-call rates; 64× is best effort and the achieved rate is displayed. Pause is speed 0 (no calls). Acceleration (REQ-SES-001) is separate from speed and is never offered as a manual control: the player cannot jump past events they could have watched, only catch up on time they were absent for. This keeps the Wait verb honest and keeps every attended tick observable.

### 6.4 Retention metrics and ethics (`PLAY`, continued)

### REQ-PLAY-011: Engagement without deception (GI-8)

1. No hidden timers: every regeneration, countdown, or cadence the player experiences is a displayed function of simulated ticks.
2. No purchasable simulation advantage: monetization may sell cosmetics (layer palettes, syllable tables, audio instruments), additional world slots, larger scale profiles, and entry to verified Challenges; nothing sold changes `F`, the Budget, or the Kernel constants.
3. No manufactured scarcity beyond the displayed Budget; no energy, seed, or feature is withheld to be sold back.
4. No monetization prompt inside a Session; offers appear only on the world-list screen.
5. Notifications: at most one push per completed catch-up and one per Epoch boundary; no re-engagement pushes on any other trigger; all opt-in.
6. A product target of DEOS-F05 section 1.3 that is missed is a design signal for this module's constants, never a reason to violate rules 1–5.

Why it retains: trust. A player who learns the game never lies to them keeps playing after the novelty is gone.

### REQ-PLAY-012: Telemetry and targets

Host-side telemetry events (never in the Kernel, never in the Input Log): `session_start`, `session_end`, `loop_seconds`, `action_committed` (kind, cost, radius), `consequence_ticks`, `row_opened` (kind, drill-down depth), `phase_reached`, `catchup` (ticks, seconds), `share`, `challenge_submitted`, `surprise_rate` (per Epoch). Targets (ASSUMED until live data, per DEOS-F05 section 1.3): median `loop_seconds` 30–60; median `consequence_ticks` ≤ 3,600; `row_opened` on ≥ 30 % of first-order rows; D1 ≥ 40 %, D7 ≥ 20 %, D30 ≥ 10 %; share rate ≥ 5 % of active worlds; `surprise_rate` 50–95 %.

---

## 7. Algorithms & Mathematics

### 7.1 Cost reference values

At `r = 4` (`af = 1.0`): `WARM` with `m = 8.0` costs 6.0; `m = 32.0` costs 24.0. `METEOR` with `m = 1.0`, `r = 8`: `af = 289/81 = 3.5679`, cost = 142.7, above `CAT_CAPACITY`: the largest meteor needs the whole Budget and a radius of at most 7 (`af = 2.78`, cost 111.1). `WHISPER` `m = 0.25`, `r = 8`: 28.5.

### 7.2 Seed code example

Master Seed `0x0123456789ABCDEF`, scale 0, version 1: the nineteen nibbles above the check, from bit 4 upward, are the seed's `F,E,D,C,B,A,9,8,7,6,5,4,3,2,1,0`, the scale `0`, and the version's `1,0`, whose XOR is `0x1`; the 80 bits grouped into sixteen 5-bit values and mapped through the alphabet give **`0401-4D2P-F2DB-SQQH`** (computed from the definition with Python integer arithmetic; TS-PLAY-003 recomputes it).

### 7.3 Catch-up batch loop

```
due = min(floor(A * 60 / 16), MAX_OFFLINE_TICKS)
deos_set_egress_mode(K, EGRESS_REDUCED)
while due > 0:
    n = min(600, due); deos_step(K, n, &done); due -= done
    render(deos_chronicle_poll(...)); render_progress(tick / TICKS_PER_DAY)
    if done < n: handle error (halt, egress)
deos_set_egress_mode(K, EGRESS_FULL)     -- flushes the reduction buffer's Epoch selection
```

### 7.4 Epoch summary selection

```
rows = first-order rows of the Epoch, sorted by (magnitude desc, tick asc, kind asc, subject asc)
pick = []; per_kind = {}
for r in rows: if per_kind[r.kind] < 3: pick.append(r); per_kind[r.kind] += 1; if len(pick) == 12: break
pinned rows of the Epoch are prepended (at most 3), deduplicated
```

---

## 8. Data Structures

### 8.1 `CatalystLedger` (DEOS section 5.4; Kernel state)

```c
struct CatalystLedger {          /* 48 bytes; hashed; serialized (DEOS-RT REQ-SNAP-002 section 18) */
    int64_t  balance;            /* Q32.32, [0, capacity] */
    int64_t  capacity;           /* Q32.32; CAT_CAPACITY = 120.0 */
    int64_t  regen_per_tick;     /* Q32.32; CAT_REGEN = 2^-5 */
    int64_t  spent_total;        /* Q32.32, monotone */
    uint64_t actions_applied;    /* accepted entries since tick 0 */
    uint64_t reserved;           /* bits 0-3 World Phases reached, bits 8-15 FIRST_OF_KIND mask (DEOS-PROTO); else 0 */
};
```

### 8.2 Play constants

| Constant | Value | Use |
| :--- | :--- | :--- |
| `CAT_CAPACITY` | 120.0 (`0x0000007800000000`) | REQ-CAT-004 |
| `CAT_REGEN` | 2^-5 (`0x0000000008000000`) | REQ-CAT-004 |
| `CAT_MAX_RADIUS` | 8 | REQ-CAT-001 |
| `BASE[kind]`, `MAG_UNIT[kind]` | REQ-CAT-003 table | cost |
| `CATCHUP_BATCH` | 600 ticks | REQ-SES-001 |
| `PROBE_TICKS`, `PROBE_MAX_TRIES` | 5,400; 8 | REQ-PLAY-008 |
| `SUMMARY_K`, `SUMMARY_PER_KIND` | 12; 3 | REQ-PLAY-007 |
| `SNAPSHOT_RING` | 4 interval Snapshots plus every Epoch Snapshot | REQ-PLAY-007 |
| Cadence band per phase | 4–40, 4–40, 8–80, 12–120 per simulated day | REQ-PLAY-008 |
| `SURPRISE_MIN`, `SURPRISE_MAX` | 0.50, 0.95 | REQ-PLAY-008 |

### 8.3 Reference action script (for P5, surprise, and consequence tests)

Applied to every seed-sample world in TS-PLAY-002's attended variant, at the listed ticks, each at the world's centre Cell unless stated: tick 600 `ENRICH m = 64, r = 4`; tick 3,600 `WARM m = 8, r = 4` at the northernmost land Cell of the central column; tick 7,200 `VOLATILITY m = 2, r = 3`; tick 10,800 `WHISPER m = 0.25, q = 8 (sharing), r = 4`; tick 18,000 `METEOR m = 0.5, r = 4` at the Cell of the largest Institution's founder; tick 36,000 `MONSOON m = 0.5, r = 4`. Total cost 10 + 6 + 5 + 8 + 20 + 12 = 61, within one refill.

---

## 9. Subsystem Interfaces

Compiled into the Kernel (DEOS-RT section 9): `cat_kind_table` (REQ-CAT-001 ranges and families), `cat_cost` (REQ-CAT-003), `cat_expand` (REQ-CAT-002). Host services (outside the Kernel): seed curation, Snapshot ring, share export/import, Challenge publication and verification (which runs `deos_verify` on a server), telemetry. Events consumed: every kind; events produced: none (kind 4 `EPOCH_BOUNDARY` is emitted by DEOS-RT on this module's behalf).

---

## 10. Failure Cases & Risk Mitigation

| Case | Behaviour | Mitigation |
| :--- | :--- | :--- |
| Player cannot afford any action | the Palette shows time-to-affordable for each kind; a check-in still has ≥ 30 Budget after 16 minutes away | REQ-CAT-004 constants |
| A world is dull (below cadence band) | tuning failure surfaced by TS-PLAY-002; curation rejects the seed in the first 90 s | REQ-PLAY-008 |
| A world is noise (above band) | the Chronicle's first-order filter and pinning; tuning failure surfaced by TS-PLAY-002 | REQ-PLAY-006, 008 |
| Catch-up exceeds 60 s on weak hardware | the Host shows the honest progress line and lets the player observe during catch-up | REQ-SES-001 |
| Absence of weeks | capped at `MAX_OFFLINE_TICKS` (3 Epochs); the world did not die (ADR-0002); the summary says how much time passed | REQ-SES-001 |
| Tampered submission | rejected by `deos_verify` with the tick | REQ-SES-005 |
| Seed code typo | check nibble; refused with a message | REQ-SES-003 |
| Kernel halts (Desync, ledger fault) | the Host shows the report and offers to send seed + log; the world is preserved at its last Snapshot | DEOS-RT REQ-HASH-005 |

---

## 11. Performance & Scalability Targets

| Item | Target |
| :--- | :--- |
| Observation View | 60 fps at MVS scale reading the view once per frame; the view is 148 MB resident with the Kernel (DEOS-RT section 8.5) |
| Chronicle rendering | ≤ 1 ms per polled batch of 256 rows |
| Drill-down by ghost rewind | ≤ 2 s at MVS scale (≤ 3,600 ticks at `MIN_ACCELERATION`) |
| Catch-up | ≤ 60 s per Epoch; first row ≤ 1 s (DEOS-F05 P3) |
| Seed curation | ≤ 3 s per probe; ≤ 24 s worst case (8 probes) |
| Verification service | ≤ 5 s per 10,000-tick log (P4) |

---

## 12. Future Expansion

1. Multiplayer worlds: one `CatalystLedger` per player id in the Input Log record (a reserved payload bit range), verified per player.
2. Stochastic composites using the SystemID 1 Stream (weather systems that drift).
3. Named eras: player-authored names for Epochs, stored Host-side and shared with the log.
4. Spectator broadcast of a ghost-mode world.
5. Curated seed catalogues ("worlds that reach Intelligence by day 20") built from the seed sample.

---

## 13. Revision History

| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 | 2026-09-12 | Initial DEOS draft | DEOS Arch Team |
