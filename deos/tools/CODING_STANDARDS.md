# DEOS Kernel Coding & Determinism Standards

All simulation runtime code written for the **DEOS Kernel** (the EE Kernel of DEOS-F04) must enforce these standards. They are the code-level form of DEOS-F02 Directives 2 through 8 and of the Game-Facing Invariants GI-1, GI-4, and GI-6 (`DEOS.md` section 6). Every rule is checkable by a test named in `tests/SPEC_CONSISTENCY_TEST_PLAN.md`.

---

## 1. Math Rules (Strict Determinism)
- **NO FLOATING POINT TYPES**: The keywords `float` and `double` are forbidden in Kernel files. A grep for either keyword in the Kernel source tree returns zero matches.
- Use `Fixed64` (`Q32.32`, stored in `int64_t`) for all fractional calculations, with the rounding and saturation rules of DEOS-Core: multiplication and division use a 128-bit intermediate, round toward negative infinity on the fractional shift, and saturate to `INT64_MIN` / `INT64_MAX` on overflow.
- Transcendentals ($\sin, \cos, \exp, \ln$) must use the fixed lookup tables of DEOS-Core with linear interpolation; no libm call exists inside the Kernel.
- Integer division by zero and shifts by 64 or more are unreachable by construction: every divisor is checked and every shift amount is a compile-time constant or masked.

## 2. Memory Rules (Zero Allocation)
- No `malloc()`, `realloc()`, `free()`, `new`, or `delete` inside `tick()` pipelines; an allocation counter installed at Kernel initialization reads 0 after every tick.
- Use custom stack/pool allocators pre-allocated during `EE_Kernel_Init()`; every pool is sized from `MAX_ENTITIES`, `CHUNK_SIZE`, `GRID_W`, and `GRID_H` at initialization.
- Every array is aligned to `CACHE_LINE` = 64 bytes; component storage is Struct of Arrays.

## 3. Threading Rules
- Worker threads execute over contiguous memory slices (Chunks of `CHUNK_SIZE` = 1,024 entities), one thread per Chunk per stage.
- No cross-thread dynamic mutex locking during the tick pipeline. All system outputs write to double-buffered output slices assigned exclusively per worker thread; cross-entity writes go to the per-Chunk command buffer and are resolved at the stage barrier (DEOS-ECS).
- Thread count affects throughput only. A Kernel built with `THREADS = 1` and one built with `THREADS = 4` produce identical Tick Hash sequences for the same Master Seed and Input Log; the parity test runs both.
- No wall-clock read (`time()`, `clock()`, `rdtsc`, or any equivalent) exists in the Kernel. Time is the tick counter (GI-4).

## 4. Hashing Rule (Little-Endian Serialization)
- Every value that enters a Chunk Hash or Tick Hash is serialized in **little-endian byte order** at its declared width before hashing: `int64_t` and `uint64_t` as 8 bytes, `uint32_t` as 4, `uint16_t` as 2, `uint8_t` as 1, in the field order the DEOS-ECS component layout declares, with padding bytes written as zero. In-memory representation is never hashed directly; a big-endian platform serializes explicitly.
- Every write path folds exactly the canonical bytes it writes (or the Command records it applies) into its write fold with the fold function of DEOS-Runtime REQ-HASH-001; the Tick Hash is `BLAKE3-256` over the tick number, every fold in canonical order, and the global records (REQ-HASH-002). A write that is not folded is a determinism defect even when the state it produces is correct.
- A Chunk Hash is `BLAKE3-256` over the Chunk's canonical stream (DEOS-ECS REQ-DAT-007: the entity-table slice, then the component arrays in catalog order, each slot by slot), computed at Checkpoint ticks; the Checkpoint Hash is the Merkle root over Chunk Hashes, Cell Chunk Hashes, and the global records with the domain-separation prefixes and the tick number serialized little-endian, using the tree construction of DEOS-Runtime REQ-HASH-003 (ADR-0001).
- Hash inputs never include pointers, thread identifiers, wall-clock values, or padding with undefined contents.

## 5. Ordering Rule (Core ORD)
- Every iteration whose result can depend on order follows the deterministic ordering rules of DEOS-Core (`ORD` prefix). The default order is ascending `EntityID`; a Cell iteration is row-major, ascending `y` then ascending `x`; a Chunk iteration is ascending Chunk index.
- Ties in any comparison (utility scores, candidate targets, resolution of conflicting writes at a stage barrier) are broken by ascending `EntityID`, and where both entities are equal, by ascending command sequence number. No tie is ever broken by memory address, hash-map iteration order, or thread arrival order.
- Hash maps and any container with unspecified iteration order are forbidden in the Kernel. Sorting uses a stable algorithm with a total order over the key.
- PRNG draws are taken from the stream keyed by `(system, tick, chunk)` and consumed in the same order as the iteration above; a system that skips an entity still advances nothing for it, so the draw count per entity is fixed by the code path, not by data.

## 6. Egress and Host Boundary
- The Host reads only the read-only buffer and the egress ring (Chronicle, `WorldMood`); it never receives a pointer into the write buffer (GI-6).
- The Host mutates the world only by appending `CatalystAction` records to the Input Log; no other entry point writes Kernel state.

Player-facing consequence: because every one of these rules is a condition for identical Tick Hashes, the player's shared seed, verified challenge, and offline catch-up work identically on every machine that runs the game.
