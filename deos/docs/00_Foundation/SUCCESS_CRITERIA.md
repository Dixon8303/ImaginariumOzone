# Specification: Success Criteria & Engineering Metrics (DEOS-F05)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | DEOS-F05 |
| **Semantic Version** | v0.1.0 |
| **Status** | Approved |
| **Dependencies** | DEOS, DEOS-F01, DEOS-F02 |
| **Supersedes** | EESS-0005 |

---

## 1. Quantitative Verification Metrics

To achieve **DEOS-1.0 Blueprint Acceptance**, the runtime built from these specifications must satisfy every threshold in section 1.1 (engineering) and section 1.2 (playability). Section 1.3 lists product targets that are assumed, not verified, until live data exists; they gate nothing.

All wall-clock figures are measured on the baseline hardware defined by DEOS-MVS. All tick figures are exact. "Seed sample" means the 100 worlds with Master Seed values 1 through 100 inclusive, each started from tick 0 with an empty Input Log and the module default constants of DEOS section 5.1 at MVS scale.

### 1.1 Target Performance Benchmarks (engineering)
```
 Metric                  Target Threshold             Pass/Fail Condition
─────────────────────────────────────────────────────────────────────────────
 Active Entities          1,000,000 entities           Must complete loop in <16.6ms
 Simulation Tick Rate     60 Hz (16.66 ms/tick)        Zero frame drops in headless mode
 Deterministic Parity     100% Bitwise Identity        State hash identical across x86/ARM
 Heap Allocation (Tick)   0 Bytes                       Zero GC calls during tick pipeline
 Memory Footprint         < 4.0 GB RAM                 For 1,000,000 active entities
```

Refinements binding from DEOS (the table above is the EESS baseline and stands unchanged):

| Row | Refinement |
| :--- | :--- |
| Deterministic Parity | "State hash" is the Tick Hash (DEOS-F04). Identity is required across x86-64 and ARM64, across 1 and 4 worker threads, and between attended stepping and Acceleration, for the full Tick Hash sequence of the MVS acceptance run, not only the final digest (GI-1, GI-4). |
| Active Entities | `MAX_ENTITIES` (1,048,576) at v1.0 scale. The MVS build is accepted at `MAX_ENTITIES` (16,384) against the DEOS-MVS benchmark (10,000 ticks in under 5.0 s). |
| Heap Allocation | Measured by an allocation counter that reads 0 across a full tick, every tick of the acceptance run (DEOS section 7). |

### 1.2 Playability Metrics

Binding for DEOS-1.0 acceptance. Each row is measured over the seed sample at MVS scale by the test named in the last column (tests/SPEC_CONSISTENCY_TEST_PLAN.md), with the Kernel stepped headlessly and the Host's presentation excluded from timing except where the row names it.

| # | Metric | Definition | Target | Pass condition | Test |
| :-- | :--- | :--- | :--- | :--- | :--- |
| P1 | Time to first Notable Event | Ticks from tick 0 to the first `NotableEvent` of a domain kind (`kind` ≥ 16), converted at speed 1× (`TICK_RATE_HZ` = 60) | ≤ 90 real seconds, which is ≤ 5,400 ticks | 100 of 100 seeds | TS-PLAY-002 |
| P2 | First Institution | Ticks from tick 0 to the first tick at which an entity carries an `InstitutionState` component with `member count` ≥ 1 | by simulated day 10, which is ≤ 36,000 ticks (10 × `TICKS_PER_DAY`) | ≥ 80 of 100 seeds | TS-PLAY-002 |
| P3 | Epoch catch-up | Wall-clock time to step one Epoch (`TICKS_PER_EPOCH` = 108,000 ticks) in Acceleration from a Snapshot, with the Chronicle streamed to the Host incrementally | ≤ 60 s at MVS scale; first Chronicle row delivered to the Host within 1.0 s of start | 100 of 100 seeds; Tick Hash sequence identical to attended stepping of the same span | TS-BENCH-003 |
| P4 | Replay verification | Wall-clock time to re-simulate a 10,000-tick Input Log from tick 0 and compare all 156 Checkpoints (ticks 64, 128, …, 9,984) | ≤ 5.0 s | every Checkpoint matches; any mismatch is reported as a Desync with the first mismatching tick | TS-BENCH-002 |
| P5 | Notable Event cadence | Notable Events of domain kinds per simulated day over the first Epoch | within the cadence band DEOS-PLAY sets for each World Phase | 100 of 100 seeds within band | TS-PLAY-002 |
| P6 | Legibility | Fraction of `Decision` components written in Stage 4 that carry a non-zero `DecisionTrace.action` and three contributors | 100% | zero exceptions across the acceptance run | TS-PLAY-001 |

Player-facing consequence: P1 and P2 guarantee that a new player sees something happen and something form before they can lose interest; P3 guarantees that returning after an absence is a stream of history rather than a loading screen; P4 guarantees that a shared challenge verifies faster than it is discussed; P5 and P6 guarantee that what happens is readable.

### 1.3 Product Targets (ASSUMED benchmarks)

The following are **assumed** targets for *Emergence: The Digital Rise*, adopted from category norms for simulation games in the absence of playtest data. They are not conformance gates, they are not measured by any test in this repository, and they are revised by DEOS-Play once live cohorts exist. A day is a player-local calendar day; day 0 is the day of a player's first session.

| # | Metric | Definition | Assumed target |
| :-- | :--- | :--- | :--- |
| T1 | D1 retention | Fraction of players with a day-0 session who have a session on day 1 | ≥ 40% |
| T2 | D7 retention | Fraction of players with a day-0 session who have a session on day 7 | ≥ 20% |
| T3 | D30 retention | Fraction of players with a day-0 session who have a session on day 30 | ≥ 10% |
| T4 | Share rate | Fraction of active worlds (at least one session in the trailing 30 days) whose Master Seed, Input Log, or Snapshot was exported through the Host's share function at least once | ≥ 5% of active worlds |

A product target that is missed is a design signal for DEOS-Play, never a reason to add a hidden timer, a purchasable outcome, or an undisplayed scarcity (GI-8).

---

## 2. Acceptance Procedure

1. Run the engineering benchmarks of section 1.1 on baseline hardware; record every figure with the commit hash of the Kernel build.
2. Run the seed sample for the playability metrics of section 1.2; record per-seed tick counts for P1 and P2, wall-clock for P3 and P4, per-day counts for P5, and the exception count for P6.
3. Every row of sections 1.1 and 1.2 passes, or DEOS-1.0 is not accepted. There is no partial acceptance and no waiver.
4. Publish the results table with the release; the same seeds re-run on a later build must reproduce identical Tick Hashes (GI-1).

---

## 3. Revision History
| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 (EESS) | 2026-07-20 | Quantitative metrics initial specification (lineage) | EE Arch Team |
| v0.1.0 (DEOS) | 2026-09-12 | Rebranded to DEOS-F05; engineering table kept with DEOS refinements; Playability Metrics and assumed Product Targets added; acceptance procedure added; supersedes EESS-0005 | DEOS Arch Team |
