# Specification: Core Engineering Principles (DEOS-F02)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | DEOS-F02 |
| **Semantic Version** | v0.1.0 |
| **Status** | Approved |
| **Dependencies** | DEOS, DEOS-F01 |
| **Supersedes** | EESS-0002 |

---

## 1. Core Engineering Directives

Directives 1 through 10 are carried forward unchanged from the EESS lineage. Directives 11 and 12 are added by DEOS because the product is a game (DEOS section 1.1): a substrate that cannot be read is noise, and a world that cannot be reproduced from its log cannot be shared, verified, or caught up on.

### Directives Checklist
- [x] **Directive 1: Systems Over Content.** Content is never hardcoded. Behavior is calculated.
- [x] **Directive 2: Strict Determinism.** Floating-point types (`float`, `double`) are banned in the simulation kernel. All math must use fixed-point standard (`Q32.32`).
- [x] **Directive 3: Data-Oriented Design (DOD).** Entity Component Systems (ECS) must use contiguous Struct of Arrays (SoA) layout for cache efficiency.
- [x] **Directive 4: Kernel/Host Separation.** The simulation kernel must build as a standalone, headless library with zero graphics dependencies.
- [x] **Directive 5: Zero-Allocation Runtime.** Allocation of memory on the heap during the simulation tick loop is strictly prohibited.
- [x] **Directive 6: Explicit Temporal Order.** Systems execute in a single-threaded deterministic sequence per tick, even when internal system tasks run in parallel.
- [x] **Directive 7: Explicit Data Ownership.** Systems read from read-only buffers and write to double-buffered output blocks to prevent race conditions.
- [x] **Directive 8: Seeded PRNG Isolation.** No global random number generators. Each system instance maintains its own deterministic PRNG state.
- [x] **Directive 9: Independently Testable Modules.** Every module must have a headless unit test suite verifying state checksums.
- [x] **Directive 10: Emergent Behavior Supremacy.** If a mechanics issue arises, solve it by tweaking universal substrate laws, never by adding special-case IF-statements.
- [x] **Directive 11: Legibility is a Requirement.** Every decision leaves a Decision Trace; every significant change emits a Notable Event. A Protocol system that chooses an action without writing the `DecisionTrace` record of DEOS section 5.4, or that crosses a significance threshold without emitting a `NotableEvent`, is non-conformant regardless of how good its output looks (GI-5).
- [x] **Directive 12: The Log is the Save.** `world(t) = F(MasterSeed, InputLog[0..t])`. A world persists as (Master Seed, Input Log, optional Snapshot) and nothing else. No module may introduce state that is not a pure function of those inputs, and no Host feature may mutate the world except through a Catalyst Action appended to the Input Log (GI-1, GI-2, GI-6).

### 1.1 Directive 11 in practice
1. The `DecisionTrace` record (40 bytes: chosen action plus the top three utility contributors with signed weights) is written in Stage 4 for every agent that makes a decision that tick, in the same pass that writes the `Decision` component.
2. The `NotableEvent` record (48 bytes in a 64-byte slot) is emitted only when a significance threshold defined in DEOS-PROTO is crossed. A birth is not notable; the first birth in a founded settlement is.
3. Thresholds are Protocol constants. Raising or lowering the cadence of Notable Events is a constant change, never a special case (Directive 10).
4. The `cause` field of a `NotableEvent` links the event to the Decision Trace that produced it, or holds 0 when the event has no agent cause.

Player-facing consequence: the player can select any agent, tribe, or Institution and read "why" in one panel, and the Chronicle they scroll through is the Kernel's own record rather than a narration written afterwards.

### 1.2 Directive 12 in practice
1. The Input Log is the ordered, append-only sequence of Catalyst Actions and host commands, each stamped with the tick at which it takes effect, applied in Stage 1 in `(tick, seq)` order.
2. A Checkpoint (the Tick Hash) is appended every `CHECKPOINT_INTERVAL` ticks so any prefix can be verified incrementally.
3. A Snapshot is an optimization for restore time, never a second source of truth: restoring a Snapshot and stepping yields the same Tick Hashes as replaying the Input Log from tick 0.
4. Wall-clock time never enters the Kernel. Offline catch-up is Acceleration over the same Input Log (GI-4).

Player-facing consequence: a world is small enough to paste into a message, a challenge is an Input Log the verifier re-runs, and a return after an absence is a real continuation of the same history.

---

## 2. Revision History
| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 (EESS) | 2026-07-20 | Initial Baseline Release (lineage) | EE Arch Team |
| v0.1.0 (DEOS) | 2026-09-12 | Rebranded to DEOS-F02; Directives 1-10 kept verbatim; Directive 11 (Legibility is a Requirement) and Directive 12 (The Log is the Save) added; supersedes EESS-0002 | DEOS Arch Team |
