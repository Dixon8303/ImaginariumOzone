# Specification: Project Glossary & Terminology (DEOS-F04)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | DEOS-F04 |
| **Semantic Version** | v0.1.0 |
| **Status** | Approved |
| **Dependencies** | DEOS, DEOS-F01 |
| **Supersedes** | EESS-0004 |

---

## 1. Terminology Standard

This table is the single canonical vocabulary of the repository. Section 1.1 carries the EESS baseline forward; section 1.2 mirrors every term of DEOS section 4 with the same definition and the same banned synonyms. A term is used verbatim everywhere it appears; a banned synonym in a normative sentence is a defect (CONTRIBUTING.md Rule 1). Where a term in section 1.1 is refined by a term in section 1.2, the row says so and the section 1.2 term governs.

### 1.1 Baseline terms

| Term | Canonical Definition | Banned / Obsolete Synonyms |
| :--- | :--- | :--- |
| **Entity** | A pure 64-bit numerical identifier representing a discrete object in the world. Holds no data or methods directly. | Object, Actor, Unit, GameObject |
| **Component** | A contiguous, plain-old-data (POD) struct stored in flat arrays representing specific state properties. | Attribute object, Class property |
| **System** | A stateless execution function that queries matching components and transforms their state deterministically. | Manager, Controller, Handler |
| **Tick** | A single discrete atomic step of simulation time ($\Delta t = 1$). | Frame, Turn, Update Step |
| **EE Kernel** | The headless, graphics-free, deterministic simulation runtime engine. Short form: *Kernel* (section 1.2). | Game Core, Backend, Engine Core |
| **Host Application**| The client wrapper (*Emergence: The Digital Rise*) handling UI, rendering, and audio. Short form: *Host* (section 1.2). | Game Frontend, Client GUI |
| **Flux ($\Phi$)** | The scalar rate of energy/information transfer between two entities or spatial nodes per tick. | Flow rate, Transfer rate |
| **Progress ($P$)** | The cumulative state transformation metric of a complex system node over time. | Experience, Development Value |
| **Meme-Vector** | A fixed-size array of `MEME_DIM` fixed-point values representing cultural concepts, beliefs, or technological ideas. Stored as the `MemeVector` component. | Culture variable, Idea stat |
| **Catalyst Action**| A direct injection of energy, information, or environmental change by the user/host application, recorded as a 64-byte `CatalystAction` record in the Input Log (DEOS section 5.4). | Player move, God power, Spell |
| **State Hash** | A 256-bit cryptographic digest (BLAKE3) of all entity component data at the end of a tick. Refined by **Tick Hash** (section 1.2), which fixes the digest as the Merkle root over Chunk Hashes; new text uses *Tick Hash*. | World checksum, Save hash |
| **Fixed-Point Q32.32**| A 64-bit signed integer representation using 32 bits for integer and 32 bits for fractional parts. | Float, Double |

### 1.2 Terms canonical from DEOS section 4

| Term | Canonical Definition | Banned / Obsolete Synonyms |
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
| **Kernel** | Short form of *EE Kernel* (section 1.1). | — |
| **Host** | Short form of *Host Application* (section 1.1). | — |

### 1.3 Player-loop and interface vocabulary

These names come from research/INTERFACE_INSPIRATION.md section C and are canonical wherever a module names the player loop or a Host region. They are listed here so that no module coins an alternative; their mechanics are owned by DEOS-Play (loop, regions) and DEOS-Protocol (World Phase thresholds).

| Term | Canonical Definition | Banned / Obsolete Synonyms |
| :--- | :--- | :--- |
| **Catalyst** | The player's role: an agent of indirect influence who shapes the probabilities, not the people. A Catalyst issues Catalyst Actions and never commands an individual entity (commitment C1). | ruler, god, commander, player character |
| **Observe · Influence · Wait · Adapt · History** | The five verbs of the core loop (commitment C2). The Host's primary regions map one-to-one: Observation View, Catalyst Palette, Time Control, Chronicle. | look/act/skip, turn phases, any other verb set for these regions |
| **Catalyst Palette** | The Host region holding the four Catalyst Action families: Climate, Resource, Mutation, Cosmic (commitment C3). | spellbook, power menu, toolbar |
| **Observation View** | The Host region rendering the read-only buffer through three layers: Particles, Living Diagram, Network Map (commitment C7). | map view, minimap, viewport (unqualified) |
| **World Phase** | The player-facing progression ladder Reality → Life → Society → Intelligence (indices 1 to 4), with Player Interaction as the constant fifth; reached when a threshold Notable Event first occurs and marked by reserved kind 6 `WORLD_PHASE_REACHED` (DEOS-F01 section 3.5, commitment C5). | age, tier, level, stage (reserved for the tick pipeline) |
| **Affective Signals** | The per-tick `WorldMood` record (population, institutions, cooperation, conflict, growth, entropy) emitted through egress in Stage 6, which the Host maps to harmony and dissonance (commitment C8). | mood meter, vibe, soundtrack state |

---

## 2. Usage Rules

1. A term in bold in sections 1.1 through 1.3 is written with the capitalization shown wherever it carries its canonical meaning; lowercase use of the same word in its ordinary English sense is permitted only where no canonical meaning could be read into it.
2. "Stage" followed by a number 1 to 6 always means a tick pipeline stage (DEOS section 5.2). "Phase" always means a World Phase or a ROADMAP phase, never a pipeline stage.
3. "Energy" without a qualifier means Substrate or entity energy in Q32.32; the player's pool is always *Catalyst Budget*.
4. Registry constants are written in backticks with their registry name (`TICKS_PER_DAY`), never as a bare number in normative text unless the name accompanies it.
5. `tools/spec_lint.py` warns on the high-signal banned synonyms of this table; a warning is a defect to fix before merge even though it does not fail the run.

Player-facing consequence: the words the player reads in the Host (Chronicle, Catalyst Budget, Epoch, World Phase, Seed Lineage) are the same words the specification and the code use, so a challenge description, a bug report, and a Kernel record all name the same thing.

---

## 3. Revision History
| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 (EESS) | 2026-07-20 | Canonical terminology baseline (lineage) | EE Arch Team |
| v0.1.0 (DEOS) | 2026-09-12 | Rebranded to DEOS-F04; DEOS section 4 terms mirrored in; State Hash refined to Tick Hash; player-loop and interface vocabulary added; usage rules added; supersedes EESS-0004 | DEOS Arch Team |
