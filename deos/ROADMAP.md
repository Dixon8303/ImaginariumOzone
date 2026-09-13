# DEOS: Emergence — Roadmap

This roadmap runs from the specification release (Phase 0) through the first playable build (Phase 1) and the implementation phases that follow. Phases 2 through 6 mirror the World Phase ladder of DEOS-F01 section 3.5 (Reality → Life → Society → Intelligence → Player Interaction), which is also the tick pipeline order and the module order. Every milestone names the artifact or measurement that closes it.

---

## Phase 0: DEOS v0.1 → DEOS-1.0 Blueprint Complete (specification)
> **Goal:** a 100% deterministic, zero-ambiguity engineering specification, with player-facing requirements in every module, before any Kernel code is written.

**v0.1.0 (this release, 2026-09-12)**
- [x] `DEOS.md` root contract: identity, hierarchy, identifier scheme, vocabulary, shared registry, Game-Facing Invariants GI-1 through GI-8, conformance gates.
- [x] `tools/spec_lint.py`: identifier, lineage, placeholder, link, and constant-drift checks.
- [x] Interface and experience commitments C1 through C10 captured in `research/INTERFACE_INSPIRATION.md`.

**Module status toward DEOS-1.0**

| Module | Document | Status | Closes when |
| :--- | :--- | :--- | :--- |
| DEOS-Foundation | DEOS-F01 … DEOS-F06 | [x] Approved v0.1.0 | all six documents carry DEOS IDs, Supersedes rows, and DEOS revision rows |
| DEOS-Core | DEOS-CORE | [ ] Draft | every Q32.32 operation, table function, and PRNG draw has published determinism vectors; ordering rules cover every iteration in the pipeline |
| DEOS-ECS | DEOS-ECS | [ ] Draft | every component of DEOS section 5.3 has an exact layout; pools, alignment, and command-buffer resolution are specified |
| DEOS-Runtime | DEOS-RT | [ ] Draft | the C ABI, six-stage pipeline, Chunk dispatch, Tick Hash, Checkpoint, Snapshot, replay, and Acceleration are specified to the byte |
| DEOS-Protocol | DEOS-PROTO | [ ] Draft | perception, utility, memory, Meme-Vector transmission, trust, Institutions, technology, and the Notable Event taxonomy are specified with thresholds |
| DEOS-Play | DEOS-PLAY | [ ] Draft | core and meta loops, the four Catalyst families, Catalyst Budget, Chronicle presentation, sessions, catch-up, challenges, Seed Lineage, and retention metrics are specified |
| DEOS-MVS | DEOS-MVS | [ ] Draft | scope, seed sample, acceptance criteria, and benchmarks are specified and traceable |

**DEOS-1.0 Blueprint Complete** (milestone tag) requires all of:
- [ ] Every module Approved; `python3 deos/tools/spec_lint.py` reports 0 errors and 0 warnings.
- [ ] `docs/architecture/REQUIREMENT_TRACEABILITY_MATRIX.md` lists every defined requirement with a named test.
- [ ] `docs/architecture/SYSTEM_DEPENDENCY_GRAPH.md` is acyclic and matches DEOS section 2.2.
- [ ] Every mechanism in every module carries a "Player-facing consequence:" sentence (CONTRIBUTING.md Rule 8).
- [ ] The test plan in `tests/` covers TS-SPEC-001 through TS-SPEC-004, TS-BENCH-001 through TS-BENCH-003, and TS-PLAY-001 through TS-PLAY-002.

---

## Phase 1: MVS build (DEOS-MVS)
> **Goal:** the first playable, verifiable build at MVS scale (`MAX_ENTITIES` at 16,384; `GRID_W` × `GRID_H` at 256 × 256).

- [ ] Q32.32 library with the DEOS-Core determinism vectors passing on x86-64 and ARM64.
- [ ] ECS pools and the six-stage pipeline with Chunk dispatch; allocation counter reads 0 across every tick.
- [ ] Tick Hash, Checkpoint every 64 ticks, Snapshot every 3,600 ticks; identical Tick Hash sequences at 1 and 4 threads.
- [ ] Minimal Protocol: metabolism, reproduction, utility scoring with Decision Traces, Meme-Vector transmission, Institution founding.
- [ ] Minimal Play: the four Catalyst families on the Catalyst Palette, Catalyst Budget, Chronicle with cause drill-down, `SPEED_LEVELS`, Acceleration catch-up.
- [ ] DEOS-MVS benchmark: 10,000 ticks in under 5.0 s on baseline hardware; final Tick Hash identical across three runs on each platform.
- [ ] DEOS-F05 Playability Metrics P1 through P6 measured over the seed sample and published.

---

## Phase 2: Kernel v1.x — Reality (DEOS-Core, DEOS-ECS, DEOS-Runtime)
> **Goal:** the Kernel at v1.0 scale.

- [ ] `MAX_ENTITIES` (1,048,576) within `TICK_BUDGET_MS` (16.6); memory footprint under 4.0 GB.
- [ ] Substrate at 1,024 × 1,024 Cells: conservation, diffusion, thermodynamics, material decay, `mutation_bias` decay.
- [ ] Full Snapshot and replay tooling; Desync localization to a Chunk Hash.
- [ ] Published conformance vectors for every Core operation (DEOS section 7).

---

## Phase 3: Life & Society v2.x — Life (DEOS-Protocol, Stages 3–4)
- [ ] Genome inheritance with per-gene mutation under `mutation_bias`.
- [ ] Metabolic state and Lifecycle at v1.0 scale.
- [ ] Perception within `PERCEPTION_RADIUS`, utility scoring over `NEED_COUNT` needs, `MEMORY_SLOTS` ring memory; every Decision carries its Trace.
- [ ] World Phase 2 (Life) reached in ≥ 95 of 100 seed-sample worlds by simulated day 5.

---

## Phase 4: Life & Society v3.x — Society (DEOS-Protocol, Stage 5)
- [ ] Meme-Vector transmission and mutation over `TRUST_EDGES` trust networks.
- [ ] Institutions: founding, membership through `Affiliation`, pooled energy, policy Meme-Vectors, dissolution.
- [ ] Trade and conflict as Institution-level policy outcomes, never special-case code (GI-7).
- [ ] World Phase 3 (Society) reached in ≥ 80 of 100 seed-sample worlds by simulated day 10 (DEOS-F05 P2).

---

## Phase 5: Life & Society v4.x — Intelligence (DEOS-Protocol, technology and cross-layer coupling)
- [ ] Technology discovery from material constraints and Meme-Vector knowledge dimensions.
- [ ] Cross-layer coupling (`XL`): technology alters Substrate flux; Institutions alter climate exposure.
- [ ] `WorldMood` Affective Signals computed at the end of Stage 5 and emitted in Stage 6.
- [ ] World Phase 4 (Intelligence) reachable within one Epoch in ≥ 50 of 100 seed-sample worlds.

---

## Phase 6: Emergence: The Digital Rise v5.x — Player Interaction (DEOS-Play)
- [ ] Observation View with the Particles, Living Diagram, and Network Map layers bound to the read buffer.
- [ ] Generative audio driven by `WorldMood`: harmony for cooperation, dissonance for conflict.
- [ ] Sessions, offline catch-up at `OFFLINE_RATE` capped at `MAX_OFFLINE_TICKS`, Epoch summaries.
- [ ] Shared seeds, Seed Lineage, verified challenges and leaderboards from Input Log submissions.
- [ ] Product Targets of DEOS-F05 section 1.3 measured on a live cohort and revised from ASSUMED to measured.

---

## Phase 7: Scale v6.x
- [ ] GPU compute for Stage 2 diffusion with a proof of identical Tick Hashes against the CPU path.
- [ ] SIMD vectorization (AVX2, AVX-512, ARM NEON) of Stage 2 and Stage 4 with identical Tick Hashes.
- [ ] Distributed headless verification: challenge submissions verified by independent nodes comparing Checkpoints.
