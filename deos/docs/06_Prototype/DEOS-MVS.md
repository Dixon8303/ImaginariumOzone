# Specification: Minimum Viable Simulation (DEOS-MVS)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | DEOS-MVS |
| **Semantic Version** | v0.1.0 |
| **Status** | Draft |
| **Dependencies** | DEOS, DEOS-F01, DEOS-F02, DEOS-F03, DEOS-F04, DEOS-F05, DEOS-F06, DEOS-CORE, DEOS-ECS, DEOS-RT, DEOS-PROTO, DEOS-PLAY |
| **Supersedes** | EESS-0701 (Prototype & Minimum Viable Simulation) |
| **Reserved Prefixes** | `MVS` (from DEOS section 3.2) |

---

## 1. Purpose

The MVS is the first build that is simultaneously **correct** (it passes the determinism gates of DEOS section 7) and **playable** (a person can open it, act as a Catalyst, and read consequences). It fixes the scope of every module at MVS scale, the tick-0 population, the baseline hardware, the benchmark, the seeds, and the acceptance tests, and it defines the smallest Host that lets a person complete the core loop. Everything deferred is listed so that the MVS is a whole thing, not a sample.

Player-facing consequence: the MVS is the version of *Emergence: The Digital Rise* a first player will hold, and this document is the promise of what it does.

## 2. Scope

**Included.** Scope by module at requirement-prefix granularity (section 6.1); configuration (6.2); baseline hardware (6.3); the headless benchmark (6.4); determinism acceptance (6.5); playability acceptance and the agency test (6.6); memory ceiling (6.7); deliverables and the First Playable (6.8); exit criteria (6.9).

**Excluded.** v1.0 scale (ROADMAP Phase 2); the sexual reproduction flag; multiplayer; server-stepped worlds; Challenges beyond local verification.

## 3. Dependencies

Every module above this one; in particular DEOS section 5.1 (MVS-scale registry values), DEOS-F05 (the seed sample and metrics), DEOS-RT REQ-LOOP-002 (world generation counts this module fixes), DEOS-RT section 11 (the tick budget), DEOS-PLAY REQ-PLAY-008 (the first five minutes), and tests/SPEC_CONSISTENCY_TEST_PLAN.md.

## 4. Definitions

| Term | Definition |
| :--- | :--- |
| **Baseline hardware** | The two reference machines of REQ-MVS-003; every wall-clock figure in DEOS-F05 and DEOS-RT is measured on them. |
| **Acceptance run** | The set of runs of REQ-MVS-005 and REQ-MVS-006 on both baseline machines. |
| **MVS seeds** | Master Seeds 1 through 10: the first ten of the DEOS-F05 seed sample. |
| **First Playable** | The Host of REQ-MVS-008 rule 4. |

## 5. Assumptions

1. `SCALE_MVS` values from DEOS section 5.1: `MAX_ENTITIES` 16,384; `GRID_W` × `GRID_H` 256 × 256; `CHECKPOINT_INTERVAL` 64; `THREADS` 4 on both baselines.
2. The Kernel is built from the same source for both baselines; only the compiler target differs.
3. The DEOS-CORE tables and vectors, the DEOS-RT fold vectors, and the DEOS-PLAY seed-code vector are shipped as test fixtures with the build.

---

## 6. Requirements

### REQ-MVS-001: Scope by module

| Module | Prefix | In the MVS | Deferred |
| :--- | :--- | :--- | :--- |
| DEOS-Core | `LAW` | all, including REQ-LAW-013 insolation | seasonal insolation (section 12 of DEOS-Core) |
| | `MATH` | all seven tables and every vector | `fx_pow`, `fx_atan2_rot` |
| | `PRNG`, `TICK`, `ORD` | all | — |
| DEOS-ECS | `ENT`, `CMP`, `DAT`, `MUT` | all at MVS pool sizes | buffer-B elision in Snapshots |
| DEOS-Runtime | `ARCH`, `LOOP`, `THR`, `HASH`, `SNAP` | all; `EGRESS_REDUCED`; `deos_verify` | incremental Chunk Hashes; server-stepped worlds |
| DEOS-Protocol | `XL`, `COG`, `SOC`, `EVT` | all rules with `PROTO_SEXUAL = 0`; every event kind 16–31 | kinds 32–33 are presentation aggregates (DEOS-PLAY) |
| DEOS-Play | `PLAY` | REQ-PLAY-001 … 010, 011; REQ-PLAY-012 telemetry local only | Seed Lineage sharing service (local branch only) |
| | `CAT` | all 21 kinds; Budget | — |
| | `SES` | catch-up, summary, seed code, local share export/import, time control | Challenge service and leaderboard (local `deos_verify` of a shared log only); rivalry |

### REQ-MVS-002: Configuration

`deos_config` for the MVS: `scale = SCALE_MVS`, `threads = 4`, `organisms = 8,192`, `agents = 2,048`, `springs = 1,024`, `input_log_capacity = 131,072`, `chronicle_ring = 65,536`, `worldmood_ring = 4,096`, `egress_mode = EGRESS_FULL`. The tick-0 population of 10,240 entities honours the EESS lineage figure of 10,000 organisms; the 1,024 springs are the lineage's static energy nodes realized as high-energy Cells (DEOS-RT REQ-LOOP-002 rule 4). Free agent slots at tick 0: 15,359 − 10,240 = 5,119; Institution slots: 1,024.

### REQ-MVS-003: Baseline hardware

| Baseline | Specification | Role |
| :--- | :--- | :--- |
| **A (ARM64)** | Apple M1, 8 cores (4 performance), 8 GB, macOS; Kernel built with clang, `-O2`, no fast-math (DEOS-CORE REQ-MATH-009) | phone-class ceiling and ARM parity |
| **B (x86-64)** | one socket, 4 cores at 3.0 GHz base with AVX2, 16 GB, Linux; Kernel built with clang or gcc, `-O2` | desktop parity |

Both run the acceptance run with `THREADS = 4` and, for TS-BENCH-002, also `THREADS = 1`.

### REQ-MVS-004: Headless benchmark

`deos_generate` with Master Seed 1, then 10,000 `deos_tick` calls with an empty Input Log in `EGRESS_REDUCED` mode, wall-clock measured from the first tick to the return of the last, Checkpoint hashing overlapped per DEOS-RT section 11: **under 5.0 s on both baselines** (2,000 ticks per second, 33× real time, above `MIN_ACCELERATION`). The same run in `EGRESS_FULL` mode with a Host stub polling every tick: under 6.0 s. The benchmark is repeated three times per baseline; every run reports its final Tick Hash, and the three must be identical (REQ-MVS-005).

Player-facing consequence: an Epoch of catch-up finishes in under a minute on a phone-class chip, which is the promise DEOS-F05 P3 makes to a returning player.

### REQ-MVS-005: Determinism acceptance

For each MVS seed, with an empty Input Log and with the DEOS-PLAY section 8.3 reference action script, run 10,000 ticks on: baseline A × {1, 4} threads, baseline B × {1, 4} threads, and baseline B × 4 threads in `EGRESS_REDUCED`. All five configurations produce the identical sequence of 10,000 Tick Hashes and 157 Checkpoint Hashes (ticks 0, 64, …, 9,984). Any difference is a Desync and fails acceptance; the report of DEOS-RT REQ-HASH-005 is attached. Additionally, restoring the tick-3,600 Snapshot and stepping to 10,000 reproduces the same hashes (DEOS-RT REQ-SNAP-003), and `deos_verify` of the exported log returns `DEOS_OK` on the other baseline (REQ-SNAP-004).

### REQ-MVS-006: Playability acceptance and the agency test

Over the ten MVS seeds, 10,000 ticks each with an empty Input Log:

1. **Cadence.** At least 12 first-order Notable Events of at least 4 distinct kinds per seed; the first first-order event by tick 5,400 in 10 of 10 seeds (DEOS-F05 P1).
2. **Society.** At least one `INSTITUTION_FOUNDED` by tick 36,000 in ≥ 8 of 10 seeds, measured by extending the run to 36,000 ticks for this check only (DEOS-F05 P2; TS-PLAY-002).
3. **Persistence.** No `EXTINCTION` before tick 10,000 in 10 of 10 seeds; population at tick 108,000 (one Epoch, run in `EGRESS_REDUCED`) at least 50 % of the tick-0 population in ≥ 9 of 10 seeds (ADR-0002).
4. **Legibility.** Every `Decision` written in Stage 4 carries a non-zero `action` and three contributor slots (unused slots marked `0xFF`), and every Notable Event with non-zero `cause` refers to a slot whose `Decision` was written in the same tick (DEOS-F05 P6; TS-PLAY-001).
5. **Agency.** For each seed, the run with the reference action script diverges from the empty-log run: the Tick Hashes differ within 64 ticks of tick 600 (the first action) in 10 of 10 seeds, and at least one domain event whose `cell` lies in the affected square of each of the six actions appears within `TICKS_PER_DAY` ticks of that action in ≥ 8 of 10 seeds per action (DEOS-PLAY REQ-PLAY-003).
6. **Budget.** The reference script's total cost (61) is accepted in full: six `CATALYST_APPLIED` rows and zero `INGRESS_REJECTED` rows in 10 of 10 seeds.

Player-facing consequence: these six checks are the first player's first hour, run before they are: something happens, a society forms, the world lives, every row has a why, and the player's hand is visible.

### REQ-MVS-007: Memory ceiling

Resident Kernel memory at MVS configuration is at most 160 MB (DEOS-ECS 63.6 MB arena plus DEOS-RT pools with `input_log_capacity` 131,072: ≈ 26 MB of runtime pools), measured after `deos_generate`; the allocation counter reads 0 across every tick of the acceptance run (DEOS-ECS REQ-DAT-002). The First Playable Host adds at most 200 MB.

### REQ-MVS-008: Deliverables and the First Playable

1. **Kernel library** conforming to DEOS-RT REQ-ARCH-001, with the ABI of REQ-ARCH-003.
2. **CLI runner** `deos-run`: `generate <seedcode> | step <n> | verify <log> | snapshot <file> | restore <file> | bench` printing Tick Hashes, Checkpoint Hashes, `WorldMood`, and the Chronicle as text rows rendered with the DEOS-PROTO story templates.
3. **Parity harness** executing REQ-MVS-004 through REQ-MVS-006 on both baselines and emitting the DEOS-F05 results table with the commit hash.
4. **First Playable Host**: the smallest Host that lets a person complete the five-verb loop: a 2D Observation View with the Particles layer (Cells as coloured squares, entities as dots) and an inspect panel showing every component field; the Catalyst Palette with all four families as sliders and a region brush; Time Control with `SPEED_LEVELS` and pause; the Chronicle as a scrolling list with story text, first-order emphasis, and the drill-down to the Decision Trace for current-tick rows; seed-code entry and curation; catch-up with the progress line and the while-you-were-away summary; Epoch summary; local Snapshot ring with ghost mode and branch. The Living Diagram and Network Map layers, Affective Signals audio, sharing service, and Challenge service are not required for First Playable.

### REQ-MVS-009: Exit criteria to v1.x

The MVS is complete, and ROADMAP Phase 2 may begin, when: REQ-MVS-004 through REQ-MVS-007 pass on both baselines; the DEOS-F05 seed sample (100 seeds) meets P1 through P6; the First Playable has been played by at least 20 people for at least one Session each, with `loop_seconds`, `consequence_ticks`, and `surprise_rate` telemetry within the DEOS-PLAY REQ-PLAY-012 targets in aggregate; and every pacing constant changed during playtesting has a DEOS-F06 rubric on record.

---

## 7. Algorithms & Mathematics

The acceptance harness:

```
for seed in 1..10:
    for cfg in configurations(REQ-MVS-005):
        K = create(cfg); seed(K, seed); generate(K); [import script]
        for t in 1..10000: tick(K); record(tick_hash(K)); if t % 64 == 0: record(checkpoint_hash(K))
        record(chronicle, worldmood, stats)
    assert all hash sequences equal
    evaluate REQ-MVS-006 checks 1, 4, 5, 6 on the 10,000-tick runs; extend one run to 36,000 for check 2 and to 108,000 (reduced egress) for check 3
```

## 8. Data Structures

The results table (published with the build): one row per (seed, configuration) with the final Tick Hash, the count of Checkpoints, wall-clock, peak resident memory, first-order event count and kinds, first-event tick, first-Institution tick, population at 10,000 and 108,000, agency divergence tick, Budget accepted.

## 9. Subsystem Interfaces

`deos-run` is a Host over the DEOS-RT ABI; the parity harness drives `deos-run` and parses its output. No new Kernel interface.

## 10. Failure Cases & Risk Mitigation

| Case | Behaviour | Mitigation |
| :--- | :--- | :--- |
| Benchmark misses 5.0 s | acceptance fails | overlap Checkpoint hashing (DEOS-RT section 11); profile Stage 4 first (the largest budget) |
| A seed fails cadence or society | acceptance fails | tune the DEOS-PROTO ★ constants under DEOS-F06; never add a script (GI-7) |
| A seed goes extinct | acceptance fails | ADR-0002 insolation and `FX_PHOTO_RATE`; verify `LAT` and material thresholds |
| Hash mismatch between baselines | Desync report localizes it | DEOS-CORE REQ-MATH-009 build flags; REQ-ORD-006 |
| First Playable exceeds memory | fails REQ-MVS-007 | reduce `input_log_capacity`; the Kernel figure is fixed |

## 11. Performance & Scalability Targets

Those of REQ-MVS-004 and REQ-MVS-007; v1.0 targets are DEOS-RT section 11 and DEOS-F05 section 1.1.

## 12. Future Expansion

The v1.x plan is ROADMAP Phases 2 through 7; the MVS harness becomes the regression suite for every later scale profile.

## 13. Revision History

| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 | 2026-09-12 | Initial DEOS draft; absorbs EESS-0701 | DEOS Arch Team |
