# Specification: Data Schemas & Entity-Component Architecture (DEOS-ECS)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | DEOS-ECS |
| **Semantic Version** | v0.1.0 |
| **Status** | Draft |
| **Dependencies** | DEOS, DEOS-F01, DEOS-F02, DEOS-F03, DEOS-F04, DEOS-F05, DEOS-F06, DEOS-CORE |
| **Supersedes** | EESS-0401 (Entity Component Model), EESS-0601 (Data & Memory Layout) |
| **Reserved Prefixes** | `ENT`, `CMP`, `DAT`, `MUT` (from DEOS section 3.2) |

---

## 1. Purpose

DEOS-ECS owns the data of the Kernel: the `EntityID` layout and lifecycle, the canonical component catalog of DEOS section 5.3 with exact Struct-of-Arrays layouts, the Substrate Cell field arrays, the pool allocator and alignment rules, the double-buffered state mutation discipline, and the Command buffers that carry every cross-entity effect and are resolved at each stage barrier in canonical order (DEOS section 5.2). Everything a system reads or writes, every byte a Chunk Hash covers, and every byte a Snapshot serializes is laid out here.

The module exists so that two conforming implementations on x86-64 and ARM64, with 1 or 4 worker threads, attended or in Acceleration, produce identical Tick Hashes (GI-1). It achieves that by removing every source of order dependence from data access: fixed slot indices, fixed field orders, fixed iteration orders, and a Command resolution rule whose result does not depend on which thread ran which Chunk.

Player-facing consequence: the catalog in this document is exactly what the Chronicle and the Host inspect view can show; every field of every component is a value the player can open and read, and a trade or a fight resolves identically in a replay because the Command ordering rule is part of the data contract, not of the scheduler.

---

## 2. Scope

**Included.** `EntityID` packing, null identity, validity, generation policy, free-slot allocation, spawn and despawn Commands, `MAX_ENTITIES` and slot ranges per scale (`ENT`); one requirement per component of DEOS section 5.3, the Substrate Cell fields, and the `WorldMood` slot (`CMP`); pool allocator, alignment, Chunk-major layout, padding, index-only references, little-endian serialization, the Snapshot byte layout, the SpatialIndex, and the memory budget (`DAT`); double buffering, the owner-stage write rule, the Command record, Command kinds and their application semantics, buffer capacities, barrier resolution, the pure-function system rule, and the Stage 6 commit sequence as far as data is concerned (`MUT`).

**Excluded.** When Snapshots are taken, how Chunks are dispatched to threads, the Tick Hash tree construction, and the C ABI (DEOS-RT). The rules that decide *which* Commands a system issues, the meaning of actions, needs, and memory kinds, and every threshold of cognition and society (DEOS-PROTO). The `CatalystAction` kind enumeration and its expansion (DEOS-PLAY, DEOS-RT). Q32.32 arithmetic semantics, transcendental tables, PRNG stream derivation, and the ordering rules this module cites (DEOS-CORE).

---

## 3. Dependencies

In the order of DEOS section 2.2:

1. **DEOS** — identifier scheme (section 3), vocabulary (section 4), registry constants, tick pipeline, component catalog, and record headers (section 5), Game-Facing Invariants (section 6).
2. **DEOS-F01 … DEOS-F06** — Directives 2, 3, 5, 6, 7, 8, 11, 12; Pillar 3 (Massive Scalability); the memory footprint ceiling (DEOS-F05 section 1.1, under 4.0 GB for 1,000,000 active entities); the rubric.
3. **DEOS-CORE** — the Q32.32 format (`MATH`: 128-bit intermediates, round toward negative infinity on the fractional shift, saturation to `INT64_MIN` / `INT64_MAX`); the conservation ledger (`LAW`); PRNG streams keyed by `(system, tick, chunk)` (`PRNG`); the deterministic ordering rules (`ORD`: ascending `EntityID`, row-major Cells, ascending Chunk index, stable sorts over total keys).

Nothing below this module is cited. DEOS-RT, DEOS-PROTO, and DEOS-PLAY consume the layouts and rules defined here by name.

---

## 4. Definitions

Terms of DEOS section 4 and DEOS-F04 are used verbatim. The following terms are introduced by this module and used only with the meaning given here.

| Term | Definition |
| :--- | :--- |
| **Slot** | One entity index in `[0, MAX_ENTITIES)`. Every component array has exactly one element per slot. Slot 0 is reserved and never allocated. |
| **Chunk slab** | The contiguous, 64-byte-aligned region holding one component's data for one Chunk, laid out field-by-field (SoA) inside the slab (REQ-DAT-004). |
| **Cell Chunk** | A contiguous run of `CELL_CHUNK_SIZE` = 1,024 Cells in row-major Cell index order, processed by exactly one worker per stage; the unit of parallelism for Cell writes and the analogue of a Chunk for the Substrate. |
| **Owner stage** | The single pipeline stage that writes a component (or a Cell field) for every slot of every Chunk each tick (REQ-CMP-013). |
| **Read buffer (A)** | The state buffer that holds the end-of-previous-tick state, read by systems and by the Host; never written during a tick. |
| **Write buffer (B)** | The state buffer written during the tick; becomes A at the buffer swap in Stage 6. |
| **Command** | A fixed-size 64-byte record (REQ-MUT-003) describing one cross-entity or cross-Cell effect, appended by the issuing worker to its Chunk's outbox and applied at a stage barrier in canonical order. |
| **Outbox** | The per-Chunk, per-stage array of Commands issued while processing that Chunk (REQ-MUT-005). |
| **Lifecycle outbox** | The per-Chunk, per-tick array of `SPAWN` and `DESPAWN` Commands, resolved in Stage 6 rather than at the issuing stage's barrier (REQ-ENT-008, REQ-ENT-009). |
| **Canonical Command order** | Ascending `(target_kind, target Chunk, target index, source EntityID, seq)` (REQ-MUT-006). |
| **Derived structure** | Memory rebuilt from authoritative state whenever needed (free bitmap, SpatialIndex, IngressOverlay, outboxes); never hashed, never serialized. |
| **Authoritative state** | The entity table, both state buffers, and the Cell field buffers; hashed and serialized. |

Archetype constants (DEOS section 5.3 tags): `ARCH_PHYSICAL` = 0x01, `ARCH_BIOLOGICAL` = 0x02, `ARCH_COGNITIVE` = 0x04, `ARCH_CULTURAL` = 0x08, `ARCH_INSTITUTIONAL` = 0x10. The three legal archetype values are given in REQ-ENT-010.

---

## 5. Assumptions

1. `CHUNK_SIZE` = 1,024 and `CACHE_LINE` = 64 (DEOS section 5.1); `MAX_ENTITIES` is a power of two that is a multiple of `CHUNK_SIZE` × 16, which holds at both registry scales (2^14 and 2^20).
2. `GRID_W` × `GRID_H` is a multiple of `CELL_CHUNK_SIZE` = 1,024 (65,536 Cells at MVS; 1,048,576 at v1.0) and the Cell index fits in 20 bits at v1.0.
3. The Substrate grid is bounded: a Cell coordinate outside `[0, GRID_W) × [0, GRID_H)` does not exist and is excluded from every neighbourhood computation in this module. If DEOS-CORE declares a toroidal grid, the coordinate wrap is applied before every Cell lookup in this module and nothing else changes.
4. The Q32.32 operations named in this module (`add_sat`, `sub_sat`, `mul_q`, `div_q`, `clamp`) have the semantics of DEOS-CORE `MATH`: saturating addition and subtraction; multiplication with a 128-bit intermediate, floor on the 32-bit fractional shift, saturation on overflow; division with a 128-bit numerator, floor toward negative infinity, divisor never zero by construction.
5. Every system executes over a Chunk as a pure function (REQ-MUT-007); DEOS-RT guarantees that no two workers process the same Chunk in the same stage and that a barrier separates stages.
6. The memory ceiling of DEOS-F05 ("< 4.0 GB RAM for 1,000,000 active entities") is read as 4.0 × 10^9 bytes resident for the Kernel's authoritative state, derived structures, and buffers, excluding the Input Log, the egress rings, Snapshot staging, DEOS-CORE tables, code, and stacks (REQ-DAT-010).
7. Baseline hardware and thread count are those of DEOS-MVS; thread count never enters any rule in this module.

---

## 6. Requirements

### 6.1 Entity identity and lifecycle (`ENT`)

### REQ-ENT-001: 64-bit Packed EntityID
An `EntityID` is a `uint64_t` bitfield holding index, generation, and archetype:

```
 63                       32 31               16 15                    0
┌───────────────────────────┬───────────────────┬───────────────────────┐
│     Slot Index (32-bit)   │ Generation (16-bit)│  Archetype Tag (16-bit)│
└───────────────────────────┴───────────────────┴───────────────────────┘
```

- **Slot Index (32-bit)**: `index = id >> 32`. The field permits 2^32 slots; a conforming Kernel allocates `MAX_ENTITIES` of them (REQ-ENT-007).
- **Generation (16-bit)**: `generation = (id >> 16) & 0xFFFF`. Incremented on every despawn of the slot (REQ-ENT-005) so that a stale reference never validates.
- **Archetype Tag (16-bit)**: `archetype = id & 0xFFFF`. A bitmask over 0x01 Physical, 0x02 Biological, 0x04 Cognitive, 0x08 Cultural, 0x10 Institutional. Bits 5 to 15 are zero. The tag is fixed at spawn and never changes for the life of the entity.

Packing is `make_id(index, generation, archetype) = ((uint64_t)index << 32) | ((uint64_t)generation << 16) | archetype`. The Chunk of an entity is `index >> 10` and its slot within the Chunk is `index & 1023` (`CHUNK_SIZE` = 1,024). Every `EntityID` stored anywhere in authoritative state is the packed form; no component stores a bare index.

Player-facing consequence: an `EntityID` is a stable name the player can bookmark, search the Chronicle for, and follow across an Epoch; the generation bits guarantee that a bookmark of a dead agent never silently points at a newborn that reused its slot (GI-1, GI-5).

### REQ-ENT-002: Position Component (`Position2D`)
`Position2D` is the Physical-archetype component holding an entity's location in Q32.32 Cell units. Layout per slot (16 bytes), owner Stage 4, double-buffered:

```c
struct Position2D {           // 16 bytes; SoA per REQ-DAT-004
    int64_t x;                // Q32.32, invariant 0 <= x < GRID_W
    int64_t y;                // Q32.32, invariant 0 <= y < GRID_H
};
```

Rules:
1. An entity writes only its own slot (DEOS section 5.3). No Command kind writes `Position2D`.
2. The Cell of an entity is `cell = (y >> 32) * GRID_W + (x >> 32)` using arithmetic right shift; the invariant guarantees both integer parts are in range.
3. Every write clamps `x` to `[0, GRID_W * 2^32 - 1]` and `y` to `[0, GRID_H * 2^32 - 1]` in Q32.32 raw units before storing.
4. Initial value at spawn: `payload[1]`, `payload[2]` of the `SPAWN` Command (REQ-ENT-008), clamped by rule 3.
5. Institutional entities carry `Position2D` (their founding Cell); the Stage 4 owner write for an entity without a Cognitive tag copies A to B unchanged.

Player-facing consequence: the Particles layer of the Observation View is a direct rendering of this array, so what the player sees moving is the authoritative state itself, not an interpolation the Kernel cannot reproduce (GI-6).

### REQ-ENT-003: Energy Component (`EnergyState`)
`EnergyState` is the Biological-archetype component holding an entity's energy. Layout per slot (24 bytes), owner Stage 3, double-buffered:

```c
struct EnergyState {          // 24 bytes; SoA per REQ-DAT-004
    int64_t current_energy;   // Q32.32, invariant 0 <= current_energy <= max_capacity
    int64_t max_capacity;     // Q32.32, invariant max_capacity > 0
    int64_t metabolic_rate;   // Q32.32, invariant metabolic_rate >= 0
};
```

Rules:
1. `current_energy` is modified by the owner (Stage 3 metabolism, DEOS-PROTO) and by the `ENERGY_TRANSFER`, `DAMAGE`, and `CELL_ENERGY_DELTA` Commands (REQ-MUT-004); `max_capacity` and `metabolic_rate` are written from the Genome at spawn and rewritten by the owner every tick as `gene_param` of rows 0 and 1 (REQ-CMP-002), so they are constant for the life of the entity.
2. Every write clamps `current_energy` to `[0, max_capacity]`; energy removed by the clamp, and every own-write loss (metabolism, DEOS-PROTO), is accounted as dissipation in the Chunk ledger (REQ-MUT-009), never silently lost.
3. Initial value at spawn: `current_energy = min(payload[0], max_capacity)`; `max_capacity = gene_param(genome, 0)`; `metabolic_rate = gene_param(genome, 1)`.

Player-facing consequence: the energy bar the player sees on an inspected agent, the pooled energy of an Institution, and the Cell energy of a drought all draw from one accounted quantity, so a famine the player caused is visible as a real shortfall and never as a scripted penalty (GI-7).

### REQ-ENT-004: Null EntityID and validity
`NULL_ENTITY_ID` = 0 (index 0, generation 0, archetype 0). Slot 0 is reserved: it is in no free range (REQ-ENT-006), its entity table entry (REQ-ENT-005) is 0 forever, and every component array holds zero at slot 0 in both buffers.

An `EntityID` `id` is **valid in buffer X** when all of:

```
id != NULL_ENTITY_ID
index(id) < MAX_ENTITIES
id == entity_table[index(id)]            // generation and archetype match
X.Lifecycle.alive[index(id)] == 1
```

The first three conditions are one 64-bit comparison against the entity table; the fourth is read from the buffer the reader is entitled to read for `Lifecycle` (REQ-MUT-001). Every `EntityID` field stored in a component (`Lifecycle.parent`, `Perception.nearest[].id`, `Memory.entries[].subject`, `Decision.target`, `TrustEdges.edges[].id`, `Affiliation.institution`, `InstitutionState.founder`) is validated by its reader before use; an invalid stored reference is treated as `NULL_ENTITY_ID` and, where the owner stage rewrites the field, written back as `NULL_ENTITY_ID` with its companion fields zeroed.

Player-facing consequence: an agent that remembers a dead friend, trusts a dissolved Institution, or targets a vanished rival behaves as though the reference is gone, and the Chronicle shows that loss rather than an impossible interaction with a ghost (GI-5).

### REQ-ENT-005: Entity table and generation policy
The entity table is a single-buffered, 64-byte-aligned array `uint64_t entity_table[MAX_ENTITIES]` holding, for every slot, the packed `EntityID` currently valid there, or the packed value `make_id(index, generation, 0)` for a free slot (archetype 0 marks a free slot). It is authoritative state: it is hashed as the first array of every Chunk (REQ-DAT-007) and serialized in every Snapshot (REQ-DAT-008).

Generation policy:
1. At Kernel initialization every slot has generation 1 and archetype 0 (free), except slot 0 which is 0.
2. A despawn (REQ-ENT-009) increments the generation of the slot: `generation' = (generation == 65535) ? 1 : generation + 1`. Generation 0 is never assigned to an allocatable slot, so no live `EntityID` ever equals `NULL_ENTITY_ID` and no reference with generation 0 ever validates.
3. Wrap consequence: a reference that is exactly 65,535 despawns stale can validate against a later occupant of the slot. The bound is stated so that DEOS-PROTO can size memory decay against it; the reference fields of REQ-ENT-004 carry no additional stamp.
4. The table is written only in Stage 6 substeps 6.2 and 6.3 (REQ-MUT-010), by the worker of the Chunk that contains the slot.

Player-facing consequence: a slot that has been born and died sixty-five thousand times is still addressable, and a shared Input Log replays the same births into the same slots on every device (GI-1).

### REQ-ENT-006: Deterministic free-slot allocation
Free slots are tracked by a two-level bitmap, both levels derived structures rebuilt from `Lifecycle.alive` on Snapshot restore:

```c
uint64_t free_bits[MAX_ENTITIES / 64];        // bit set = slot free
uint64_t free_summary[MAX_ENTITIES / 4096];   // bit w set = free_bits[w] != 0
```

Rules:
1. Two allocation ranges exist: the agent range `[1, INSTITUTION_BASE)` and the Institution range `[INSTITUTION_BASE, MAX_ENTITIES)` where `MAX_INSTITUTIONS` = `MAX_ENTITIES` / 16 and `INSTITUTION_BASE` = `MAX_ENTITIES` − `MAX_INSTITUTIONS` (REQ-ENT-007). A `SPAWN` with an Institutional archetype allocates from the Institution range; every other `SPAWN` allocates from the agent range.
2. **Lowest free index first.** `alloc(range)` returns the smallest set bit in `free_bits` within the range: scan `free_summary` from the range's first word upward for a non-zero word, then `free_bits` within it, then count trailing zeros. The scan is bounded by `MAX_ENTITIES` / 4096 + 1 word reads (257 at v1.0).
3. **Allocation is serial.** All `SPAWN` Commands of a tick are assigned slots by one worker in the canonical order of REQ-ENT-008 substep 6.1, so the result is independent of thread count.
4. **Slots freed in tick t become allocatable in tick t+1.** Substep 6.1 (allocation) precedes substep 6.3 (despawn finalization, which sets the free bit) within Stage 6, so a slot freed in tick t is never assigned in tick t; it is free from Stage 1 of tick t+1 onward, at which point it is the lowest candidate if it is the lowest free index.
5. A `SPAWN` for which `alloc` finds no free slot is dropped per REQ-MUT-009 with `NotableEvent.kind` 2 `COMMAND_DROPPED`; the `SPAWN` Commands after it in canonical order are still processed, so a later Institutional spawn succeeds when only the agent range is full.
6. Clearing a free bit (allocation) and setting one (despawn) touch only the words of the Chunk that contains the slot; substep 6.3 runs one worker per Chunk over disjoint words, so no synchronization beyond the substep barrier is needed.

Player-facing consequence: a population that fills the world hits a hard, visible ceiling (the Chronicle records the dropped births) rather than an invisible slowdown, and the same seed produces the same overcrowding on every device (GI-1, GI-8).

### REQ-ENT-007: `MAX_ENTITIES`, Chunks, and slot ranges per scale
The registry values of DEOS section 5.1 fix the following derived counts; a Kernel is built for exactly one scale and every pool of REQ-DAT-003 is sized from these numbers at initialization.

| Quantity | Definition | MVS | v1.0 |
| :--- | :--- | ---: | ---: |
| `MAX_ENTITIES` | registry | 16,384 | 1,048,576 |
| `NUM_CHUNKS` | `MAX_ENTITIES` / `CHUNK_SIZE` | 16 | 1,024 |
| `MAX_INSTITUTIONS` | `MAX_ENTITIES` / 16 | 1,024 | 65,536 |
| `INSTITUTION_BASE` | `MAX_ENTITIES` − `MAX_INSTITUTIONS` | 15,360 | 983,040 |
| Institution Chunks | `MAX_INSTITUTIONS` / `CHUNK_SIZE` | 1 | 64 |
| Agent slots | `INSTITUTION_BASE` − 1 | 15,359 | 983,039 |
| Cells | `GRID_W` × `GRID_H` | 65,536 | 1,048,576 |
| `NUM_CELL_CHUNKS` | Cells / `CELL_CHUNK_SIZE` | 64 | 1,024 |
| Cell key bits | log2(Cells) | 16 | 20 |

`INSTITUTION_BASE` is a multiple of `CHUNK_SIZE` at both scales, so the `InstitutionState` slabs (REQ-CMP-010) exist exactly for the last `MAX_INSTITUTIONS` / `CHUNK_SIZE` Chunks and for no other.

Player-facing consequence: the MVS world of 15,359 agents and 1,024 Institutions on a 256 × 256 grid is the world that fits a phone (REQ-DAT-010); the v1.0 world of 983,039 agents is the same rules at a scale that fills a desktop, and a Master Seed means the same thing at both because the allocation order is identical.

### REQ-ENT-008: Spawn as a Command
An entity comes into existence only through a `SPAWN` Command (kind 7, REQ-MUT-004) resolved in Stage 6. Sources and stages:

| Source | Issuing stage | `source` field | Genome origin | `payload[0]` energy |
| :--- | :--- | :--- | :--- | :--- |
| Reproduction (DEOS-PROTO) | 3 | the parent's `EntityID` | SpawnPayload written by the parent's Stage 3 system (REQ-DAT-003 pool 12) | debited from the parent as an own write in Stage 3 |
| Institution founding (DEOS-PROTO) | 5 | the founder's `EntityID` | none (Institutions have no Genome); policy copied from the founder's `MemeVector` in B | must be 0 (Stage 5 cannot own-write `EnergyState`); the founder deposits by `ENERGY_TRANSFER` from tick t+1 |
| Ingress (DEOS-RT, when a host command spawns) | 1 | `NULL_ENTITY_ID`, `seq` = the Input Log `seq` | PRNG stream `(SPAWN_INIT, tick, target Chunk)`: 32 draws of `uint16_t` in gene order | external input, accounted by DEOS-CORE `LAW` as Catalyst energy |
| Kernel initialization (tick 0 population, DEOS-RT/DEOS-MVS) | before tick 0 | `NULL_ENTITY_ID`, `seq` ascending | as Ingress, with tick = 0 | as Ingress |

Record fields for `SPAWN` (layout REQ-MUT-003): `target` = 0 at issue, overwritten with the new `EntityID` in substep 6.1; `target_kind` = 0; `payload[0]` = initial energy (Q32.32, ≥ 0); `payload[1]`, `payload[2]` = initial `x`, `y` (Q32.32); `payload[3]` = archetype tag in the low 16 bits (REQ-ENT-010) with `lineage_generation` of the parent in bits 16 to 31, or 0; `aux` = SpawnPayload reference `(issuing Chunk << 32) | local index`, or `0xFFFFFFFFFFFFFFFF` when the Genome comes from the PRNG stream.

Resolution (REQ-MUT-010): substep 6.1 assigns slots serially in canonical order `(source EntityID, seq)` with Ingress records (source 0) first; substep 6.2 initializes every component of the new slot in B per the initial-value column of section 8.1 and writes `entity_table[index] = make_id(index, generation, archetype)`, reading parent data from B where a rule names it. At most one `SPAWN` per entity per tick may be issued (assertion in REQ-MUT-005).

Visibility: the new entity is absent from every buffer and index during tick t's Stages 1 to 5; it is included in tick t's Chunk Hash (B is complete before hashing); after the swap it is present in A and is processed from Stage 1 of tick t+1.

Player-facing consequence: a birth the player watches in the Observation View at tick t+1 is the same birth, in the same slot, that a friend replaying the Input Log sees, and the Lifecycle `parent` field lets the Chronicle draw the family line back to the founding population (GI-1, GI-5).

### REQ-ENT-009: Despawn as a Command
An entity leaves existence only through a `DESPAWN` Command (kind 8) whose `target` equals its `source`: only an entity's own owner-stage system despawns it. Issue rules:

1. Stage 3 (DEOS-PROTO Lifecycle): when the owner write sets `Lifecycle.alive` from 1 to 0 (`current_energy` ≤ 0 after metabolism, or `age_ticks` ≥ the Genome's maximum age, or a cause DEOS-PROTO enumerates), the same pass issues `DESPAWN` with `payload[0]` = the entity's `current_energy` before zeroing and `payload[3]` = `death_cause`.
2. Stage 5 (DEOS-PROTO Institutions): an Institution whose dissolution condition holds sets its own `InstitutionState.status` to 0 and issues `DESPAWN` with `payload[0]` = `pooled_energy`.
3. Damage from another entity never despawns directly: `DAMAGE` (REQ-MUT-004) lowers `current_energy` at a barrier; the victim's own Stage 3 pass in the next tick observes `current_energy` = 0 and despawns itself. Death is therefore always one tick after the last blow, and always the victim's own write.
4. Between issue and resolution the entity has `alive` = 0 in B; every Command that targets it at a later barrier of the same tick is dropped (REQ-MUT-009).

Resolution (substep 6.3, one worker per Chunk, own lifecycle outbox only, no cross-Chunk traffic): for every `DESPAWN` record in issue order, write zero to every component slab element of the slot in B (all twelve components and the SpawnPayload entry), write `entity_table[index] = make_id(index, generation', 0)` with `generation'` per REQ-ENT-005, and set the slot's free bit. The energy in `payload[0]` is returned to the Substrate by the Stage 3 or Stage 5 pass that issued the `DESPAWN`, as a `CELL_ENERGY_DELTA` with a positive amount targeting the entity's Cell (REQ-MUT-004), so that death conserves energy under DEOS-CORE `LAW`.

Player-facing consequence: a death is final at the end of the tick in which the body's energy returns to its Cell, so the player sees a corpse feed the ground it fell on, and the Chronicle's death Notable Event (DEOS-PROTO) names the cause the Lifecycle recorded (GI-5, GI-7).

### REQ-ENT-010: Archetypes and component membership
Exactly three archetype tag values are legal at spawn; a `SPAWN` carrying any other value is dropped (REQ-MUT-009).

| Archetype | Tag | Components present | Slot range |
| :--- | :--- | :--- | :--- |
| `ARCH_ORGANISM` | 0x03 (Physical, Biological) | `Position2D`, `EnergyState`, `Lifecycle`, `Genome`, `Needs` (levels only) | agent range |
| `ARCH_AGENT` | 0x0F (Physical, Biological, Cognitive, Cultural) | all of Organism plus `Needs` (weights), `Perception`, `Memory`, `Decision`, `MemeVector`, `TrustEdges`, `Affiliation` | agent range |
| `ARCH_INSTITUTION` | 0x19 (Physical, Cultural, Institutional) | `Position2D`, `Lifecycle`, `MemeVector`, `TrustEdges`, `Affiliation`, `InstitutionState` | Institution range |

Rules:
1. A component not present for an entity's archetype holds zero in every buffer for that slot; the owner stage writes zero there every tick (REQ-MUT-002).
2. A Command whose apply rule names a component absent on the target is dropped (REQ-MUT-009); `ENERGY_TRANSFER` is the exception that resolves by archetype (REQ-MUT-004).
3. Stage 4 systems consume no PRNG draw for a slot whose archetype lacks the Cognitive tag; Stage 5 systems consume none for a slot lacking the Cultural tag (DEOS-CORE `PRNG`: draw count fixed by code path).
4. For an Institution, the `MemeVector` component and `InstitutionState.policy` hold identical values at the end of every tick: the Stage 5 owner writes both from one computed value (REQ-CMP-007, REQ-CMP-010).

Player-facing consequence: plants, agents, and Institutions are three shapes of one data model, so the Network Map can draw a tribe and its members with the same MemeVector similarity rule, and a temple is inspectable with the same panel as the priest who founded it (GI-5).

### 6.2 Component catalog (`CMP`)

The catalog index below is the hash and Snapshot order of REQ-DAT-007. `Position2D` and `EnergyState` are specified by REQ-ENT-002 and REQ-ENT-003; the requirements of this section specify the other ten, the Cell fields, and the `WorldMood` slot. Section 8.1 tabulates sizes, owners, and initial values in one place.

| # | Component | Requirement | Bytes per slot | Archetype tag | Owner stage |
| ---: | :--- | :--- | ---: | :--- | :--- |
| 0 | `Position2D` | REQ-ENT-002 | 16 | 0x01 | 4 |
| 1 | `EnergyState` | REQ-ENT-003 | 24 | 0x02 | 3 |
| 2 | `Lifecycle` | REQ-CMP-001 | 24 | any | 3 |
| 3 | `Genome` | REQ-CMP-002 | 64 | 0x02 | 3 (computed), written in Stage 6 spawn |
| 4 | `Needs` | REQ-CMP-003 | 128 | 0x02 levels, 0x04 weights | 3 (levels), 4 (weights) |
| 5 | `Perception` | REQ-CMP-004 | 288 | 0x04 | 4 |
| 6 | `Memory` | REQ-CMP-005 | 520 | 0x04 | 4 |
| 7 | `Decision` | REQ-CMP-006 | 64 | 0x04 | 4 |
| 8 | `MemeVector` | REQ-CMP-007 | 256 | 0x08 | 5 |
| 9 | `TrustEdges` | REQ-CMP-008 | 128 | 0x08 | 5 |
| 10 | `Affiliation` | REQ-CMP-009 | 32 | 0x08 | 5 |
| 11 | `InstitutionState` | REQ-CMP-010 | 288 | 0x10 | 5 |

### REQ-CMP-001: `Lifecycle`
Layout per slot (24 bytes), present on every archetype, owner Stage 3, double-buffered:

```c
struct Lifecycle {            // 24 bytes
    uint64_t born_tick;       // tick in which the SPAWN resolved (Stage 6 of that tick)
    uint64_t parent;          // EntityID of SPAWN.source, or NULL_ENTITY_ID
    uint32_t age_ticks;       // ticks since born_tick; saturates at 0xFFFFFFFF
    uint16_t generation;      // lineage depth: parent's generation + 1, saturating at 65535; 0 for Ingress spawns
    uint8_t  alive;           // 1 = live, 0 = dead or free
    uint8_t  death_cause;     // 0 NONE, 1 STARVATION, 2 AGE, 3 DAMAGE, 4 CATALYST, 5 DISSOLUTION; 6-255 reserved, treated as 0
};
```

`Lifecycle.generation` is the *lineage* generation and is distinct from the slot generation of REQ-ENT-001. Owner rule: Stage 3 writes `age_ticks = min(A.age_ticks + 1, 0xFFFFFFFF)` for every live slot, copies `born_tick`, `parent`, `generation`, and sets `alive`/`death_cause` per REQ-ENT-009 rule 1. Initial value at spawn: `born_tick = t`, `parent = source`, `age_ticks = 0`, `generation` from `payload[3]` bits 16 to 31, `alive = 1`, `death_cause = 0`.

Player-facing consequence: the inspect view shows an agent's age in simulated days (`age_ticks` / `TICKS_PER_DAY`), its generation since the founding population, and, on death, why it died, straight from this record (GI-5).

### REQ-CMP-002: `Genome` and the parameter table
Layout per slot (64 bytes), Biological archetype, single-buffered, immutable after spawn:

```c
struct Genome {               // 64 bytes; GENE_COUNT = 32
    uint16_t gene[32];        // each in [0, 65535]
};
```

**Mapping.** Every gene maps into a Q32.32 parameter by

```
gene_param(genome, row) = min_row + floor( (max_row - min_row) * gene[row] / 65535 )
```

computed with a 128-bit intermediate: `(max_row − min_row)` is Q32.32 and non-negative, the product with the integer `gene[row]` cannot overflow 128 bits, the division by the integer 65,535 rounds toward negative infinity, and the result lies in `[min_row, max_row]` exactly (gene 0 yields `min_row`, gene 65,535 yields `max_row`). No saturation is reachable because every `max_row` is below 2^31.

**Parameter table (genes 0 to 15).** Values are Q32.32; the hex column is the raw `int64_t`.

| Row | Parameter | Unit | min | max | min (raw) | max (raw) | Consumed by |
| ---: | :--- | :--- | ---: | ---: | :--- | :--- | :--- |
| 0 | `max_capacity` | energy | 50.0 | 200.0 | 0x0000003200000000 | 0x000000C800000000 | REQ-ENT-003 |
| 1 | `metabolic_rate` | energy / tick | 0.0078125 | 0.125 | 0x0000000002000000 | 0x0000000020000000 | REQ-ENT-003, Stage 3 |
| 2 | `reproduction_threshold` | fraction of `max_capacity` | 0.5 | 0.9375 | 0x0000000080000000 | 0x00000000F0000000 | Stage 3 |
| 3 | `reproduction_cost` | fraction of `max_capacity` | 0.125 | 0.5 | 0x0000000020000000 | 0x0000000080000000 | Stage 3 |
| 4 | `max_age` | ticks (integer part) | 7,200 | 115,200 | 0x00001C2000000000 | 0x0001C20000000000 | Stage 3 |
| 5 | `move_speed` | Cells / tick | 0.03125 | 0.5 | 0x0000000008000000 | 0x0000000080000000 | Stage 4 |
| 6 | `perception_acuity` | weight | 0.0 | 1.0 | 0x0000000000000000 | 0x0000000100000000 | Stage 4 |
| 7 | `forage_efficiency` | fraction of Cell energy per draw | 0.0625 | 0.5 | 0x0000000010000000 | 0x0000000080000000 | Stage 4 |
| 8 | `thermal_optimum` | temperature (DEOS-CORE unit) | −16.0 | 48.0 | 0xFFFFFFF000000000 | 0x0000003000000000 | Stage 3 |
| 9 | `thermal_tolerance` | temperature half-width | 2.0 | 32.0 | 0x0000000200000000 | 0x0000002000000000 | Stage 3 |
| 10 | `moisture_optimum` | moisture | 0.0 | 1.0 | 0x0000000000000000 | 0x0000000100000000 | Stage 3 |
| 11 | `aggression` | weight | 0.0 | 1.0 | 0x0000000000000000 | 0x0000000100000000 | Stage 4 |
| 12 | `altruism` | weight | 0.0 | 1.0 | 0x0000000000000000 | 0x0000000100000000 | Stage 4, 5 |
| 13 | `conformity` | Meme adoption rate | 0.0 | 1.0 | 0x0000000000000000 | 0x0000000100000000 | Stage 5 |
| 14 | `curiosity` | exploration weight | 0.0 | 1.0 | 0x0000000000000000 | 0x0000000100000000 | Stage 4 |
| 15 | `mutation_rate_base` | per-gene probability | 0.0009765625 | 0.03125 | 0x0000000000400000 | 0x0000000008000000 | Stage 3 |

**Trait table (genes 16 to 31).** Each maps to `[0.0, 1.0]` by the same formula with `min` = 0 and `max` = 1.0.

| Genes | Trait | Consumed by |
| :--- | :--- | :--- |
| 16 … 23 | `need_weight_bias[k]`, k = gene − 16, one per need of `NEED_COUNT` = 8 | REQ-CMP-003 initial weights; Stage 4 |
| 24 | `trust_gain_rate` | Stage 5 |
| 25 | `trust_decay_rate` | Stage 5 |
| 26 | `forgiveness` | Stage 5 |
| 27 | `loyalty` | Stage 5 |
| 28 | `memory_salience` | Stage 4 |
| 29 | `risk_tolerance` | Stage 4 |
| 30 | `fertility` | Stage 3 |
| 31 | `receptivity` (to Ingress Meme deltas and transmission) | Stage 5 |

Rules:
1. A Genome is written exactly once, in Stage 6 substep 6.2, from the SpawnPayload the parent's Stage 3 system produced (inheritance and per-gene mutation under `mutation_bias` are DEOS-PROTO rules executed in Stage 3 with the Stage 3 PRNG stream) or from the `SPAWN_INIT` stream (REQ-ENT-008). Despawn zeroes it (REQ-ENT-009).
2. No Command and no owner pass modifies a live Genome; `mutation_bias` affects only the child's genes at reproduction (DEOS section 5.3).
3. Initial value: as written at spawn; Institutions have no Genome (all zero).

Player-facing consequence: every trait the inspect view lists for an agent is one of these 32 numbers, so the player who raised `mutation_bias` in a valley can open a descendant, see which rows drifted, and follow the Genome-drift Notable Events DEOS-PROTO emits (GI-5, GI-7).

### REQ-CMP-003: `Needs`
Layout per slot (128 bytes), levels present on the Biological tag and written by Stage 3, weights present on the Cognitive tag and written by Stage 4; both double-buffered as two separate field groups with two owner stages:

```c
struct Needs {                // 128 bytes; NEED_COUNT = 8
    int64_t level[8];         // Q32.32 in [0, 1]; owner Stage 3
    int64_t weight[8];        // Q32.32 in [0, 1]; owner Stage 4
};
```

Rules:
1. `level[k]` is the satisfaction of need `k` (1.0 = fully satisfied); `weight[k]` is its current utility weight. Need indices 0 to 7 are named and updated by DEOS-PROTO (`COG`); this module fixes only range, order, and ownership.
2. Every write clamps each element to `[0, 1.0]` (raw `[0, 0x0000000100000000]`).
3. Initial value at spawn: `level[k] = 0.5` (raw 0x0000000080000000) for all k; `weight[k] = gene_param` of gene 16 + k for Agents, 0 for Organisms and Institutions.
4. Utility scoring (DEOS-PROTO) reads `weight` from A and `level` from B (Stage 3 < Stage 4, REQ-MUT-001), so a decision reacts to this tick's metabolism with last tick's weights.

Player-facing consequence: the Decision Trace's three contributors are indices into this array, so "hunger 0.71, safety −0.20, belonging 0.12" on the inspect panel are literal values the player can watch change tick by tick (GI-5).

### REQ-CMP-004: `Perception`
Layout per slot (288 bytes), Cognitive tag, owner Stage 4, double-buffered. A fixed-size summary of the Cells and entities within Chebyshev distance `PERCEPTION_RADIUS` = 4 of the entity's Cell, excluding its own Cell and itself:

```c
struct PerceptionSector {     // 24 bytes
    int64_t energy_sum;       // Q32.32, saturating sum of Cell energy over the sector's in-range Cells
    int64_t temperature_mean; // Q32.32, floor(sum / in-range count); 0 when the count is 0
    int64_t moisture_mean;    // Q32.32, floor(sum / in-range count); 0 when the count is 0
};
struct PerceptionNearest {    // 16 bytes
    uint64_t id;              // EntityID or NULL_ENTITY_ID
    int64_t  distance_sq;     // Q32.32, dx*dx + dy*dy in Cell units, from Position2D in A
};
struct Perception {           // 288 bytes; PERCEPTION_SECTORS = 8, PERCEPTION_NEAREST = 4
    uint32_t cell;            // the entity's own Cell index from Position2D in A
    uint16_t sensed_count;    // live entities within the radius, saturating at 65535
    uint8_t  in_range_mask;   // bit s set when sector s has at least one in-range Cell
    uint8_t  pad;             // 0
    struct PerceptionSector sector[8];        // 192 bytes
    uint16_t sector_entities[8];              // live entities per sector, saturating at 65535
    uint8_t  sector_material[8];              // modal material_id per sector; ties → lowest id; 0 when no Cells
    struct PerceptionNearest nearest[4];      // 64 bytes, ascending (distance_sq, id); unused entries zero
};
```

**Sector assignment.** For a Cell at integer offset `(dx, dy)` from the entity's Cell, with `dx, dy ∈ [−4, 4]` and not both zero:

| Condition | Sector | Cells at radius 4 |
| :--- | :---: | ---: |
| `|dx| < |dy|` and `dy < 0` | 0 (N) | 16 |
| `|dx| == |dy|` and `dx > 0` and `dy < 0` | 1 (NE) | 4 |
| `|dx| > |dy|` and `dx > 0` | 2 (E) | 16 |
| `|dx| == |dy|` and `dx > 0` and `dy > 0` | 3 (SE) | 4 |
| `|dx| < |dy|` and `dy > 0` | 4 (S) | 16 |
| `|dx| == |dy|` and `dx < 0` and `dy > 0` | 5 (SW) | 4 |
| `|dx| > |dy|` and `dx < 0` | 6 (W) | 16 |
| `|dx| == |dy|` and `dx < 0` and `dy < 0` | 7 (NW) | 4 |

The 80 non-self Cells of the 9 × 9 square are covered exactly once. Cells outside the grid are excluded from sums, counts, and the modal material; `in_range_mask` records which sectors had any Cell.

**Nearest entities.** Every live entity (A.`alive` = 1, index ≠ self) in the 81-Cell square, found through the SpatialIndex (REQ-DAT-009), is a candidate with `distance_sq = mul_q(dx, dx) + mul_q(dy, dy)` where `dx = other.x − self.x` and `dy = other.y − self.y` in Q32.32 (each product floors on the fractional shift; the sum cannot overflow since each term is below 32.0). The four candidates with the smallest `(distance_sq, id)` in lexicographic order fill `nearest[0..3]`; fewer than four candidates leave trailing entries zero. Candidate enumeration order does not affect the result because the key is a total order over distinct `EntityID` values.

Rules:
1. Perception reads `Position2D`, `Lifecycle.alive`, and `MemeVector` from A (their owner stages are ≥ 4 or the stage is 4) and Cell fields from B (owner Stage 2 < 4), per REQ-MUT-001.
2. The Stage 4 system computes Perception into a local record, uses that local record for utility scoring in the same pass, and writes it to B; it never reads Perception from B (REQ-MUT-008).
3. Initial value at spawn: all zero.

Player-facing consequence: when the player asks why an agent fled south, the inspect view shows the eight sector aggregates and the four nearest entities the agent actually saw at that tick, so "it saw a stronger rival to the north and richer ground to the south" is read from data, not inferred (GI-5).

### REQ-CMP-005: `Memory`
Layout per slot (520 bytes), Cognitive tag, owner Stage 4, double-buffered. A ring of `MEMORY_SLOTS` = 16 entries:

```c
struct MemoryEntry {          // 32 bytes
    uint64_t tick;            // tick of the remembered outcome
    uint16_t kind;            // 0 EMPTY; kinds >= 1 enumerated by DEOS-PROTO (COG)
    uint16_t pad;             // 0
    uint32_t cell;            // Cell index where it happened
    int64_t  magnitude;       // Q32.32 signed
    uint64_t subject;         // EntityID involved, or NULL_ENTITY_ID
};
struct Memory {               // 520 bytes
    uint16_t head;            // index of the next entry to overwrite, in [0, 16)
    uint16_t count;           // live entries, in [0, 16]
    uint32_t pad;             // 0
    struct MemoryEntry entry[16];
};
```

Rules:
1. Append: `entry[head] = e; head = (head + 1) & 15; count = min(count + 1, 16)`. Entries are read newest-first as `entry[(head − 1 − i) & 15]` for `i` in `[0, count)`.
2. The Stage 4 owner appends at most 4 entries per tick per entity, in the order DEOS-PROTO specifies, then copies the remaining entries unchanged; an entry whose `subject` fails validation (REQ-ENT-004) keeps `tick`, `kind`, `cell`, `magnitude` and has `subject` rewritten to `NULL_ENTITY_ID`.
3. Initial value at spawn: all zero (`count` = 0).

Player-facing consequence: the "Memories" panel of an inspected agent is this ring, newest first, each row naming a tick the player can jump the Chronicle to, so an agent's grudge or gratitude traces to an outcome the player can replay (GI-5).

### REQ-CMP-006: `Decision`
Layout per slot (64 bytes), Cognitive tag, owner Stage 4, double-buffered. Holds the chosen action and the `DecisionTrace` of DEOS section 5.4:

```c
struct DecisionTraceContributor {  // 12 bytes
    uint8_t  need;            // index into Needs, in [0, 8); 0xFF when the slot is unused
    uint8_t  pad[3];          // 0
    int64_t  weight;          // Q32.32 signed contribution
};
struct DecisionTrace {        // 40 bytes (DEOS section 5.4)
    uint16_t action;          // chosen action; 0 = NONE
    uint16_t pad;             // 0
    struct DecisionTraceContributor contributors[3];  // descending |weight|, ties → ascending need
};
struct Decision {             // 64 bytes
    uint16_t action;          // == trace.action
    uint16_t flags;           // bit 0: target is a Cell; bit 1: action issued a Command this tick; bit 2: exploratory choice (DEOS-PROTO); bits 3-15: 0
    uint32_t target_cell;     // Cell index when flags bit 0 is set, else 0
    uint64_t target;          // EntityID when flags bit 0 is clear, else NULL_ENTITY_ID
    int64_t  utility;         // Q32.32 utility of the chosen action
    struct DecisionTrace trace;
};
```

Rules:
1. Action values ≥ 1 are enumerated by DEOS-PROTO (`COG`); `action` = 0 is written only for slots whose archetype lacks the Cognitive tag or whose `alive` is 0 in B.
2. Invariant: `action == trace.action`; every live Agent slot written in Stage 4 has `action ≠ 0` and three contributors (DEOS-F05 P6), with `need` = 0xFF and `weight` = 0 marking a contributor slot DEOS-PROTO declares unused.
3. Initial value at spawn: all zero.
4. The index of a Decision Trace, as referenced by `NotableEvent.cause` (DEOS section 5.4), is the slot index of the entity whose `Decision` was written in the same tick as the Notable Event.

Player-facing consequence: this record is the "why" panel: the action, its utility, and the three needs that drove it with signed weights, and it is the record a Chronicle row's chevron drills down to (commitment C6, GI-5).

### REQ-CMP-007: `MemeVector`
Layout per slot (256 bytes), Cultural tag, owner Stage 5, double-buffered:

```c
struct MemeVector {           // 256 bytes; MEME_DIM = 32
    int64_t v[32];            // Q32.32, each in [-1, 1]
};
```

Rules:
1. **Norm invariant.** The max-norm is bounded: `|v[i]| ≤ 1.0` for every `i`. Every write, by the owner or by the `MEME_DELTA` Command, clamps each element to `[−1.0, 1.0]` (raw `[0xFFFFFFFF00000000, 0x0000000100000000]`); there is no rescaling step, so the invariant is enforced without a square root and without rounding error.
2. Dimension semantics (belief and knowledge dimensions, technology dimensions) are enumerated by DEOS-PROTO (`SOC`); this module fixes count, range, and ownership.
3. Similarity between two vectors, used by the Network Map (commitment C7) and by DEOS-PROTO, is `dot(a, b) = Σ mul_q(a[i], b[i])` accumulated in a 128-bit integer and floored to Q32.32 once at the end; the magnitude is at most 32.0 so no saturation occurs.
4. Initial value at spawn: Agents inherit the parent's `MemeVector` from B (a copy, with `receptivity`-weighted drift left to DEOS-PROTO in Stage 5); Institutions copy the founder's `MemeVector` from B; Organisms hold zero.

Player-facing consequence: an idea the player seeded with a Mutation-family or Cosmic Catalyst Action is a bounded delta on these 32 numbers, and the Network Map's colour of a settlement is their similarity, so the player watches a belief spread as a visible gradient (GI-5, GI-7).

### REQ-CMP-008: `TrustEdges`
Layout per slot (128 bytes), Cultural tag, owner Stage 5, double-buffered:

```c
struct TrustEdge {            // 16 bytes
    uint64_t id;              // EntityID or NULL_ENTITY_ID
    int64_t  weight;          // Q32.32 in [-1, 1]; 0 when id is NULL_ENTITY_ID
};
struct TrustEdges {           // 128 bytes; TRUST_EDGES = 8
    struct TrustEdge edge[8];
};
```

Rules:
1. **Canonical order.** Non-null edges occupy the lowest indices in ascending `id`; null edges follow. Every writer (owner pass and `TRUST_DELTA` apply) restores this order with an 8-element insertion sort before storing, so two identical edge sets always serialize to identical bytes.
2. An edge whose `id` fails validation (REQ-ENT-004) is removed by the owner pass (set to null, re-sorted).
3. Every `weight` write clamps to `[−1.0, 1.0]`.
4. Initial value at spawn: Agents receive one edge `{ parent, +0.5 }` when the parent is valid in B, else none; Institutions receive one edge `{ founder, +0.5 }`; Organisms hold zero.

Player-facing consequence: the Living Diagram draws these eight edges per entity as the trust graph, and because the array is canonically ordered the same graph appears in the same shape on every replay (GI-1, GI-5).

### REQ-CMP-009: `Affiliation`
Layout per slot (32 bytes), Cultural tag, owner Stage 5, double-buffered:

```c
struct Affiliation {          // 32 bytes
    uint64_t institution;     // EntityID of the Institution, or NULL_ENTITY_ID
    uint64_t joined_tick;     // tick of the INSTITUTION_JOIN Command; 0 when none
    int64_t  standing;        // Q32.32 in [-1, 1]; 0 when none
    uint8_t  role;            // 0 NONE, 1 MEMBER, 2 ELDER, 3 FOUNDER; 4-255 reserved, treated as 0
    uint8_t  pad[7];          // 0
};
```

Rules:
1. An entity holds at most one Affiliation. Joining is an own write of this component in Stage 5 together with an `INSTITUTION_JOIN` Command to the Institution (REQ-MUT-004); leaving is an own write together with `INSTITUTION_LEAVE`.
2. When `institution` fails validation in the owner pass (the Institution despawned), the owner writes `{ NULL_ENTITY_ID, 0, 0, 0 }`; no `INSTITUTION_LEAVE` is issued for a dissolved Institution.
3. For an Institution entity, `institution` names a parent Institution or `NULL_ENTITY_ID`; the same rules apply.
4. Initial value at spawn: all zero.

Player-facing consequence: the Living Diagram's membership lines are this one field per entity, and a tribe's dissolution shows as members' lines vanishing one tick later, which is exactly when the data changed (GI-5).

### REQ-CMP-010: `InstitutionState`
Layout per slot (288 bytes), Institutional tag, owner Stage 5, double-buffered. Slabs exist only for the Chunks of the Institution range (REQ-ENT-007); the element for Institution `index` is at `index − INSTITUTION_BASE`.

```c
struct InstitutionState {     // 288 bytes
    int64_t  pooled_energy;   // Q32.32 >= 0; saturating
    uint64_t founded_tick;    // tick in which the SPAWN resolved
    uint64_t founder;         // EntityID of SPAWN.source (validated by readers)
    uint32_t member_count;    // count of INSTITUTION_JOIN minus INSTITUTION_LEAVE applied; saturating
    uint8_t  status;          // 1 active, 0 dissolving (DESPAWN issued this tick)
    uint8_t  discovered;      // bit k set when technology k has been discovered (DEOS-PROTO); 0 at spawn
    uint8_t  pad[2];          // 0
    int64_t  policy[32];      // Q32.32, each in [-1, 1]; == the Institution's MemeVector (REQ-ENT-010 rule 4)
};
```

Rules:
1. `pooled_energy` changes through `ENERGY_TRANSFER` Commands (as source: debit; as target: credit) and through the owner pass (DEOS-PROTO upkeep, which returns energy to the Substrate by `CELL_ENERGY_DELTA`); it never goes below 0 and saturates at `INT64_MAX` with the excess accounted as dissipation (REQ-MUT-009).
2. `member_count` is maintained only by `INSTITUTION_JOIN` (+1, saturating at 0xFFFFFFFF) and `INSTITUTION_LEAVE` (−1, floor 0). DEOS-F05 P2 reads this field.
3. Initial value at spawn: `pooled_energy = 0`, `founded_tick = t`, `founder = source`, `member_count = 0`, `status = 1`, `policy` = founder's `MemeVector` from B.

Player-facing consequence: the tribe card the player opens shows pooled energy, members, founding day, and the founder, and the Chronicle's "first Institution" Notable Event and the World Phase 3 marker both key off this record (GI-5, commitment C5).

### REQ-CMP-011: Substrate Cell fields
Cells are not entities and hold SoA fields (DEOS section 4). Six arrays, each of `GRID_W` × `GRID_H` elements in row-major Cell index order (`cell = y * GRID_W + x`), each 64-byte aligned, double-buffered, laid out in Cell Chunk slabs of `CELL_CHUNK_SIZE` = 1,024 Cells (REQ-DAT-004):

| # | Field | Type | Bytes | Range | Written by | Command-writable |
| ---: | :--- | :--- | ---: | :--- | :--- | :--- |
| 0 | `energy` | `int64_t` Q32.32 | 8 | ≥ 0 (DEOS-CORE `LAW`) | Stage 2 owner; Stage 1 via IngressOverlay | `CELL_ENERGY_DELTA` |
| 1 | `temperature` | `int64_t` Q32.32 | 8 | DEOS-CORE unit and range | Stage 2; Stage 1 via IngressOverlay | none |
| 2 | `moisture` | `int64_t` Q32.32 | 8 | [0, 1] | Stage 2; Stage 1 via IngressOverlay | none |
| 3 | `elevation` | `int64_t` Q32.32 | 8 | DEOS-CORE unit and range | Stage 2 (copy unless a DEOS-CORE law changes it); Stage 1 via IngressOverlay | none |
| 4 | `material_id` | `uint8_t` | 1 | enumerated by DEOS-CORE; 0 = none | Stage 2; Stage 1 via IngressOverlay | none |
| 5 | `mutation_bias` | `int64_t` Q32.32 | 8 | [0.25, 4.0] (raw [0x0000000040000000, 0x0000000400000000]); default 1.0 | Stage 1 via IngressOverlay (`SET`, `ADD`, `MUL`); decays toward 1.0 in Stage 2 at the DEOS-CORE rate | none |

41 bytes per Cell per buffer. Rules:
1. Stage 2 is the owner of every field: it writes every Cell of every Cell Chunk into B each tick, reading A and the IngressOverlay (REQ-MUT-011). Stages 3 to 5 read Cells from B.
2. Every write clamps `mutation_bias` to `[0.25, 4.0]` and `moisture` to `[0, 1.0]`, and floors `energy` at 0.
3. Initial values at world generation are written by DEOS-RT before tick 0 through the same owner path with tick = 0; `mutation_bias` is 1.0 in every Cell of every new world.

Player-facing consequence: the Climate, Resource, and Mutation sliders on the Catalyst Palette write exactly these fields and nothing else, so the player's influence is always a visible change in the ground the agents stand on (commitments C1, C3; GI-6).

### REQ-CMP-012: `WorldMood` slot
The `WorldMood` record of DEOS section 5.4 is stored in a 64-byte slot:

```c
struct WorldMoodSlot {        // 64 bytes; bytes 0-47 are the DEOS section 5.4 record
    uint64_t tick;
    uint32_t population;      // live slots with the Biological tag at the end of Stage 5
    uint32_t institutions;    // live slots with the Institutional tag at the end of Stage 5
    int64_t  cooperation;     // Q32.32, computed by DEOS-PROTO (SOC)
    int64_t  conflict;        // Q32.32
    int64_t  growth;          // Q32.32
    int64_t  entropy;         // Q32.32
    uint64_t reserved[2];     // 0
};
```

One slot is authoritative state per tick (the Kernel's current `WorldMood`); DEOS-RT copies it into the egress ring in Stage 6. `population` and `institutions` are computed by summing per-Chunk live counts in ascending Chunk index after the Stage 5 barrier; the Q32.32 fields are written by DEOS-PROTO with saturating arithmetic. The slot is serialized last in a Snapshot's ECS sections (REQ-DAT-008) and is hashed as its own leaf by DEOS-RT.

Player-facing consequence: the Affective Signals the Host turns into harmony and dissonance are these four numbers, emitted every tick, so the player hears a war before reading it (commitment C8).

### REQ-CMP-013: Ownership matrix and read rule
Every component field group and Cell field has exactly one owner stage, one buffering class, and a fixed set of Command kinds that may modify it after the owner's write in the same tick. The table is binding for every system.

| Data | Owner stage | Buffering | Modified at barriers by | Read by stage s from |
| :--- | :---: | :--- | :--- | :--- |
| `entity_table` | 6 (substeps 6.2, 6.3) | single | — | the table (stable during Stages 1 to 5) |
| `Position2D` | 4 | double | — | A when s ≤ 4, B when s ≥ 5 |
| `EnergyState` | 3 | double | `ENERGY_TRANSFER`, `DAMAGE`, `CELL_ENERGY_DELTA` (source side) | A when s ≤ 3, B when s ≥ 4 |
| `Lifecycle` | 3 | double | — | A when s ≤ 3, B when s ≥ 4 |
| `Genome` | 6 (substep 6.2) | single | — | the array (stable during Stages 1 to 5) |
| `Needs.level` | 3 | double | — | A when s ≤ 3, B when s ≥ 4 |
| `Needs.weight` | 4 | double | — | A when s ≤ 4, B when s ≥ 5 |
| `Perception` | 4 | double | — | A when s ≤ 4, B when s ≥ 5 |
| `Memory` | 4 | double | — | A when s ≤ 4, B when s ≥ 5 |
| `Decision` | 4 | double | — | A when s ≤ 4, B when s ≥ 5 |
| `MemeVector` | 5 | double | `MEME_DELTA` | A when s ≤ 5, B when s = 6 |
| `TrustEdges` | 5 | double | `TRUST_DELTA` | A when s ≤ 5, B when s = 6 |
| `Affiliation` | 5 | double | — | A when s ≤ 5, B when s = 6 |
| `InstitutionState` | 5 | double | `ENERGY_TRANSFER`, `INSTITUTION_JOIN`, `INSTITUTION_LEAVE` | A when s ≤ 5, B when s = 6 |
| Cell fields | 2 (Stage 1 through the IngressOverlay) | double | `CELL_ENERGY_DELTA` (target side) | A when s ≤ 2 (plus the IngressOverlay in Stage 2), B when s ≥ 3 |
| `WorldMoodSlot` | 5 (end of stage) | single | — | Stage 6 |

The read rule in one sentence: **a system in stage s reads a datum from B when the datum's owner stage is below s, and from A otherwise.** A Command may target only a datum whose owner stage is ≤ the issuing stage (assertion, REQ-MUT-005), which is why every kind in REQ-MUT-004 modifies B in place at its barrier and is never overwritten later in the tick.

Player-facing consequence: because the same table decides what every system sees, a decision made in Stage 4 always sees this tick's hunger and last tick's beliefs, on every machine, which is the precondition for the replayed story matching the lived one (GI-1).

### 6.3 Memory layout (`DAT`)

### REQ-DAT-001: 64-Byte Cache Line Boundary Alignment
All component arrays must be aligned on **64-byte boundaries** (`alignas(64)` in C/C++, `#[repr(align(64))]` in Rust) to match modern CPU cache line sizes and facilitate SIMD auto-vectorization (AVX-512 / ARM Neon). Tightened: every Chunk slab, every leaf field array inside a slab (REQ-DAT-004), every Cell field array, the entity table, every outbox, every lifecycle outbox, the SpawnPayload pool, and every derived structure of REQ-DAT-003 starts at an address that is a multiple of `CACHE_LINE` = 64, and the Kernel asserts this for every pool at initialization (DEOS section 7, "every array is 64-byte aligned").

Player-facing consequence: alignment is what lets a million-agent Stage 2 and Stage 4 pass fit `TICK_BUDGET_MS`, which is what lets the player run a v1.0 world at speed 1× and an MVS catch-up in under a minute (DEOS-F05 P3).

### REQ-DAT-002: Zero Heap Allocation During Tick
All memory required for entities, components, queues, and state buffers must be **pre-allocated** in fixed contiguous pools during engine initialization. Calling `malloc()`, `free()`, `new`, or GC triggers inside the tick pipeline is strictly illegal. Tightened: the allocation counter installed at Kernel initialization (DEOS-F05 section 1.1) reads 0 after every tick of the acceptance run; the pools of REQ-DAT-003 are the only heap memory the Kernel owns, and their sizes are pure functions of the registry constants and the scale (REQ-ENT-007), so a conforming Kernel can print its exact footprint before allocating it.

Player-facing consequence: no tick ever stalls on the allocator, so the Time Control's speed levels feel like a dial and not a lottery, and Acceleration produces a steady stream of Chronicle rows (DEOS-F05 P3).

### REQ-DAT-003: Pool allocator design
The Kernel allocates exactly one arena at initialization and carves the pools below from it, in this order, each pool's start rounded up to 64 bytes and each pool's size rounded up to a multiple of 64 bytes. Sizes are stated for one buffer; double-buffered pools are allocated twice (A then B), consecutively.

| # | Pool | Elements | Bytes per element | Buffers |
| ---: | :--- | :--- | ---: | :---: |
| 0 | Entity table (REQ-ENT-005) | `MAX_ENTITIES` | 8 | 1 |
| 1 | Component slabs, catalog #0 to #10 (REQ-DAT-004) | `MAX_ENTITIES` per component | per section 8.1 | 2 |
| 2 | `Genome` slabs | `MAX_ENTITIES` | 64 | 1 |
| 3 | `InstitutionState` slabs | `MAX_INSTITUTIONS` | 288 | 2 |
| 4 | Cell field arrays (REQ-CMP-011) | `GRID_W` × `GRID_H` | 41 (six arrays) | 2 |
| 5 | Free bitmap and summary (REQ-ENT-006) | `MAX_ENTITIES` bits + `MAX_ENTITIES` / 64 bits | — | 1 |
| 6 | Outboxes (REQ-MUT-005) | `NUM_CHUNKS` × `MAX_COMMANDS_PER_ENTITY_PER_STAGE` × `CHUNK_SIZE` | 64 | 1 |
| 7 | Outbox segment offsets (REQ-MUT-006) | `NUM_CHUNKS` × (`NUM_CHUNKS` + 1) entity offsets + `NUM_CHUNKS` × (`NUM_CELL_CHUNKS` + 1) Cell offsets | 4 | 1 |
| 8 | Lifecycle outboxes (REQ-ENT-008, REQ-ENT-009) | `NUM_CHUNKS` × 2 × `CHUNK_SIZE` | 64 | 1 |
| 9 | Ingress lifecycle outbox | `MAX_INGRESS_WRITES_PER_TICK` = 1,024 | 64 | 1 |
| 10 | Spawn references (REQ-MUT-010 substep 6.1) | `NUM_CHUNKS` × `CHUNK_SIZE` | 4 | 1 |
| 11 | SpatialIndex (REQ-DAT-009) | `sorted[MAX_ENTITIES]`, `scratch[MAX_ENTITIES]`, `cell_start[Cells + 1]`, `hist[NUM_CHUNKS][1024]` | 4 | 1 |
| 12 | SpawnPayload (REQ-ENT-008) | `MAX_ENTITIES` | 64 | 1 |
| 13 | IngressOverlay (REQ-MUT-011) | `MAX_INGRESS_WRITES_PER_TICK` = 1,024 | 32 | 1 |
| 14 | Chunk ledgers (REQ-MUT-009) | `NUM_CHUNKS` + `NUM_CELL_CHUNKS` | 24 | 1 |
| 15 | `WorldMoodSlot` (REQ-CMP-012) | 1 | 64 | 1 |

Rules:
1. Pools 0 to 4 and 15 are authoritative state; pools 5 to 14 are derived structures, zeroed at initialization and rebuilt or cleared as their requirements state.
2. Every pool address is stored in the Kernel context as a base pointer plus element count; no pool is resized, moved, or freed before `EE_Kernel_Shutdown`.
3. The arena size is computed before allocation as the sum of the rounded pool sizes; REQ-DAT-010 tabulates it.

Player-facing consequence: the Kernel's footprint is a number printed at startup, so the Host can tell the player on a phone that the MVS world fits with room to spare instead of discovering it mid-Epoch.

### REQ-DAT-004: Chunk-major Struct-of-Arrays layout
For every component, the pool is an array of `NUM_CHUNKS` slabs; slab `c` holds the component for slots `[c × CHUNK_SIZE, (c + 1) × CHUNK_SIZE)`. Inside a slab, the record is flattened into leaf scalar fields in declared order, each array element of a fixed-size field becoming its own leaf, and each leaf becomes one contiguous array of `CHUNK_SIZE` elements:

```
slab(c) for Position2D:   x[1024] | y[1024]
slab(c) for Genome:       gene[0][1024] | gene[1][1024] | … | gene[31][1024]
slab(c) for TrustEdges:   edge[0].id[1024] | edge[0].weight[1024] | edge[1].id[1024] | … | edge[7].weight[1024]
```

Rules:
1. The address of leaf `f` of slot `i` is `pool + chunk(i) × SLAB_BYTES + LEAF_OFFSET[f] + slot_in_chunk(i) × sizeof(f)`, where `SLAB_BYTES` = bytes-per-slot × `CHUNK_SIZE` and `LEAF_OFFSET[f]` is the prefix sum of `CHUNK_SIZE` × sizeof of the preceding leaves. Every leaf array is a multiple of 64 bytes because `CHUNK_SIZE` = 1,024 and sizeof(f) ∈ {1, 2, 4, 8}.
2. One Chunk's data for one component is therefore one contiguous slab, which a single worker owns for the stage; the read of another Chunk's slab is permitted only under the read rule of REQ-CMP-013.
3. The `InstitutionState` pool has `MAX_INSTITUTIONS` / `CHUNK_SIZE` slabs, slab `k` serving Chunk `INSTITUTION_BASE` / `CHUNK_SIZE` + k.
4. Cell field arrays follow the same rule with Cell Chunk slabs of `CELL_CHUNK_SIZE` = 1,024 Cells per field.
5. The in-memory layout is never hashed or serialized directly; REQ-DAT-007 defines the canonical byte stream.

Player-facing consequence: this layout is why a worker thread streams through a Chunk without cache misses, which is why one Epoch of catch-up fits in a minute on MVS hardware and a million agents fit a 16.6 ms tick (Pillar 3).

### REQ-DAT-005: Padding rules
1. Every record type in this module has a size that is a multiple of 8 bytes; every array pool and every slab has a size that is a multiple of 64 bytes (rules 1 and 2 hold by the tables of section 8 and REQ-DAT-004).
2. Explicit `pad` fields are always written as zero by every writer and are serialized as zero (REQ-DAT-007); a reader never interprets them.
3. Reserved enumerations (`death_cause` 6 to 255, `role` 4 to 255, Command kinds 10 to 65535, Memory kind semantics, action values) are interpreted as their zero value by this module; a future revision that assigns them bumps `SNAPSHOT_LAYOUT_VERSION`.

Player-facing consequence: padding that is always zero is the difference between "same world, same bytes" and a Desync that no player is able to explain (GI-1).

### REQ-DAT-006: Indices only, never pointers
No component, Cell field, Command, SpawnPayload, or Snapshot section contains a memory address. Every reference is a packed `EntityID` (REQ-ENT-001), a Cell index (`uint32_t`, row-major), a Chunk index, or a slot-local index. The Kernel context holds base pointers for pools (REQ-DAT-003 rule 2) and nothing else holds one. A `Perception.nearest[].id`, a `Memory.entry[].subject`, a `TrustEdge.id`, an `Affiliation.institution`, a `Lifecycle.parent`, an `InstitutionState.founder`, and a `Command.source`/`target` are all `EntityID` values validated per REQ-ENT-004.

Player-facing consequence: a Snapshot restored on a different machine, a different architecture, or a different build points at exactly the same agents, so a shared world is the same world (GI-1, GI-2).

### REQ-DAT-007: Little-endian canonical serialization
The canonical byte stream of any authoritative datum is produced by the following rules, used identically for Chunk Hashes (DEOS-RT `HASH`) and for Snapshots (REQ-DAT-008):

1. Scalars are written little-endian at their declared width: `int64_t`/`uint64_t` as 8 bytes, `uint32_t` as 4, `uint16_t` as 2, `uint8_t` as 1. In-memory representation is never hashed directly; a big-endian platform serializes explicitly (tools/CODING_STANDARDS.md section 4).
2. A record is serialized field by field in declared order, array fields element by element in ascending index, padding as zero.
3. A component array for a Chunk is serialized slot by slot in ascending slot index, each slot as one record per rule 2 (a gather from the SoA slab).
4. **Chunk serialization order** (the input of a Chunk Hash): the entity table slice for the Chunk (`CHUNK_SIZE` × 8 bytes), then components in catalog order #0 to #11 (REQ-CMP-013 table; #11 only for Institution Chunks), from buffer B at the end of Stage 6 substep 6.3.
5. **Cell Chunk serialization order**: Cell by Cell in ascending Cell index, each Cell as the six fields of REQ-CMP-011 in order (41 bytes per Cell), from buffer B.
6. `WorldMoodSlot` is serialized as its 64 bytes.

Byte counts per Chunk: 8,192 + 1,480 × 1,024 + 64 × 1,024 = 1,589,248 bytes for an agent Chunk; plus 288 × 1,024 = 294,912 for an Institution Chunk. Per Cell Chunk: 41 × 1,024 = 41,984 bytes.

Player-facing consequence: every Tick Hash and every Checkpoint a player publishes with a challenge was computed over this stream, so a verifier on any platform reproduces the same digest byte for byte (GI-1, GI-3).

### REQ-DAT-008: Snapshot byte layout
A Snapshot's ECS payload is a header followed by sections; DEOS-RT decides when a Snapshot is taken and appends its own sections (PRNG stream counters, Input Log cursor, Chronicle cursor) with `kind` ≥ 16 after the ECS sections.

```c
struct SnapshotHeader {       // 64 bytes, little-endian
    uint8_t  magic[8];        // "DEOS-SNP"
    uint32_t layout_version;  // SNAPSHOT_LAYOUT_VERSION = 1
    uint32_t header_bytes;    // 64
    uint32_t max_entities;    // scale check
    uint32_t chunk_size;      // 1024
    uint32_t grid_w;
    uint32_t grid_h;
    uint64_t tick;            // the tick whose end this Snapshot captures
    uint32_t section_count;
    uint32_t pad;             // 0
    uint64_t payload_bytes;   // total bytes of all sections including their headers
    uint64_t reserved;        // 0
};
struct SectionHeader {        // 16 bytes
    uint16_t kind;            // see table
    uint16_t buffer;          // 0 = A, 1 = B, 0 for buffer-independent sections
    uint32_t index;           // catalog index for kind 2, else 0
    uint64_t length;          // bytes that follow, excluding this header
};
```

Section order (binding):

| Order | `kind` | Content | `length` at scale S |
| ---: | ---: | :--- | :--- |
| 1 | 1 ENTITY_TABLE | `entity_table[0 … MAX_ENTITIES)` | 8 × `MAX_ENTITIES` |
| 2 … 13 | 2 COMPONENT, buffer 0, index 0 … 11 | buffer A, Chunk by Chunk in ascending Chunk index, each per REQ-DAT-007 rule 3 (index 3 Genome is single-buffered and appears once here, not in buffer B's run) | bytes per slot × slots that carry the component |
| 14 | 3 CELLS, buffer 0 | buffer A Cells per REQ-DAT-007 rule 5 | 41 × Cells |
| 15 … 25 | 2 COMPONENT, buffer 1, index 0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11 | buffer B as of the tick boundary (the state at the end of tick − 1) | as above |
| 26 | 3 CELLS, buffer 1 | buffer B Cells | 41 × Cells |
| 27 | 4 WORLDMOOD | `WorldMoodSlot` | 64 |

Restore: verify `magic`, `layout_version` = 1, and the four scale fields against the built Kernel (mismatch refuses the restore, REQ-MUT-012 case 6); load sections in order; rebuild the free bitmap from `Lifecycle.alive` of buffer A and the entity table; clear every derived structure. Stepping from a restored Snapshot yields the Tick Hash sequence of the original run (DEOS section 4, Snapshot).

Player-facing consequence: a Snapshot is the "start from here" of Seed Lineage: a friend who receives one opens the identical world, and the version tag is what tells them, instead of a corrupted world, that they need a newer build (GI-2).

### REQ-DAT-009: SpatialIndex
A derived structure mapping each Cell to the live entities in it, rebuilt at the beginning of Stage 4 from buffer A before any Stage 4 system runs, valid through Stage 5:

```c
uint32_t sorted[MAX_ENTITIES];       // slot indices of live entities, ascending (cell, slot)
uint32_t scratch[MAX_ENTITIES];      // radix pass output
uint32_t cell_start[Cells + 1];      // entities of Cell k are sorted[cell_start[k] … cell_start[k+1])
uint32_t hist[NUM_CHUNKS][1024];     // per-range bucket histogram for the current pass
```

Build (deterministic at any thread count):
1. **Collect.** For each Chunk `c` in parallel, write the slot indices with `A.Lifecycle.alive` = 1 and the Physical tag, in ascending slot order, into `scratch` at the Chunk's reserved range `[c × CHUNK_SIZE, c × CHUNK_SIZE + live_c)`; record `live_c`. A serial exclusive prefix sum over `live_c` in ascending Chunk index compacts the ranges into `sorted[0 … n)` (each Chunk copies its run to its offset in parallel). `n` is the live Physical count.
2. **Key.** `key(i) = cell(i)` per REQ-ENT-002 rule 2, `CELL_KEY_BITS` = 16 (MVS) or 20 (v1.0); digit width `D` = `CELL_KEY_BITS` / 2 (8 or 10 bits); 2^D ≤ 1,024 buckets.
3. **Two stable LSD radix passes** (pass 0 on the low digit, pass 1 on the high digit). In each pass the input array is split into fixed ranges `r` of `CHUNK_SIZE` consecutive items (`r` = item index / 1,024, defined by index, not by thread). (a) Each range counts `hist[r][b]` over its items in input order. (b) One worker computes `off[r][b] = Σ_{b' < b} Σ_{r'} hist[r'][b'] + Σ_{r' < r} hist[r'][b]` (bucket-major, then range-major, ascending), reusing `hist` in place. (c) Each range scatters its items in input order to `out[off[r][b]++]`. Stability plus the ascending initial order gives `sorted` in ascending `(cell, slot)`.
4. **Boundaries.** For each item `i` in parallel by range: with `k0 = key(sorted[i − 1])` (or −1 when `i` = 0) and `k1 = key(sorted[i])`, write `cell_start[k] = i` for every `k` in `(k0, k1]`; the range that holds item `n − 1` also writes `cell_start[k] = n` for every `k` in `(key(sorted[n − 1]), Cells]`. Every `cell_start[k]` is written by exactly one item, so the parallel writes never conflict.

The SpatialIndex is never hashed, never serialized, and never read by Stage 6.

Player-facing consequence: this index is what lets every agent perceive its neighbourhood within the tick budget, which is why the Perception panel is populated for a million agents and not a sample of them.

### REQ-DAT-010: Memory budget
The arena of REQ-DAT-003 at both scales, computed from the pool table with the sizes of section 8.1 (`MAX_COMMANDS_PER_ENTITY_PER_STAGE` = 4). Per-slot double-buffered agent bytes: 16 + 24 + 24 + 128 + 288 + 520 + 64 + 256 + 128 + 32 = 1,480; doubled: 2,960.

| Pool | Arithmetic (v1.0) | MVS bytes | v1.0 bytes |
| :--- | :--- | ---: | ---: |
| Agent components, catalog #0 … #10 except Genome, ×2 | 2 × 1,480 × 2^20 | 48,496,640 | 3,103,784,960 |
| `Genome`, ×1 | 64 × 2^20 | 1,048,576 | 67,108,864 |
| `InstitutionState`, ×2 | 2 × 288 × 65,536 | 589,824 | 37,748,736 |
| Entity table | 8 × 2^20 | 131,072 | 8,388,608 |
| Free bitmap + summary | 2^20 / 8 + 2^20 / 4096 | 2,052 | 131,328 |
| Cell fields, ×2 | 2 × 41 × 2^20 | 5,373,952 | 85,983,232 |
| Outboxes | 4 × 2^20 × 64 | 4,194,304 | 268,435,456 |
| Outbox segment offsets | 1,024 × 1,025 × 4 (entity) + 1,024 × 1,025 × 4 (Cell) | 5,248 | 8,396,800 |
| Lifecycle outboxes | 2 × 2^20 × 64 | 2,097,152 | 134,217,728 |
| Ingress lifecycle outbox | 1,024 × 64 | 65,536 | 65,536 |
| Spawn references | 2^20 × 4 | 65,536 | 4,194,304 |
| SpatialIndex | 4 × 2^20 × 2 + 4 × (2^20 + 1) + 1,024 × 1,024 × 4 | 458,756 | 16,777,220 |
| SpawnPayload | 64 × 2^20 | 1,048,576 | 67,108,864 |
| IngressOverlay | 1,024 × 32 | 32,768 | 32,768 |
| Chunk ledgers | (1,024 + 1,024) × 24 | 1,920 | 49,152 |
| `WorldMoodSlot` | 64 | 64 | 64 |
| **Total** | | **63,611,976** (63.6 MB) | **3,802,423,620** (3.80 GB) |

The v1.0 total is 3.802 × 10^9 bytes, 4.9 % under the 4.0 GB ceiling of DEOS-F05 section 1.1 (3.54 GiB). Excluded from the figure, as stated in section 5 assumption 6: the Input Log, the egress rings (Chronicle, `WorldMood` history), Snapshot staging and files, DEOS-CORE lookup tables, code, and thread stacks; each is owned and budgeted by DEOS-RT or DEOS-CORE. The MVS total of 63.6 MB is the figure the Host may rely on for mobile targets.

Player-facing consequence: the game runs on a phone at MVS scale because the whole world is 64 megabytes, and on a desktop at v1.0 because a million agents with full memories, perceptions, and beliefs still fit under four gigabytes.

### 6.4 State mutation rules (`MUT`)

### REQ-MUT-001: Double buffering
Two state buffers exist for every double-buffered datum of REQ-CMP-013: A (read) and B (write). During a tick no system, Command apply, or Host access writes A; the Host reads A and the egress rings only (GI-6). At the buffer swap in Stage 6 the roles exchange atomically (DEOS-RT owns the swap), after which the former B is exposed to the Host as A and the former A is overwritten during the next tick.

Consequences that are binding:
1. B is fully rewritten every tick: every owner stage writes every slot of every slab it owns (REQ-MUT-002). Nothing in B survives from two ticks earlier, so B's content at a tick boundary never influences the next tick.
2. Single-buffered data (`entity_table`, `Genome`, `WorldMoodSlot`) is written only in Stage 6 substeps or at the end of Stage 5 where no system reads it, and is therefore race-free without a second copy.
3. The read rule of REQ-CMP-013 selects A or B per datum and stage; no other buffer choice is permitted.

Player-facing consequence: the Host always renders a complete, consistent end-of-tick world, never a half-written one, so the Observation View never shows an agent in two places (GI-6).

### REQ-MUT-002: Owner-slot write rule
An entity's own components are written only by the worker that owns the entity's Chunk in the component's owner stage. For every slab it owns, the owner stage's system writes every slot of the Chunk, in ascending slot order, as follows:

```
for slot in chunk (ascending):
    if archetype lacks the component, or the freshest readable alive flag is 0:
        write zero to every leaf of the slot in B
    else:
        write the computed record (a full record; unchanged fields are copied from A)
```

"Freshest readable alive flag" is `Lifecycle.alive` read per REQ-CMP-013: A in Stages 1 to 3, B in Stages 4 to 6. A worker never writes a slot outside its Chunk in any slab; every effect on another entity is a Command (REQ-MUT-003). Institutions and Organisms follow the same rule with the copy branch for components they carry but whose stage has no rule for them (`Position2D` of an Institution, for instance, is copied A → B in Stage 4).

Player-facing consequence: the Kernel has no "who wrote this" ambiguity, so an inspected value has exactly one author, the stage the ownership matrix names, and the player's question "what changed this?" always has one answer (GI-5).

### REQ-MUT-003: Command record
Every cross-entity or cross-Cell effect is one 64-byte record:

```c
struct Command {              // 64 bytes; little-endian when serialized for tests
    uint64_t source;          // issuing EntityID; NULL_ENTITY_ID for Stage 1 and initialization
    uint64_t target;          // EntityID (target_kind 0) or Cell index in the low 32 bits (target_kind 1); 0 for SPAWN at issue
    uint32_t seq;             // per-source, per-stage sequence in [0, MAX_COMMANDS_PER_ENTITY_PER_STAGE); Input Log seq for Stage 1
    uint16_t kind;            // CommandKind (REQ-MUT-004)
    uint8_t  target_kind;     // 0 entity, 1 Cell
    uint8_t  stage;           // issuing stage 1..5
    int64_t  payload[4];      // Q32.32 or packed per kind
    uint64_t aux;             // kind-specific (REQ-MUT-004); 0 when unused
};
```

Rules:
1. `(source, stage, seq)` is unique within a tick; `seq` restarts at 0 for every entity in every stage and increases by one per Command issued by that entity in that stage.
2. `payload[i]` holds `actual` values written back during application (REQ-MUT-004 two-sided kinds); the record is otherwise immutable after issue.
3. Commands are never serialized into Snapshots (every outbox is empty at a tick boundary) and never hashed.

Player-facing consequence: a trade, a blow, a gift to the temple, a whispered belief, a trust shift, a birth, and a death are the seven verbs of the world, each a 64-byte record the Chronicle can quote exactly (GI-5).

### REQ-MUT-004: Command kinds and application semantics
Kinds 1 to 6 and 9 are **stage-resolved**: applied at the barrier of the issuing stage. Kinds 7 and 8 are **commit-resolved**: appended to the lifecycle outbox and resolved in Stage 6 (REQ-ENT-008, REQ-ENT-009). Application has three passes at every barrier (REQ-MUT-006): pass 1 (source side, by the issuing Chunk's worker over its own outbox in issue order), pass 2 (target side, by the target Chunk's or Cell Chunk's worker in canonical order), pass 3 (source side again, by the issuing Chunk's worker over its own sorted outbox in sorted order). All arithmetic is Q32.32 with the semantics of section 5 assumption 4; `room(e) = max_capacity − current_energy` of entity `e` in B.

| Kind | Name | Legal issuing stages | Target | Pass 1 (source) | Pass 2 (target) | Pass 3 (source) |
| ---: | :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | `NONE` | none | — | dropped | dropped | — |
| 1 | `ENERGY_TRANSFER` | 3, 4, 5 (Institution target or source: 5 only) | entity | `actual = min(payload[0], balance(source))`; `balance −= actual`; write `actual` to `payload[1]` | `heat = max(mul_q(payload[1], FX_ENTROPY_TAX), 1)` (DEOS-CORE REQ-LAW-005); `give = payload[1] − heat`; `credited = min(give, room(target))` for Biological targets, or `min(give, FX_INST_CAP − pooled_energy)` for Institutional targets; `balance(target) += credited`; `payload[1] − credited` → ledger `dissipated` of the target Chunk | none |
| 2 | `DAMAGE` | 3, 4, 5 | entity (Biological), may equal source | none | `actual = min(payload[0], current_energy(target))`; `current_energy −= actual`; `actual` → ledger `dissipated` | none |
| 3 | `INSTITUTION_JOIN` | 5 | entity (Institutional) | none | `member_count = min(member_count + 1, 0xFFFFFFFF)` | none |
| 4 | `INSTITUTION_LEAVE` | 5 | entity (Institutional) | none | `member_count = max(member_count − 1, 0)` | none |
| 5 | `MEME_DELTA` | 5 | entity (Cultural) | none | for `i` in `[0, n)` with `n = aux & 0xFF` (≤ 4) and `dim_i = (aux >> (8 + 8 i)) & 0xFF` (< 32): `v[dim_i] = clamp(v[dim_i] + payload[i], −1.0, 1.0)`; duplicates of `dim_i` within one Command apply in ascending `i` | none |
| 6 | `TRUST_DELTA` | 5 | entity (Cultural) | none | find edge with `id == source`: if found, `weight = clamp(weight + payload[0], −1.0, 1.0)`; else if `payload[0] > 0`: take the null edge if any, else the edge with minimum `weight` (ties → lowest index) if that weight < `payload[0]`, and set it to `{ source, clamp(payload[0], −1.0, 1.0) }`; else no change; re-sort per REQ-CMP-008 rule 1 | none |
| 7 | `SPAWN` | 1, 3, 5 | — (slot assigned in Stage 6) | commit-resolved (REQ-ENT-008) | | |
| 8 | `DESPAWN` | 3, 5 | entity == source | commit-resolved (REQ-ENT-009) | | |
| 9 | `CELL_ENERGY_DELTA` | 3, 4, 5 | Cell | if `payload[0] > 0` (deposit): `actual = min(payload[0], balance(source))`; `balance −= actual`; write `actual` to `payload[1]`; else write 0 to `payload[1]` | deposit: `heat = max(mul_q(payload[1], FX_ENTROPY_TAX), 1)`; `give = payload[1] − heat`; `credited = min(give, FX_CELL_ENERGY_CAP − energy)`; `energy += credited`; `payload[1] − credited` → ledger `dissipated` of the Cell Chunk. Draw (`payload[0] < 0`): `actual = min(−payload[0], energy)`; `energy −= actual`; write `actual` to `payload[2]` | draw: `heat = max(mul_q(payload[2], FX_ENTROPY_TAX), 1)`; `give = payload[2] − heat`; `credited = min(give, room(source))`; `current_energy += credited`; `payload[2] − credited` → ledger `dissipated` of the source Chunk |
| 10 … 65535 | unassigned | none | — | dropped | dropped | — |

`balance(e)` is `current_energy` for Biological entities and `pooled_energy` for Institutional entities. Application consumes no PRNG draw. A Command whose target fails validation in pass 2 (REQ-ENT-004 in B for entities; `target < Cells` for Cells), whose kind is illegal for the issuing stage, whose target lacks the required tag, or whose `SPAWN` archetype is illegal is dropped per REQ-MUT-009; a dropped two-sided Command's already-debited `payload[1]` goes to the target Chunk's ledger `dropped`.

Player-facing consequence: because "give", "hit", "join", "leave", "whisper", "trust", "bear", and "die" have exactly these formulas, the player who reads that a temple received 12.5 energy from a farmer can trust that the farmer lost exactly 12.5, and the world's energy books balance every tick (GI-1, GI-7).

### REQ-MUT-005: Outbox capacity and the overflow assertion
`MAX_COMMANDS_PER_ENTITY_PER_STAGE` = 4. Each Chunk owns one outbox holding `MAX_COMMANDS_PER_ENTITY_PER_STAGE` × `CHUNK_SIZE` Commands, that is 4,096 Commands (262,144 bytes), reused by every stage, and one lifecycle outbox holding twice `CHUNK_SIZE` Commands, that is 2,048 (one `SPAWN` and one `DESPAWN` per entity per tick), reused every tick. Stage 1 owns one ingress lifecycle outbox of capacity `MAX_INGRESS_WRITES_PER_TICK` = 1,024.

```c
struct Outbox {
    uint32_t count;                       // Commands issued in the current stage
    uint32_t sorted;                      // 1 after REQ-MUT-006 step 2
    uint64_t pad[7];                      // 0; keeps records 64-byte aligned
    struct Command record[4096];
};
```

Assertions (checked in every build in debug, and in the acceptance run):
1. A system issues at most `MAX_COMMANDS_PER_ENTITY_PER_STAGE` stage-resolved Commands per entity per stage (`seq` < 4), at most one `SPAWN` and one `DESPAWN` per entity per tick.
2. Therefore `count` ≤ 4 × `CHUNK_SIZE` for every outbox and ≤ 2 × `CHUNK_SIZE` for every lifecycle outbox; overflow is impossible by construction, and the `issue` interface (section 9) halts the Kernel with a Desync-class fault rather than dropping a Command when the assertion fails, because a dropped Command from a capacity limit would be thread-timing dependent in a non-conforming implementation.
3. A Command targets only a datum whose owner stage is ≤ the issuing stage (REQ-CMP-013).

Player-facing consequence: no burst of trades, births, or fights can ever be silently truncated, so a replay of a crowded market resolves exactly as the original did (GI-1).

### REQ-MUT-006: Barrier resolution in canonical order
At the barrier of stage `s` ∈ {3, 4, 5} (Stage 1 and 2 issue no stage-resolved Commands; Stage 1 writes the IngressOverlay of REQ-MUT-011) the Kernel performs, with a synchronization barrier between numbered steps:

1. **Pass 1, parallel by issuing Chunk.** Each worker walks its own outbox in issue order (index 0 to `count − 1`, which is ascending `(source, seq)` because the stage pass visits slots in ascending order) and applies the pass-1 column of REQ-MUT-004. Lifecycle Commands (kinds 7, 8) are copied to the lifecycle outbox at issue time and are not present in the stage outbox.
2. **Sort, parallel by issuing Chunk.** Each worker sorts its own outbox in place by the total key `(target_kind, target Chunk or Cell Chunk, target slot index or Cell index, source, seq)`; keys are unique so any correct sort yields one result. The worker then writes `entity_first[c][d]` for `d` in `[0, NUM_CHUNKS]` and `cell_first[c][e]` for `e` in `[0, NUM_CELL_CHUNKS]`: the index of the first record whose target Chunk (respectively Cell Chunk) is ≥ `d` (respectively ≥ `e`), so segment `d` of outbox `c` is `[entity_first[c][d], entity_first[c][d + 1])`.
3. **Pass 2, parallel by target Chunk and by target Cell Chunk.** The worker for target Chunk `d` applies, in ascending canonical key, the union of the segments `d` of all `NUM_CHUNKS` outboxes (the reference method is a k-way merge with a binary heap of at most `NUM_CHUNKS` entries keyed by the canonical key; because keys are unique the output order is independent of the method). The worker for Cell Chunk `e` does the same over the Cell segments. Entity and Cell workers write disjoint data and run concurrently. Validation and drops (REQ-MUT-009) happen here.
4. **Pass 3, parallel by issuing Chunk.** Each worker walks its own (now sorted) outbox in sorted order and applies the pass-3 column.
5. **Reset.** Each worker sets its outbox `count` and `sorted` to 0.

Determinism argument: every write in steps 1, 3, and 4 is performed by exactly one worker over data it exclusively owns during that step; the order of writes to any one datum is a total order over unique keys; thread assignment affects only which worker performs a Chunk's work, never the order within it. Hence the result at any thread count equals the result at one thread.

Player-facing consequence: this rule is why a fight between two agents from different Chunks, a trade across a border, or a temple's donations from a hundred members resolve identically in a replay, a challenge verification, and an Acceleration catch-up (GI-1, GI-4).

### REQ-MUT-007: Pure-function system rule
Every system is a function

```
system(stage, chunk, read_view, prng_stream) -> (write_slice, outbox_records, lifecycle_records)
```

where `read_view` grants exactly the reads of REQ-CMP-013 for stage `stage`, `prng_stream` is the DEOS-CORE stream keyed by `(system, tick, chunk)`, `write_slice` is the set of slabs the stage owns for `chunk` in B, and the two record outputs are appended to the Chunk's outbox and lifecycle outbox. A system has no other effect: no static or thread-local mutable state, no wall-clock read, no allocation, no write outside `write_slice` and the two outboxes, no read of another Chunk's write slice for a datum whose owner stage equals `stage`, and no PRNG source other than `prng_stream`, whose draws are consumed in ascending slot order with a draw count fixed by the code path for each archetype (REQ-ENT-010 rule 3). Two calls with equal inputs produce equal outputs on every platform.

Player-facing consequence: purity is the property that makes "how did this war start?" answerable: any Snapshot can be restored and stepped forward to the same answer, so the Chronicle's rewind is exact rather than approximate (GI-1, GI-5).

### REQ-MUT-008: No same-stage read of the write buffer
A system executing in stage `s` never reads from B a datum whose owner stage is `s`, for its own slot or any other. A stage that needs its own freshly computed value (Perception feeding utility scoring in Stage 4) keeps it in a local record and writes it once. Reads of B are permitted only for data whose owner stage is below `s` (REQ-CMP-013), which are complete before the stage begins and are modified afterwards only by Commands at barriers ≥ `s`, which no system of stage `s` observes.

Player-facing consequence: an agent's decision never depends on whether its neighbour's Chunk happened to be processed first, so the story the player watches is the same story on every core count (GI-1).

### REQ-MUT-009: Dropped Commands and the Chunk ledger
Each Chunk and each Cell Chunk owns a ledger, zeroed at the start of Stage 1:

```c
struct ChunkLedger {          // 24 bytes
    int64_t  dissipated;      // Q32.32, energy removed by clamps, saturation, DAMAGE, the entropy tax of Command transfers,
                              //         and own-write losses (metabolism, upkeep; DEOS-PROTO) this tick
    int64_t  dropped;         // Q32.32, energy carried by Commands dropped in pass 2 this tick
    uint32_t births, deaths;  // SPAWN and DESPAWN Commands issued by the Chunk this tick (WorldMood partials, DEOS-PROTO)
};
```

Rules:
1. A Command dropped in pass 2 (REQ-MUT-004 last paragraph, REQ-ENT-006 rule 5, REQ-ENT-010 rule 2) emits one `NotableEvent` with `kind` = 2 `COMMAND_DROPPED`, `subject` = `source`, `object` = `target` (or `NULL_ENTITY_ID` for a Cell target), `cell` = the target Cell index for `target_kind` 1 or the source's Cell otherwise, `magnitude` = the energy carried (`payload[1]` for two-sided kinds, `payload[0]` for `SPAWN`, 0 otherwise), `cause` = 0, appended to the tick's Notable Event stream by the applying worker in the manner DEOS-RT specifies for Notable Events emitted by Chunk workers.
2. Energy carried by a dropped Command is added to the applying Chunk's ledger `dropped`; energy removed by clamps, by the entropy tax, by `DAMAGE`, and by own-write losses is added to `dissipated`. Every such amount is heat: nothing leaves the world through this ledger.
3. In Stage 6 substep 6.4, DEOS-RT sums both energy fields over all Chunks and Cell Chunks in ascending index and credits the total to `Ledger.heat_sink` (DEOS-CORE REQ-LAW-005) before the conservation check, which therefore holds exactly; the per-Chunk sums are also part of the tick's egress diagnostics but not of the Tick Hash. `births` and `deaths` are folded likewise for the `WorldMood` record.

Player-facing consequence: nothing vanishes without a row: a gift to a temple that dissolved in the same tick appears in the Chronicle as a dropped offering, and the world's energy books still balance (GI-5, GI-7).

### REQ-MUT-010: Stage 6 commit sequence (data substeps)
Stage 6 begins after the Stage 5 barrier resolution of REQ-MUT-006 has completed. Its data substeps, in order, each separated by a synchronization barrier; DEOS-RT owns substeps 6.4 and 6.5 and is cited here only for order:

| Substep | Parallelism | Action |
| :--- | :--- | :--- |
| 6.1 Spawn assignment | serial | Walk the ingress lifecycle outbox, then every Chunk's lifecycle outbox in ascending Chunk index, each in issue order (together: ascending `(source, seq)`); for every `SPAWN`, `alloc` per REQ-ENT-006 in the range of its archetype; write the new `EntityID` into `target`, and append the packed reference `(issuing Chunk << 12) | record index` (ingress outbox as Chunk value 0xFFFFF) to `spawn_refs[target Chunk]`; drop on exhaustion per REQ-ENT-006 rule 5. |
| 6.2 Spawn initialization | parallel by target Chunk | For every reference in `spawn_refs[d]` in order: initialize all components of the slot in B per section 8.1 (reading parent or founder data from B and the SpawnPayload or the `SPAWN_INIT` stream per REQ-ENT-008), write `Genome`, write `entity_table[index]`, clear the free bit. |
| 6.3 Despawn finalization | parallel by Chunk | For every `DESPAWN` in the Chunk's own lifecycle outbox in issue order: zero the slot in every slab of B and in `Genome` and SpawnPayload, write `entity_table[index] = make_id(index, generation', 0)`, set the free bit and its summary bit. Then clear the lifecycle outbox and `spawn_refs[d]`. |
| 6.4 Hashing and ledgers | DEOS-RT | Chunk Hashes over REQ-DAT-007 order from B; Tick Hash; ledger sums (REQ-MUT-009 rule 3); `WorldMoodSlot` copy to egress. |
| 6.5 Flush and swap | DEOS-RT | Chronicle flush; buffer swap (REQ-MUT-001); egress. |

Because 6.1 precedes 6.3, a slot freed in tick t is first allocatable in tick t+1 (REQ-ENT-006 rule 4); because 6.2 precedes 6.3, a child initialized from a parent that died this tick still reads the parent's intact B data.

Player-facing consequence: births and deaths of one tick land in the Chronicle in one deterministic order, so the Epoch summary's "born 412, died 398" is the same on every replay and a child of a parent who died giving birth still inherits (GI-1, GI-5).

### REQ-MUT-011: IngressOverlay
Stage 1 never writes a state buffer. It writes the IngressOverlay, a derived per-tick list of primitive field writes produced from the Input Log entries stamped for this tick (DEOS-RT applies them in `(tick, seq)` order and expands composite `CatalystAction` kinds, DEOS section 5.4), and the ingress lifecycle outbox:

```c
struct IngressWrite {         // 32 bytes
    uint32_t seq;             // Input Log seq of the originating CatalystAction; ascending in the list
    uint16_t field;           // 0 CELL_ENERGY, 1 CELL_TEMPERATURE, 2 CELL_MOISTURE, 3 CELL_ELEVATION, 4 CELL_MATERIAL, 5 CELL_MUTATION_BIAS, 6 MEME_DELTA
    uint8_t  op;              // 0 ADD, 1 SET, 2 MUL (MUL only for fields 0, 5; SET only for field 4 uses the low 8 bits of value)
    uint8_t  dim;             // MemeVector dimension for field 6, in [0, 32); else 0
    uint16_t x, y;            // centre Cell
    uint16_t radius;          // Chebyshev radius in Cells; 0 = the centre Cell only
    uint16_t pad;             // 0
    int64_t  value;           // Q32.32 (integer in the low 8 bits for CELL_MATERIAL)
    uint64_t reserved;        // 0
};
struct IngressOverlay { uint32_t count; uint32_t pad; uint64_t pad2[3]; struct IngressWrite write[1024]; };
```

Consumption:
1. Stage 2, for every Cell it writes: start from A's value, apply every overlay write whose field targets a Cell field and whose square contains the Cell, in ascending `seq` (`ADD`: `add_sat`; `SET`: replace; `MUL`: `mul_q`), clamp per REQ-CMP-011 rule 2, then evaluate the DEOS-CORE law. Each Cell Chunk worker first selects the overlay writes whose square intersects its Cell Chunk (at most 1,024 comparisons), so the per-Cell cost is proportional to the intersecting writes only.
2. Stage 5, for every Cultural slot it writes: apply every `MEME_DELTA` overlay write whose square contains the entity's Cell (from A's `Position2D`) as `v[dim] = clamp(v[dim] + mul_q(value, receptivity), −1.0, 1.0)` with `receptivity` = `gene_param` of gene 31 for Agents and 1.0 for Institutions, in ascending `seq`, before the DEOS-PROTO transmission rule.
3. `count` ≤ `MAX_INGRESS_WRITES_PER_TICK` = 1,024; DEOS-RT rejects further Input Log entries for the tick with `NotableEvent.kind` 1 `INGRESS_REJECTED`. The overlay is cleared at the start of Stage 1.

Player-facing consequence: a Catalyst Action lands in the tick it is stamped for, on exactly the region the player painted, and never overrides an agent's decision because no field of the overlay can name a `Decision` (commitment C1, GI-6).

### REQ-MUT-012: Fault handling
The following conditions are faults with the stated behaviour; none is ever tolerated silently:

| # | Condition | Behaviour |
| ---: | :--- | :--- |
| 1 | Outbox or lifecycle outbox assertion of REQ-MUT-005 fails | Kernel halts the tick and reports a Desync-class fault naming stage, Chunk, and source `EntityID`; the tick's Tick Hash is not emitted. |
| 2 | A Command names an illegal kind, stage, target tag, or archetype | dropped with `COMMAND_DROPPED` (REQ-MUT-009); the world continues. |
| 3 | A free range is exhausted | `SPAWN` dropped with `COMMAND_DROPPED`, `magnitude` = carried energy; later spawns in the other range proceed. |
| 4 | A stored `EntityID` fails validation | treated as `NULL_ENTITY_ID` by the reader (REQ-ENT-004); no event. |
| 5 | A pool alignment or size check fails at initialization | initialization fails; no tick runs. |
| 6 | Snapshot header mismatch (magic, version, scale) | restore refused; the loaded world is unchanged. |
| 7 | A Q32.32 operation saturates during application | the saturated value is stored and the discarded amount enters the ledger (REQ-MUT-009); saturation is deterministic and identical on every platform. |
| 8 | Generation wrap (REQ-ENT-005 rule 3) | the slot continues from generation 1; no event. |

Player-facing consequence: the only faults that stop the world are those that would make it unreproducible, and every one of those is reported as a Desync the player can send with their Input Log; everything else becomes a row in the Chronicle (GI-1, GI-5).

---

## 7. Algorithms & Mathematics

### 7.1 Gene mapping

```
gene_param(genome, row):
    span   = max_row - min_row                      // Q32.32, >= 0
    prod   = (int128) span * genome.gene[row]       // exact
    q      = prod / 65535                           // int128 division, floor (prod >= 0)
    return min_row + (int64) q                      // no overflow: q <= span
```

### 7.2 Perception summary (Stage 4, per Agent slot `i`, computed into a local record)

```
p = zero Perception
p.cell = cell(i) from A.Position2D
(cx, cy) = (p.cell mod GRID_W, p.cell div GRID_W)
sum_t[8] = sum_m[8] = 0; cnt[8] = 0; mat_count[8][256] = 0
for dy in -4..4, for dx in -4..4 (row-major):
    if dx == 0 and dy == 0: continue
    (x, y) = (cx + dx, cy + dy); if out of grid: continue
    s = sector(dx, dy)                                    // REQ-CMP-004 table
    k = y * GRID_W + x
    p.sector[s].energy_sum = add_sat(p.sector[s].energy_sum, B.energy[k])
    sum_t[s] = add_sat(sum_t[s], B.temperature[k]); sum_m[s] = add_sat(sum_m[s], B.moisture[k])
    cnt[s] += 1; mat_count[s][B.material_id[k]] += 1
    for j in sorted[cell_start[k] .. cell_start[k+1]):     // ascending slot
        if j == i: continue
        id = entity_table[j]
        dxq = A.x[j] - A.x[i]; dyq = A.y[j] - A.y[i]
        d2 = add_sat(mul_q(dxq, dxq), mul_q(dyq, dyq))
        insert (d2, id) into p.nearest keeping the 4 smallest by (d2, id)
        p.sector_entities[s] = min(p.sector_entities[s] + 1, 65535)
        p.sensed_count = min(p.sensed_count + 1, 65535)
for s in 0..7:
    if cnt[s] > 0:
        p.in_range_mask |= 1 << s
        p.sector[s].temperature_mean = div_q(sum_t[s], cnt[s])   // floor
        p.sector[s].moisture_mean    = div_q(sum_m[s], cnt[s])
        p.sector_material[s] = argmax over m of mat_count[s][m], ties -> lowest m
```

### 7.3 Canonical Command key

```
key(cmd) = (cmd.target_kind,
            cmd.target_kind == 0 ? index(cmd.target) >> 10 : (cmd.target & 0xFFFFFFFF) >> 10,
            cmd.target_kind == 0 ? index(cmd.target)       : (cmd.target & 0xFFFFFFFF),
            cmd.source,
            cmd.seq)
compared lexicographically, all fields unsigned ascending.
```

### 7.4 Two-sided energy Commands (conservation)

For `ENERGY_TRANSFER` with amount `a` from `s` to `t` at one barrier: pass 1 removes `a1 = min(a, balance(s))` from `s`; pass 2 adds `a2 = min(a1, room(t))` to `t` and books `a1 − a2` as dissipated. Sum over the world: `Δbalance = −a1 + a2`, `Δdissipated = a1 − a2`, total change 0. For a Cell draw of `a` by `s`: pass 2 removes `a1 = min(a, energy(cell))`, pass 3 adds `a2 = min(a1, room(s))` and books `a1 − a2`. The same identity holds. Because every debit precedes every credit and every credit is bounded by what was debited, no sequence of Commands at one barrier creates energy, whatever their order; the order fixes only which Command's excess is booked, and the canonical order fixes that too.

### 7.5 Free-slot search

```
alloc(lo, hi):                                     // range [lo, hi), multiples of 4096 at both ends except lo = 1
    for w in (lo / 4096) .. (hi - 1) / 4096:
        if free_summary[w] == 0: continue
        for b in bits of free_summary[w] ascending:
            word = free_bits[w * 64 + b]
            if word == 0: continue
            i = (w * 64 + b) * 64 + ctz(word)
            if i < lo: continue; if i >= hi: return NONE
            free_bits[w*64+b] &= ~(1 << ctz(word)); if free_bits[w*64+b] == 0: free_summary[w] &= ~(1 << b)
            return i
    return NONE
```

The agent range starts at 1 because slot 0 is reserved; the loop's `i < lo` test skips it.

---

## 8. Data Structures

### 8.1 Per-slot sizes, owners, and initial values at spawn

| # | Component | Bytes | Buffers | Owner stage | Initial value at spawn (substep 6.2) |
| ---: | :--- | ---: | :---: | :---: | :--- |
| 0 | `Position2D` | 16 | 2 | 4 | `payload[1]`, `payload[2]` clamped to the grid |
| 1 | `EnergyState` | 24 | 2 | 3 | `min(payload[0], gene_param(0))`, `gene_param(0)`, `gene_param(1)`; all 0 for Institutions |
| 2 | `Lifecycle` | 24 | 2 | 3 | `{ t, source, 0, payload[3] bits 16-31, 1, 0 }` |
| 3 | `Genome` | 64 | 1 | 6 (from Stage 3 SpawnPayload or `SPAWN_INIT`) | SpawnPayload copy, or 32 stream draws; 0 for Institutions |
| 4 | `Needs` | 128 | 2 | 3 / 4 | levels 0.5 each; weights `gene_param(16 + k)` for Agents, else 0 |
| 5 | `Perception` | 288 | 2 | 4 | 0 |
| 6 | `Memory` | 520 | 2 | 4 | 0 |
| 7 | `Decision` | 64 | 2 | 4 | 0 |
| 8 | `MemeVector` | 256 | 2 | 5 | parent's or founder's `MemeVector` from B; 0 for Organisms |
| 9 | `TrustEdges` | 128 | 2 | 5 | `{ parent or founder, +0.5 }` in edge 0 when valid in B; else 0 |
| 10 | `Affiliation` | 32 | 2 | 5 | 0 |
| 11 | `InstitutionState` | 288 | 2 | 5 | `{ 0, t, source, 0, 1, founder's MemeVector }` |
| — | `entity_table[index]` | 8 | 1 | 6 | `make_id(index, generation, archetype)` |

Total per agent slot, double-buffered: 1,480 × 2 = 2,960 bytes, plus 64 bytes of Genome. `t` is the tick in which Stage 6 runs; `source` is the `SPAWN` source.

### 8.2 Entity and Chunk numbering

```
slot index i          in [0, MAX_ENTITIES);  slot 0 reserved
chunk(i)              = i >> 10
slot_in_chunk(i)      = i & 1023
agent range           = [1, INSTITUTION_BASE)
Institution range     = [INSTITUTION_BASE, MAX_ENTITIES)
cell index k          = y * GRID_W + x, row-major
cell_chunk(k)         = k >> 10
```

### 8.3 Command, overlay, ledger, and Snapshot structures
Defined in REQ-MUT-003, REQ-MUT-005, REQ-MUT-011, REQ-MUT-009, and REQ-DAT-008 respectively. The `SpawnPayload` element is:

```c
struct SpawnPayload {         // 64 bytes; pool 12; element (chunk, local) addressed by SPAWN.aux
    uint16_t gene[32];        // the child's Genome computed in Stage 3 (DEOS-PROTO)
};
```

### 8.4 Layout diagram

```
 Arena (one allocation, 64-byte aligned pools in REQ-DAT-003 order)
 ┌──────────────┬───────────────────────────────┬────────────┬───────────────┬─────────────────┐
 │ entity_table │ A: slabs #0..#10 (Chunk-major) │ Genome     │ A: Inst slabs │ A: Cell fields  │
 │              │ B: slabs #0..#10               │ (single)   │ B: Inst slabs │ B: Cell fields  │
 ├──────────────┴───────────────────────────────┴────────────┴───────────────┴─────────────────┤
 │ derived: free bitmap · outboxes · offsets · lifecycle outboxes · spawn_refs · SpatialIndex   │
 │          SpawnPayload · IngressOverlay · ledgers · WorldMoodSlot                              │
 └───────────────────────────────────────────────────────────────────────────────────────────────┘

 Slab for component X, Chunk c:   leaf0[1024] │ leaf1[1024] │ … │ leafN[1024]     (each 64-aligned)
 Canonical stream for Chunk c:    entity_table[c] ‖ X0 slot-by-slot ‖ X1 slot-by-slot ‖ … ‖ X11
```

---

## 9. Subsystem Interfaces

C signatures the Kernel exposes internally; DEOS-RT wraps the subset the Host needs (`ARCH`). All functions are re-entrant with respect to distinct Chunks and allocate nothing.

```c
// Identity (REQ-ENT-001, REQ-ENT-004)
uint64_t ecs_make_id(uint32_t index, uint16_t generation, uint16_t archetype);
int      ecs_valid(const EcsContext*, uint64_t id, int buffer /*0 = A, 1 = B*/);

// Issue (REQ-MUT-003, REQ-MUT-005): appends to the current Chunk's outbox or lifecycle outbox;
// halts on assertion failure; returns the seq assigned.
uint32_t ecs_issue(EcsContext*, uint32_t chunk, const struct Command*);

// Barrier resolution (REQ-MUT-006): called by DEOS-RT after the stage barrier, once per stage 3..5.
void     ecs_resolve_barrier(EcsContext*, uint8_t stage);

// Stage 6 data substeps (REQ-MUT-010): 6.1 serial, 6.2 and 6.3 per Chunk.
void     ecs_commit_assign(EcsContext*);
void     ecs_commit_spawn_chunk(EcsContext*, uint32_t chunk);
void     ecs_commit_despawn_chunk(EcsContext*, uint32_t chunk);

// Canonical serialization (REQ-DAT-007): writes the Chunk's or Cell Chunk's stream into a caller buffer of
// the exact size and returns the byte count; used by DEOS-RT hashing and by Snapshots.
uint64_t ecs_serialize_chunk(const EcsContext*, uint32_t chunk, int buffer, uint8_t* out, uint64_t cap);
uint64_t ecs_serialize_cell_chunk(const EcsContext*, uint32_t cell_chunk, int buffer, uint8_t* out, uint64_t cap);

// Snapshot (REQ-DAT-008): DEOS-RT decides when; sections are written and read in the binding order.
uint64_t ecs_snapshot_write(const EcsContext*, uint8_t* out, uint64_t cap);
int      ecs_snapshot_read(EcsContext*, const uint8_t* in, uint64_t len);   // 0 = ok, 6 = header mismatch

// Derived structures
void     ecs_spatial_index_build(EcsContext*);                      // REQ-DAT-009, start of Stage 4
void     ecs_ingress_overlay_reset(EcsContext*);                    // REQ-MUT-011, start of Stage 1
int      ecs_ingress_overlay_push(EcsContext*, const struct IngressWrite*);   // 0 = ok, 1 = full
```

Events emitted by this module: `NotableEvent.kind` 2 `COMMAND_DROPPED` with the fields of REQ-MUT-009 rule 1. Events consumed: none. Data consumed from DEOS-CORE: Q32.32 operations, PRNG streams `(system, tick, chunk)` including `SPAWN_INIT`, the ordering rules. Data provided to DEOS-RT: the canonical streams, the ledgers, the `WorldMoodSlot`. Data provided to DEOS-PROTO: every component layout, `gene_param`, the SpatialIndex, and the seven mutation verbs of REQ-MUT-004.

---

## 10. Failure Cases & Risk Mitigation

| Risk | Consequence if unmitigated | Mitigation in this module |
| :--- | :--- | :--- |
| Thread-count-dependent Command order | Desync between 1 and 4 threads | unique total key, three-pass application with exclusive ownership per pass (REQ-MUT-006) |
| Same-stage read of B | result depends on Chunk scheduling | REQ-MUT-008 and the ownership matrix; debug builds poison unwritten B slabs at stage start to make a violation detectable |
| Energy created by a dropped or clamped Command | conservation law fails, drought Catalyst Actions lose meaning | every excess enters a ledger reported to the conservation check (REQ-MUT-009, section 7.4) |
| Stale `EntityID` after slot reuse | agent interacts with a stranger as if it were a friend | generation match in every validation; generation 0 never assigned (REQ-ENT-004, REQ-ENT-005) |
| Generation wrap after 65,535 reuses | rare false validation | bound stated for DEOS-PROTO memory decay; Memory entries carry `tick` so a reader can reject entries older than the wrap horizon |
| Free-range exhaustion | population growth silently stops | visible `COMMAND_DROPPED` per birth; Institution and agent ranges fail independently (REQ-ENT-006) |
| Big-endian or differently padded platform | different Tick Hash | explicit little-endian canonical stream; padding always zero (REQ-DAT-005, REQ-DAT-007) |
| Snapshot from a different scale or layout | corrupted world | header check refuses restore (REQ-DAT-008) |
| Outbox overflow | lost Commands, timing-dependent | capacity from the per-entity bound; overflow unreachable; assertion halts (REQ-MUT-005) |
| Hashing bandwidth at v1.0 | Tick Hash cost exceeds the tick budget | canonical stream sizes stated (section 11) so DEOS-RT can schedule hashing; the byte count is a fixed function of scale |
| Perception cost with dense Cells | Stage 4 super-linear | per-sector counts saturate; nearest-4 insertion is O(candidates); the SpatialIndex bounds candidate enumeration to the 81 Cells |

---

## 11. Performance & Scalability Targets

| Metric | MVS (2^14) | v1.0 (2^20) | Note |
| :--- | ---: | ---: | :--- |
| Arena size | 63.6 MB | 3.80 GB | REQ-DAT-010; under the 4.0 GB ceiling |
| Bytes an owner stage writes per tick (all stages, B) | 24.2 MB | 1.55 GB | 1,480 × slots; the per-slot cost is constant, so throughput is linear in `MAX_ENTITIES` (Pillar 3) |
| Canonical stream hashed per tick | 28.4 MB | 1.69 GB | entity table + agent components + Genome + Institutions + Cells (REQ-DAT-007); DEOS-RT schedules the hash within `TICK_BUDGET_MS` |
| Command capacity per stage | 65,536 | 4,194,304 | 4 × `MAX_ENTITIES` |
| Worst-case pass-2 merge inputs per target Chunk | 16 segments | 1,024 segments | heap of `NUM_CHUNKS` entries; O(records × log `NUM_CHUNKS`) |
| SpatialIndex build | 2 radix passes over ≤ 16,384 items | 2 passes over ≤ 1,048,576 items | O(n + Cells + `NUM_CHUNKS` × 1,024) per tick, all parallel except the two prefix sums |
| Perception per Agent | 80 Cell reads + candidates | same | constant per entity |
| Free-slot search | ≤ 5 word reads | ≤ 257 word reads | REQ-ENT-006 rule 2 |
| Snapshot size (ECS sections) | 55.6 MB | 3.30 GB | 8 × slots + (1,480 + 64) × slots + 2 × 288 × Institutions + 2 × 41 × Cells + 1,480 × slots + 64, both buffers per REQ-DAT-008 |

Per-entity per-tick cost is a constant number of bytes and operations for every rule in this module, which is the property the 16.6 ms budget at v1.0 requires; DEOS-RT's thread dispatch and DEOS-CORE's arithmetic costs complete the budget.

Player-facing consequence: the MVS numbers are what make an Epoch catch-up stream into the Chronicle in under a minute and a fresh world show its first Notable Event within 90 seconds on a phone (DEOS-F05 P1, P3).

---

## 12. Future Expansion

1. **Sparse archetype pools.** A later revision may omit Cognitive and Cultural slabs for Chunks that hold no Agents; the catalog order and canonical stream stay unchanged (zeros serialize as zeros), so the Tick Hash stays identical.
2. **Buffer B elision in Snapshots.** Under REQ-MUT-001 rule 1, buffer B at a tick boundary never influences a later tick; an ADR may permit Snapshots that omit sections 15 to 26 with `SNAPSHOT_LAYOUT_VERSION` = 2, halving Snapshot size at v1.0.
3. **SIMD leaf layouts.** The leaf-array slab layout (REQ-DAT-004) is already the layout AVX-512 and NEON kernels for Stage 2 and Stage 4 consume; no data change is needed for ROADMAP Phase 7.
4. **Registry growth.** Raising `MEMORY_SLOTS`, `TRUST_EDGES`, `MEME_DIM`, or `NEED_COUNT` changes byte counts in section 8.1 and REQ-DAT-010 and bumps `SNAPSHOT_LAYOUT_VERSION`; nothing else in this module depends on their values beyond the sizes stated.
5. **Additional Command kinds.** Kinds 10 to 15 are held for this module; assigning one follows the DEOS-F06 rubric and states its three-pass semantics and conservation identity in the REQ-MUT-004 table.

---

## 13. Revision History

| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 | 2026-09-12 | Initial DEOS draft; absorbs EESS-0401 and EESS-0601; at integration: entropy tax applied at Command barriers, Chunk ledger credited to `Ledger.heat_sink`, `births`/`deaths` counters, `Decision.flags` bit 2, `InstitutionState.discovered` | DEOS Arch Team |
