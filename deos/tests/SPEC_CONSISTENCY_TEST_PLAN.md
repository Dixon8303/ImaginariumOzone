# Specification Consistency & Determinism Test Plan

This test plan defines the verification scripts and benchmark runs that validate the DEOS documents and, once the Kernel exists, the DEOS-MVS build. Every test is named here and in `docs/architecture/REQUIREMENT_TRACEABILITY_MATRIX.md`; the conformance gates of `DEOS.md` section 7 map onto the suites below.

---

## 1. Verification Test Matrix

```
 Test Suite ID       Target Subsystem                         Verification Method
──────────────────────────────────────────────────────────────────────────────────────────────
 TS-SPEC-001         Glossary Consistency                     Automated term-checker script
 TS-SPEC-002         Dependency Directed Graph                Cycle detection script
 TS-SPEC-003         Traceability Matrix                      Validate REQ-IDs map to specs
 TS-SPEC-004         Identifier lint (tools/spec_lint.py)     Linter exit status 0 on the tree
 TS-BENCH-001        Q32.32 Math Parity                       Cross-platform math sanity unit test
 TS-BENCH-002        Tick Hash Determinism and Replay         Verify 10,000-tick BLAKE3 Tick Hash sequence
 TS-BENCH-003        Epoch Catch-up                           108,000 ticks in Acceleration, streamed
 TS-PLAY-001         Legibility: every Decision has a Trace   Decision/DecisionTrace audit over a run
 TS-PLAY-002         Event cadence within DEOS-PLAY targets   Notable Event timing and rate over seeds
```

---

## 2. Test Definitions

### TS-SPEC-001 Glossary Consistency
- Input: every `.md` file under `deos/` except `LEGACY_*` files.
- Method: scan for the banned synonyms of DEOS-F04 sections 1.1 through 1.3 outside table rows and "Banned" columns.
- Pass: zero occurrences. (`tools/spec_lint.py --warn` reports the high-signal subset; the full list is checked here.)

### TS-SPEC-002 Dependency Directed Graph
- Input: the `Dependencies` metadata row of every specification document.
- Method: build the graph; verify it is acyclic and that every edge points to a document earlier in the order `DEOS → Foundation → Core → ECS → Runtime → Protocol → Play → MVS`.
- Pass: no cycle; no edge from a lower module to a higher one; the graph matches `docs/architecture/SYSTEM_DEPENDENCY_GRAPH.md`.

### TS-SPEC-003 Traceability Matrix
- Input: every `### REQ-PREFIX-nnn:` definition heading and `docs/architecture/REQUIREMENT_TRACEABILITY_MATRIX.md`.
- Method: every defined requirement appears in the matrix with a source document and a named test; every matrix row names a requirement that is defined.
- Pass: both sets are equal.

### TS-SPEC-004 Identifier lint (tools/spec_lint.py)
- Input: the `deos/` tree.
- Method: `python3 deos/tools/spec_lint.py` from the monorepo root. The linter checks Document ID validity against `DEOS.md` section 3.1, single definition of each requirement under its owning module (`DEOS.md` section 3.2), resolution of every requirement reference, confinement of retired EESS identifiers to lineage contexts, the no-deferred-text rule (CONTRIBUTING.md Rule 7), and relative-link resolution.
- Pass: exit status 0 with `0 errors`. At DEOS-1.0 the run is `--warn` clean as well.

### TS-BENCH-001 Q32.32 Math Parity
- Input: the DEOS-Core determinism vectors (input → output pairs for every Q32.32 operation, table function, and PRNG draw).
- Method: run every vector on x86-64 and ARM64.
- Pass: every output bitwise equal to the vector on both platforms.

### TS-BENCH-002 Tick Hash Determinism and Replay
- Input: the seed sample of DEOS-F05 (Master Seeds 1 through 100) at MVS scale with an empty Input Log, plus one 10,000-tick Input Log per seed containing at least 50 Catalyst Actions across all four families.
- Method: step 10,000 ticks on x86-64 and ARM64, at 1 and 4 worker threads, attended and in Acceleration; record the Tick Hash every tick. Then re-simulate each Input Log from tick 0 and compare its 156 Checkpoints (ticks 64 through 9,984).
- Pass: all Tick Hash sequences identical across the eight configurations; every Checkpoint matches; replay of a 10,000-tick log completes in ≤ 5.0 s on baseline hardware (DEOS-F05 P4); any mismatch is reported as a Desync naming the first mismatching tick and Chunk index.

### TS-BENCH-003 Epoch Catch-up
- Input: for each seed of the seed sample, a Snapshot at tick 3,600.
- Method: restore the Snapshot and step `TICKS_PER_EPOCH` = 108,000 ticks in Acceleration with the Chronicle streamed to a Host stub that records the wall-clock arrival time of every Notable Event; separately, step the same span attended at speed 1× in a headless harness with wall-clock excluded.
- Pass: wall-clock ≤ 60 s at MVS scale; first Chronicle row delivered within 1.0 s of start; Tick Hash sequence identical to the attended run (DEOS-F05 P3; GI-4).

### TS-PLAY-001 Legibility: every Decision has a Trace
- Input: the TS-BENCH-002 runs.
- Method: after every Stage 4 barrier, for every entity whose `Decision` component was written this tick, read its `DecisionTrace`: `action` is non-zero and each of the three `contributors` has a `need` index below `NEED_COUNT` and a non-zero `weight`, or the contributor slot is marked unused by the DEOS-PROTO rule for agents with fewer than three contributing needs. For every Notable Event with a non-zero `cause`, the referenced Decision Trace exists at that tick.
- Pass: zero exceptions across the acceptance run (DEOS-F05 P6; GI-5).

### TS-PLAY-002 Event cadence within DEOS-PLAY targets
- Input: the seed sample stepped for one Epoch (108,000 ticks) with an empty Input Log.
- Method: record every Notable Event of a domain kind (`kind` ≥ 16) with its tick, and every `WORLD_PHASE_REACHED` event with its `magnitude`. Compute per seed: tick of the first domain event; tick of the first `InstitutionState` with `member count` ≥ 1; domain events per simulated day (`TICKS_PER_DAY` = 3,600) for each of the 30 days, bucketed by the World Phase the world is in on that day.
- Pass: first domain event ≤ 5,400 ticks in 100 of 100 seeds (DEOS-F05 P1); first Institution ≤ 36,000 ticks in ≥ 80 of 100 seeds (P2); every daily count within the per-phase cadence band DEOS-PLAY sets, in 100 of 100 seeds (P5); World Phase indices non-decreasing over the run.

---

## 3. Mapping to the DEOS section 7 Conformance Gates

| Conformance gate | Test suites |
| :--- | :--- |
| Core determinism vectors | TS-BENCH-001 |
| ECS zero-allocation and alignment | TS-BENCH-002 (allocation counter and alignment assertions enabled) |
| Runtime hash parity | TS-BENCH-002, TS-BENCH-003 |
| Protocol legibility | TS-PLAY-001, TS-PLAY-002 |
| MVS acceptance | TS-BENCH-002, TS-BENCH-003, TS-PLAY-001, TS-PLAY-002 on baseline hardware |
| Specification integrity | TS-SPEC-001 through TS-SPEC-004 |
