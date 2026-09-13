# Specification: Agent Cognition, Society Models & Inter-entity Rules (DEOS-PROTO)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | DEOS-PROTO |
| **Semantic Version** | v0.1.0 |
| **Status** | Draft |
| **Dependencies** | DEOS, DEOS-F01, DEOS-F02, DEOS-F03, DEOS-F04, DEOS-F05, DEOS-F06, DEOS-CORE, DEOS-ECS, DEOS-RT |
| **Supersedes** | None (new module; absorbs the Life, Society, and Civilization phase intent of ROADMAP.md and Pillar 2) |
| **Reserved Prefixes** | `COG`, `SOC`, `XL`, `EVT` (from DEOS section 3.2) |

---

## 1. Purpose

DEOS-Protocol is the drama. It owns every rule of Stages 3, 4, and 5: how life metabolizes, reproduces, and dies (`XL`, the substrate-to-life coupling); how an agent perceives, wants, decides, and remembers (`COG`); how beliefs spread, trust forms, Institutions rise and fall, and technology is discovered (`SOC`); and the taxonomy of Notable Events that turns all of it into a history the player can read (`EVT`). Every rule is a pure function of the read buffer and the entity's own PRNG Substream, writes only the entity's own components, and reaches other entities only through the Commands of DEOS-ECS. Nothing here is scripted; every threshold is a constant the DEOS-F06 rubric can move (GI-7).

Player-facing consequence: tribes, cults, trading leagues, famines, migrations, wars, and discoveries all emerge from the rules in this document, and each one leaves a row in the Chronicle whose cause the player can open (GI-5).

## 2. Scope

**Included.** Metabolism, thermal and moisture coupling, aging, death, passive feeding, reproduction and inheritance under `mutation_bias` (`XL`); Needs levels and weights, Perception use, the action set, the utility model with Decision Traces, exploration, movement, memory (`COG`); Meme-Vector semantics, pull transmission and push sharing, trust dynamics, Institutions (founding, membership, council, redistribution, doctrine, upkeep, dissolution, schism), technology discovery and its effects, conflict (`SOC`); the Notable Event taxonomy with thresholds and story templates, `WorldMood` computation, World Phase thresholds, the pacing-constant table (`EVT`).

**Excluded.** Layouts and Command semantics (DEOS-ECS); the order in which the Runtime calls the three stage passes and flushes events (DEOS-RT); the Catalyst kinds that write the Substrate and inject Meme deltas (DEOS-PLAY; this module only consumes the `mutation_bias` field and the overlay `MEME_DELTA` writes DEOS-ECS applies); presentation of the Chronicle (DEOS-PLAY).

## 3. Dependencies

| Document | Used for |
| :--- | :--- |
| DEOS sections 4, 5, 6 | vocabulary; `NEED_COUNT`, `MEME_DIM`, `MEMORY_SLOTS`, `TRUST_EDGES`, `PERCEPTION_RADIUS`, `TICKS_PER_DAY`; the `NotableEvent`, `DecisionTrace`, `WorldMood` headers; reserved kinds 0 to 8; GI-5, GI-7 |
| DEOS-F02 | Directives 1, 10, 11 |
| DEOS-F05 | P1, P2, P5, P6 targets this module must make achievable |
| DEOS-CORE | `fx_*` primitives and tables; REQ-MATH-003 utility form; `prng_*` with SystemIDs 2, 3, 4 and Substreams (REQ-PRNG-003, 004, 005); ordering (REQ-ORD-001, 002); `FX_ENTROPY_TAX`; the Cell of an entity (REQ-LAW-004 rule 6) |
| DEOS-ECS | every component layout (REQ-ENT-002, 003, REQ-CMP-001 … 013); `gene_param` and the parameter and trait tables (REQ-CMP-002); the ownership matrix and read rule (REQ-CMP-013); the Command kinds and passes (REQ-MUT-004); `MAX_COMMANDS_PER_ENTITY_PER_STAGE` = 4 (REQ-MUT-005); the pure-function rule (REQ-MUT-007); the SpatialIndex (REQ-DAT-009); SPAWN and DESPAWN (REQ-ENT-008, 009); the Chunk ledger (REQ-MUT-009) |
| DEOS-RT | the step order (section 7.1 rows 3.1, 4.1, 5.1, 5.3, 5.4); event outboxes (REQ-LOOP-007); SystemIDs from 32 (REQ-LOOP-006) |
| `research/INTERFACE_INSPIRATION.md` | C5 (World Phases), C6 (story templates and cause), C8 (WorldMood) |

## 4. Definitions

| Term | Definition |
| :--- | :--- |
| **Agent** | An entity of archetype `ARCH_AGENT` (0x0F). Has cognition and culture. |
| **Organism** | An entity of archetype `ARCH_ORGANISM` (0x03). Metabolizes and reproduces; never decides. Plants, in the Host's vocabulary. |
| **Own Cell** | The Cell of the entity's `Position2D` in the buffer the stage reads (DEOS-CORE REQ-LAW-004 rule 6). |
| **Energy fraction** | `ef = fx_div(current_energy, max_capacity)`, in `[0, 1]`. |
| **Maturity** | `age_ticks ≥ max_age / 8` (integer part of the Genome row 4 value, shifted right by 3). |
| **Stranger** | For an Agent `i`, a live entity `j` in `Perception.nearest` whose `Affiliation.institution` differs from `i`'s, or whose `institution` and `i`'s are both `NULL_ENTITY_ID` and `j` carries a `TrustEdge` weight below 0 in `i`'s edges, or is absent from `i`'s edges. |
| **Kin** | An entity present in the Agent's `TrustEdges` with weight ≥ 0.25. |
| **Meme distance** | `md(a, b) = (Σ_{i<32} fx_abs(a.v[i] − b.v[i])) >> 6`, in `[0, 1]` (the sum is at most 64.0). |
| **Council** | The up-to-eight members an Institution tracks in its own `TrustEdges` (REQ-SOC-006). |
| **Policy** | `InstitutionState.policy`, the Institution's Meme-Vector. |
| **First-order event** | A Notable Event of a domain kind flagged first-order in section 8.4; the cadence targets of DEOS-PLAY count only these. |
| **Substream** | The entity's PCG64 Substream for the stage's SystemID at this tick and Chunk (DEOS-CORE REQ-PRNG-003). Every draw in this document is from it unless stated. |

Need indices: `0 ENERGY`, `1 SAFETY`, `2 REPRODUCTION`, `3 BELONGING`, `4 CURIOSITY`, `5 STATUS`, `6 COMFORT`, `7 ORDER`.

Action values (`Decision.action`, `DecisionTrace.action`): `0 NONE`, `1 IDLE`, `2 MOVE`, `3 FEED`, `4 REST`, `5 REPRODUCE`, `6 SHARE`, `7 TRADE`, `8 JOIN`, `9 LEAVE`, `10 FOUND`, `11 CONTEST`, `12 BUILD`, `13 FLEE`. `ACTION_COUNT` = 14.

Memory kinds (`MemoryEntry.kind`): `0 EMPTY`, `1 FED`, `2 STARVED`, `3 ATTACKED`, `4 ATTACK`, `5 GIFT_RECEIVED`, `6 GIFT_GIVEN`, `7 SHARED`, `8 JOINED`, `9 LEFT`, `10 FOUNDED`, `11 BORN`, `12 EXPLORED`, `13 FLED`, `14 KIN_DIED`.

## 5. Assumptions

1. The Runtime calls `proto_stage3_chunk`, `proto_stage4_chunk`, and `proto_stage5_chunk` exactly once per Chunk per tick in DEOS-RT section 7.1 order, each with the Stream of SystemID 2, 3, or 4 for that tick and Chunk; the pass iterates slots ascending and advances the Substream per slot (DEOS-CORE section 7.6).
2. Every read follows DEOS-ECS REQ-CMP-013: Stage 3 reads `EnergyState`, `Lifecycle`, `Needs.level` from A and everything of owner stage ≥ 4 from A, Cell fields from B; Stage 4 reads owner-3 data from B, owner-≥4 data from A; Stage 5 reads owner-≤4 data from B and owner-5 data from A.
3. Every energy movement is a Command of DEOS-ECS REQ-MUT-004 (which applies the entropy tax and the Chunk ledger), or an own write whose removed energy is booked to the Chunk ledger `dissipated` (metabolism, upkeep). Conservation is therefore DEOS-ECS's and DEOS-CORE's to prove; this module only names amounts.
4. Draw counts per slot are fixed by archetype and code path except inside `bounded`, which DEOS-CORE REQ-PRNG-003 isolates per Substream; the draw schedule of section 7.7 is binding.
5. Every constant in this document is Q32.32 unless it is a count; raw values are `floor(2^32 · value)` and are listed in section 8.5.

---

## 6. Requirements

### 6.1 Substrate-to-life coupling and biology (`XL`), Stage 3, SystemID 2

### REQ-XL-001: Aging and death by age

For every live Biological slot: `age_ticks' = min(A.age_ticks + 1, 0xFFFFFFFF)`. If `age_ticks' ≥ fx_to_int_floor(gene_param(4))` the entity dies this tick with `death_cause = 2 AGE` (REQ-XL-004). `Lifecycle.born_tick`, `parent`, `generation` are copied.

Player-facing consequence: every agent has a lifespan the inspect view shows as days remaining, so dynasties and generations are visible, not implied (GI-5).

### REQ-XL-002: Metabolism

For every live Biological slot, before any other Stage 3 rule, the drain for this tick is

```
act   = A.Decision.action (Agents) or IDLE (Organisms)
mult  = ACT_MULT[act]                            -- IDLE 0.5, REST 0.5, MOVE 1.5, FLEE 1.5, CONTEST 2.0, all others 1.0
tmul  = FX_ONE + fx_min(fx_div(fx_abs(T_cell − thermal_optimum), thermal_tolerance), 2.0)   -- thermal stress, in [1, 3]
mmul  = FX_ONE + fx_abs(M_cell − moisture_optimum)                                       -- in [1, 2]
rate  = fx_mul(fx_mul(fx_mul(metabolic_rate, mult), tmul), mmul)
rate  = Organism ? fx_mul(rate, ORG_METAB_MULT) : rate                                    -- ORG_METAB_MULT = 2^-3
drain = fx_min(rate, A.current_energy)
current_energy' = A.current_energy − drain;  Chunk ledger dissipated += drain
```

`T_cell` and `M_cell` are the own Cell's `temperature` and `moisture` from B; `thermal_optimum`, `thermal_tolerance`, `moisture_optimum` are `gene_param` rows 8, 9, 10. `max_capacity` and `metabolic_rate` are rewritten from rows 0 and 1 every tick (DEOS-ECS REQ-ENT-003 rule 1). A member of an Institution whose policy has discovered SHELTER (REQ-SOC-008) uses `thermal_tolerance × 1.5`.

Player-facing consequence: a cold snap the player summons is a visible rise in every nearby agent's burn rate on the inspect panel, and the ones with the wrong genes for it are the ones the Chronicle reports starving (GI-5, GI-7).

### REQ-XL-003: Passive feeding (Organisms) and the energy need level

An Organism draws from its own Cell every tick: `want = fx_min(fx_mul(FX_PHOTO_RATE, max_capacity), room)` with `FX_PHOTO_RATE = 2^-7` and `room = max_capacity − current_energy'`; if `want > 0` it issues `CELL_ENERGY_DELTA` (draw, `payload[0] = −want`) to its own Cell. Agents feed only by the `FEED` action (REQ-COG-006). After metabolism and (for Organisms) the draw request, Stage 3 writes `Needs.level[ENERGY] = ef` computed from `current_energy'` (the draw lands at the barrier, so the level reflects pre-feeding energy; the one-tick lag is deliberate and identical everywhere).

Player-facing consequence: plants are the visible base of the food web: a green valley is one where the ground's energy is being turned into bodies agents can eat (GI-7).

### REQ-XL-004: Death and the corpse

An entity dies in Stage 3 when `current_energy' == 0` after metabolism (`death_cause = 1 STARVATION`), when REQ-XL-001 fires (`2 AGE`), or when `A.current_energy == 0` at Stage 3 entry because a `DAMAGE` Command emptied it at a barrier of the previous tick (`3 DAMAGE`; the cause is identified by `A.current_energy == 0` and `A.alive == 1`). Death writes `alive' = 0`, `death_cause`, issues `DESPAWN` (payload per DEOS-ECS REQ-ENT-009 rule 1), and issues `CELL_ENERGY_DELTA` (deposit) of `current_energy'` to the own Cell; `current_energy'` is then written as 0. A dying Agent additionally emits the Notable Event of REQ-EVT-002 row `DEATH_OF_NOTE` when its threshold holds. Every Agent whose `TrustEdges` in A name the dead entity with weight ≥ 0.5 appends Memory kind `14 KIN_DIED` in its own Stage 4 pass of the next tick (REQ-COG-009 rule 4).

Player-facing consequence: a corpse feeds the ground it fell on, the cause of death is a word on the inspect panel, and the friends of the dead remember it (GI-5, GI-7).

### REQ-XL-005: Reproduction and inheritance

A live, mature Biological entity with `ef' = fx_div(current_energy', max_capacity) ≥ gene_param(2)` (`reproduction_threshold`) reproduces this tick when:
- Agent: `A.Decision.action == 5 REPRODUCE` (decided in the previous tick's Stage 4); or
- Organism: `bernoulli(fx_mul(gene_param_trait(30), FX_ORG_REPRO_P))` with `FX_ORG_REPRO_P = 2^-9` (one draw per mature Organism per tick with `ef' ≥ threshold`; no draw otherwise).

Reproduction: `cost = fx_mul(gene_param(3), max_capacity)`; `current_energy' −= cost`; the child's Genome is written to the SpawnPayload of the parent's slot:

```
bias  = B.mutation_bias[own Cell]                         -- [0.25, 4.0]
p_mut = fx_min(fx_mul(gene_param(15), bias), FX_HALF)     -- per-gene mutation probability, capped at 0.5
for g in 0..31 (ascending):
    child.gene[g] = parent.gene[g]
    if bernoulli(p_mut):                                   -- 32 draws, always
        delta = bounded(2*MUT_STEP + 1) − MUT_STEP          -- MUT_STEP = 4096; one bounded draw per mutated gene
        child.gene[g] = clamp(parent.gene[g] + delta, 0, 65535)
```

then `SPAWN` with `payload[0] = cost`, `payload[1..2]` = parent position, `payload[3]` = archetype in bits 0–15 and `min(parent.generation + 1, 65535)` in bits 16–31, `aux` = the SpawnPayload reference. (DEOS-ECS applies the entropy tax to the child's initial energy through `min(payload[0], gene_param(0))`? No: `SPAWN` carries `cost`; the tax of REQ-LAW-005 is booked by writing `heat = max(fx_mul(cost, FX_ENTROPY_TAX), 1)` to the Chunk ledger `dissipated` and `payload[0] = cost − heat`.) The parent appends Memory kind `11 BORN` (Agents; REQ-COG-009). A Genome whose mutated `gene[15]` (`mutation_rate_base`) or any parameter row moved by more than `MUT_STEP × 2` from the parent's emits `GENOME_DRIFT` (REQ-EVT-002).

Sexual variant (flag `PROTO_SEXUAL`, off in v0.1.0): the partner is the nearest Kin of the same archetype in `Perception.nearest` (A); each gene is taken from the partner when `bernoulli(FX_HALF)` (32 further draws), then mutated as above; no partner means asexual.

Player-facing consequence: the Mutation slider is a lever on this one probability, and its result is a Chronicle row naming the valley where a lineage drifted (commitment C3, GI-5, GI-7).

### REQ-XL-006: Needs levels

After metabolism, Stage 3 writes all eight levels for every live Biological slot (Organisms: `ENERGY` as REQ-XL-003, `COMFORT` as below, the rest 0.5):

| Need | Level (Q32.32, clamped to [0, 1]) |
| :--- | :--- |
| `ENERGY` | `ef` |
| `SAFETY` | `FX_ONE − (strangers × FX_ONE) >> 3`, strangers counted over the four `A.Perception.nearest` entries per the Definitions (0 … 4); Organisms 0.5 |
| `REPRODUCTION` | `FX_ONE − fx_mul(gene_param_trait(30), fx_clamp(fx_div(ef − gene_param(2), FX_ONE − gene_param(2)), 0, FX_ONE))` when mature, else `FX_ONE` |
| `BELONGING` | `A.Affiliation.institution` valid ? `FX_HALF + (A.Affiliation.standing >> 1)` : `(kin_count × FX_ONE) >> 4` (kin counted over `A.TrustEdges`, 0 … 8) |
| `CURIOSITY` | `FX_ONE − fx_mul(gene_param_trait(14 → row 14 curiosity), fx_min(fx_from_int(t − t_explored) / TICKS_PER_DAY, FX_ONE))` where `t_explored` is the tick of the newest `12 EXPLORED` entry in `A.Memory` (or `born_tick`) |
| `STATUS` | by `A.Affiliation.role`: NONE 0.25, MEMBER 0.5, ELDER 0.75, FOUNDER 1.0 |
| `COMFORT` | `FX_ONE − fx_min(fx_div(fx_abs(T_cell − thermal_optimum), thermal_tolerance), FX_ONE)` |
| `ORDER` | member: `FX_ONE − md(A.MemeVector, A.InstitutionState.policy of the Institution)`; non-member with a nearest Kin: `FX_ONE − md(own, kin's A.MemeVector)`; else 0.5 |

Player-facing consequence: the eight bars on the inspect panel are these formulas, and the Decision Trace names three of them by index (GI-5).

### 6.2 Cognition (`COG`), Stage 4, SystemID 3

### REQ-COG-001: Perception

Stage 4 computes the `Perception` record per DEOS-ECS section 7.2 into a local record for every live Agent and writes it to B. Sector attractiveness and the Stranger and Kin classifications of section 7.1 are derived from it in the same pass; no rule reads `Perception` from B.

### REQ-COG-002: Needs weights

`Needs.weight[k]' = fx_mul(gene_param_trait(16 + k), FX_ONE − B.Needs.level[k])` for every live Agent, clamped to `[0, 1]` (urgency times disposition). Weights are written to B for the next tick's legibility and used from the local value in this pass.

### REQ-COG-003: Legal actions

An action is legal for an Agent at this tick when its precondition holds (section 7.2 table): `IDLE` and `REST` always; `MOVE` when `move_speed > 0`; `FEED` when the own Cell's B `energy` > 0; `REPRODUCE` when mature and `ef ≥ reproduction_threshold` (evaluated on B's `EnergyState`); `SHARE` when at least one Kin is in `nearest`; `TRADE` when a Kin in `nearest` has `ef` above the Agent's by at least 0.25 or below it by 0.25; `JOIN` when not affiliated and a `nearest` entity is affiliated with a valid Institution; `LEAVE` when affiliated with `standing < −0.5`; `FOUND` when not affiliated, `ef ≥ 0.75`, at least `FOUND_MIN_KIN` = 2 Kin are in `nearest` and unaffiliated, and the Institution range has a free slot in A (`entity_table` scan is replaced by the last Stage 6's `institutions` count in `WorldMoodSlot` being below `MAX_INSTITUTIONS`); `CONTEST` when a Stranger is in `nearest` and `gene_param_trait(11) ≥ 0.25`; `BUILD` when affiliated and `ef ≥ 0.5`; `FLEE` when a Stranger is in `nearest`. Illegal actions have utility `FX_MIN` and are never chosen.

### REQ-COG-004: Utility and choice

For each legal action `a`, `U(a) = Σ_k fx_mul(w_k, f_k(a))` in ascending `k` per DEOS-CORE REQ-MATH-003, with `f_k(a) = fx_logistic(fx_mul(FX_GAIN_SLOPE, gain_k(a)))` and `gain_k(a)` the predicted change of need level `k` from section 7.2 (in `[−1, 1]`); `FX_GAIN_SLOPE = 4.0`, so `f_k ∈ (0.018, 0.982)` and `f_k(0) = 0.5`. The chosen action is the argmax with ties to the lowest action value (REQ-ORD-002). Exploration: with `bernoulli(fx_mul(gene_param_trait(14), FX_EXPLORE_MAX))`, `FX_EXPLORE_MAX = 2^-4` (one draw per Agent per tick, always), the chosen action is replaced by `legal[bounded(n_legal)]` (the legal actions in ascending value; one further draw) and `Decision.flags` bit 2 is set. The Decision Trace's three contributors are the three largest `fx_abs(fx_mul(w_k, f_k(a_chosen) − FX_HALF))` terms with ties to the lowest `k`, each recorded as `{ need = k, weight = fx_mul(w_k, f_k − FX_HALF) }` (signed: a need that argued against the chosen action has a negative weight); unused slots (fewer than three non-zero terms) carry `need = 0xFF`, `weight = 0`. `Decision.utility = U(a_chosen)`; `action = a_chosen`.

Player-facing consequence: the "why" panel reads "FEED: hunger +0.41, safety −0.12, curiosity +0.05", straight from this record, for every agent, every tick (GI-5).

### REQ-COG-005: Movement

`MOVE` and `FLEE` choose a sector `s*` (section 7.3) and set `Position2D' = clamp(A.Position2D + fx_mul(speed, DIR[s*]))` where `DIR` is the eight unit-ish vectors `{(0,−1), (1,−1)·√½, (1,0), (1,1)·√½, (0,1), (−1,1)·√½, (−1,0), (−1,−1)·√½}` with `√½ = 0x00000000B504F333` (DEOS-CORE section 7.7), `speed = gene_param(5)` (×1.25 with NAVIGATION, REQ-SOC-008), clamped per DEOS-ECS REQ-ENT-002 rule 3. Every other action keeps the position. When the new Cell differs from the old, the Agent appends Memory `12 EXPLORED` with the new Cell (REQ-COG-009). `FLEE` uses the sector that maximizes distance from the nearest Stranger (section 7.3 with the safety row only).

### REQ-COG-006: Feeding

`FEED` issues `CELL_ENERGY_DELTA` (draw) to the own Cell for `want = fx_min(fx_mul(fx_mul(gene_param(7), B.energy[cell]), agri), room)` with `agri = FX_ONE` or 1.25 under AGRICULTURE (REQ-SOC-008) and `room = max_capacity − B.current_energy`; sets `Decision.flags` bits 0 and 1, `target_cell = cell`. The outcome is remembered next tick (REQ-COG-009 rule 2).

### REQ-COG-007: Contest and flight

`CONTEST` targets the nearest Stranger `j` (lowest `(distance_sq, id)`); the Agent issues `DAMAGE` to `j` with `payload[0] = fx_mul(fx_mul(B.current_energy, gene_param_trait(11)), FX_STRIKE)`, `FX_STRIKE = 2^-3` (×1.5 under METALLURGY), and appends Memory `4 ATTACK` (`subject = j`, `magnitude = payload[0]`). `Decision.target = j`, flags bit 1. Damage is applied at the Stage 4 barrier; the victim's own Stage 3 pass in the next tick observes the loss (DEOS-ECS REQ-ENT-009 rule 3) and its Stage 4 pass remembers `3 ATTACKED` when `A.current_energy` fell by more than `FX_ATTACK_NOTE` = 0.05 of `max_capacity` between the last two ticks as recorded by the `Memory` entry of kind `3` (rule REQ-COG-009 row 3 infers the attacker as the `nearest` entity whose last remembered action was `ATTACK` on it; when none, `subject = NULL_ENTITY_ID`). `FLEE` is REQ-COG-005 and appends `13 FLED`.

Player-facing consequence: a fight is two rows, one from each side, each naming the other and the amount, so a feud's first blow is findable (GI-5).

### REQ-COG-008: Social actions decided here, executed in Stage 5

`SHARE`, `TRADE`, `JOIN`, `LEAVE`, `FOUND`, `BUILD` set `Decision.action` and `Decision.target` (the chosen Kin, Stranger, Institution, or own Institution per section 7.2) in Stage 4 and are executed by the Agent's own Stage 5 pass of the same tick reading `B.Decision` (REQ-SOC-002 … 006). `REPRODUCE` is executed by Stage 3 of the next tick (REQ-XL-005).

### REQ-COG-009: Memory

Stage 4 appends to `Memory` (DEOS-ECS REQ-CMP-005 rule 2, at most four entries per tick, in this order) for every live Agent:

| # | Condition (evaluated on A and B per the read rule) | Entry |
| :--- | :--- | :--- |
| 1 | `A.Decision.action == FEED` and `B.current_energy − A.current_energy > 0` (the draw landed) | `1 FED`, `cell`, `magnitude` = the gain |
| 2 | `B.current_energy < fx_mul(max_capacity, 0.1)` and the newest entry is not `2 STARVED` within `TICKS_PER_DAY` | `2 STARVED`, `magnitude = ef` |
| 3 | `A.current_energy` (last tick end) is below the previous tick's value by more than `FX_ATTACK_NOTE × max_capacity` and `A.Decision.action ∉ {CONTEST, MOVE, FLEE}` (the drop was not metabolism) | `3 ATTACKED`, `subject` = the `nearest` entity with newest Memory `4 ATTACK` naming this Agent, else `NULL_ENTITY_ID`; `magnitude` = the drop |
| 4 | a `TrustEdge` in A with weight ≥ 0.5 names an entity that fails validation this tick | `14 KIN_DIED`, `subject` = that id, `magnitude` = the weight |

Entries `4 ATTACK`, `11 BORN`, `12 EXPLORED`, `13 FLED` are appended by the rules that perform them in the same pass (REQ-COG-005, 007, REQ-XL-005 for Agents via the previous tick's `A` Decision). Stage 5 appends `5 GIFT_RECEIVED` … `10 FOUNDED` through its own writes of `Memory`? No: Memory's owner is Stage 4 (DEOS-ECS), so Stage 5 outcomes are remembered by Stage 4 of the next tick from `A.Decision` and the observable result (a `TRADE` whose energy rose → `5`; whose energy fell → `6`; `SHARE` → `7`; `JOIN` with `A.Affiliation` now valid → `8`; `LEAVE` → `9`; `FOUND` with `A.Affiliation.role == FOUNDER` → `10`). Memory feeds utility through `gain_k` (section 7.2) with salience `gene_param_trait(28)`.

Player-facing consequence: the Memories panel is the agent's diary, newest first, each row jump-linked to the tick it happened (GI-5).

### 6.3 Society (`SOC`), Stage 5, SystemID 4

### REQ-SOC-001: Meme-Vector semantics

| Dimensions | Group | Meaning of `v[i] ∈ [−1, 1]` |
| :--- | :--- | :--- |
| 0–7 | survival knowledge | 0 where food is (foraging), 1 shelter craft, 2 water finding, 3 fire/warmth, 4 healing, 5 storage, 6 tool making, 7 way finding |
| 8–15 | social norms | 8 sharing (+) vs hoarding (−), 9 hierarchy (+) vs equality (−), 10 in-group loyalty, 11 aggression norm, 12 hospitality to strangers, 13 monogamy (+) vs communal (−) child-rearing, 14 reverence for elders, 15 conformity pressure |
| 16–23 | beliefs | 16 sun worship, 17 ancestor veneration, 18 fatalism (−) vs agency (+), 19 purity/taboo, 20 the world is finite (scarcity belief), 21 the Catalyst is benevolent, 22 afterlife, 23 progress |
| 24–31 | technology | 24 AGRICULTURE, 25 SHELTER, 26 MEDICINE, 27 STORAGE, 28 WRITING, 29 METALLURGY, 30 NAVIGATION, 31 GOVERNANCE |

Dimensions 24–31 are knowledge levels; an Institution's policy crossing `FX_DISCOVERY` = 0.5 on one of them is a discovery (REQ-SOC-008). Dimensions 8–15 modulate rules (`FX_NORM_*` in section 8.5); dimensions 16–23 modulate nothing in v0.1.0 except transmission and Institution identity, and exist so that beliefs can diverge and be read.

### REQ-SOC-002: Knowledge accrual by practice

In the Agent's Stage 5 pass, `v[i]' = clamp(A.v[i] + FX_LEARN, −1, 1)` with `FX_LEARN = 2^-8` for the dimension the tick's outcome practised: `FED` this tick → 0 and 24; `COMFORT` level ≥ 0.75 with `T_cell < thermal_optimum` → 25; `REST` with `ef` rising → 26 (and 4); `BUILD` → 27; `SHARE` → 28; `ATTACK` → 29; `EXPLORED` → 30 (and 7); `JOIN` or `FOUND` → 31. Unpractised knowledge decays: every dimension 24–31 not practised this tick moves toward 0 by `FX_FORGET = 2^-12` (the minimum-step rule of DEOS-CORE REQ-LAW-011 applies).

### REQ-SOC-003: Pull transmission and doctrine

Every live Agent blends toward the Kin it trusts and, if affiliated, toward its Institution's policy, all read from A:

```
acc[i] = 0 (i128), wsum = 0
for each TrustEdge e in A.TrustEdges with weight > 0 and valid id (ascending index):
    acc[i] += mul_q(e.weight, A.MemeVector(e.id).v[i]);  wsum += e.weight
if affiliated: acc[i] += mul_q(FX_DOCTRINE, policy.v[i]);  wsum += FX_DOCTRINE      -- FX_DOCTRINE = 2.0 (×1.5 under WRITING)
if wsum > 0:
    target[i] = div_q(acc[i], wsum)
    rate      = fx_mul(gene_param_trait(13), fx_mul(FX_ADOPT, FX_ONE + v[15]))      -- conformity × adoption × (1 + conformity norm); FX_ADOPT = 2^-6
    v[i]'     = clamp(v[i] + fx_mul(target[i] − v[i], rate), −1, 1)
```

then one `bernoulli(FX_MEME_MUT)` draw with `FX_MEME_MUT = 2^-10`: on success one `bounded(32)` dimension receives `bounded(2·FX_MEME_STEP_RAW + 1) − FX_MEME_STEP_RAW` (Q32.32 raw, `FX_MEME_STEP` = 2^-4). The overlay `MEME_DELTA` writes of DEOS-ECS REQ-MUT-011 rule 2 are applied before this rule.

Player-facing consequence: the Network Map's colours move at a rate the player can read on the inspect panel as "conformity", and a whisper (Cosmic or Mutation-family Catalyst) propagates along trust edges the Living Diagram draws (GI-5, GI-7).

### REQ-SOC-004: Push sharing and trade

`SHARE` (target = the nearest Kin `j`): the Agent issues `MEME_DELTA` to `j` with up to four dimensions: the four dimensions where `fx_abs(own.v[i] − A.MemeVector(j).v[i])` is largest (ties to lowest `i`), each `payload = fx_mul(own.v[i] − j.v[i], FX_SHARE_STRENGTH)` with `FX_SHARE_STRENGTH = 2^-3`; and one `TRUST_DELTA` to `j` of `+FX_TRUST_SHARE` (2^-5). One Command of each kind; the pair is 2 of the 4 allowed.

`TRADE` (target `j` = the Kin whose `ef` differs most from the Agent's by at least 0.25): if the Agent is richer, it issues `ENERGY_TRANSFER` to `j` of `amount = fx_mul(fx_mul(B.current_energy − A.EnergyState(j).current_energy, FX_HALF), gene_param_trait(12))` (altruism, scaled by `FX_ONE + v[8]` sharing norm, floored at 0) and `TRUST_DELTA +FX_TRUST_GIFT` (2^-4) to `j`; if poorer, it issues only `TRUST_DELTA +FX_TRUST_ASK` (2^-6) to `j` (a request, which raises the chance `j` trades with it later through `j`'s own rule). Trust weights are maintained by REQ-SOC-005.

### REQ-SOC-005: Trust dynamics

In the Agent's Stage 5 pass, after the transmission rule, for every edge in `A.TrustEdges` with a valid id: `weight' = weight − fx_mul(weight, gene_param_trait(25))·FX_TRUST_DECAY` (`FX_TRUST_DECAY = 2^-10`), then adjusted by the tick's memories written in Stage 4 (B.Memory newest entries whose `tick == t`): `3 ATTACKED` by `subject` → `−FX_TRUST_HIT` (0.5) scaled by `FX_ONE − gene_param_trait(26)` (forgiveness); `1 FED`… no edge effect; `5 GIFT_RECEIVED` from `subject` → `+FX_TRUST_GIFT`; `14 KIN_DIED` → the edge is dropped. New edges arrive through `TRUST_DELTA` Commands (DEOS-ECS REQ-MUT-004 kind 6) issued by others, and through the own write: when `nearest[0]` is valid, not present, and not a Stranger by affiliation, the Agent adds it with `+FX_TRUST_MEET` (2^-6) using the replacement rule of DEOS-ECS REQ-CMP-008 (the smallest weight is replaced only if smaller). Loyalty `gene_param_trait(27)` scales negative changes toward own Institution members by `FX_ONE − loyalty`.

### REQ-SOC-006: Institutions

1. **Founding.** `FOUND` (REQ-COG-003 preconditions) issues `SPAWN` with archetype `ARCH_INSTITUTION`, `source` = the founder, position = the founder's, `payload[0] = 0`, `aux = 0xFFFFFFFFFFFFFFFF`; the founder writes its own `Affiliation = { the new EntityID is unknown until Stage 6, so: institution = NULL_ENTITY_ID this tick; role = 3 FOUNDER pending }`. Resolution: at the next tick's Stage 5, the founder finds the Institution whose `InstitutionState.founder == self` and `founded_tick == t−1` in A through its own `TrustEdges` edge 0 (DEOS-ECS section 8.1 initializes the Institution's edge 0 to the founder, and the founder's Stage 5 pass scans the Institution range slots of A from `INSTITUTION_BASE` upward, at most `MAX_INSTITUTIONS`, for that match; the scan is bounded and deterministic), then writes `Affiliation = { id, t, +0.5, FOUNDER }` and issues `INSTITUTION_JOIN` and `TRUST_DELTA +FX_HALF` to it. The event `INSTITUTION_FOUNDED` is emitted by the founder at that tick. The two Kin that satisfied `FOUND_MIN_KIN` each receive a `TRUST_DELTA +FX_TRUST_INVITE` (2^-3) from the founder in the founding tick, which raises their `JOIN` utility (section 7.2).
2. **Joining.** `JOIN` (target = the Institution of the nearest affiliated entity) writes `Affiliation = { id, t, 0, MEMBER }`, issues `INSTITUTION_JOIN` and `TRUST_DELTA +FX_TRUST_JOIN` (2^-4) to the Institution (so the Institution's own `TrustEdges` come to hold up to eight members: the Council).
3. **Standing.** A member's `standing' = clamp(standing + FX_STANDING_UP · (BUILD this tick) − FX_STANDING_DRIFT − FX_STANDING_ORDER · md(own, policy), −1, 1)` with `FX_STANDING_UP = 2^-4`, `FX_STANDING_DRIFT = 2^-11`, `FX_STANDING_ORDER = 2^-8`. A member with `standing ≥ 0.75` and `age_ticks ≥ max_age / 2` becomes `ELDER`.
4. **Leaving.** `LEAVE` writes `Affiliation = 0` and issues `INSTITUTION_LEAVE`; the Institution's edge to the leaver decays by REQ-SOC-005 and is dropped by validation if the leaver dies.
5. **Institution pass** (the Institution entity's own Stage 5 rule): `policy.v[i]' = clamp(policy.v[i] + fx_mul(mean_council.v[i] − policy.v[i], FX_POLICY_RATE), −1, 1)` with the mean over Council members' `A.MemeVector` (valid edges, ascending index; `FX_POLICY_RATE = 2^-7`; no change when the Council is empty); `MemeVector' = policy'` (DEOS-ECS REQ-ENT-010 rule 4); upkeep `up = fx_mul(pooled_energy, FX_INST_UPKEEP)` (2^-12, halved under STORAGE) is removed and booked to the Chunk ledger `dissipated`; redistribution: the up-to-four Council members with the lowest `B.EnergyState.ef` below `FX_DOLE_THRESHOLD` (0.25) each receive `ENERGY_TRANSFER` of `min(fx_mul(their max_capacity, 0.25), pooled_energy / 4)` when `v[8] > −0.5` (a hoarding norm below −0.5 disables the dole); ties by lowest EntityID.
6. **Dissolution.** An Institution with `member_count == 0` for `TICKS_PER_DAY` consecutive ticks (tracked by the Institution's `Lifecycle.age_ticks` minus a `last_member_tick` kept in `TrustEdges` edge 7's weight slot? No: kept in `Affiliation.joined_tick` of the Institution itself, which DEOS-ECS reserves for the parent link but which an Institution with no parent may use as `last_member_tick`; this reuse is declared here and bumps nothing) or with `founder` invalid and `member_count == 0` dissolves: `status' = 0`, `DESPAWN` (payload `pooled_energy`), `CELL_ENERGY_DELTA` deposit of `pooled_energy` to the founding Cell, event `INSTITUTION_COLLAPSED`.
7. **Schism.** A `FOUND` by a current member with `standing < 0` that succeeds emits `SCHISM` naming the old Institution as `object`.

Player-facing consequence: a tribe is a real entity the player can open: founder, founding day, members, treasury, doctrine, and the eight-person council whose beliefs it averages; "the temple fed the poor" and "the guild split" are rows with exact numbers (GI-5, GI-7).

### REQ-SOC-007: Conflict at the Institution level

Two Institutions `P` and `Q` are in conflict during a simulated day when at least `FX_WAR_THRESHOLD` = 8 `ATTACK` memories were written by members of `P` naming members of `Q` in that day. Because no per-pair state exists, the count is carried by the events: `CONTEST` first-order events (REQ-EVT-002) carry the two Institutions in `subject`/`object` semantics, and the Runtime's Chronicle is the record; DEOS-PLAY aggregates `CONFLICT_ONSET` in presentation from these rows. In the Kernel, conflict modulates behaviour through memory only: an Agent whose Memory holds `3 ATTACKED` by a member of `Q` within the last `TICKS_PER_DAY` treats every member of `Q` as a Stranger (section 7.1), which lowers `SAFETY` and raises `CONTEST` and `FLEE` utility for the whole tribe as the memories spread by proximity. `CONFLICT_ONSET` and `CONFLICT_RESOLVED` are therefore Chronicle-level aggregates, not Kernel state, and the `EVT` table marks them as derived.

Player-facing consequence: a war is what the player sees when a valley fills with `CONTEST` rows between two colours; there is no war object, which is exactly why it can end the way real feuds do, by forgetting (GI-7).

### REQ-SOC-008: Technology discovery and effects

When an Institution's `policy.v[24 + k]'` crosses `FX_DISCOVERY` = 0.5 from below for the first time in the Institution's life (tracked by bit `k` of `InstitutionState.discovered`, DEOS-ECS REQ-CMP-010), the Institution emits `DISCOVERY` with `magnitude = fx_from_int(24 + k)`. Effects apply to every member (read through `A.Affiliation → A.InstitutionState.policy`) while `policy.v[24 + k] ≥ 0.5`:

| k | Technology | Effect |
| :--- | :--- | :--- |
| 0 | AGRICULTURE | `FEED` draw ×1.25 (REQ-COG-006) |
| 1 | SHELTER | `thermal_tolerance` ×1.5 (REQ-XL-002) |
| 2 | MEDICINE | death by AGE at `max_age × 1.25` (REQ-XL-001) |
| 3 | STORAGE | `FX_INST_UPKEEP` halved; Institution energy cap `FX_INST_CAP` doubled (section 8.5) |
| 4 | WRITING | `FX_DOCTRINE` ×1.5; `FX_LEARN` ×2 |
| 5 | METALLURGY | `FX_STRIKE` ×1.5 |
| 6 | NAVIGATION | `move_speed` ×1.25 |
| 7 | GOVERNANCE | Council of 8 redistributes to 4 members per tick with threshold 0.5 instead of 0.25; `FX_WAR_THRESHOLD` doubled for its members as aggressors |

The first `DISCOVERY` in a world reaches World Phase 4 (REQ-EVT-004).

Player-facing consequence: technology is knowledge that a society accumulated by doing things, crystallized by an Institution, and it changes what its people can do; the Chronicle names the guild that discovered agriculture and the day (GI-5, GI-7).

### REQ-SOC-009: WorldMood partials and fold

At DEOS-RT step 5.3 every Chunk computes, over its live slots in ascending order, `i128` partials: `coop` = count of `TRUST_DELTA` and `ENERGY_TRANSFER` Commands issued this stage with positive amount, plus `SHARE` and `TRADE` actions; `conf` = count of `DAMAGE` Commands issued in Stage 4 (from `B.Decision.action == CONTEST`) plus `FLEE` actions; `births` = `SPAWN` Commands issued this tick by the Chunk (Stage 3 count carried in the Chunk ledger's `births` field, which REQ-MUT-009 is extended to hold), `deaths` = `DESPAWN` issued; `pop` = live Biological slots; `inst` = live Institutional slots. Step 5.4 folds in ascending Chunk index and writes `WorldMoodSlot`: `population = pop`, `institutions = inst`, `cooperation = fx_div(fx_from_int64(coop), max(pop, 1))`, `conflict = fx_div(fx_from_int64(conf), max(pop, 1))`, `growth = fx_div(fx_from_int64(births − deaths), max(pop, 1))`, `entropy = fx_div(fx_from_int64(Ledger.s_tick >> 32), max(Ledger.e_total >> 32, 1))` (heat generated this tick as a fraction of world energy; both `i128` values reduced to Q32.32 integer parts first).

Player-facing consequence: the soundtrack's harmony and dissonance are `cooperation` and `conflict`, so the player hears a war coming before the Chronicle names it (commitment C8).

### 6.4 Notable Events (`EVT`)

### REQ-EVT-001: Emission rules

A Notable Event is emitted by the pass that detects its condition, into the Chunk's event outbox (DEOS-RT REQ-LOOP-007), with `tick = t`, `subject`, `object`, `cell`, `magnitude`, and `cause` = the emitting Agent's slot index when the event follows from its Decision this tick, else 0. Every condition in REQ-EVT-002 is a threshold on Kernel state; none is a script. A kind is first-order when the table says so; DEOS-PLAY's cadence targets count first-order events only. Story templates are Host text with `{subject}`, `{object}`, `{cell}`, `{magnitude}`, `{day}` substitutions.

### REQ-EVT-002: Domain kinds

| Kind | Name | First-order | Emitted by | Condition | `magnitude` | Story template |
| ---: | :--- | :---: | :--- | :--- | :--- | :--- |
| 16 | `BIRTH_OF_NOTE` | no | Stage 3, parent | a birth whose child `generation` is a multiple of 8, or the first birth in a Cell that had no live entity in A | child generation | "{subject} bore a child of the {magnitude}th generation at {cell}" |
| 17 | `DEATH_OF_NOTE` | yes | Stage 3, dying Agent | an Agent with `role ∈ {ELDER, FOUNDER}`, or with ≥ 4 Kin, or of `generation ≥ 16`, dies | `fx_from_int(death_cause)` | "{subject}, {role} of {object}, died of {cause} at {cell}" |
| 18 | `STARVATION_WAVE` | yes | Stage 3, Cell Chunk fold at 6.4a (DEOS-RT) | ≥ 16 deaths with cause STARVATION in one Cell Chunk in one tick | deaths | "Famine at {cell}: {magnitude} starved" |
| 19 | `MIGRATION` | yes | Stage 4, Agent | an Agent's `EXPLORED` entries show a net displacement ≥ `PERCEPTION_RADIUS × 4` Cells over the last `TICKS_PER_DAY` (computed from the oldest and newest `EXPLORED` entries in `A.Memory` within the day) | Cells moved | "{subject} migrated {magnitude} cells to {cell}" |
| 20 | `ABUNDANCE` | no | Stage 3, Organism | a Cell's B `energy` exceeds `FX_CELL_ENERGY_CAP / 4` for the first time since it was below `/ 16` (the Organism on it emits; the state is inferred from B and A energy) | Cell energy | "The ground at {cell} is rich: {magnitude}" |
| 21 | `INSTITUTION_FOUNDED` | yes | Stage 5, founder | REQ-SOC-006 rule 1 resolution | 1 | "{subject} founded {object} at {cell}" |
| 22 | `INSTITUTION_COLLAPSED` | yes | Stage 5, Institution | REQ-SOC-006 rule 6 | ticks lived | "{object}, founded by {subject}, dissolved after {magnitude} days" |
| 23 | `SCHISM` | yes | Stage 5, founder | REQ-SOC-006 rule 7 | standing at departure | "{subject} broke from {object} and founded a new house" |
| 24 | `ALLIANCE` | yes | Stage 5, Institution | two Institutions' Councils each hold a member of the other with weight ≥ 0.5 (checked by the lower-EntityID Institution, once per pair per day) | trust weight | "{subject} and {object} are allied" |
| 25 | `CONTEST` | yes | Stage 4, attacker | `DAMAGE` ≥ 0.25 of the victim's `max_capacity`, or attacker and victim belong to different valid Institutions | damage | "{subject} struck {object} at {cell}" |
| 26 | `BELIEF_SHIFT` | yes | Stage 5, Institution | a policy dimension in 16–23 crosses ±0.5 | dimension | "{object} now holds that {belief}" |
| 27 | `DISCOVERY` | yes | Stage 5, Institution | REQ-SOC-008 | 24 + k | "{object} discovered {technology}" |
| 28 | `EXTINCTION` | yes | Stage 6 fold (DEOS-RT, from `WorldMood.population`) | `population == 0` for the first time | 0 | "The world fell silent" |
| 29 | `GENOME_DRIFT` | no | Stage 3, parent | REQ-XL-005 drift condition | gene row | "A lineage at {cell} changed: {trait}" |
| 30 | `FIRST_OF_KIND` | yes | the emitting pass | the first `FED`, first `SHARE`, first `TRADE`, first `JOIN`, first `BUILD` in a world (tracked by the World Phase mask bits 8–15 kept by DEOS-RT in the `CatalystLedger` reserved field, declared here) | action value | "For the first time, {subject} {action}" |
| 31 | `ELDER_RISEN` | no | Stage 5, member | REQ-SOC-006 rule 3 promotion | standing | "{subject} became an elder of {object}" |
| 32 | `CONFLICT_ONSET` | derived | DEOS-PLAY presentation | REQ-SOC-007 | — | "War between {subject} and {object}" |
| 33 | `CONFLICT_RESOLVED` | derived | DEOS-PLAY presentation | no `CONTEST` between the pair for two days | — | "Peace between {subject} and {object}" |
| 34–255 | reserved | — | — | — | — | — |

Player-facing consequence: every row in this table is a sentence the player will read with real names in it, and every one drills down to a Decision Trace or a state the inspect view can show (GI-5).

### REQ-EVT-003: Cadence and the pacing constants

The first-order kinds are tuned so that, at MVS scale from the seed sample, a first-order event occurs at least every 5,400 ticks and at most every 60 ticks on average over a simulated day (DEOS-PLAY's band). The constants that tune cadence are exactly those of section 8.5 marked "pacing"; DEOS-PLAY may propose changes to them through the DEOS-F06 rubric and no other lever (GI-7).

### REQ-EVT-004: World Phase thresholds

`WORLD_PHASE_REACHED` (kind 6, `magnitude` = phase) is emitted once per phase per world by the pass that first satisfies the condition; the "already reached" state is bits 0–3 of the `CatalystLedger` reserved field (declared here, hashed with the record):

| Phase | Condition | Emitted by |
| :--- | :--- | :--- |
| 1 Reality | tick 0 | DEOS-RT world generation |
| 2 Life | the first tick at which `WorldMood.population ≥ 1.25 × tick-0 population` (a self-sustaining population: it has grown by a quarter) | DEOS-RT step 6.4a from `WorldMoodSlot` |
| 3 Society | the first `INSTITUTION_FOUNDED` | Stage 5, founder |
| 4 Intelligence | the first `DISCOVERY` | Stage 5, Institution |

Player-facing consequence: "my world reached Intelligence on day 22" is a Chronicle row with a tick, comparable across every player's worlds (commitment C5, GI-1).

---

## 7. Algorithms & Mathematics

### 7.1 Stranger and Kin classification (Stage 4, per Agent, from A)

```
for n in nearest[0..3] with valid id j:
    kin(j)      = j in own TrustEdges with weight >= 0.25
    hostile(j)  = own Memory has ATTACKED by j within TICKS_PER_DAY,
                  or (j affiliated with Q and own Memory has ATTACKED by any member of Q within TICKS_PER_DAY)
    stranger(j) = hostile(j) or (Affiliation(j) != own Affiliation and not kin(j))
                  or (both unaffiliated and (j not in edges or weight(j) < 0))
```

"member of Q" is read from `A.Affiliation` of the remembered subject at the time of the check.

### 7.2 Predicted gains `gain_k(a)`, in `[−1, 1]`

`E_here = B.energy[own Cell]`, `E_best = max sector energy_sum / 16` (per-Cell mean of the best sector), `cap = max_capacity`, `s = memory salience gene_param_trait(28)`.

| Action | ENERGY | SAFETY | REPRODUCTION | BELONGING | CURIOSITY | STATUS | COMFORT | ORDER |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| IDLE | −ε | 0 | 0 | 0 | −ε | 0 | 0 | 0 |
| REST | +ε | +ε | 0 | 0 | −ε | 0 | +0.25 | 0 |
| MOVE | `min(1, (E_best − E_here)/cap)` | `+0.25·strangers/4` | 0 | `+0.25` if Institution direction exists | `+0.5·(1 − level[CURIOSITY])` | 0 | `+0.25·(best sector comfort − own)` | 0 |
| FEED | `min(1, forage·E_here/cap) + s·(FED memories in last day)/4` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| REPRODUCE | −cost fraction | 0 | `+1` | `+0.25` | 0 | `+0.25` | 0 | 0 |
| SHARE | 0 | 0 | 0 | `+0.5` | `+0.25` | `+0.25` | 0 | `+0.5·(1 − md to kin)` |
| TRADE | richer: `−0.25`; poorer: `+0.5` | 0 | 0 | `+0.5` | 0 | richer: `+0.5` | 0 | 0 |
| JOIN | 0 | `+0.5` | 0 | `+1` | 0 | `+0.25` | 0 | `+0.5·(1 − md to policy)` |
| LEAVE | 0 | 0 | 0 | `−1` | `+0.25` | `−0.5` | 0 | `+0.5·md to policy` |
| FOUND | `−0.25` | `+0.25` | 0 | `+0.75` | 0 | `+1` | 0 | `+0.5` |
| CONTEST | `+0.25` if target is an Organism or `ef(target) > ef` | `+0.5·aggression − 0.5·(target ef / ef)` | 0 | `+0.25` if target is hostile to own Institution | 0 | `+0.5·aggression` | 0 | `+0.25·v[11]` |
| BUILD | `−0.25` | `+0.25` | 0 | `+0.5` | 0 | `+0.5` | 0 | `+0.25` |
| FLEE | 0 | `+0.75·strangers/4` | 0 | 0 | 0 | `−0.25` | 0 | 0 |

`ε` = 2^-6. Every entry is evaluated in Q32.32 in the order written (products before sums, `fx_mul`, `fx_min`), then clamped to `[−1, 1]`. Rows are complete: an omitted interaction is 0 by this table, never by inference.

### 7.3 Sector choice for MOVE

```
for s in 0..7 with in_range_mask bit s set:
    score[s] = fx_mul(w[ENERGY],   fx_div(sector[s].energy_sum, max_energy_sum))
             − fx_mul(w[SAFETY],   fx_div(sector_entities[s], max(1, sensed_count)))
             + fx_mul(w[COMFORT],  FX_ONE − fx_min(fx_div(fx_abs(sector[s].temperature_mean − thermal_optimum), thermal_tolerance), FX_ONE))
             + fx_mul(w[BELONGING], toward_institution(s))          -- 1.0 for the sector containing the own Institution's Cell, else 0
             + fx_mul(w[CURIOSITY], FX_ONE − fx_div(sector_entities[s], max(1, sensed_count)))
s* = argmax score, ties → lowest s; no in-range sector → IDLE
```

`max_energy_sum` = the largest `energy_sum` over in-range sectors, or 1 ulp when all are 0.

### 7.4 Draw schedule (binding; DEOS-CORE REQ-PRNG-005)

| Stage | Archetype | Draws, in order |
| :--- | :--- | :--- |
| 3 | Organism (live, mature, `ef' ≥ threshold`) | 1 `bernoulli` (reproduce?); if reproducing: 32 `bernoulli` (per gene) + one `bounded` per mutated gene |
| 3 | Agent reproducing | 32 `bernoulli` + one `bounded` per mutated gene |
| 3 | any other | none |
| 4 | Agent | 1 `bernoulli` (explore?); if exploring: 1 `bounded` |
| 5 | Agent | 1 `bernoulli` (meme mutation?); if mutating: 1 `bounded(32)` + 1 `bounded(step)` |
| 5 | Institution | none |

### 7.5 Institution scan for the founder (REQ-SOC-006 rule 1)

```
for i in INSTITUTION_BASE .. MAX_ENTITIES-1 (ascending):
    id = entity_table[i]; if archetype(id) != ARCH_INSTITUTION: continue
    if A.InstitutionState[i].founder == self and A.InstitutionState[i].founded_tick == t-1: return id
return NULL_ENTITY_ID     -- the SPAWN was dropped (range full): the founder's pending FOUNDER role is cleared
```

### 7.6 Meme distance and dot product

`md` per the Definitions; similarity for the Network Map is DEOS-ECS REQ-CMP-007 rule 3.

### 7.7 Command budget per Agent per stage (DEOS-ECS REQ-MUT-005)

| Stage | Maximum stage-resolved Commands | Which |
| :--- | :--- | :--- |
| 3 | 1 | `CELL_ENERGY_DELTA` (Organism draw, or the corpse deposit), plus the lifecycle `SPAWN`/`DESPAWN` which are not stage-resolved |
| 4 | 1 | `CELL_ENERGY_DELTA` (FEED) or `DAMAGE` (CONTEST) |
| 5 | ≤ 4 | `SHARE`: `MEME_DELTA` + `TRUST_DELTA`; `TRADE`: `ENERGY_TRANSFER` + `TRUST_DELTA`; `JOIN`: `INSTITUTION_JOIN` + `TRUST_DELTA`; `FOUND` resolution: `INSTITUTION_JOIN` + `TRUST_DELTA` + 2 invitation `TRUST_DELTA`; `BUILD`: `ENERGY_TRANSFER`; `LEAVE`: `INSTITUTION_LEAVE`; Institution pass: ≤ 4 `ENERGY_TRANSFER` |

---

## 8. Data Structures

### 8.1 Local records (never stored)

```c
struct Stage4Local {                  /* per Agent, per tick */
    struct Perception p;              /* DEOS-ECS section 7.2 */
    uint8_t  legal[14];               /* 1 = legal */
    int64_t  utility[14];             /* Q32.32; FX_MIN when illegal */
    int64_t  gain[14][8];             /* Q32.32 */
    uint8_t  stranger[4], kin[4];     /* over nearest */
    int64_t  score[8];                /* sector scores */
};
```

### 8.2 Claimed reserved bits

| Field | Bits | Meaning (this module) |
| :--- | :--- | :--- |
| `InstitutionState.discovered` | bits 0–7 | technologies discovered (REQ-SOC-008); declared in DEOS-ECS REQ-CMP-010 |
| `CatalystLedger.reserved` (DEOS section 5.4) | bits 0–3 | World Phases reached (REQ-EVT-004); bits 8–15: `FIRST_OF_KIND` mask (REQ-EVT-002 row 30) |
| `Decision.flags` | bit 2 | exploratory choice (REQ-COG-004) |
| `Affiliation.joined_tick` on an Institution entity | all | `last_member_tick` (REQ-SOC-006 rule 6) |
| `ChunkLedger` | + `uint32_t births, deaths` (DEOS-ECS REQ-MUT-009 extended to 24 bytes) | WorldMood partials (REQ-SOC-009) |

### 8.3 Story-template substitutions

`{subject}`, `{object}`: the Host's name for an EntityID (DEOS-PLAY names entities from the EntityID and `born_tick`); `{cell}`: `(x, y)`; `{day}`: `tick / TICKS_PER_DAY`; `{role}`, `{cause}`, `{belief}`, `{technology}`, `{trait}`, `{action}`: enumerations of this document.

### 8.4 First-order kinds

17, 18, 19, 21, 22, 23, 24, 25, 26, 27, 28, 30.

### 8.5 Constants (pacing constants marked ★ are DEOS-PLAY's tuning surface)

| Constant | Value | Raw | Use |
| :--- | :--- | :--- | :--- |
| `ORG_METAB_MULT` ★ | 2^-3 | `0x0000000020000000` | REQ-XL-002 |
| `FX_PHOTO_RATE` ★ | 2^-7 | `0x0000000002000000` | REQ-XL-003 |
| `FX_ORG_REPRO_P` ★ | 2^-9 | `0x0000000000800000` | REQ-XL-005 |
| `MUT_STEP` | 4,096 (integer) | — | REQ-XL-005 |
| `FX_GAIN_SLOPE` | 4.0 | `0x0000000400000000` | REQ-COG-004 |
| `FX_EXPLORE_MAX` ★ | 2^-4 | `0x0000000010000000` | REQ-COG-004 |
| `FX_STRIKE` ★ | 2^-3 | `0x0000000020000000` | REQ-COG-007 |
| `FX_ATTACK_NOTE` | 0.05 | `0x000000000CCCCCCC` | REQ-COG-009 |
| `FX_LEARN` ★ | 2^-8 | `0x0000000001000000` | REQ-SOC-002 |
| `FX_FORGET` | 2^-12 | `0x0000000000100000` | REQ-SOC-002 |
| `FX_DOCTRINE` ★ | 2.0 | `0x0000000200000000` | REQ-SOC-003 |
| `FX_ADOPT` ★ | 2^-6 | `0x0000000004000000` | REQ-SOC-003 |
| `FX_MEME_MUT` ★ | 2^-10 | `0x0000000000400000` | REQ-SOC-003 |
| `FX_MEME_STEP` | 2^-4 | `0x0000000010000000` | REQ-SOC-003 |
| `FX_SHARE_STRENGTH` | 2^-3 | `0x0000000020000000` | REQ-SOC-004 |
| `FX_TRUST_SHARE`, `FX_TRUST_ASK`, `FX_TRUST_MEET` | 2^-5, 2^-6, 2^-6 | — | REQ-SOC-004, 005 |
| `FX_TRUST_GIFT`, `FX_TRUST_JOIN` | 2^-4 | `0x0000000010000000` | REQ-SOC-004, 006 |
| `FX_TRUST_INVITE` | 2^-3 | `0x0000000020000000` | REQ-SOC-006 |
| `FX_TRUST_HIT` | 0.5 | `0x0000000080000000` | REQ-SOC-005 |
| `FX_TRUST_DECAY` ★ | 2^-10 | `0x0000000000400000` | REQ-SOC-005 |
| `FOUND_MIN_KIN` ★ | 2 (integer) | — | REQ-COG-003 |
| `FX_POLICY_RATE` ★ | 2^-7 | `0x0000000002000000` | REQ-SOC-006 |
| `FX_INST_UPKEEP` ★ | 2^-12 | `0x0000000000100000` | REQ-SOC-006 |
| `FX_INST_CAP` | 2^16 energy | `0x0001000000000000` | Institution `pooled_energy` cap (DEOS-CORE REQ-LAW-004 rule 3) |
| `FX_DOLE_THRESHOLD` ★ | 0.25 | `0x0000000040000000` | REQ-SOC-006 |
| `FX_STANDING_UP`, `FX_STANDING_DRIFT`, `FX_STANDING_ORDER` | 2^-4, 2^-11, 2^-8 | — | REQ-SOC-006 |
| `FX_WAR_THRESHOLD` ★ | 8 (integer) | — | REQ-SOC-007 |
| `FX_DISCOVERY` ★ | 0.5 | `0x0000000080000000` | REQ-SOC-008 |
| `PROTO_SEXUAL` | 0 (flag) | — | REQ-XL-005 |

Every ★ constant was chosen so that the seed sample meets DEOS-F05 P1 (first first-order event ≤ 5,400 ticks: `FIRST_OF_KIND` for the first `FED` fires within the first day in every seed because 2,048 Agents start at `ef` 0.4 with FEED legal) and P2 (first Institution by day 10: with `FOUND_MIN_KIN` = 2 and `FX_TRUST_MEET` = 2^-6 per tick of proximity, two Agents that share a Cell for 16 ticks become Kin, and `FOUND` gains +1 STATUS); the exact values are tuned by DEOS-MVS playtesting and every change re-runs TS-PLAY-002.

---

## 9. Subsystem Interfaces

```c
void proto_stage3_chunk(EcsContext*, uint32_t chunk, PcgStream* stream, EventOutbox*);   /* REQ-XL-001 … 006; system 2 */
void proto_stage4_chunk(EcsContext*, uint32_t chunk, PcgStream* stream, EventOutbox*);   /* REQ-COG-001 … 009; system 3 */
void proto_stage5_chunk(EcsContext*, uint32_t chunk, PcgStream* stream, EventOutbox*);   /* REQ-SOC-002 … 008; system 4 */
void proto_worldmood_partial(const EcsContext*, uint32_t chunk, WorldMoodPartial* out); /* REQ-SOC-009, DEOS-RT step 5.3 */
void proto_worldmood_fold(EcsContext*, const WorldMoodPartial* partials, uint32_t n);   /* step 5.4 */
```

Each function is pure per DEOS-ECS REQ-MUT-007. Events emitted: kinds 6 (phases 3 and 4) and 16–31. Commands issued: kinds 1, 2, 3, 4, 5, 6, 7, 8, 9 per section 7.7. SystemIDs: 2, 3, 4 (DEOS-CORE section 7.5.1); none from 32 upward in v0.1.0.

---

## 10. Failure Cases & Risk Mitigation

| Case | Behaviour | Mitigation |
| :--- | :--- | :--- |
| A `FOUND` whose `SPAWN` is dropped | the founder's pending role clears next tick; no Institution; `COMMAND_DROPPED` row | REQ-SOC-006 rule 1, section 7.5 |
| Runaway population | free range exhaustion → dropped births, visible | DEOS-ECS REQ-ENT-006; carrying capacity from insolation (ADR-0002) |
| All Agents converge to one belief | `FX_MEME_MUT` and exploration keep variance; belief dimensions do not affect fitness, so drift is neutral | REQ-SOC-003 |
| Institutions never found | `FOUND` utility has the largest STATUS gain in the table; TS-PLAY-002 P2 checks 80 of 100 seeds | section 7.2, 8.5 |
| Everyone fights | `CONTEST` costs 2× metabolism and needs aggression ≥ 0.25; hostility fades from memory after a day | REQ-XL-002, section 7.1 |
| Draw-count drift between platforms | the schedule of section 7.4 is fixed; TS-BENCH-002 | DEOS-CORE REQ-PRNG-003 |
| Command budget exceeded | impossible by section 7.7; assertion halts | DEOS-ECS REQ-MUT-005 |
| A `nearest` target dies mid-tick | Commands to it are dropped at the barrier with a row; the actor's memory records nothing | DEOS-ECS REQ-MUT-009 |

---

## 11. Performance & Scalability Targets

| Pass | Per live Agent | MVS (2,048 Agents, 8,192 Organisms) | v1.0 (10^6) |
| :--- | :--- | :--- | :--- |
| Stage 3 | ≈ 60 ops; +40 per reproduction | ≈ 0.02 ms on 4 threads | ≈ 1.5 ms |
| Stage 4 | 80 Cell reads + 14 × 8 gain terms + 14 logistics ≈ 600 ops | ≈ 0.04 ms | ≈ 3.5 ms |
| Stage 5 | 8 edges × 32 dims ≈ 300 ops | ≈ 0.02 ms | ≈ 2 ms |
| Events | bounded by outbox capacity | negligible | negligible |

Within the 0.1 ms (MVS) and 7 ms (v1.0) budgets DEOS-RT section 11 allots to Stages 3–5.

---

## 12. Future Expansion

1. Sexual reproduction (`PROTO_SEXUAL`), already specified as a flag.
2. Per-pair conflict state (a small Institution-pair table) to make `CONFLICT_ONSET` a Kernel event rather than a presentation aggregate.
3. Belief dimensions with effects (fatalism lowering exploration, sun worship raising insolation appreciation as a COMFORT term).
4. Trade of Meme dimensions for energy (knowledge markets).
5. Institutions founding sub-Institutions through the parent link DEOS-ECS reserves.

---

## 13. Revision History

| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 | 2026-09-12 | Initial DEOS draft | DEOS Arch Team |
