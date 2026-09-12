# Specification: Core Engineering Principles (EESS-0002)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | EESS-0002 |
| **Semantic Version** | v0.1.0 |
| **Status** | Approved |
| **Dependencies** | EESS-0001 |

---

## 1. Core Engineering Directives

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

---

## 2. Revision History
| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 | 2026-07-20 | Initial Baseline Release | EE Arch Team |
