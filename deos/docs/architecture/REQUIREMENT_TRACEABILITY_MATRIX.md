# Requirement Traceability Matrix (RTM)

Generated from every `### REQ-PREFIX-nnn:` heading under `docs/` by `python3 deos/tools/gen_rtm.py`; do not edit by hand. `python3 deos/tools/gen_rtm.py --check` fails when this file is stale, and `tools/spec_lint.py` fails when a defined requirement is missing here. The verification test of a requirement is `TEST_<PREFIX>_<nnn>` (tests/SPEC_CONSISTENCY_TEST_PLAN.md section 3), except the EESS-lineage requirements, which keep their historical names.

## DEOS-Core (DEOS-CORE) — 47 requirements

| Requirement ID | Description | Source Document | Implemented In | Verification Test |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-LAW-001** | Conservation of Energy | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_EnergyConservation` |
| **REQ-LAW-002** | Entropy Accumulation | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_EntropyIncrease` |
| **REQ-LAW-003** | Discrete Temporal Progression | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_LAW_003` |
| **REQ-LAW-004** | The Energy Ledger | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_LAW_004` |
| **REQ-LAW-005** | Entropy Tax on Transfers | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_LAW_005` |
| **REQ-LAW-006** | Radiant Dissipation | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_LAW_006` |
| **REQ-LAW-007** | Heat Diffusion | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_LAW_007` |
| **REQ-LAW-008** | Moisture Diffusion and Runoff | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_LAW_008` |
| **REQ-LAW-009** | Temperature–Moisture Coupling | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_LAW_009` |
| **REQ-LAW-010** | Materials, Decay, and Transitions | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_LAW_010` |
| **REQ-LAW-011** | Decay of `mutation_bias` toward 1.0 | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_LAW_011` |
| **REQ-LAW-012** | Field Bounds and Invariants | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_LAW_012` |
| **REQ-LAW-013** | Substrate Insolation | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_LAW_013` |
| **REQ-MATH-001** | Representation Format | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_Q32_Arithmetic` |
| **REQ-MATH-002** | The Flux Equation | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_FluxEvaluation` |
| **REQ-MATH-003** | Utility Scoring Function | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_003` |
| **REQ-MATH-004** | PCG64 Implementation and Per-System Seed Derivation | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_004` |
| **REQ-MATH-005** | Saturating Addition and Subtraction | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_005` |
| **REQ-MATH-006** | Multiplication | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_006` |
| **REQ-MATH-007** | Division | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_007` |
| **REQ-MATH-008** | Comparison, Sign, and Conversion | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_008` |
| **REQ-MATH-009** | Intermediate Widths and Implementation Constraints | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_009` |
| **REQ-MATH-010** | Function Table Construction | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_010` |
| **REQ-MATH-011** | Exponential | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_011` |
| **REQ-MATH-012** | Natural Logarithm | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_012` |
| **REQ-MATH-013** | Square Root | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_013` |
| **REQ-MATH-014** | Sine and Cosine in Rotations | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_014` |
| **REQ-MATH-015** | Logistic | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_015` |
| **REQ-MATH-016** | Reciprocal | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_016` |
| **REQ-MATH-017** | Conformance Vectors | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_MATH_017` |
| **REQ-ORD-001** | Canonical Iteration Order | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_ORD_001` |
| **REQ-ORD-002** | Tie-break Rule | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_ORD_002` |
| **REQ-ORD-003** | Stable Sort | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_ORD_003` |
| **REQ-ORD-004** | Reduction Order | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_ORD_004` |
| **REQ-ORD-005** | Hashing Order | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_ORD_005` |
| **REQ-ORD-006** | Prohibited Dependencies | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_ORD_006` |
| **REQ-ORD-007** | Cell Chunk Layout | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_ORD_007` |
| **REQ-PRNG-001** | PCG64 XSL-RR 128/64 Generator | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_PRNG_001` |
| **REQ-PRNG-002** | Seed Hierarchy and Byte Layout | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_PRNG_002` |
| **REQ-PRNG-003** | Per-Slot Substreams | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_PRNG_003` |
| **REQ-PRNG-004** | Draw Functions | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_PRNG_004` |
| **REQ-PRNG-005** | Stream Use Discipline | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_PRNG_005` |
| **REQ-PRNG-006** | Generator and Derivation Test Vectors | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_PRNG_006` |
| **REQ-TICK-001** | The Tick Is the Only Clock | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_TICK_001` |
| **REQ-TICK-002** | Explicit Euler With Unit Step | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_TICK_002` |
| **REQ-TICK-003** | Stage 2 Sub-step Order | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_TICK_003` |
| **REQ-TICK-004** | Acceleration Identity | `DEOS-CORE` | Kernel core library: `fx_*` arithmetic and tables, `prng_*`, `ledger_*`, `substrate_stage2*` | `TEST_TICK_004` |

## DEOS-ECS (DEOS-ECS) — 45 requirements

| Requirement ID | Description | Source Document | Implemented In | Verification Test |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-CMP-001** | `Lifecycle` | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_CMP_001` |
| **REQ-CMP-002** | `Genome` and the parameter table | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_CMP_002` |
| **REQ-CMP-003** | `Needs` | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_CMP_003` |
| **REQ-CMP-004** | `Perception` | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_CMP_004` |
| **REQ-CMP-005** | `Memory` | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_CMP_005` |
| **REQ-CMP-006** | `Decision` | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_CMP_006` |
| **REQ-CMP-007** | `MemeVector` | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_CMP_007` |
| **REQ-CMP-008** | `TrustEdges` | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_CMP_008` |
| **REQ-CMP-009** | `Affiliation` | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_CMP_009` |
| **REQ-CMP-010** | `InstitutionState` | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_CMP_010` |
| **REQ-CMP-011** | Substrate Cell fields | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_CMP_011` |
| **REQ-CMP-012** | `WorldMood` slot | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_CMP_012` |
| **REQ-CMP-013** | Ownership matrix and read rule | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_CMP_013` |
| **REQ-DAT-001** | 64-Byte Cache Line Boundary Alignment | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_CacheAlignment` |
| **REQ-DAT-002** | Zero Heap Allocation During Tick | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_ZeroAllocations` |
| **REQ-DAT-003** | Pool allocator design | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_DAT_003` |
| **REQ-DAT-004** | Chunk-major Struct-of-Arrays layout | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_DAT_004` |
| **REQ-DAT-005** | Padding rules | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_DAT_005` |
| **REQ-DAT-006** | Indices only, never pointers | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_DAT_006` |
| **REQ-DAT-007** | Little-endian canonical serialization | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_DAT_007` |
| **REQ-DAT-008** | Snapshot byte layout | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_DAT_008` |
| **REQ-DAT-009** | SpatialIndex | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_DAT_009` |
| **REQ-DAT-010** | Memory budget | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_DAT_010` |
| **REQ-ENT-001** | 64-bit Packed EntityID | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_EntityIDUnpack` |
| **REQ-ENT-002** | Position Component (`Position2D`) | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_ENT_002` |
| **REQ-ENT-003** | Energy Component (`EnergyState`) | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_ENT_003` |
| **REQ-ENT-004** | Null EntityID and validity | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_ENT_004` |
| **REQ-ENT-005** | Entity table and generation policy | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_ENT_005` |
| **REQ-ENT-006** | Deterministic free-slot allocation | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_ENT_006` |
| **REQ-ENT-007** | `MAX_ENTITIES`, Chunks, and slot ranges per scale | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_ENT_007` |
| **REQ-ENT-008** | Spawn as a Command | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_ENT_008` |
| **REQ-ENT-009** | Despawn as a Command | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_ENT_009` |
| **REQ-ENT-010** | Archetypes and component membership | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_ENT_010` |
| **REQ-MUT-001** | Double buffering | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_MUT_001` |
| **REQ-MUT-002** | Owner-slot write rule | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_MUT_002` |
| **REQ-MUT-003** | Command record | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_MUT_003` |
| **REQ-MUT-004** | Command kinds and application semantics | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_MUT_004` |
| **REQ-MUT-005** | Outbox capacity and the overflow assertion | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_MUT_005` |
| **REQ-MUT-006** | Barrier resolution in canonical order | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_MUT_006` |
| **REQ-MUT-007** | Pure-function system rule | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_MUT_007` |
| **REQ-MUT-008** | No same-stage read of the write buffer | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_MUT_008` |
| **REQ-MUT-009** | Dropped Commands and the Chunk ledger | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_MUT_009` |
| **REQ-MUT-010** | Stage 6 commit sequence (data substeps) | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_MUT_010` |
| **REQ-MUT-011** | IngressOverlay | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_MUT_011` |
| **REQ-MUT-012** | Fault handling | `DEOS-ECS` | ECS arena, slabs, entity table, Command outboxes and barrier resolver, Snapshot serializer | `TEST_MUT_012` |

## DEOS-Runtime (DEOS-RT) — 29 requirements

| Requirement ID | Description | Source Document | Implemented In | Verification Test |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-ARCH-001** | Headless Kernel Compilation | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_HeadlessBuild` |
| **REQ-ARCH-002** | Double-Buffered State Buffer | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_BufferSwap` |
| **REQ-ARCH-003** | The C ABI | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_ARCH_003` |
| **REQ-ARCH-004** | Single-caller discipline | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_ARCH_004` |
| **REQ-ARCH-005** | The read view | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_ARCH_005` |
| **REQ-HASH-001** | Write folds | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_HASH_001` |
| **REQ-HASH-002** | Tick Hash | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_HASH_002` |
| **REQ-HASH-003** | Chunk Hashes and the Checkpoint Hash | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_HASH_003` |
| **REQ-HASH-004** | Checkpoint records | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_HASH_004` |
| **REQ-HASH-005** | Desync detection and localization | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_HASH_005` |
| **REQ-HASH-006** | Ledger faults | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_HASH_006` |
| **REQ-LOOP-001** | 6-Stage Deterministic Pipeline | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_PipelineSequence` |
| **REQ-LOOP-002** | World generation at tick 0 | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_LOOP_002` |
| **REQ-LOOP-003** | Stage 1 Ingress | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_LOOP_003` |
| **REQ-LOOP-004** | Input Log records and Checkpoints | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_LOOP_004` |
| **REQ-LOOP-005** | Stage sub-order and barriers | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_LOOP_005` |
| **REQ-LOOP-006** | Runtime SystemIDs | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_LOOP_006` |
| **REQ-LOOP-007** | Event outboxes and the Stage 6 flush order | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_LOOP_007` |
| **REQ-LOOP-008** | Egress rings and backpressure | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_LOOP_008` |
| **REQ-SNAP-001** | Runtime pools | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_SNAP_001` |
| **REQ-SNAP-002** | Snapshot format | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_SNAP_002` |
| **REQ-SNAP-003** | Restore and continuation identity | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_SNAP_003` |
| **REQ-SNAP-004** | Replay and verification | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_SNAP_004` |
| **REQ-SNAP-005** | Acceleration and reduced egress | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_SNAP_005` |
| **REQ-SNAP-006** | Hosting-neutral continuity | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_SNAP_006` |
| **REQ-THR-001** | Worker pool and work units | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_THR_001` |
| **REQ-THR-002** | Independence obligation | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_THR_002` |
| **REQ-THR-003** | Barriers and serial steps | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_THR_003` |
| **REQ-THR-004** | Thread-count identity | `DEOS-RT` | Runtime: C ABI, world generation, step scheduler and Worker pool, hasher, Snapshot and verify, egress rings | `TEST_THR_004` |

## DEOS-Protocol (DEOS-PROTO) — 28 requirements

| Requirement ID | Description | Source Document | Implemented In | Verification Test |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-COG-001** | Perception | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_COG_001` |
| **REQ-COG-002** | Needs weights | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_COG_002` |
| **REQ-COG-003** | Legal actions | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_COG_003` |
| **REQ-COG-004** | Utility and choice | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_COG_004` |
| **REQ-COG-005** | Movement | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_COG_005` |
| **REQ-COG-006** | Feeding | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_COG_006` |
| **REQ-COG-007** | Contest and flight | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_COG_007` |
| **REQ-COG-008** | Social actions decided here, executed in Stage 5 | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_COG_008` |
| **REQ-COG-009** | Memory | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_COG_009` |
| **REQ-EVT-001** | Emission rules | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_EVT_001` |
| **REQ-EVT-002** | Domain kinds | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_EVT_002` |
| **REQ-EVT-003** | Cadence and the pacing constants | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_EVT_003` |
| **REQ-EVT-004** | World Phase thresholds | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_EVT_004` |
| **REQ-SOC-001** | Meme-Vector semantics | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_SOC_001` |
| **REQ-SOC-002** | Knowledge accrual by practice | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_SOC_002` |
| **REQ-SOC-003** | Pull transmission and doctrine | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_SOC_003` |
| **REQ-SOC-004** | Push sharing and trade | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_SOC_004` |
| **REQ-SOC-005** | Trust dynamics | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_SOC_005` |
| **REQ-SOC-006** | Institutions | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_SOC_006` |
| **REQ-SOC-007** | Conflict at the Institution level | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_SOC_007` |
| **REQ-SOC-008** | Technology discovery and effects | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_SOC_008` |
| **REQ-SOC-009** | WorldMood partials and fold | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_SOC_009` |
| **REQ-XL-001** | Aging and death by age | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_XL_001` |
| **REQ-XL-002** | Metabolism | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_XL_002` |
| **REQ-XL-003** | Passive feeding (Organisms) and the energy need level | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_XL_003` |
| **REQ-XL-004** | Death and the corpse | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_XL_004` |
| **REQ-XL-005** | Reproduction and inheritance | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_XL_005` |
| **REQ-XL-006** | Needs levels | `DEOS-PROTO` | Protocol systems `proto_stage3/4/5_chunk`, `proto_worldmood_*`, event emission | `TEST_XL_006` |

## DEOS-Play (DEOS-PLAY) — 23 requirements

| Requirement ID | Description | Source Document | Implemented In | Verification Test |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-CAT-001** | Catalyst Action kinds | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_CAT_001` |
| **REQ-CAT-002** | Composite expansion | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_CAT_002` |
| **REQ-CAT-003** | Cost | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_CAT_003` |
| **REQ-CAT-004** | The Catalyst Budget | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_CAT_004` |
| **REQ-CAT-005** | Host-side settings that are not logged | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_CAT_005` |
| **REQ-PLAY-001** | The fantasy | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_PLAY_001` |
| **REQ-PLAY-002** | The core loop (30 seconds) | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_PLAY_002` |
| **REQ-PLAY-003** | Agency and consequence | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_PLAY_003` |
| **REQ-PLAY-004** | Session and daily loops | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_PLAY_004` |
| **REQ-PLAY-005** | The meta loop, Seed Lineage, and the legacy trait | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_PLAY_005` |
| **REQ-PLAY-006** | Chronicle presentation and the why drill-down | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_PLAY_006` |
| **REQ-PLAY-007** | Epoch summary, rewind, and branch | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_PLAY_007` |
| **REQ-PLAY-008** | Cadence, surprise, and the first five minutes | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_PLAY_008` |
| **REQ-PLAY-009** | Observation View and Affective Signals | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_PLAY_009` |
| **REQ-PLAY-010** | World Phases presentation | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_PLAY_010` |
| **REQ-PLAY-011** | Engagement without deception (GI-8) | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_PLAY_011` |
| **REQ-PLAY-012** | Telemetry and targets | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_PLAY_012` |
| **REQ-SES-001** | Offline catch-up | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_SES_001` |
| **REQ-SES-002** | The "while you were away" summary | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_SES_002` |
| **REQ-SES-003** | Seed code | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_SES_003` |
| **REQ-SES-004** | World sharing and rivalry | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_SES_004` |
| **REQ-SES-005** | Challenges and leaderboards | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_SES_005` |
| **REQ-SES-006** | Time control | `DEOS-PLAY` | Host (Emergence: The Digital Rise) and the compiled `cat_kind_table`, `cat_cost`, `cat_expand` | `TEST_SES_006` |

## DEOS-MVS (DEOS-MVS) — 9 requirements

| Requirement ID | Description | Source Document | Implemented In | Verification Test |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-MVS-001** | Scope by module | `DEOS-MVS` | MVS build: `deos-run`, parity harness, First Playable Host | `TEST_MVS_001` |
| **REQ-MVS-002** | Configuration | `DEOS-MVS` | MVS build: `deos-run`, parity harness, First Playable Host | `TEST_MVS_002` |
| **REQ-MVS-003** | Baseline hardware | `DEOS-MVS` | MVS build: `deos-run`, parity harness, First Playable Host | `TEST_MVS_003` |
| **REQ-MVS-004** | Headless benchmark | `DEOS-MVS` | MVS build: `deos-run`, parity harness, First Playable Host | `TEST_MVS_004` |
| **REQ-MVS-005** | Determinism acceptance | `DEOS-MVS` | MVS build: `deos-run`, parity harness, First Playable Host | `TEST_MVS_005` |
| **REQ-MVS-006** | Playability acceptance and the agency test | `DEOS-MVS` | MVS build: `deos-run`, parity harness, First Playable Host | `TEST_MVS_006` |
| **REQ-MVS-007** | Memory ceiling | `DEOS-MVS` | MVS build: `deos-run`, parity harness, First Playable Host | `TEST_MVS_007` |
| **REQ-MVS-008** | Deliverables and the First Playable | `DEOS-MVS` | MVS build: `deos-run`, parity harness, First Playable Host | `TEST_MVS_008` |
| **REQ-MVS-009** | Exit criteria to v1.x | `DEOS-MVS` | MVS build: `deos-run`, parity harness, First Playable Host | `TEST_MVS_009` |

**Total: 181 requirements across 6 modules.**
