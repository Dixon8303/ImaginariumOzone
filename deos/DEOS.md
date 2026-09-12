> **DEOS-v0.1.0**
> **Title:** Deterministic Emergence Operating Specification
> **Status:** Draft / Active Specification
> **Reference Implementation:** Emergence: The Digital Rise
> **Repository:** DEOS: Emergence
> **Supersedes:** Emergence Engine Software Specification (EESS) v0.1.0

# DEOS — Deterministic Emergence Operating Specification

| Metadata | Value |
| :--- | :--- |
| **Document ID** | DEOS |
| **Semantic Version** | v0.1.0 |
| **Status** | Draft |
| **Dependencies** | None (root) |
| **Supersedes** | EESS README §1–§4, EESS-1000 milestone definition |

---

## 0. How to read this repository

1. This document. It is the binding contract: identity, hierarchy, identifiers, vocabulary, shared registry, and the invariants every module must satisfy.
2. `docs/00_Foundation/` — vision, principles, pillars, glossary, success criteria, decision rubric.
3. The six module specifications in dependency order: Core → ECS → Runtime → Protocol → Play → MVS.
4. `docs/architecture/` — the dependency graph and requirement traceability matrix generated from the modules.

A module may cite only this document, the Foundation, and modules above it in the order. Nothing cites DEOS-Play except DEOS-MVS.

---

## 1. Identity

**DEOS** is the engineering specification for a deterministic, data-oriented emergence substrate. ***Emergence: The Digital Rise*** is the game built on it. The repository is named **DEOS: Emergence** because the two are inseparable by design.

### 1.1 The product is a game

DEOS is written to be implemented. Emergence is written to be played, compulsively, for months. Every module in this hierarchy therefore carries player-facing requirements alongside engineering ones, and every mechanism must state what the player perceives, does, or returns for.

Determinism is not engineering hygiene here. It is the product. The game's signature features are direct consequences of bitwise reproducibility:

| Determinism provides | The game sells it as |
| :--- | :--- |
| `world(t) = F(MasterSeed, InputLog[0..t])` | **Shareable worlds.** A 64-bit seed plus an Input Log reproduces any world on any device. "Try seed 9F3A-…; a religion forms by day 40." |
| A Tick Hash every tick, Checkpoints every 64 | **Verified challenges and leaderboards.** A submission is an Input Log; the verifier re-simulates it. Cheating is structurally impossible. |
| Pure functions of prior state | **The Chronicle.** Rewind, replay, and ask "how did this war start?" from any Snapshot. |
| Tick count decoupled from wall-clock | **Offline catch-up.** Leave overnight; return to an Epoch of real consequences that actually happened, not a lookup-table payout. |
| Utility-scored decisions with Decision Traces | **Legibility.** The player can always see *why* an agent, tribe, or institution did what it did. Emergence you cannot read is noise; emergence you can read is a story you want to keep reading. |

### 1.2 What DEOS is not

- Not a general game engine. No rendering, audio, input, or UI is specified below the Host boundary.
- Not a content pipeline. There are no quests, scripts, unit lists, or stat tables. Behavior is computed from substrate laws and Protocol rules (Directive 1, Directive 10).
- Not a floating-point system. `float` and `double` do not exist inside the Kernel.

---

## 2. Specification Hierarchy

```
DEOS (Deterministic Emergence Operating Specification)
 ├── DEOS-Foundation  Vision · Principles · Pillars · Glossary · Success Criteria · Decision Framework
 ├── DEOS-Core        Mathematical Foundations & Fixed-Tick Rules
 ├── DEOS-ECS         Data Schemas & Entity-Component Architecture
 ├── DEOS-Runtime     Simulation Loop, Threading & State Hashing
 ├── DEOS-Protocol    Agent Cognition, Society Models & Inter-entity Rules
 ├── DEOS-Play        Player Loop, Catalyst Interface, Chronicle & Retention Systems
 └── DEOS-MVS         Minimum Viable Simulation: the first playable, verifiable build
```

**DEOS-Play is the addition relative to the four-module proposal.** Four engineering modules describe a substrate. Without a fifth, the specification has no owner for the questions that decide whether anyone plays: what the player does, what they see, and why they come back. Play sits below Protocol because it consumes Protocol's events and shapes Protocol's pacing thresholds; it sits above MVS because the first build must be playable, not merely correct.

### 2.1 Module registry

| Module | Document ID | Path | Owns | Status |
| :--- | :--- | :--- | :--- | :--- |
| DEOS-Foundation | DEOS-F01 … DEOS-F06 | `docs/00_Foundation/` | identity, terminology, rubric, acceptance metrics | Approved (v0.1.0) |
| DEOS-Core | DEOS-CORE | `docs/01_Core/DEOS-Core.md` | Q32.32 arithmetic, transcendental tables, conservation laws, fixed-tick integration, PRNG streams and seed hierarchy, deterministic ordering and tie-break rules | Draft |
| DEOS-ECS | DEOS-ECS | `docs/02_ECS/DEOS-ECS.md` | EntityID layout, the canonical component catalog with exact layouts, memory pools and alignment, state mutation rules, command buffers, entity lifecycle | Draft |
| DEOS-Runtime | DEOS-RT | `docs/03_Runtime/DEOS-Runtime.md` | Kernel/Host boundary and C ABI, six-stage tick pipeline, threading and chunk dispatch, Tick Hash and desync detection, Snapshots, replay, Acceleration, egress | Draft |
| DEOS-Protocol | DEOS-PROTO | `docs/04_Protocol/DEOS-Protocol.md` | perception → utility → action model, memory, Meme-Vectors and transmission, trust networks, Institutions, technology discovery, cross-layer coupling, Notable Event taxonomy | Draft |
| DEOS-Play | DEOS-PLAY | `docs/05_Play/DEOS-Play.md` | core and meta loops, Catalyst interface and Budget, Chronicle presentation, sessions and offline catch-up, challenges and Seed Lineage, retention metrics, engagement ethics | Draft |
| DEOS-MVS | DEOS-MVS | `docs/06_Prototype/DEOS-MVS.md` | scope, acceptance criteria, and benchmarks of the first playable, verifiable build | Draft |

### 2.2 Dependency order

```
DEOS ─► Foundation ─► Core ─► ECS ─► Runtime ─► Protocol ─► Play ─► MVS
```

Protocol references the ECS component catalog by name. Play references the Protocol event taxonomy by name. MVS references all of them. Reverse references are prohibited; a lower module that needs something from a higher one proposes it in §5 of this document via an ADR.

---

## 3. Identifier Scheme

### 3.1 Document IDs

| Pattern | Meaning | Example |
| :--- | :--- | :--- |
| `DEOS` | this root document | — |
| `DEOS-F0n` | Foundation document *n* | `DEOS-F04` (Glossary) |
| `DEOS-CORE`, `DEOS-ECS`, `DEOS-RT`, `DEOS-PROTO`, `DEOS-PLAY`, `DEOS-MVS` | module specification | `DEOS-RT` |
| `DEOS-1.0` | Blueprint Complete milestone | — |
| `ADR-nnnn` | Architecture Decision Record | `ADR-0001` |

**EESS → DEOS lineage.** The EESS IDs below are retired. They may appear only in `Supersedes` metadata rows, in `CHANGELOG.md`, and in this table.

| EESS | DEOS | Disposition |
| :--- | :--- | :--- |
| EESS-0001 Vision | DEOS-F01 | migrated; §3.1 rewritten for the game-first identity |
| EESS-0002 Core Principles | DEOS-F02 | migrated |
| EESS-0003 Design Pillars | DEOS-F03 | migrated; Pillar 5 (Playable Emergence) added |
| EESS-0004 Glossary | DEOS-F04 | migrated; §4 terms below mirrored in |
| EESS-0005 Success Criteria | DEOS-F05 | migrated; playability metrics added |
| EESS-0006 Decision Framework | DEOS-F06 | migrated; rubric metric 6 (Player Legibility & Engagement) added |
| EESS-0101 Physics & Conservation | DEOS-CORE | absorbed |
| EESS-0201 Simulation Mathematics | DEOS-CORE | absorbed |
| EESS-0301 System Architecture | DEOS-RT | absorbed |
| EESS-0401 Entity Component Model | DEOS-ECS | absorbed |
| EESS-0501 Simulation Loop | DEOS-RT | absorbed |
| EESS-0601 Data & Memory Layout | DEOS-ECS | absorbed |
| EESS-0701 Prototype / MVS | DEOS-MVS | absorbed |
| EESS-1000 Foundation Complete | DEOS-1.0 | renamed |

### 3.2 Requirement IDs

Format: `REQ-<PREFIX>-nnn`. A requirement is **defined** exactly once, as a level-3 or level-4 Markdown heading of the form `### REQ-PREFIX-nnn: Title`, inside the module that owns the prefix. Everywhere else it is a reference. IDs are never renumbered or reused; a withdrawn requirement keeps its ID with status *Withdrawn*.

| Prefix | Module | Domain |
| :--- | :--- | :--- |
| `LAW` | Core | conservation and universal laws |
| `MATH` | Core | Q32.32 arithmetic and function tables |
| `PRNG` | Core | random streams and the seed hierarchy |
| `TICK` | Core | fixed-tick time and integration |
| `ORD` | Core | deterministic ordering and tie-break rules |
| `ENT` | ECS | entity identity and lifecycle |
| `CMP` | ECS | component catalog and layouts |
| `DAT` | ECS | memory layout, pools, alignment |
| `MUT` | ECS | state mutation and command buffers |
| `ARCH` | Runtime | Kernel/Host boundary and ABI |
| `LOOP` | Runtime | tick pipeline |
| `THR` | Runtime | threading and chunk dispatch |
| `HASH` | Runtime | Tick Hash, Checkpoints, desync detection |
| `SNAP` | Runtime | Snapshots, replay, Acceleration |
| `COG` | Protocol | perception, utility, action, memory |
| `SOC` | Protocol | Meme-Vectors, trust, Institutions, technology |
| `XL` | Protocol | cross-layer coupling |
| `EVT` | Protocol | Notable Event taxonomy |
| `PLAY` | Play | core and meta loops, retention |
| `CAT` | Play | Catalyst interface and Budget |
| `SES` | Play | sessions, offline catch-up, sharing, challenges |
| `MVS` | MVS | prototype scope and acceptance |

Existing EESS requirements (`REQ-LAW-001…003`, `REQ-MATH-001…004`, `REQ-ARCH-001…002`, `REQ-ENT-001…003`, `REQ-LOOP-001`, `REQ-DAT-001…002`) keep their IDs and meaning. They may be tightened; they may not be contradicted. New requirements continue the numbering.

---

## 4. Canonical Vocabulary (delta to DEOS-F04)

These terms are canonical from this document forward and are mirrored into the Glossary. Banned synonyms carry the same force as in the existing glossary.

| Term | Definition | Banned synonyms |
| :--- | :--- | :--- |
| **Master Seed** | The 64-bit unsigned integer from which every PRNG stream in a world is derived. With the Input Log it fully determines the world. | world seed, random seed, map seed |
| **Input Log** | The ordered, append-only sequence of Catalyst Actions and host commands, each stamped with the tick at which it takes effect. `world(t) = F(MasterSeed, InputLog[0..t])`. The Input Log *is* the save file. | replay file, command history, save game |
| **Catalyst Budget** | The player's spendable, regenerating pool of catalyst energy. A pacing valve, never a paywall: regeneration is a visible, deterministic function of simulated ticks. | mana, action points, unqualified "energy" (collides with substrate energy) |
| **Tick Hash** | Refines *State Hash*: the BLAKE3-256 digest of the write buffer at the end of a tick, computed as the Merkle root over Chunk Hashes. | checksum, world hash |
| **Chunk** | A contiguous slice of `CHUNK_SIZE` entity slots processed by exactly one worker thread per stage. The unit of parallelism and of hashing. | batch, block, partition |
| **Chunk Hash** | BLAKE3-256 of one Chunk's component data at end of tick. The leaves of the Tick Hash tree; they localize a Desync. | — |
| **Checkpoint** | A Tick Hash recorded in the Input Log every `CHECKPOINT_INTERVAL` ticks so replays and challenge submissions verify incrementally. | — |
| **Snapshot** | A complete, versioned serialization of both state buffers, all PRNG stream counters, and the Input Log cursor at a tick boundary. Restoring a Snapshot and stepping yields Tick Hashes identical to the original run. | save state, memento |
| **Desync** | A Tick Hash mismatch between two executions of the same (Master Seed, Input Log) prefix. Always a defect; never tolerated silently. | drift, divergence |
| **Chronicle** | The append-only stream of Notable Events emitted by the Kernel each tick, and the game's presentation of that stream as history the player reads, rewinds, and shares. | event log, news feed, history tab |
| **Notable Event** | A typed, fixed-size record emitted by a Protocol system when a significance threshold is crossed. A birth is not notable; the first birth in a founded settlement is. Kinds are enumerated in DEOS-PROTO. | event (unqualified), message, notification |
| **Decision Trace** | The fixed-size record written with every agent decision: the chosen action and the top three utility contributors with signed weights. The source of legibility. | debug info, reasoning |
| **Institution** | A Cultural-archetype entity that pools energy, holds a policy Meme-Vector, and has members through Affiliation components. Tribes, guilds, temples, and states are Institutions with different policy vectors, not different code. | faction, guild class, nation object |
| **Epoch** | A player-facing span of `TICKS_PER_EPOCH` simulated ticks. At its boundary the Chronicle produces a summary and the meta loop advances. | era, chapter, season (reserved for climate) |
| **Seed Lineage** | The parent–child relation between a world and any world started from its Snapshot or shared seed; the unit of the sharing and prestige meta loop. | — |
| **Acceleration** | Headless stepping of the Kernel with egress disabled, used for offline catch-up. Produces Tick Hashes identical to real-time stepping. | fast-forward, turbo, skip |
| **Substrate** | The environment grid together with the physical laws that govern it (Stage 2). Not an entity. | terrain, map, unqualified "world" |
| **Cell** | One node of the Substrate grid, addressed by `(x, y)`. Holds SoA fields, not components. | tile, hex, voxel |
| **Kernel** | Short form of *EE Kernel* (DEOS-F04). | — |
| **Host** | Short form of *Host Application* (DEOS-F04). | — |

---

## 5. Shared Registry

Every module uses these names verbatim. A module that needs a new shared name proposes it here through an ADR; it does not coin a local synonym.

### 5.1 Constants

Defaults. The owning module may tighten a value with justification; no module may contradict one.

| Constant | Value | Owner | Note |
| :--- | :--- | :--- | :--- |
| `FIXED_FORMAT` | Q32.32 in `int64_t` | Core | REQ-MATH-001 |
| `TICK_RATE_HZ` | 60 | Core | simulated ticks per real second at speed 1× |
| `TICK_BUDGET_MS` | 16.6 | Runtime | per tick at `MAX_ENTITIES` (v1.0 scale) |
| `CHUNK_SIZE` | 1,024 entities | ECS | |
| `CACHE_LINE` | 64 bytes | ECS | REQ-DAT-001 |
| `MAX_ENTITIES` | 2^20 (1,048,576) at v1.0 scale; 2^14 (16,384) at MVS scale | ECS | the index field permits 2^32 |
| `GRID_W`, `GRID_H` | 256 × 256 at MVS; 1,024 × 1,024 at v1.0 | Core | |
| `MEME_DIM` | 32 | Protocol | |
| `NEED_COUNT` | 8 | Protocol | |
| `MEMORY_SLOTS` | 16 | Protocol | ring buffer per agent |
| `TRUST_EDGES` | 8 | Protocol | fixed fan-out per agent |
| `PERCEPTION_RADIUS` | 4 cells | Protocol | |
| `CHECKPOINT_INTERVAL` | 64 ticks | Runtime | |
| `SNAPSHOT_INTERVAL` | 3,600 ticks | Runtime | one simulated day |
| `TICKS_PER_DAY` | 3,600 | Play | one real minute at speed 1× |
| `TICKS_PER_EPOCH` | 108,000 | Play | 30 simulated days; 30 real minutes at 1× |
| `SPEED_LEVELS` | {1, 4, 16, 64} | Play | real-time multipliers during attended play |
| `OFFLINE_RATE` | 1/16 of real time | Play | 8 real hours away = 1 Epoch of simulated time |
| `MAX_OFFLINE_TICKS` | 3 × `TICKS_PER_EPOCH` | Play | catch-up ceiling per absence |
| `MIN_ACCELERATION` | 32× real time at MVS scale | Runtime | 1,920 ticks per second; consistent with the MVS benchmark |
| `HASH` | BLAKE3-256 | Runtime | |
| `PRNG` | PCG64 (XSL-RR 128/64) | Core | one stream per (system, tick, chunk) |

Derived consistency checks: at MVS scale, one Epoch of catch-up (108,000 ticks) at `MIN_ACCELERATION` takes 56.25 s of compute; the MVS benchmark (10,000 ticks in under 5.0 s) is 33.3×; `MAX_OFFLINE_TICKS` at `MIN_ACCELERATION` is under 3 minutes and is therefore always streamed into the Chronicle incrementally rather than blocked on a loading screen (DEOS-PLAY).

### 5.2 Tick pipeline

Fixed. DEOS-Runtime owns the details; DEOS-ECS owns the command-buffer resolution rule at each stage barrier.

```
Stage 1  Ingress     apply Input Log entries stamped for this tick, in (tick, seq) order
Stage 2  Substrate   conservation, diffusion, thermodynamics, material decay          (Core laws)
Stage 3  Biology     metabolism, Lifecycle, reproduction, Genome inheritance          (Protocol)
Stage 4  Cognition   Perception, utility scoring, Decision + Decision Trace, Memory   (Protocol)
Stage 5  Society     Meme-Vector transmission, trust, Institutions, technology        (Protocol)
Stage 6  Commit      final command resolution → Chunk Hashes → Tick Hash → Chronicle flush → buffer swap → egress
```

Each stage ends with a barrier. Cross-entity writes issued during a stage are resolved at that stage's barrier in canonical order (DEOS-ECS, `MUT`), so every later stage reads a consistent buffer.

### 5.3 Canonical component catalog

Names and owners are fixed here; DEOS-ECS specifies exact layouts, and DEOS-Protocol specifies update rules.

| Component | Archetype | Written in stage | Purpose |
| :--- | :--- | :--- | :--- |
| `Position2D` | Physical | 4 | `x`, `y` in Q32.32 Cell units; an entity writes only its own slot |
| `EnergyState` | Biological | 3 | current, max capacity, metabolic rate |
| `Lifecycle` | Biological | 3 | age, generation, alive flag, death cause |
| `Genome` | Biological | 3 (at reproduction) | fixed gene array; parameterizes metabolism and utility weights |
| `Needs` | Cognitive | 3 (levels), 4 (weights) | `NEED_COUNT` levels and weights |
| `Perception` | Cognitive | 4 | fixed-size summary of sensed Cells and neighbours within `PERCEPTION_RADIUS` |
| `Memory` | Cognitive | 4 | `MEMORY_SLOTS` ring of past outcomes |
| `Decision` | Cognitive | 4 | chosen action plus Decision Trace |
| `MemeVector` | Cultural | 5 | `MEME_DIM` beliefs and knowledge |
| `TrustEdges` | Cultural | 5 | `TRUST_EDGES` (EntityID, weight) pairs |
| `Affiliation` | Cultural | 5 | Institution EntityID and role |
| `InstitutionState` | Institutional | 5 | pooled energy, member count, policy MemeVector, founding tick |

Substrate Cell fields (SoA arrays, not components): `energy`, `temperature`, `moisture`, `elevation`, `material_id`.

Archetype tags: `0x01` Physical · `0x02` Biological · `0x04` Cognitive · `0x08` Cultural · `0x10` Institutional.

### 5.4 Shared record headers

Exact field order is binding; the owning module may only append reserved padding.

| Record | Layout | Kinds owned by | Ordering owned by |
| :--- | :--- | :--- | :--- |
| `CatalystAction` | `{ tick: u64, seq: u32, kind: u16, target_kind: u8, pad: u8, target: u64, payload: [4] Q32.32, cost: Q32.32 }` — 64 bytes | Play (`CAT`) | Runtime (`LOOP`) |
| `NotableEvent` | `{ tick: u64, kind: u16, pad: u16, cell: u32, subject: EntityID, object: EntityID, magnitude: Q32.32, cause: u32, pad: u32 }` — 48 bytes, stored in 64-byte slots | Protocol (`EVT`) | Runtime (`LOOP`) |
| `DecisionTrace` | `{ action: u16, pad: u16, contributors: [3] { need: u8, pad: [3] u8, weight: Q32.32 } }` — 40 bytes | Protocol (`COG`) | — |
| `Checkpoint` | `{ tick: u64, tick_hash: [32] u8 }` — 40 bytes | Runtime (`HASH`) | Runtime |

`target_kind` ∈ { 0 = global, 1 = Cell, 2 = entity }. `EntityID` is the 64-bit packed identifier of REQ-ENT-001. `cause` is the index of the Decision Trace that produced the event, or 0.

---

## 6. Game-Facing Invariants

Every module must satisfy every invariant that names it. A verifier may reject a module for violating one even when the module's own requirements are internally consistent.

| ID | Invariant | Enforced by |
| :--- | :--- | :--- |
| **GI-1 Reproducibility** | `world(t) = F(MasterSeed, InputLog[0..t])`, bitwise, on every supported platform. | Core, ECS, Runtime |
| **GI-2 The log is the save** | A world persists as (Master Seed, Input Log, optional Snapshot). Nothing else is needed to restore it. | Runtime, Play |
| **GI-3 Verifiable history** | A Checkpoint every `CHECKPOINT_INTERVAL` ticks; any prefix of a run can be verified by re-simulation from the nearest Snapshot. | Runtime |
| **GI-4 Time is decoupled** | Simulated time is a tick count. Wall-clock never enters the Kernel. Acceleration produces the same Tick Hashes as attended play. | Core, Runtime |
| **GI-5 Legibility** | Every agent decision writes a Decision Trace; every significant state change emits a Notable Event. The player can always answer "why did that happen?" | Protocol, Play |
| **GI-6 Host isolation** | The Host reads the read-only buffer and the Chronicle. It mutates the world only through Catalyst Actions in the Input Log. | Runtime, Play |
| **GI-7 Emergence over script** | No outcome is scripted. Pacing is tuned through Substrate constants and Protocol thresholds, never through special-case code (Directive 10). | Protocol, Play |
| **GI-8 Engagement without deception** | Retention comes from novelty and agency. No hidden timers; no purchasable advantage that alters simulation outcomes; no scarcity the Catalyst Budget does not display. | Play |

---

## 7. Conformance

An implementation is **DEOS-conformant** when it passes all of:

| Gate | Evidence |
| :--- | :--- |
| Core determinism vectors | published (input → output) vectors for every Q32.32 operation, table function, and PRNG draw |
| ECS zero-allocation and alignment | allocation counter reads 0 across a full tick; every array is 64-byte aligned |
| Runtime hash parity | identical Tick Hash sequences on x86-64 and ARM64 for the MVS run |
| Protocol legibility | every `Decision` carries a `DecisionTrace`; Notable Event cadence within DEOS-PLAY targets |
| MVS acceptance | the DEOS-MVS acceptance run passes on baseline hardware |

Test names are registered in `docs/architecture/REQUIREMENT_TRACEABILITY_MATRIX.md`. `tools/spec_lint.py` enforces the identifier rules of §3 across the repository and must pass before any specification change merges.

---

## 8. Revision History

| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 | 2026-09-12 | Initial DEOS root specification; supersedes EESS v0.1.0 | DEOS Arch Team |
