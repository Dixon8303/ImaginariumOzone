# Specification: Design Pillars (DEOS-F03)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | DEOS-F03 |
| **Semantic Version** | v0.1.0 |
| **Status** | Approved |
| **Dependencies** | DEOS, DEOS-F01, DEOS-F02 |
| **Supersedes** | EESS-0003 |

---

## 1. The Five Pillars

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              DEOS: EMERGENCE PILLARS                                 │
├─────────────────┬─────────────────┬─────────────────┬─────────────────┬──────────────┤
│ 1. Deep         │ 2. Autonomous   │ 3. Massive      │ 4. Catalyst     │ 5. Playable  │
│    Substrate    │    Cognition &  │    Scalability  │    Intervention:│    Emergence │
│    Physics      │    Meme-Vectors │                 │    Shape the    │              │
│                 │                 │                 │    Probabilities│              │
├─────────────────┼─────────────────┼─────────────────┼─────────────────┼──────────────┤
│ Stage 2         │ Stages 3–4      │ Chunks, SoA,    │ Stage 1         │ Chronicle,   │
│ Core laws       │ Protocol        │ zero-alloc      │ Input Log       │ Traces, Play │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┴──────────────┘
```

Pillars 1 through 4 are carried forward from the EESS lineage; Pillar 4 is reworded around the governing sentence of the player role (research/INTERFACE_INSPIRATION.md, commitment C1), and Pillar 5 is added because the product is a game (DEOS section 1.1). Each pillar states what it commits the specification to and what the player perceives because of it.

### Pillar 1: Deep Substrate Physics
The world is constructed of fundamental matter, energy, and entropy dynamics. Ecosystems and biomes form because temperature, moisture, and chemical energy flow strictly according to conservation laws evaluated in Q32.32 on the Substrate grid every tick (DEOS section 5.2, Stage 2). Nothing above the Substrate is exempt from it: an agent's metabolism draws from a Cell's `energy` field, and an Institution's pooled energy is energy that left Cells.

Commitments:
1. Every unit of energy in the world is accounted for by the Core conservation laws; no system creates or destroys energy outside them.
2. Climate and resource distribution are outputs of Substrate constants and Catalyst Actions on Cell fields, never of authored maps.

Player-facing consequence: a drought the player causes with a Climate Catalyst Action is a real shortfall in Cell energy that agents, tribes, and Institutions must survive, and the Chronicle records who did not.

### Pillar 2: Autonomous Cognition & Meme-Vectors
Agents possess utility-driven decision-making models. They do not follow fixed decision trees. Knowledge, culture, and beliefs are represented as quantitative **Meme-Vectors** (`MEME_DIM` = 32 Q32.32 values) that mutate and transmit through social interaction in Stage 5.

Commitments:
1. Every action an agent takes is the highest-utility action under its `Needs` weights, `Genome`, `Memory`, and `MemeVector` at that tick; ties are broken by the deterministic ordering rules of DEOS-Core.
2. Every decision writes a Decision Trace (Directive 11, GI-5).

Player-facing consequence: the player can open any agent and read which three needs drove its last action, with signed weights, and watch beliefs spread across a population as a visible change in the Network Map.

### Pillar 3: Massive Scalability
The architecture prioritizes data layout and CPU cache alignment. Simulation algorithms are vectorizable and scale linearly across multi-core systems: entities are processed in Chunks of `CHUNK_SIZE` = 1,024 slots, one worker thread per Chunk per stage, with zero heap allocation inside the tick.

Commitments:
1. `MAX_ENTITIES` (1,048,576) at v1.0 scale within `TICK_BUDGET_MS` (16.6) per tick; 16,384 at MVS scale.
2. Thread count changes throughput only; it never changes a Tick Hash (GI-1, GI-4).

Player-facing consequence: a world of a million agents runs at speed 1× on a desktop, and an Epoch of catch-up after a night away completes in under a minute at MVS scale (DEOS-F05).

### Pillar 4: Catalyst Intervention — Shape the Probabilities, Not the People
The player (or Host) does not act as a direct unit commander. The player acts as a **Catalyst**: they shape the probabilities, not the people. The governing sentence has an exact meaning:

1. A Catalyst Action may write Substrate Cell fields (Climate and Resource families), population-level rates (the Cell field `mutation_bias`, Mutation family), MemeVector deltas applied to every agent within a radius, and composite Cosmic events that expand into those same primitive writes in Stage 1 (research/INTERFACE_INSPIRATION.md, commitment C3).
2. A Catalyst Action never writes a `Decision` component, never overrides an agent's action choice, and never addresses a single agent as a unit to be commanded (commitment C1). A whisper changes what agents believe; it never chooses for them.
3. Every Catalyst Action is a 64-byte `CatalystAction` record appended to the Input Log with a cost in Catalyst Budget that scales with magnitude and radius (commitment C4). It is the only channel through which the Host mutates the world (Directive 12, GI-6).
4. Influence is continuous. Payloads are Q32.32 magnitudes set with sliders and regions; there is no discrete "order".

Player-facing consequence: the player's loop is Observe · Influence · Wait · Adapt · History. They warm a coastline, raise mutation in a valley, or seed an idea, then wait to see what the population makes of it; the satisfaction is authorship of conditions, not control of outcomes.

### Pillar 5: Playable Emergence
Legibility, agency, and return hooks are first-class engineering requirements, not presentation-layer polish. An emergent system that the player cannot read, cannot influence, or has no reason to return to has failed regardless of its dynamics.

Commitments:
1. **Legibility.** Every agent decision writes a Decision Trace and every significant change emits a Notable Event (Directive 11, GI-5). The Chronicle is the Kernel's own record, and every Chronicle row drills down through its `cause` field to the Decision Trace that produced it (commitment C6).
2. **Agency.** Every Catalyst Action produces a consequence the player can perceive within the same session, either as a change in the Observation View or as a Notable Event, and the Catalyst Budget that paces it is displayed, deterministic, and regenerates as a function of simulated ticks (GI-8).
3. **Return hooks.** Shareable worlds, verified challenges, the Chronicle, offline catch-up, and Seed Lineage are each a property of determinism (DEOS-F01 section 3.4) and each is a reason to come back. The DEOS-F05 Playability Metrics make the hooks measurable.
4. **Ethics.** Retention comes from novelty and agency. No hidden timers, no purchasable advantage that alters simulation outcomes, no scarcity the Catalyst Budget does not display (GI-8).

Player-facing consequence: within 90 real seconds of a fresh world the player has seen something notable happen and can read why; within the first simulated ten days in most seeds an Institution has formed that they can name, watch, and share.

---

## 2. Pillar Ownership

| Pillar | Primary module | Invariants satisfied |
| :--- | :--- | :--- |
| 1. Deep Substrate Physics | DEOS-Core | GI-1, GI-7 |
| 2. Autonomous Cognition & Meme-Vectors | DEOS-Protocol | GI-5, GI-7 |
| 3. Massive Scalability | DEOS-ECS, DEOS-Runtime | GI-1, GI-4 |
| 4. Catalyst Intervention | DEOS-Play (`CAT`), DEOS-Runtime (ingress) | GI-2, GI-6 |
| 5. Playable Emergence | DEOS-Play, DEOS-Protocol (`EVT`) | GI-5, GI-8 |

A proposed change that weakens any pillar is scored under DEOS-F06 before it is considered; a change that removes a pillar's commitment is rejected without scoring.

---

## 3. Revision History
| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 (EESS) | 2026-07-20 | Initial Baseline Specification (lineage) | EE Arch Team |
| v0.1.0 (DEOS) | 2026-09-12 | Rebranded to DEOS-F03; Pillar 4 reworded around "shape the probabilities, not the people"; Pillar 5 Playable Emergence added; diagram widened to five columns; supersedes EESS-0003 | DEOS Arch Team |
