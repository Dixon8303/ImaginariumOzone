# Specification: Simulation Loop, Threading & State Hashing (DEOS-RT)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | DEOS-RT |
| **Semantic Version** | v0.1.0 |
| **Status** | Draft |
| **Dependencies** | DEOS, DEOS-F01, DEOS-F02, DEOS-F03, DEOS-F04, DEOS-F05, DEOS-F06, DEOS-CORE, DEOS-ECS |
| **Supersedes** | EESS-0301 (REQ-ARCH-001…002), EESS-0501 (REQ-LOOP-001) |
| **Reserved Prefixes** | `ARCH`, `LOOP`, `THR`, `HASH`, `SNAP` (from DEOS section 3.2) |

---

## 1. Purpose

DEOS-Runtime owns the machine that runs the world: the Kernel/Host boundary and its C ABI, world generation at tick 0, the six-stage tick pipeline with every barrier and sub-order, the worker pool and Chunk dispatch, the two-tier state hashing that makes every tick checkable and every Checkpoint verifiable, Snapshots, replay, Acceleration, and the egress rings through which the Chronicle and the Affective Signals reach the Host. DEOS-CORE says what is computed and DEOS-ECS says where it lives; this document says when, by whom, and how the result is proven identical on every machine.

Player-facing consequence: this module is why the game shows a living world at 60 frames per second while the Kernel ticks underneath it, why a shared seed and a leaderboard entry can be trusted, why rewind exists, and why a night away returns a world that genuinely moved on (GI-1 through GI-4, GI-6).

## 2. Scope

**Included.** Headless build and the C ABI (`ARCH`); world generation, the tick pipeline with the exact order of every sub-step and barrier, Stage 1 ingress including validation, Catalyst Budget enforcement, composite expansion and the IngressOverlay, and the Stage 6 commit order (`LOOP`); the worker pool, work units, barriers, and the thread-count identity obligation (`THR`); write folds, the Tick Hash, Chunk Hashes, the Checkpoint Hash, Checkpoint records, Desync detection and localization (`HASH`); Snapshot sections, restore, replay, verification, Acceleration, and egress rings (`SNAP`).

**Excluded.** Q32.32 arithmetic, laws, streams, ordering (DEOS-CORE); layouts, Commands, barrier resolution passes, and the data substeps of Stage 6 (DEOS-ECS); every rule of Stages 3 to 5 and the Notable Event kinds ≥ 16 (DEOS-PROTO); the `CatalystAction` kind table, costs, and the composite expansion table (DEOS-PLAY); benchmarks and seeds (DEOS-MVS). Where this document names a rule of a lower module it states the call site and the order, never the rule.

## 3. Dependencies

| Document | Used for |
| :--- | :--- |
| DEOS sections 4, 5, 6 | vocabulary; registry constants; the pipeline of section 5.2; the record headers of section 5.4 (`CatalystAction`, `NotableEvent`, `Checkpoint`, `WorldMood`, `CatalystLedger`); reserved event kinds 0 to 8; GI-1 through GI-6 |
| DEOS-F02 | Directives 4 (Kernel/Host separation), 5, 6, 7, 9, 11, 12 |
| DEOS-F05 | `TICK_BUDGET_MS`, P3 and P4 wall-clock targets, the seed sample |
| DEOS-CORE | `fx_*` primitives; `ledger_*` and `substrate_stage2*` (REQ-TICK-003); `prng_derive` and SystemIDs (REQ-PRNG-002, section 7.5.1); ordering (REQ-ORD-001 … 007); the `Ledger` record; `Ledger.fault` (REQ-LAW-004 rule 5) |
| DEOS-ECS | `ecs_*` interfaces (section 9); the ownership matrix (REQ-CMP-013); Command resolution (REQ-MUT-006); Stage 6 data substeps (REQ-MUT-010); the IngressOverlay (REQ-MUT-011); canonical serialization (REQ-DAT-007); Snapshot ECS sections (REQ-DAT-008); faults (REQ-MUT-012) |
| `research/INTERFACE_INSPIRATION.md` | C8 (WorldMood emission), C9 (time model, hosting-neutral offline continuity) |

## 4. Definitions

| Term | Definition |
| :--- | :--- |
| **Worker** | One of `THREADS` operating-system threads owned by the Kernel, created at `deos_create`, that execute work units. Worker 0 is the Host's calling thread. |
| **Work unit** | The triple `(stage or sub-step, system, Chunk or Cell Chunk)`; the smallest unit dispatched to a Worker. |
| **Barrier** | A point at which every Worker has finished every work unit of the preceding step and none has started the next; the Kernel's only synchronization primitive. |
| **Write fold** | A `uint64_t` accumulated by a Worker over the little-endian bytes it writes to buffer B for one (Chunk, component) or (Cell Chunk, field) in one stage, and over the Command records it applies at one barrier (REQ-HASH-001). |
| **Tick Hash** | BLAKE3-256 over the tick's write folds, the `Ledger`, the `CatalystLedger`, and the `WorldMoodSlot` (REQ-HASH-002). Computed every tick. Refines the DEOS section 4 definition per ADR-0001. |
| **Chunk Hash** | BLAKE3-256 over a Chunk's or Cell Chunk's canonical stream (DEOS-ECS REQ-DAT-007). Computed at Checkpoint ticks. |
| **Checkpoint Hash** | BLAKE3-256 Merkle root over the Chunk Hashes, the global records, and the tick (REQ-HASH-003). Stored in the Checkpoint record. |
| **Checkpoint tick** | A tick `t` with `t mod CHECKPOINT_INTERVAL == 0` and `t > 0`. |
| **Input Log entry** | One 64-byte `CatalystAction` record. Kinds below `0x8000` are Catalyst Actions (DEOS-PLAY); kinds from `0x8000` are Runtime records (REQ-LOOP-004). |
| **Egress ring** | A single-producer, single-consumer ring buffer of fixed-size records that the Kernel fills in Stage 6 and the Host drains between calls. |
| **Event outbox** | The per-Chunk (and per-Cell-Chunk) bounded array of `NotableEvent` records emitted during a tick, flushed to the Chronicle ring in Stage 6 (REQ-LOOP-007). |
| **Scale profile** | `SCALE_MVS` (registry MVS values) or `SCALE_V1` (registry v1.0 values); fixed at `deos_create`. |
| **Egress mode** | `EGRESS_FULL` (attended play) or `EGRESS_REDUCED` (Acceleration); REQ-SNAP-005. |

## 5. Assumptions

1. The Host calls every ABI function from one thread (Worker 0). Reentrancy is not supported and is detected (REQ-ARCH-004).
2. `THREADS` is in `[1, 64]` and fixed at `deos_create`; it affects throughput only (REQ-THR-004).
3. The operating system provides a barrier or the equivalent (futex, condition variable, or a spin-wait on an atomic counter); the Kernel's barrier implementation is not part of any hash and may differ across platforms.
4. BLAKE3 (plain and keyed) is available; its 32-byte output is the reference for every hash and derivation.
5. The Host owns persistent storage: the Kernel writes Snapshots and the Input Log into Host-provided buffers and never touches a file system.
6. Wall-clock never enters the Kernel (DEOS-CORE REQ-TICK-001, REQ-ORD-006); every "per second" figure in this document is a Host-side throughput target, not a Kernel input.
7. The `CatalystLedger` (DEOS section 5.4) is Kernel state: the Catalyst Budget's balance, capacity, and regeneration are enforced in Stage 1 with the constants DEOS-PLAY sets, and the record is hashed and serialized like the `Ledger`.

---

## 6. Requirements

### 6.1 Kernel/Host boundary (`ARCH`)

### REQ-ARCH-001: Headless Kernel Compilation

The Kernel must compile into a standalone dynamic library (`.so`, `.dll`, `.dylib`) or static archive with zero linking to graphics APIs (OpenGL, DirectX, Vulkan, Metal) or windowing systems (SDL, GLFW).

DEOS tightening: the Kernel's link set is the C runtime, a threading primitive, and a BLAKE3 implementation, and nothing else; the build fails if the link map names any other library. The ABI of REQ-ARCH-003 is the only entry surface; every symbol the library exports begins with `deos_`. The same source builds the headless CLI runner of DEOS-MVS, so the runner is a Host like any other.

Player-facing consequence: the same Kernel binary runs the phone build, the desktop build, the challenge verifier, and the overnight catch-up job, which is why all four agree on every Tick Hash (GI-1, GI-6).

### REQ-ARCH-002: Double-Buffered State Buffer

To allow concurrent visualization and simulation, component storage is double-buffered: Buffer A (read-only) is exposed to the Host for rendering and query streams; Buffer B (write-only) is modified strictly by ECS worker threads during tick `t`; at the end of tick `t`, pointers to Buffer A and Buffer B swap atomically.

DEOS tightening: the swap is Stage 6 substep 6.5 (DEOS-ECS REQ-MUT-010) and is performed by Worker 0 after the final barrier of the tick as a single pointer exchange in the Kernel context; the Host's view (REQ-ARCH-005) is stable from the return of one `deos_tick` to the entry of the next; the Host never receives a pointer into B. Single-buffered data (`entity_table`, `Genome`, `WorldMoodSlot`, `Ledger`, `CatalystLedger`) is exposed through the same view because it is written only in Stage 6 substeps or at the end of Stage 5, when no Host call is in progress (assumption 1).

Player-facing consequence: the Observation View never renders a half-written world; every frame is one whole tick (GI-6).

### REQ-ARCH-003: The C ABI

The Kernel exports exactly the functions below, with C linkage, the stated signatures, and the error codes of section 8.1. Every function returns `DEOS_OK` (0) or a negative error code, except those whose return is a count or a byte length. No function allocates after `deos_create`.

| Function | Signature | Semantics |
| :--- | :--- | :--- |
| `deos_version` | `uint32_t deos_version(void)` | `(major << 16) | (minor << 8) | patch` of the DEOS version implemented; `0x000100` for v0.1.0. |
| `deos_create` | `int deos_create(const DeosConfig* cfg, DeosKernel** out)` | validates `cfg` (section 8.2), allocates the single arena (DEOS-ECS REQ-DAT-003) and the Runtime pools of REQ-SNAP-001, builds the Core tables (`fx_tables_init`) and the `LAT` table, starts `THREADS − 1` Workers parked at a barrier, sets `state = CREATED`. |
| `deos_destroy` | `int deos_destroy(DeosKernel*)` | joins Workers, frees the arena and pools; the only deallocation. |
| `deos_seed` | `int deos_seed(DeosKernel*, uint64_t master_seed)` | stores the Master Seed; legal only in `CREATED`. |
| `deos_generate` | `int deos_generate(DeosKernel*)` | world generation (REQ-LOOP-002); sets tick 0, computes the tick-0 Tick Hash and Chunk Hashes, sets `state = READY`. |
| `deos_push_action` | `int deos_push_action(DeosKernel*, const CatalystAction* a)` | validates `a` per REQ-LOOP-003 rule 1 and appends it to the Input Log with `a->tick` overwritten by `max(a->tick, current_tick + 1)` and `a->seq` overwritten by the next sequence number for that tick; returns `DEOS_E_LOG_FULL` when the Input Log pool is full. |
| `deos_tick` | `int deos_tick(DeosKernel*)` | steps one tick (REQ-LOOP-001); returns `DEOS_E_EGRESS_FULL` without stepping when REQ-LOOP-008 rule 3 holds, `DEOS_E_HALTED` after a halting fault. |
| `deos_step` | `int deos_step(DeosKernel*, uint32_t n, uint32_t* done)` | calls `deos_tick` up to `n` times, stopping at the first non-`DEOS_OK` return; writes the count completed. |
| `deos_current_tick` | `uint64_t deos_current_tick(const DeosKernel*)` | the tick number of buffer A. |
| `deos_tick_hash` | `int deos_tick_hash(const DeosKernel*, uint8_t out[32])` | the Tick Hash of the last completed tick. |
| `deos_checkpoint_hash` | `int deos_checkpoint_hash(const DeosKernel*, uint64_t* tick, uint8_t out[32])` | the most recent Checkpoint Hash and its tick; `DEOS_E_NONE` before the first Checkpoint. |
| `deos_read_view` | `int deos_read_view(const DeosKernel*, DeosReadView* out)` | fills the read view of section 8.3 (buffer A base pointers, entity table, Cell arrays, global records, tick). |
| `deos_chronicle_poll` | `uint32_t deos_chronicle_poll(DeosKernel*, NotableEvent* out, uint32_t cap)` | copies up to `cap` records from the Chronicle ring in emission order and frees them; returns the count. |
| `deos_worldmood_poll` | `uint32_t deos_worldmood_poll(DeosKernel*, WorldMood* out, uint32_t cap)` | as above for the WorldMood ring. |
| `deos_set_egress_mode` | `int deos_set_egress_mode(DeosKernel*, uint8_t mode)` | `EGRESS_FULL` or `EGRESS_REDUCED` (REQ-SNAP-005); takes effect at the next tick. |
| `deos_input_log_export` | `uint64_t deos_input_log_export(const DeosKernel*, uint8_t* out, uint64_t cap)` | writes the Input Log (all entries, Checkpoints included) as 64-byte records in `(tick, seq)` order; returns the byte count (0 with `cap` too small: the required size is `deos_input_log_size`). |
| `deos_input_log_size` | `uint64_t deos_input_log_size(const DeosKernel*)` | bytes the export needs. |
| `deos_input_log_import` | `int deos_input_log_import(DeosKernel*, const uint8_t* in, uint64_t len)` | replaces the Input Log; legal only in `CREATED` or `READY` at tick 0; validates every record (REQ-LOOP-004). |
| `deos_snapshot_size` | `uint64_t deos_snapshot_size(const DeosKernel*)` | bytes `deos_snapshot_write` needs at the current tick. |
| `deos_snapshot_write` | `uint64_t deos_snapshot_write(const DeosKernel*, uint8_t* out, uint64_t cap)` | REQ-SNAP-002; legal between ticks; returns the byte count. |
| `deos_snapshot_read` | `int deos_snapshot_read(DeosKernel*, const uint8_t* in, uint64_t len)` | REQ-SNAP-003; replaces the world; the Input Log is replaced by the Snapshot's embedded prefix. |
| `deos_verify` | `int deos_verify(const DeosConfig* cfg, uint64_t master_seed, const uint8_t* log, uint64_t len, uint64_t* first_bad_tick)` | REQ-SNAP-004; creates a private Kernel, replays, compares every embedded Checkpoint; `DEOS_OK` when all match, `DEOS_E_DESYNC` with the first mismatching Checkpoint tick otherwise. |
| `deos_desync_report` | `int deos_desync_report(const DeosKernel*, DesyncReport* out)` | after a `DEOS_E_DESYNC` from `deos_tick` or `deos_verify`: the localization of REQ-HASH-005. |
| `deos_stats` | `int deos_stats(const DeosKernel*, DeosStats* out)` | diagnostics of section 8.4 (`fx_flags_tick`, ledger dissipation sums, events dropped, per-stage Worker cycle counts when compiled in); never hashed. |

Rules:
1. Every pointer argument is validated for non-null and, for buffers, for the stated capacity; a violation returns `DEOS_E_ARG` and changes nothing.
2. State machine: `CREATED → (deos_seed) → CREATED → (deos_generate | deos_snapshot_read) → READY → (deos_tick) → READY | HALTED`. A call illegal in the current state returns `DEOS_E_STATE`.
3. The ABI is versioned by `deos_version`; a Host built against a different major or minor refuses to run.

Player-facing consequence: the Host is a renderer and a log writer, nothing more, so a bug in the Host cannot change the world and a replay of the Input Log on the verifier is the whole truth of what the player did (GI-2, GI-6).

### REQ-ARCH-004: Single-caller discipline

All ABI calls are made from one Host thread. The Kernel detects a concurrent call by an atomic `in_call` flag set on entry and cleared on exit; a second entry while the flag is set returns `DEOS_E_REENTRANT` immediately and does nothing. Workers never call the ABI.

### REQ-ARCH-005: The read view

`DeosReadView` (section 8.3) exposes buffer A, the entity table, the Genome pool, buffer A's Cell field arrays, the `Ledger`, the `CatalystLedger`, the `WorldMoodSlot`, the current tick, and the scale constants, as `const` base pointers plus counts. The view is valid until the next `deos_tick`, `deos_generate`, `deos_snapshot_read`, or `deos_destroy`. The Host reads through the view and never writes through it (the pointers are `const`; a Host that casts away `const` is non-conformant, GI-6). The three Observation View layers of DEOS-PLAY are bound to this view and nothing else.

Player-facing consequence: everything on screen is authoritative state; there is no Host-side model that could drift from the Kernel (GI-6).

### 6.2 The tick pipeline (`LOOP`)

### REQ-LOOP-001: 6-Stage Deterministic Pipeline

Every simulation tick (`t → t+1`) executes six stages in strict temporal sequence: Stage 1 Ingress (process incoming player catalyst actions and environmental mutations); Stage 2 Physical & Environmental (energy conservation, diffusion, thermodynamics, landform decay); Stage 3 Biological & Metabolic (cellular respiration, energy consumption, biological decay, reproduction); Stage 4 Cognition & Decision (utility function scoring, action choice resolution, memory updates); Stage 5 Societal & Cultural (meme-vector exchange, trust score recalculation, institution maintenance); Stage 6 State Hash & Synchronization (compute the state checksum; swap double buffers).

DEOS tightening: the stages carry the DEOS section 5.2 names (Ingress, Substrate, Biology, Cognition, Society, Commit); the sub-order inside every stage is section 7.1 and is binding; every stage ends with a barrier, and Stages 3, 4, and 5 end with the Command resolution of DEOS-ECS REQ-MUT-006 before their barrier is considered complete; the "state checksum" is the Tick Hash of REQ-HASH-002 with the Checkpoint Hash of REQ-HASH-003 at Checkpoint ticks.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 TICK t → t+1                                            │
├──────────┬──────────────┬───────────────┬───────────────┬───────────────┬──────────────┤
│ Stage 1  │ Stage 2      │ Stage 3       │ Stage 4       │ Stage 5       │ Stage 6      │
│ Ingress  │ Substrate    │ Biology       │ Cognition     │ Society       │ Commit       │
│ log →    │ 2a … 2j      │ metabolism,   │ SpatialIndex, │ transmission, │ 6.1 … 6.5    │
│ overlay, │ (Core)       │ Lifecycle,    │ Perception,   │ trust, Insti- │ hashes,      │
│ Budget,  │              │ reproduction  │ utility,      │ tutions,      │ Checkpoint,  │
│ expansion│              │ (Protocol)    │ Decision      │ WorldMood     │ flush, swap  │
│          │              │ + barrier     │ (Protocol)    │ (Protocol)    │              │
│          │              │   resolution  │ + resolution  │ + resolution  │              │
└──────────┴──────────────┴───────────────┴───────────────┴───────────────┴──────────────┘
```

Player-facing consequence: because the order never changes, a Catalyst Action stamped for tick `t` is felt by the Substrate in the same tick, by metabolism one stage later, by decisions two stages later, and by institutions three stages later, on every device (GI-1).

### REQ-LOOP-002: World generation at tick 0

`deos_generate` builds the tick-0 world from the Master Seed alone, in this order, using only Streams of SystemID 0 (`WORLDGEN`) at tick 0 (DEOS-CORE REQ-PRNG-005 rule 4):

1. **Lattice noise.** Two lattices of Q32.32 values in `[0, 1)`, `L1` with spacing 16 Cells and `L2` with spacing 4 Cells, each point `(i, j)` of lattice `k` and field `f` drawn as the first `uniform_q32()` of the Stream derived with `ChunkIndex = 0x80000000 | (k << 28) | (f << 24) | (j << 12) | i` (a namespace disjoint from Cell Chunk indices, which are below `2^20`). Fields: `f = 0` elevation, `f = 1` moisture, `f = 2` fertility. A lattice has `GRID_W / spacing + 1` by `GRID_H / spacing + 1` points; the last column and row duplicate the first (`i mod (GRID_W / spacing)`), so interpolation at the far edge is defined.
2. **Per-Cell noise.** For Cell `(x, y)` and lattice spacing `s`: `i = x / s`, `j = y / s`, `u = fx_from_int(x mod s) / s`, `v = fx_from_int(y mod s) / s` (Q32.32 divisions by the integer `s`, floor); `n = lerp(lerp(P[i][j], P[i+1][j], u), lerp(P[i][j+1], P[i+1][j+1], u), v)` with `lerp(a, b, w) = a + fx_mul(b − a, w)`. `noise_f(x, y) = (3·n1 + n2) >> 2` using `L1` and `L2` of field `f` (weights 0.75 and 0.25; the shift is arithmetic).
3. **Fields.** In Cell index order per Cell Chunk (parallel by Cell Chunk):
   - `elevation = fx_mul(FX_ELEV_MAX, noise_0)`.
   - `material = elevation < fx_mul(FX_ELEV_MAX, 0.35) ? WATER : elevation > fx_mul(FX_ELEV_MAX, 0.80) ? ROCK : SOIL`.
   - `temperature = max(0, fx_mul(4.0, LAT[y]) − fx_mul(2.0, fx_div(elevation, FX_ELEV_MAX)))`; then WATER with `temperature < FX_FREEZE_T` becomes ICE.
   - `moisture = material == WATER ? FX_ONE : fx_mul(FX_HALF, noise_1)`.
   - `energy = fx_mul(FX_INIT_CELL_ENERGY[material], FX_HALF + (noise_2 >> 1))` with `FX_INIT_CELL_ENERGY = { WATER 16.0, SOIL 64.0, ROCK 4.0, ICE 0 }`.
   - `mutation_bias = FX_ONE`.
   - `atmosphere = N_CELLS × 0.1` (Q32.32, exact); `e_total`, `m_total` computed per DEOS-CORE section 7.3.1; all other `Ledger` fields 0.
4. **Springs.** `SPRINGS` Cells (DEOS-MVS fixes the count; 1,024 at MVS scale) receive `energy = FX_CELL_ENERGY_CAP >> 4`: the Cells are chosen by `SPRINGS` draws of `bounded(N_CELLS)` from the Stream `ChunkIndex = 0xC0000000`, skipping WATER and ICE Cells (draw again; the draw count is data-dependent only within this one Stream), each chosen Cell set once (a repeated index is drawn again).
5. **Population.** `ORGANISMS` then `AGENTS` `SPAWN` Commands (DEOS-MVS fixes the counts) are issued into the ingress lifecycle outbox in that order with `source = NULL_ENTITY_ID` and ascending `seq`, positions drawn from the Stream `ChunkIndex = 0xC0000001` as `bounded(N_CELLS)` re-drawn while the Cell's material is WATER or ICE, `x = fx_from_int(cell mod GRID_W) + FX_HALF`, `y = fx_from_int(cell / GRID_W) + FX_HALF`, `payload[0] = 40.0`, archetype `ARCH_ORGANISM` or `ARCH_AGENT`, `aux = 0xFFFFFFFFFFFFFFFF` (Genome from the `SPAWN_INIT` Stream, REQ-LOOP-006). The ingress lifecycle outbox capacity (1,024) is smaller than the population: generation issues the Commands in batches of 1,024 and runs DEOS-ECS substeps 6.1 to 6.3 after each batch, all at tick 0, so slot assignment is ascending in issue order regardless of batching.
6. **Tick-0 hashes.** The Chunk Hashes, the Checkpoint Hash for tick 0 (recorded as the first Input Log entry, REQ-LOOP-004), and the tick-0 Tick Hash (write folds over the whole of buffer A as if written) are computed; `state = READY`.

`FX_INIT_CELL_ENERGY`, the 0.35 and 0.80 thresholds, and the lattice spacings are generation constants of this module (section 8.6). World generation is a pure function of `(scale, master_seed, ORGANISMS, AGENTS, SPRINGS)`; DEOS-MVS fixes the three counts per scale so that a Master Seed alone names a world.

Player-facing consequence: a seed is a world: coastlines, mountains, a frozen north and a temperate belt, springs, and a founding population, all derived from 64 bits, identical on every device, and shareable as a 16-character code (GI-1, DEOS-PLAY).

### REQ-LOOP-003: Stage 1 Ingress

Stage 1 runs on Worker 0 alone (its cost is bounded by `MAX_INGRESS_WRITES_PER_TICK`). In order:

1. **Regeneration.** `CatalystLedger.balance = min(balance + regen_per_tick, capacity)` (Q32.32, `fx_add` then `fx_min`), using the constants of DEOS-PLAY held in the record.
2. **Selection.** The Input Log entries with `tick == t`, in ascending `seq`. Entries with kind `≥ 0x8000` (Runtime records) are skipped here; they are consumed by REQ-LOOP-004.
3. **Validation**, per entry, in this order; the first failure rejects the entry with `NotableEvent` kind 1 `INGRESS_REJECTED` (`subject = NULL_ENTITY_ID`, `object = NULL_ENTITY_ID`, `cell = target` for Cell targets, `magnitude = cost`, `cause = the failing check number 1 to 6`), and rejected entries stay in the Input Log so that a replay rejects them identically:
   1. `kind` is defined by DEOS-PLAY (`CAT`) and `target_kind` matches the kind's target class;
   2. a Cell target is below `N_CELLS`; an entity target validates in A (DEOS-ECS REQ-ENT-004); a global target is 0;
   3. every payload element is within the kind's range (DEOS-PLAY table) and the resulting Cell values respect DEOS-CORE REQ-LAW-012 (a write below 0, an `elevation` outside `[0, FX_ELEV_MAX]`, a `material_id ≥ 4`, or a `mutation_bias` outside `[0.25, 4.0]` after clamping is a rejection only when the clamp would change the sign of the effect; otherwise the write is clamped);
   4. `cost` equals the cost DEOS-PLAY's formula gives for `(kind, payload, radius)`; a mismatch is a rejection (the Host computes the same formula, so a mismatch is a tampered log);
   5. `cost ≤ CatalystLedger.balance`;
   6. the Catalyst energy credit would not raise `E_total` above `FX_WORLD_ENERGY_MAX`, nor the moisture total above `FX_WORLD_MOISTURE_MAX`.
4. **Application**, per accepted entry: `balance −= cost`, `spent_total += cost`, `actions_applied += 1`; the entry is expanded into `IngressWrite` records per the DEOS-PLAY expansion table (a primitive kind yields one write; a composite (Cosmic) kind yields the table's list, in table order, with any draws taken from the SystemID 1 (`SUBSTRATE`) Stream of the target's Cell Chunk at tick `t`, Substream `CHUNK_SIZE`, in table order); each `IngressWrite` carries the entry's `seq` and is pushed with `ecs_ingress_overlay_push`. When the overlay is full the entry is rejected with `cause = 7` and its Budget debit is reverted (the debit and the push are one operation).
5. **Ledger.** Cell energy and moisture writes are recorded in `Ledger.e_cat` and `m_cat` by `ledger_catalyst_energy` and `ledger_catalyst_moisture` when Stage 2 applies the overlay (DEOS-CORE section 9 obligation), not here; Stage 1 only counts.
6. **Notable Event.** Every accepted entry emits kind 5 `CATALYST_APPLIED` (`cell = centre Cell or 0`, `magnitude = cost`, `cause = kind`) into Worker 0's event outbox.

The IngressOverlay is reset at the start of Stage 1 (`ecs_ingress_overlay_reset`). Stage 1 issues no stage-resolved Commands and writes no state buffer (DEOS-ECS REQ-MUT-011).

Player-facing consequence: an action lands in the tick the player aimed at, costs exactly what the Palette said, and is refused with a reason the Chronicle shows rather than silently shrinking; the Budget is a visible, deterministic valve (GI-6, GI-8).

### REQ-LOOP-004: Input Log records and Checkpoints

The Input Log is an array of 64-byte `CatalystAction` records ordered by `(tick, seq)`, with `seq` unique per tick. Kinds `≥ 0x8000` are Runtime records:

| Kind | Name | Fields | Written when |
| :--- | :--- | :--- | :--- |
| `0x8000` | `CHECKPOINT` | `tick`; `seq = 0xFFFFFFFF`; `target_kind = 0`; `target = 0`; `payload[0..3]` = the 32-byte Checkpoint Hash as four little-endian `uint64_t`; `cost = 0` | Stage 6 of every Checkpoint tick and at tick 0 (REQ-HASH-004) |
| `0x8001` | `SNAPSHOT_MARK` | `tick`; `seq = 0xFFFFFFFE`; `payload[0]` = Snapshot byte length; `payload[1..3]` = the first 24 bytes of the Snapshot's BLAKE3-256 | `deos_snapshot_write` |
| `0x8002` … `0x80FF` | reserved | — | — |

Rules:
1. A Runtime record is never accepted through `deos_push_action` (`DEOS_E_ARG`).
2. `deos_input_log_import` validates that records are in `(tick, seq)` order, that every `CHECKPOINT` has `tick mod CHECKPOINT_INTERVAL == 0` or `tick == 0`, and that no two records share `(tick, seq)`; otherwise `DEOS_E_LOG_FORMAT`.
3. On import, `CHECKPOINT` records are the expected values `deos_verify` and `deos_tick` compare against (REQ-HASH-005 rule 1).
4. The Input Log pool holds `INPUT_LOG_CAPACITY` records (section 8.5); the Host exports and truncates on Snapshot to bound it.

Player-facing consequence: the save file is one flat list of what the player did and what the world's fingerprint was every 64 ticks; a shared world is that list plus a seed (GI-2, GI-3).

### REQ-LOOP-005: Stage sub-order and barriers

The exact sequence of section 7.1 is binding: which systems run in which stage, in which order, over which unit, and where every barrier falls. A conforming Kernel may fuse two consecutive rows only when no barrier separates them and the fused pass writes the same bytes in the same order.

### REQ-LOOP-006: Runtime SystemIDs

This module assigns, in the range DEOS-CORE section 7.5.1 leaves to it:

| SystemID | Name | Used by |
| :--- | :--- | :--- |
| 16 | `SPAWN_INIT` | DEOS-ECS substep 6.2 Genome initialization for Ingress and tick-0 spawns (`prng_derive(master, 16, t, target Chunk)`, Substream = slot, 32 `bounded(65536)` draws) |
| 17 | `EVENT_SELECT` | REQ-SNAP-005 reduced-egress selection (no draws in v0.1.0; reserved so the rule has a Stream if it ever needs one) |
| 18 … 31 | reserved | Runtime |

DEOS-PROTO assigns from 32 upward.

### REQ-LOOP-007: Event outboxes and the Stage 6 flush order

Every Worker appends the `NotableEvent` records it emits (Stage 1 rejections and applications on Worker 0; `COMMAND_DROPPED` in DEOS-ECS pass 2; every DEOS-PROTO event) to the event outbox of the Chunk or Cell Chunk it is processing (Worker 0's Stage 1 events go to outbox index 0). Each outbox holds `EVENT_OUTBOX` = 256 records per tick.

Overflow rule: when an outbox is full, the new record replaces the entry with the smallest `magnitude` if the new record's `magnitude` is greater (ties: the existing entry stays); otherwise the new record is discarded. In either case the outbox's `dropped` counter increments. At flush, an outbox with `dropped > 0` emits one additional record of kind 8 `EVENT_OVERFLOW` (`subject = NULL_ENTITY_ID`, `cell` = the first Cell of the Chunk's first live entity or the Cell Chunk's first Cell, `magnitude = fx_from_int(dropped)`, `cause = 0`) after its 256 records. Reserved kinds 1 to 7 are never replaced by the overflow rule (they are protected; a protected record is replaced only by a protected record of higher `magnitude`).

Flush (Stage 6 substep 6.5, Worker 0): outboxes are appended to the Chronicle ring in ascending index (entity Chunks 0 … `NUM_CHUNKS − 1`, then Cell Chunks 0 … `NUM_CELL_CHUNKS − 1`), each in its emission order, then cleared. Emission order within a Chunk is the canonical Slot order of the emitting pass, then stage order, so the flush order is a pure function of the tick's computation.

Player-facing consequence: the Chronicle is complete up to a stated, visible cap, and when a tick is too eventful to record in full the player sees a row saying so rather than silence (GI-5).

### REQ-LOOP-008: Egress rings and backpressure

1. The Chronicle ring holds `CHRONICLE_RING` = 65,536 `NotableEvent` slots (4 MiB); the WorldMood ring holds `WORLDMOOD_RING` = 4,096 `WorldMood` slots (256 KiB). Both are single-producer (Stage 6, Worker 0) single-consumer (the Host through the poll functions).
2. Stage 6 emits the tick's `WorldMood` record before the tick's Notable Events.
3. `deos_tick` refuses to step (returns `DEOS_E_EGRESS_FULL`, world unchanged) when the Chronicle ring has fewer than `(NUM_CHUNKS + NUM_CELL_CHUNKS) × (EVENT_OUTBOX + 1)` free slots or the WorldMood ring has no free slot. The Kernel never drops an emitted record to make room; the Host must poll.
4. In `EGRESS_REDUCED` mode (REQ-SNAP-005) the flush writes to the reduction buffer instead of the ring, and rule 3 does not apply.

Player-facing consequence: no event is ever lost between the Kernel and the screen; if the Host falls behind, time waits (GI-5).

### 6.3 Threading and Chunk dispatch (`THR`)

### REQ-THR-001: Worker pool and work units

`THREADS` Workers exist for the life of the Kernel. A step of the pipeline (section 7.1) is a list of work units generated in canonical order (ascending Chunk or Cell Chunk index, for each system in the step's system order). Workers claim work units from a shared atomic counter (work-stealing by index); the assignment of units to Workers is unspecified and unobservable.

### REQ-THR-002: Independence obligation

A step may be executed in parallel only if every work unit of the step writes memory disjoint from every other unit's writes and reads no memory another unit of the same step writes. Every step of section 7.1 satisfies this by construction of DEOS-ECS REQ-MUT-002, REQ-MUT-006 (each pass writes exclusively owned data), REQ-MUT-008, and DEOS-CORE REQ-TICK-003 (sub-steps 2b and 2c read `X⁰` only). A new step is admitted to the pipeline only with a written proof of this property in its module.

### REQ-THR-003: Barriers and serial steps

A barrier follows every step. Serial steps (DEOS-ECS substep 6.1, the DEOS-CORE folds of sub-step 2j and the Stage 6 ledger fold, the flush, the swap) run on Worker 0 while the other Workers wait at the barrier. There are no locks, no atomics other than the work counter and the barrier, and no data structure whose content depends on Worker arrival order (DEOS-CORE REQ-ORD-006).

### REQ-THR-004: Thread-count identity

For every `THREADS` in `[1, 64]`, the same `(scale, master_seed, Input Log)` produces the same sequence of Tick Hashes and Checkpoint Hashes. The `THREADS = 1` execution is the reference; TS-BENCH-002 runs 1 and 4. A Kernel that produces a different hash at any thread count is non-conformant regardless of which count is "right".

Player-facing consequence: the phone with two cores and the desktop with sixteen agree about the world, so the leaderboard is fair and the shared seed is honest (GI-1).

### 6.4 State hashing (`HASH`)

### REQ-HASH-001: Write folds

A write fold is a `uint64_t` computed by the Worker that writes, over the little-endian canonical bytes of what it writes, by the fold function

```
fold_init()            = 0x9E3779B97F4A7C15
fold_word(h, w)        = rotl64((h ^ w) * 0xBF58476D1CE4E5B9, 29)        // w: one little-endian uint64 word
fold_bytes(h, b[0..n)) = fold_word over each 8-byte word of b; a final partial word is zero-padded to 8 bytes
                         and followed by fold_word(h, n)
```

Folds are kept per (Chunk, component) and per (Cell Chunk, field) for owner writes, per (Chunk or Cell Chunk, stage) for Command applications (the fold is over the 64-byte `Command` record with its written-back payload, in application order, pass by pass), per Chunk for DEOS-ECS substeps 6.2 and 6.3 (over the initialized or zeroed slot records in order), and one for the IngressOverlay (over the `IngressWrite` records in `seq` order). Every fold is reset to `fold_init()` at the start of Stage 1. Folds are never hashed as in-memory bytes: the Worker folds exactly the bytes REQ-DAT-007 would serialize for the record it just wrote.

Why folds are sufficient for desync detection: B at the end of a tick is a pure function of A and the sequence of writes to B; two executions whose write sequences are identical byte for byte have identical B. A difference in any write changes the fold of its (unit, stage) with probability `1 − 2^-64` per fold, and the Tick Hash combines every fold.

### REQ-HASH-002: Tick Hash

At Stage 6 substep 6.4, after the ledger check, Worker 0 computes

```
TickHash(t) = BLAKE3-256( 0x54 ‖ LE64(t)
                          ‖ folds of entity Chunks 0..NUM_CHUNKS−1, each Chunk's folds in the order:
                              components #0..#11 owner folds, then stage-3, stage-4, stage-5 Command folds,
                              then the substep 6.2 and 6.3 folds
                          ‖ folds of Cell Chunks 0..NUM_CELL_CHUNKS−1, each in the order:
                              fields 0..5 owner folds, then the stage-3, stage-4, stage-5 Command folds
                          ‖ the IngressOverlay fold
                          ‖ Ledger (176 bytes, DEOS-CORE section 8.3)
                          ‖ CatalystLedger (48 bytes, DEOS section 5.4)
                          ‖ WorldMoodSlot (64 bytes) )
```

with `0x54` a one-byte domain tag. The input is `12 × 8 × NUM_CHUNKS` plus a bounded constant: 3.2 KiB at MVS scale, 200 KiB at v1.0 scale; the hash costs under 0.05 ms at either scale. The Tick Hash of a tick is stored in a ring of the last `CHECKPOINT_INTERVAL` values (REQ-HASH-005) and returned by `deos_tick_hash`.

Player-facing consequence: every tick has a fingerprint, so a Desync is caught within one tick of happening, not at the next Checkpoint, and the player's replay diverges at a tick the game can name (GI-3).

### REQ-HASH-003: Chunk Hashes and the Checkpoint Hash

At a Checkpoint tick (and at tick 0), after substep 6.3 and before the swap:

1. Every entity Chunk `c` and Cell Chunk `e` is serialized by `ecs_serialize_chunk` / `ecs_serialize_cell_chunk` from buffer B into the Worker's serialization buffer (1,589,248 or 1,884,160 bytes for an Institution Chunk; 41,984 bytes for a Cell Chunk) and hashed: `ChunkHash(c) = BLAKE3-256(0x43 ‖ LE32(c) ‖ stream)`, `CellChunkHash(e) = BLAKE3-256(0x45 ‖ LE32(e) ‖ stream)`. This is parallel by Chunk.
2. The leaves, in order, are the `NUM_CHUNKS` Chunk Hashes, the `NUM_CELL_CHUNKS` Cell Chunk Hashes, `BLAKE3-256(0x4C ‖ Ledger)`, `BLAKE3-256(0x42 ‖ CatalystLedger)`, and `BLAKE3-256(0x4D ‖ WorldMoodSlot)`.
3. Merkle combination (Worker 0): repeatedly replace each adjacent pair `(a, b)` in the list by `BLAKE3-256(0x4E ‖ a ‖ b)`; an unpaired last element is carried up unchanged; stop at one element `root`.
4. `CheckpointHash(t) = BLAKE3-256(0x4B ‖ LE64(t) ‖ LE32(scale) ‖ LE32(NUM_CHUNKS) ‖ LE32(NUM_CELL_CHUNKS) ‖ root)`.

The per-Chunk hashes are retained in the Kernel until the next Checkpoint tick for `deos_desync_report`.

`CHECKPOINT_INTERVAL` is a scale-profile value: 64 at `SCALE_MVS`, `SNAPSHOT_INTERVAL` (3,600) at `SCALE_V1`, because the canonical stream is 1.69 GB at v1.0 scale (DEOS-ECS section 11) and hashing it every 64 ticks would consume the tick budget of every second (ADR-0001). The registry table of DEOS section 5.1 records both values.

Player-facing consequence: a Checkpoint is a fingerprint of every byte of the world, so a challenge verifier that matches every Checkpoint has proven the whole run, and one that does not can say which Chunk of which tick differs (GI-3).

### REQ-HASH-004: Checkpoint records

At every Checkpoint tick and at tick 0, Worker 0 appends a `CHECKPOINT` record (REQ-LOOP-004) carrying `CheckpointHash(t)` to the Input Log before the buffer swap. If the Input Log already holds a `CHECKPOINT` for tick `t` (imported expected values), the computed hash is compared with it instead of appended (REQ-HASH-005 rule 1).

### REQ-HASH-005: Desync detection and localization

1. **Detection.** On an imported Input Log, at every tick that carries an expected `CHECKPOINT`, the computed Checkpoint Hash is compared; on inequality the Kernel emits `NotableEvent` kind 3 `DESYNC` (`magnitude = fx_from_int(t)`, `cause = 0`), completes the flush and swap so the faulty tick is inspectable, sets `state = HALTED`, and `deos_tick` returns `DEOS_E_DESYNC`. `deos_verify` returns the same tick in `first_bad_tick`.
2. **Localization by Chunk.** `deos_desync_report` returns the tick, the expected and computed Checkpoint Hashes, and the list of leaf indices whose Chunk Hashes differ from a reference list when the Host supplies one (`DesyncReport.reference_leaves`, obtained from the other party's Kernel by the same call); when no reference is supplied the report carries the computed leaves so the Host can exchange them.
3. **Localization by tick.** Both parties retain the last `CHECKPOINT_INTERVAL` Tick Hashes (REQ-HASH-002 ring); comparing the rings gives the first divergent tick within the interval.
4. **Localization by stage** (debug builds): with `DEOS_DEBUG_STAGE_FOLDS` compiled in, the report also carries the per-stage fold list of the first divergent tick, naming the stage, Chunk, and component or Command pass that first differs.
5. A Desync is always a defect (DEOS section 4). The Kernel never resynchronizes, retries, or continues silently.

Player-facing consequence: when two devices disagree, the game can say "tick 8,192, Chunk 7, Stage 4" instead of "something went wrong", and the report is a bug the player can file with one seed and one log (GI-1, GI-3).

### REQ-HASH-006: Ledger faults

When DEOS-CORE `ledger_stage6_check` returns a non-zero fault code, Worker 0 emits `NotableEvent` kind 7 `LEDGER_FAULT` (`magnitude = fx_from_int(fault)`, `cause = 0`), completes the tick (hashes, flush, swap), and sets `state = HALTED` so that `deos_tick` returns `DEOS_E_LEDGER`. The faulty tick's Tick Hash is emitted, so the fault itself is reproducible (DEOS-CORE REQ-LAW-004 rule 5).

### 6.5 Snapshots, replay, Acceleration (`SNAP`)

### REQ-SNAP-001: Runtime pools

Beyond the ECS arena, `deos_create` allocates once: the Input Log pool (`INPUT_LOG_CAPACITY` records), the Chronicle and WorldMood rings, the event outboxes, the per-Worker serialization buffer (one Chunk's canonical stream), the Chunk Hash lists (two lists of `NUM_CHUNKS + NUM_CELL_CHUNKS + 3` hashes), the Tick Hash ring, the reduction buffer of REQ-SNAP-005, and the `LAT` table. Sizes are in section 8.5; none is resized after creation (DEOS-ECS REQ-DAT-002 applies to this module).

### REQ-SNAP-002: Snapshot format

A Snapshot is the ECS payload of DEOS-ECS REQ-DAT-008 followed by Runtime sections, each with a `SectionHeader`, in this order:

| `kind` | Name | Content | Length |
| :--- | :--- | :--- | :--- |
| 16 | `RT_HEADER` | `{ deos_version u32, scale u32, threads_hint u32, pad u32, master_seed u64, tick u64, checkpoint_interval u32, snapshot_interval u32 }` | 40 |
| 17 | `LEDGER` | the `Ledger` record | 176 |
| 18 | `CATALYST_LEDGER` | the `CatalystLedger` record | 48 |
| 19 | `TICK_HASH_RING` | `CHECKPOINT_INTERVAL` × 32 bytes, oldest first, plus `LE64(count)` | 8 + 32 × `CHECKPOINT_INTERVAL` |
| 20 | `INPUT_LOG` | every Input Log record with `record.tick ≤ tick` (Checkpoints included), in order | 64 × n |
| 21 | `CHRONICLE_CURSOR` | `LE64(total events emitted since tick 0)` | 8 |
| 22 | `CHUNK_HASHES` | the retained leaf list of the last Checkpoint (REQ-HASH-003 rule 2) and its tick | 8 + 32 × leaves |

The Snapshot ends with `BLAKE3-256(0x53 ‖ all preceding bytes)` as a 32-byte trailer; `deos_snapshot_write` also appends a `SNAPSHOT_MARK` to the Input Log. A Snapshot is legal only between ticks (state `READY`), which guarantees every outbox is empty and every fold is reset, so no derived structure needs serializing (DEOS-ECS REQ-DAT-008 restore rebuilds them).

### REQ-SNAP-003: Restore and continuation identity

`deos_snapshot_read` verifies the trailer, the `RT_HEADER` version and scale against the Kernel, then the ECS sections (DEOS-ECS REQ-DAT-008 restore), then loads the Runtime sections, rebuilds every derived structure, sets `state = READY` at the Snapshot's tick. The Master Seed comes from `RT_HEADER`. Stepping from a restored Snapshot produces the Tick Hash and Checkpoint Hash sequences of the original run (DEOS section 4), because the Kernel step is a pure function of buffer A, the entity table, the Genome pool, the global records, the Master Seed, the tick, and the Input Log (DEOS-CORE REQ-TICK-004), all of which the Snapshot carries.

Player-facing consequence: rewind is exact: restoring the day-12 Snapshot and stepping to day 14 shows the same day 14 the player already lived, and branching from it starts a Seed Lineage child whose divergence is entirely the player's new actions (GI-2, DEOS-PLAY).

### REQ-SNAP-004: Replay and verification

Replay is `deos_create`, `deos_seed`, `deos_input_log_import`, `deos_generate`, then `deos_tick` until the last record's tick. `deos_verify` performs exactly this in a private Kernel with `THREADS = cfg->threads`, in `EGRESS_REDUCED` mode with the reduction buffer discarded, comparing every embedded `CHECKPOINT` (REQ-HASH-005 rule 1); it returns at the first mismatch. At MVS scale a 10,000-tick log verifies within the DEOS-F05 P4 budget (5.0 s) because verification is the same computation as play at `MIN_ACCELERATION` throughput.

Player-facing consequence: a challenge submission is verified by running it, not by trusting it; a forged score is impossible because there is no score, only a log whose every 64th tick is fingerprinted (GI-1, GI-3).

### REQ-SNAP-005: Acceleration and reduced egress

Acceleration is the Host calling `deos_tick` in a loop with `EGRESS_REDUCED` set. In reduced mode:

1. `WorldMood` records are written to the WorldMood ring only every `TICKS_PER_DAY` ticks (the tick's record when `t mod TICKS_PER_DAY == 0`); the Host may still poll.
2. Notable Events are flushed (REQ-LOOP-007 order) into the reduction buffer, which holds `REDUCTION_CAPACITY` = 4,096 records per Epoch plus every reserved-kind record (kinds 1 to 8) unconditionally. Domain-kind records (kind ≥ 16) compete for the 4,096 slots by the key `(magnitude descending, tick ascending, kind ascending, subject ascending)`: a new record replaces the current minimum-key record when its key is greater. At every Epoch boundary (`t mod TICKS_PER_EPOCH == 0`) and when the mode returns to `EGRESS_FULL`, the buffer's records are emitted to the Chronicle ring in `(tick, flush order)` order and the buffer is cleared. The selection is deterministic and consumes no draw.
3. Nothing else changes: every stage, every write, every fold, every hash is identical to `EGRESS_FULL` (DEOS-CORE REQ-TICK-004; GI-4). A Kernel whose Tick Hash sequence differs between the modes is non-conformant.
4. Throughput obligation: at `SCALE_MVS` on the DEOS-MVS baseline hardware with `THREADS = 4`, `deos_tick` in reduced mode sustains `MIN_ACCELERATION` (32× real time, 1,920 ticks per second), so an Epoch (108,000 ticks) completes within 60 s (DEOS-F05 P3). The Host streams the Chronicle to the player while stepping (DEOS-PLAY); the Kernel imposes no minimum batch.

Player-facing consequence: the world that greets the player after a night away is the world that would have happened had they watched; the only thing Acceleration compresses is the Chronicle, and it keeps the biggest stories and every warning (GI-4, GI-5).

### REQ-SNAP-006: Hosting-neutral continuity

Offline continuity may be realized by the Host stepping the Kernel on the player's device when they return (client-side Acceleration) or by a server stepping the same Kernel continuously with the same Input Log; both produce identical Tick Hashes and Checkpoints (REQ-THR-004, REQ-SNAP-005 rule 3), so a world may move between the two at any Snapshot without any player-visible difference. DEOS-PLAY chooses the policy per product; this module guarantees the equivalence.

---

## 7. Algorithms & Mathematics

### 7.1 The pipeline, step by step

Every row is one step; a barrier follows every row. "Unit" is the parallel unit; "W0" means Worker 0 alone. Module columns name the rule; this table names the order.

| # | Stage | Step | Unit | Rule |
| :--- | :--- | :--- | :--- | :--- |
| 1.1 | 1 | reset event outboxes, folds, Chunk ledgers, IngressOverlay | W0 | REQ-LOOP-007, REQ-HASH-001, DEOS-ECS REQ-MUT-009/011 |
| 1.2 | 1 | Budget regeneration; select, validate, apply Input Log entries; overlay pushes; events | W0 | REQ-LOOP-003 |
| 2.a–2.i | 2 | DEOS-CORE sub-steps 2a … 2i, each over every Cell Chunk, IngressOverlay applied in 2a's read of `X⁰` for `energy`, `temperature`, `moisture`, `elevation`, `material_id`, `mutation_bias` | Cell Chunk | DEOS-CORE REQ-TICK-003; DEOS-ECS REQ-MUT-011 rule 1 |
| 2.j | 2 | ledger partial fold | W0 | DEOS-CORE sub-step 2j |
| 3.1 | 3 | Biology owner pass: metabolism, Lifecycle, Needs levels, reproduction (SpawnPayload + `SPAWN`), death (`DESPAWN`), Organism passive feeding (`CELL_ENERGY_DELTA`) | Chunk | DEOS-PROTO Stage 3 |
| 3.2 | 3 | Command resolution passes 1, sort, 2, 3, reset | per DEOS-ECS | DEOS-ECS REQ-MUT-006 (each pass is its own step and barrier) |
| 4.0 | 4 | SpatialIndex build (collect, prefix sum, two radix passes, boundaries) | per DEOS-ECS | DEOS-ECS REQ-DAT-009 (each phase is its own step) |
| 4.1 | 4 | Cognition owner pass: Perception, utility, Decision + Trace, Memory, Needs weights, `Position2D`; physical action Commands (`CELL_ENERGY_DELTA` draw for FEED, `DAMAGE` for CONTEST) | Chunk | DEOS-PROTO Stage 4 |
| 4.2 | 4 | Command resolution | per DEOS-ECS | DEOS-ECS REQ-MUT-006 |
| 5.1 | 5 | Society owner pass: overlay `MEME_DELTA` application, transmission, trust, Affiliation, Institution policy, technology, social action Commands (`ENERGY_TRANSFER`, `MEME_DELTA`, `TRUST_DELTA`, `INSTITUTION_JOIN/LEAVE`, `SPAWN` for FOUND, `DESPAWN` for dissolution) | Chunk | DEOS-PROTO Stage 5 |
| 5.2 | 5 | Command resolution | per DEOS-ECS | DEOS-ECS REQ-MUT-006 |
| 5.3 | 5 | per-Chunk live counts, cooperation/conflict/growth/entropy partials | Chunk | DEOS-PROTO WorldMood partials |
| 5.4 | 5 | WorldMood fold in ascending Chunk index; `WorldMoodSlot` written | W0 | DEOS-ECS REQ-CMP-012 |
| 6.1 | 6 | spawn assignment | W0 | DEOS-ECS REQ-MUT-010 |
| 6.2 | 6 | spawn initialization (Genome from SpawnPayload or `SPAWN_INIT` Stream) | Chunk | DEOS-ECS REQ-MUT-010; REQ-LOOP-006 |
| 6.3 | 6 | despawn finalization | Chunk | DEOS-ECS REQ-MUT-010 |
| 6.4a | 6 | Chunk-ledger sums credited to `Ledger.heat_sink`, `births`/`deaths` folded, `fx_flags` OR; `E_total` and the Stage 6 conservation check; `WORLD_PHASE_REACHED` 2, `EXTINCTION`, `STARVATION_WAVE` detection from the folded counts | W0 | DEOS-ECS REQ-MUT-009 rule 3; DEOS-CORE REQ-LAW-004 rule 5; REQ-HASH-006; DEOS-PROTO REQ-EVT-002, 004 |
| 6.4b | 6 | Tick Hash | W0 | REQ-HASH-002 |
| 6.4c | 6 | Checkpoint tick only: Chunk Hashes | Chunk, Cell Chunk | REQ-HASH-003 rule 1 |
| 6.4d | 6 | Checkpoint tick only: Merkle root, Checkpoint Hash, `CHECKPOINT` record or comparison | W0 | REQ-HASH-003 rules 2–4, REQ-HASH-004, REQ-HASH-005 |
| 6.5a | 6 | WorldMood emission; event outbox flush (or reduction) | W0 | REQ-LOOP-007, REQ-LOOP-008, REQ-SNAP-005 |
| 6.5b | 6 | buffer swap; `tick += 1`; state update | W0 | REQ-ARCH-002 |

### 7.2 The Worker loop

```
worker(id):
    loop:
        wait_barrier(step_start)
        if step.serial and id != 0: wait_barrier(step_end); continue
        while (u = fetch_add(step.counter, 1)) < step.units:
            unit = step.unit_list[u]                       -- canonical order; assignment unobservable
            stream = prng_derive(master, step.system_id, tick, unit.chunk)   -- when the step draws
            step.fn(unit, stream)                          -- writes exclusively owned data; folds what it writes
        wait_barrier(step_end)
```

Worker 0 is the Host's thread inside `deos_tick`: it generates the step list, participates as a Worker, and executes serial steps.

### 7.3 Fold and hash reference

```
uint64_t fold_word(uint64_t h, uint64_t w) { h = (h ^ w) * 0xBF58476D1CE4E5B9ULL; return (h << 29) | (h >> 35); }
uint64_t fold_bytes(uint64_t h, const uint8_t* b, size_t n) {
    size_t i = 0;
    for (; i + 8 <= n; i += 8) h = fold_word(h, le64(b + i));
    if (i < n) { uint8_t tmp[8] = {0}; memcpy(tmp, b + i, n - i); h = fold_word(h, le64(tmp)); }
    return fold_word(h, (uint64_t)n);
}
```

Test vectors (computed from the definition above with Python integer arithmetic): `fold_bytes(fold_init(), "", 0) = 0x8D90CE85BACE8238`; `fold_bytes(fold_init(), "DEOS", 4) = 0xFFC4FD73F5660C75`; `fold_bytes(fold_init(), LE64(1) ‖ LE64(2), 16) = 0x29D6014757C19CA8`. TS-PLAY-003 recomputes them; the definition governs.

Merkle combination:

```
leaves = [ChunkHash(0..NUM_CHUNKS), CellChunkHash(0..NUM_CELL_CHUNKS), H(0x4C‖Ledger), H(0x42‖CatalystLedger), H(0x4D‖WorldMoodSlot)]
while len(leaves) > 1:
    next = []
    for i in 0, 2, 4, …:
        if i + 1 < len(leaves): next.append(BLAKE3(0x4E ‖ leaves[i] ‖ leaves[i+1]))
        else:                   next.append(leaves[i])
    leaves = next
root = leaves[0]
```

### 7.4 Ingress cost check

`cost_expected = cat_cost(kind, payload, radius)` is the DEOS-PLAY formula compiled into the Kernel; the check is exact Q32.32 equality. The Host computes the same function to display the cost before the player commits; a disagreement means the Host and Kernel disagree on the version, which `deos_version` prevents.

### 7.5 Reduced-egress selection

```
insert(rec):
    if rec.kind in 1..8: append to protected list                        -- unbounded within an Epoch's practical bound
    elif count < 4096:  buf[count++] = rec
    else:
        m = index of min key over buf (key = (−magnitude, tick, kind, subject), first minimum in index order)
        if key(rec) < key(buf[m]): buf[m] = rec                          -- strictly greater magnitude, or equal magnitude and earlier tick, etc.
emit at boundary: sort protected ∪ buf by (tick, flush order) stably; append to Chronicle ring; clear
```

The protected list is bounded by `8 + (NUM_CHUNKS + NUM_CELL_CHUNKS) × TICKS_PER_EPOCH` in the worst case; in practice by the rejection and overflow counts, which section 8.5 sizes generously.

---

## 8. Data Structures

### 8.1 Error codes

```c
enum DeosError {
    DEOS_OK = 0,
    DEOS_E_ARG = -1,          /* null pointer, bad capacity, bad enum */
    DEOS_E_STATE = -2,        /* call illegal in the current state */
    DEOS_E_REENTRANT = -3,    /* REQ-ARCH-004 */
    DEOS_E_NOMEM = -4,        /* deos_create only */
    DEOS_E_LOG_FULL = -5,     /* Input Log pool full */
    DEOS_E_LOG_FORMAT = -6,   /* import validation failed */
    DEOS_E_EGRESS_FULL = -7,  /* REQ-LOOP-008 rule 3; world unchanged */
    DEOS_E_DESYNC = -8,       /* REQ-HASH-005 */
    DEOS_E_LEDGER = -9,       /* REQ-HASH-006 */
    DEOS_E_HALTED = -10,      /* state HALTED */
    DEOS_E_SNAPSHOT = -11,    /* trailer, version, or scale mismatch */
    DEOS_E_VERSION = -12,     /* Host/Kernel version mismatch */
    DEOS_E_NONE = -13,        /* nothing to return yet */
    DEOS_E_FAULT = -14        /* DEOS-ECS REQ-MUT-012 case 1 or 5 */
};
```

### 8.2 Configuration

```c
struct DeosConfig {              /* 64 bytes */
    uint32_t version;            /* must equal deos_version() */
    uint32_t scale;              /* 0 SCALE_MVS, 1 SCALE_V1 */
    uint32_t threads;            /* [1, 64] */
    uint32_t egress_mode;        /* initial: 0 EGRESS_FULL, 1 EGRESS_REDUCED */
    uint32_t organisms;          /* tick-0 population (DEOS-MVS fixes per scale) */
    uint32_t agents;
    uint32_t springs;
    uint32_t input_log_capacity; /* records; default INPUT_LOG_CAPACITY */
    uint32_t chronicle_ring;     /* records; default CHRONICLE_RING */
    uint32_t worldmood_ring;     /* records; default WORLDMOOD_RING */
    uint32_t debug_stage_folds;  /* 0 or 1; REQ-HASH-005 rule 4 */
    uint32_t pad[5];
};
```

`checkpoint_interval` and `snapshot_interval` are not configurable: they are functions of `scale` (REQ-HASH-003) and of the registry. A Kernel created with non-default `organisms`, `agents`, or `springs` produces a different world for the same Master Seed; DEOS-PLAY's seed code therefore encodes the scale, and the counts are the scale's defaults for every shared world.

### 8.3 Read view

```c
struct DeosReadView {            /* filled by deos_read_view; all pointers const */
    uint64_t tick;
    uint32_t scale, max_entities, num_chunks, grid_w, grid_h, num_cell_chunks;
    const uint64_t* entity_table;
    const void*     component_slab[12];   /* buffer A pool base per catalog index; #3 is the Genome pool */
    const int64_t*  cell_energy; const int64_t* cell_temperature; const int64_t* cell_moisture;
    const int64_t*  cell_elevation; const uint8_t* cell_material; const int64_t* cell_mutation_bias;
    const Ledger*   ledger;
    const CatalystLedger* catalyst;
    const WorldMoodSlot*  worldmood;
    const uint8_t*  last_tick_hash;       /* 32 bytes */
};
```

Slab addressing follows DEOS-ECS REQ-DAT-004 rule 1; the Host uses the same `LEAF_OFFSET` tables the Kernel publishes in its header.

### 8.4 Diagnostics and reports

```c
struct DeosStats {               /* never hashed */
    uint32_t fx_flags_tick;      /* DEOS-CORE section 8.1 */
    uint32_t events_dropped;     /* sum of outbox dropped counters this tick */
    int64_t  dissipated, dropped;/* DEOS-ECS REQ-MUT-009 sums this tick */
    uint64_t actions_applied, actions_rejected;
    uint64_t worker_cycles[6];   /* per stage, Worker 0's cycle counter; 0 when not compiled in */
};
struct DesyncReport {
    uint64_t tick;
    uint8_t  expected[32], computed[32];
    uint32_t leaf_count;
    const uint8_t* computed_leaves;       /* leaf_count × 32 */
    const uint8_t* reference_leaves;      /* Host-supplied or NULL */
    uint32_t first_divergent_leaf;        /* 0xFFFFFFFF when no reference */
    uint64_t first_divergent_tick;        /* from the Tick Hash ring comparison, or 0 */
    uint32_t first_divergent_stage;       /* debug builds; 0 otherwise */
};
```

### 8.5 Runtime pool sizes

| Pool | Elements | Bytes (MVS) | Bytes (v1.0) |
| :--- | :--- | ---: | ---: |
| Input Log | `INPUT_LOG_CAPACITY` = 1,048,576 records × 64 | 67,108,864 | 67,108,864 |
| Chronicle ring | 65,536 × 64 | 4,194,304 | 4,194,304 |
| WorldMood ring | 4,096 × 64 | 262,144 | 262,144 |
| Event outboxes | (`NUM_CHUNKS` + `NUM_CELL_CHUNKS`) × 257 × 64 | 1,315,840 | 33,685,504 |
| Serialization buffers | `THREADS` × 1,884,160 | 7,536,640 (4 threads) | 7,536,640 (4 threads) |
| Chunk Hash lists | 2 × (`NUM_CHUNKS` + `NUM_CELL_CHUNKS` + 3) × 32 | 5,312 | 131,264 |
| Tick Hash ring | `CHECKPOINT_INTERVAL` × 32 | 2,048 | 115,200 |
| Reduction buffer | (4,096 + 65,536 protected) × 64 | 4,456,448 | 4,456,448 |
| `LAT` table | `GRID_H` × 8 | 2,048 | 8,192 |
| Total | | ≈ 84.9 MB | ≈ 117.5 MB |

Together with the ECS arena (63.6 MB at MVS, 3.80 GB at v1.0) the resident footprint is ≈ 148 MB at MVS and ≈ 3.92 GB at v1.0; the Input Log pool dominates the MVS figure and a Host targeting phones may set `input_log_capacity` to 131,072 (8 MiB), which holds 36 simulated hours of one action per second.

### 8.6 Generation constants

| Constant | Value |
| :--- | :--- |
| `GEN_LATTICE_1`, `GEN_LATTICE_2` | 16, 4 Cells |
| `GEN_SEA_LEVEL` | 0.35 of `FX_ELEV_MAX` |
| `GEN_ROCK_LEVEL` | 0.80 of `FX_ELEV_MAX` |
| `FX_INIT_CELL_ENERGY` | WATER 16.0, SOIL 64.0, ROCK 4.0, ICE 0 |
| `GEN_INIT_TEMP` | 4.0 × `LAT[y]` minus 2.0 × relative elevation |
| `GEN_INIT_ATMOSPHERE` | 0.1 per Cell |
| `GEN_SPAWN_ENERGY` | 40.0 |
| `GEN_SPRING_ENERGY` | `FX_CELL_ENERGY_CAP >> 4` (65,536) |

---

## 9. Subsystem Interfaces

Exported: the ABI of REQ-ARCH-003. Consumed from DEOS-CORE: `fx_tables_init`, `prng_derive`, `substrate_stage2`, `substrate_stage2_fold`, `ledger_stage6_check`, `ledger_catalyst_*`. Consumed from DEOS-ECS: `ecs_issue`, `ecs_resolve_barrier`, `ecs_commit_*`, `ecs_serialize_*`, `ecs_snapshot_*`, `ecs_spatial_index_build`, `ecs_ingress_overlay_*`. Consumed from DEOS-PROTO (by name; defined there): `proto_stage3_chunk`, `proto_stage4_chunk`, `proto_stage5_chunk`, `proto_worldmood_partial`, `proto_worldmood_fold`. Consumed from DEOS-PLAY: `cat_kind_table`, `cat_cost`, `cat_expand` (the kind table, the cost formula, the expansion table).

Events emitted by this module: kinds 1 `INGRESS_REJECTED`, 3 `DESYNC`, 5 `CATALYST_APPLIED`, 7 `LEDGER_FAULT`, 8 `EVENT_OVERFLOW`. Kind 2 is DEOS-ECS's, kind 4 is DEOS-PLAY's (emitted by the Kernel at `t mod TICKS_PER_EPOCH == 0` in step 6.5a with `magnitude = fx_from_int(t / TICKS_PER_EPOCH)`), kind 6 is DEOS-PROTO's.

---

## 10. Failure Cases & Risk Mitigation

| Case | Behaviour | Mitigation |
| :--- | :--- | :--- |
| Host calls the ABI from two threads | second call returns `DEOS_E_REENTRANT` | REQ-ARCH-004 |
| Host falls behind draining the Chronicle | `deos_tick` refuses to step; no record lost | REQ-LOOP-008 |
| Input Log tampered (cost, order, Checkpoint) | rejection with a Chronicle row, or `DEOS_E_LOG_FORMAT`, or `DEOS_E_DESYNC` | REQ-LOOP-003 rule 3.4, REQ-LOOP-004, REQ-HASH-005 |
| Desync between two runs | halt with a localizing report | REQ-HASH-005 |
| Ledger fault | halt after a reproducible tick | REQ-HASH-006 |
| Outbox assertion, pool alignment | `DEOS_E_FAULT` / creation failure | DEOS-ECS REQ-MUT-012 |
| Snapshot from another version or scale | `DEOS_E_SNAPSHOT`; world unchanged | REQ-SNAP-003 |
| Checkpoint hashing exceeds the tick budget at v1.0 scale | not attempted every 64 ticks | scale-profile interval (REQ-HASH-003, ADR-0001) |
| Reduced-egress selection hides a story | only domain events below the 4,096th magnitude of an Epoch are dropped; every warning is kept | REQ-SNAP-005 |
| World generation exhausts a Stream by re-draws (all Cells WATER) | impossible: `GEN_SEA_LEVEL` = 0.35 bounds the WATER fraction of any lattice noise below 1.0; a degenerate seed with fewer than `agents + organisms` land Cells is rejected by `deos_generate` with `DEOS_E_ARG` | DEOS-PLAY's seed curation probe never offers such a seed |

---

## 11. Performance & Scalability Targets

| Item | MVS (2^14, 256×256, 4 threads) | v1.0 (2^20, 1,024×1,024, 4 threads) |
| :--- | :--- | :--- |
| Stage 1 | ≤ 0.02 ms (≤ 1,024 overlay pushes) | same |
| Stage 2 | ≈ 0.3 ms (DEOS-CORE section 11) | ≈ 4.6 ms |
| Stages 3–5 owner passes | ≈ 0.1 ms budgeted (DEOS-PROTO section 11) | ≈ 7 ms budgeted |
| Command resolution (three passes × 3 stages) | ≈ 0.03 ms | ≈ 1.5 ms |
| SpatialIndex | ≈ 0.02 ms | ≈ 1.2 ms |
| Stage 6 data substeps | ≈ 0.01 ms | ≈ 0.4 ms |
| Tick Hash | ≤ 0.01 ms | ≤ 0.05 ms |
| Checkpoint tick extra | ≈ 4 ms every 64 ticks (28.4 MB, 4 threads) | ≈ 0.5 s every 3,600 ticks (1.69 GB) |
| Flush and swap | ≤ 0.01 ms | ≤ 0.1 ms |
| Ordinary tick total | ≈ 0.48 ms → 2,080 ticks/s ≥ `MIN_ACCELERATION` (1,920) | ≈ 15 ms < `TICK_BUDGET_MS` (16.6) |
| 10,000-tick benchmark | ≈ 4.8 s + 156 × 4 ms = 5.4 s single pass; budget 5.0 s is met when Checkpoint hashing overlaps the next tick's Stage 1 and 2 on idle Workers (permitted: it reads buffer A, which is stable until the next swap) | — |

The MVS benchmark is tight by design; DEOS-MVS names the baseline hardware, and the overlap of Checkpoint hashing with the next tick is the one scheduling freedom this module allows, because buffer A is immutable during a tick (REQ-ARCH-002).

---

## 12. Future Expansion

1. **Incremental Chunk Hashes.** Per-Chunk BLAKE3 could be maintained incrementally from the write folds' byte ranges, making every tick a Checkpoint tick at v1.0 scale; needs a tree-hash mode of BLAKE3 with per-leaf updates.
2. **Snapshot delta encoding.** Consecutive Snapshots differ in a minority of slots at MVS scale; a delta section kind would cut Snapshot I/O tenfold. `SNAPSHOT_LAYOUT_VERSION` 2.
3. **Multi-Kernel verification.** A verifier farm runs `deos_verify` in parallel over Checkpoint intervals from Snapshots (ROADMAP Phase 7).
4. **GPU Stage 2.** REQ-THR-002's independence proof holds for Cell Chunks on a GPU; a GPU implementation is conformant when its Tick Hashes match (DEOS-CORE section 12).
5. **Server-stepped worlds.** REQ-SNAP-006 already makes a server-hosted world equivalent; a wire format for Input Log streaming and Snapshot handoff is a v5.x deliverable.

---

## 13. Revision History

| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 | 2026-09-12 | Initial DEOS draft; absorbs EESS-0301 (REQ-ARCH-001…002) and EESS-0501 (REQ-LOOP-001); two-tier hashing per ADR-0001 | DEOS Arch Team |
