# Specification: Vision Document (DEOS-F01)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | DEOS-F01 |
| **Semantic Version** | v0.1.0 |
| **Status** | Approved |
| **Dependencies** | DEOS |
| **Supersedes** | EESS-0001 |
| **Author** | DEOS Arch Team |

---

## 1. Purpose
This document defines the mission, philosophy, and identity of **DEOS** (the Deterministic Emergence Operating Specification) and of ***Emergence: The Digital Rise***, the game built on it. It is the first Foundation document and the one every other document in the hierarchy inherits its identity from (DEOS section 1).

---

## 2. Scope
Applies to every document under `deos/`: the root contract, the six Foundation documents, the six module specifications (DEOS-CORE, DEOS-ECS, DEOS-RT, DEOS-PROTO, DEOS-PLAY, DEOS-MVS), the generated architecture documents, the templates, the test plan, and the tooling. Anything that contradicts this document is wrong by definition until this document is revised.

---

## 3. Vision & Philosophy

### 3.1 The Substrate Is Research-Grade and the Product Is a Game
DEOS specifies a deterministic artificial-life substrate: the fundamental laws of energy, thermodynamics, genetics, cognition, and society, implemented in Q32.32 fixed-point arithmetic inside a headless Kernel. That substrate is research-grade. Two conforming implementations, on x86-64 and ARM64, with one worker thread or four, attended or in Acceleration, produce identical Tick Hashes for the same Master Seed and Input Log.

*Emergence: The Digital Rise* is not a demonstration of that substrate. It is the product. The two are inseparable by design (DEOS section 1), and the repository is named **DEOS: Emergence** for that reason:

1. The substrate exists so that the game can be played, compulsively, for months. Every module therefore carries player-facing requirements next to engineering ones, and every mechanism states what the player perceives, does, or returns for.
2. The game exists as the reference implementation that proves the substrate. A feature of the game that cannot be expressed as a Catalyst Action in the Input Log, or read back out of the Chronicle, does not exist.
3. Determinism is the product, not engineering hygiene. Section 3.4 states what that means for the player.

Player-facing consequence: the player is never shown a system that is "under the hood"; every law of the substrate is something they can perturb with a Catalyst Action and read back as a Notable Event.

### 3.2 Systems Over Content
Traditional games rely on hand-authored content (quests, scripted trees, static stat tables). DEOS relies entirely on **system interactions**. Complex behaviors (migration, dynamic trade, religion, war, biological adaptation) must emerge strictly from Substrate laws and Protocol rules. Pacing is tuned through Substrate constants and Protocol thresholds, never through special-case code (Directive 10, GI-7).

Player-facing consequence: no two worlds tell the same story, and no story the player reads in the Chronicle was written by a designer.

### 3.3 Research-Grade Determinism
Every execution of the Kernel with the same Master Seed and Input Log prefix yields bitwise-identical state on all supported hardware (x86-64, ARM64), at every thread count, and in Acceleration. The evidence is the Tick Hash: a BLAKE3-256 digest of the write buffer at the end of every tick, recorded as a Checkpoint every `CHECKPOINT_INTERVAL` ticks. A Tick Hash mismatch is a Desync, which is always a defect and never tolerated silently (GI-1, GI-3, GI-4).

### 3.4 Determinism as Product
The signature features of *Emergence: The Digital Rise* are direct consequences of bitwise reproducibility. The five rows of the DEOS section 1.1 table read, as design commitments:

1. **Shareable worlds.** Because `world(t) = F(MasterSeed, InputLog[0..t])`, a 64-bit Master Seed together with an Input Log reproduces any world on any device. A player who says "try seed 9F3A-…; a religion forms by day 40" is making a claim that every other player can verify by simply running it. Seed Lineage, the parent-child relation between a world and any world started from its Snapshot or shared seed, is the unit of the sharing meta loop.
2. **Verified challenges and leaderboards.** Because a Tick Hash is computed every tick and a Checkpoint is written every `CHECKPOINT_INTERVAL` ticks, a challenge submission is nothing more than an Input Log. The verifier re-simulates it from the nearest Snapshot and compares Checkpoints. Cheating is structurally impossible: there is no score to forge, only a history to re-run.
3. **The Chronicle.** Because every stage is a pure function of prior state, any Snapshot can be restored and stepped forward to reproduce the same Tick Hashes. The player can rewind, replay, and ask "how did this war start?" from any point in the Chronicle and receive the same answer every time.
4. **Offline catch-up.** Because simulated time is a tick count and wall-clock never enters the Kernel, a player who leaves overnight returns to an Epoch of consequences that actually happened. Acceleration steps the Kernel headlessly at `OFFLINE_RATE`, capped at `MAX_OFFLINE_TICKS`, and produces Tick Hashes identical to attended play. There is no lookup-table payout.
5. **Legibility.** Because every agent decision is a utility score, every decision writes a Decision Trace (the chosen action and its top three contributors with signed weights), and every significant state change emits a Notable Event. The player can always see *why* an agent, tribe, or Institution did what it did. Emergence you cannot read is noise; emergence you can read is a story you want to keep reading.

Player-facing consequence: the reasons to return (a world to share, a challenge to verify, a history to interrogate, an absence to catch up on, a decision to understand) are each a property of the Kernel, not a layer painted over it; the game cannot lose them without breaking determinism.

---

## 4. Primary System Goals
1. **Uncompromised Scale**: Support `MAX_ENTITIES` = 1,048,576 active autonomous entities in a continuous simulation loop at `TICK_RATE_HZ` = 60 within `TICK_BUDGET_MS` = 16.6 per tick.
2. **Deterministic Reproducibility**: Absolute reproducibility for scientific analysis, replay verification, and Acceleration (GI-1 through GI-4).
3. **Deep Emergence**: Interlocking physical, biological, cognitive, and societal loops with zero hardcoded outcome scripts (GI-7).
4. **Compulsive Playability**: A player perceives a Notable Event within 90 real seconds of a fresh world at speed 1×, sees an Institution form by simulated day 10 in at least 80% of seeds, returns to an Epoch of legible consequences after an absence, and can share, verify, and interrogate any world (the DEOS-F05 Playability Metrics). Retention comes from novelty and agency, never from hidden timers or purchasable advantage (GI-8).

---

## 5. Revision History
| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 (EESS) | 2026-07-20 | Initial Foundation Specification release (lineage) | EE Arch Team |
| v0.1.0 (DEOS) | 2026-09-12 | Rebranded to DEOS-F01; section 3.1 rewritten for the game-first identity; section 3.4 Determinism as Product added; goal 4 Compulsive Playability added; supersedes EESS-0001 | DEOS Arch Team |
