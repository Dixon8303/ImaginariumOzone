# Specification: Decision Framework & Evaluation Rubric (DEOS-F06)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | DEOS-F06 |
| **Semantic Version** | v0.1.0 |
| **Status** | Approved |
| **Dependencies** | DEOS, DEOS-F02, DEOS-F03 |
| **Supersedes** | EESS-0006 |

---

## 1. Feature Rubric Scoring
Every proposed mechanic, architectural change, constant change, or new requirement must be evaluated against this rubric before it is merged. Six metrics are scored 0 to 10 each for a maximum of 60. Proposals scoring below **42 / 60** are rejected.

| Rubric Metric | Evaluation Criteria | Score Range |
| :--- | :--- | :---: |
| **1. Determinism** | Does this change maintain 100% bitwise cross-platform determinism? | 0 – 10 |
| **2. Performance** | Can this scale to $10^6$ entities without violating the 16.6ms tick budget? | 0 – 10 |
| **3. Zero-GC Allocation** | Does this execute without allocating heap memory during the tick loop? | 0 – 10 |
| **4. Emergent Value** | Does this yield unscripted, non-linear system dynamics? | 0 – 10 |
| **5. Architectural Simplicity**| Can the data structure and logic be described in single-page math/pseudocode? | 0 – 10 |
| **6. Player Legibility & Engagement** | Does the change produce something the player can perceive, act on, and return for? | 0 – 10 |

### 1.1 Scoring anchors

Scores are integers. The anchors below are binding; a score between two anchors is justified in writing against the nearer one.

| Metric | 0 | 5 | 10 |
| :--- | :--- | :--- | :--- |
| 1. Determinism | introduces floating point, wall-clock, unordered iteration, or thread-count-dependent results into the Kernel | deterministic only under a stated platform or thread-count assumption | identical Tick Hashes on x86-64 and ARM64, 1 and 4 threads, attended and Acceleration, with the ordering and rounding rules written down |
| 2. Performance | exceeds `TICK_BUDGET_MS` at v1.0 scale or is super-linear in entity count | fits the budget at MVS scale only | fits the budget at v1.0 scale with a stated per-entity cost |
| 3. Zero-GC Allocation | allocates inside the tick | allocates only at Snapshot or Epoch boundaries | zero allocation at any point after Kernel initialization |
| 4. Emergent Value | a scripted outcome or a special-case branch (violates Directive 10) | a new constant on an existing law with a predictable effect | a new coupling between layers whose outcomes are not predictable from the change alone |
| 5. Architectural Simplicity | requires more than one page of pseudocode or a new subsystem | one page with one new struct | fits in an existing struct and stage with a single equation |
| 6. Player Legibility & Engagement | produces no perceptible change, or produces one the player cannot read (no Notable Event, no Decision Trace, no Observation View change) | perceptible within a session but offers no action and no reason to return | perceptible within 90 s at 1×, gives the player a Catalyst Action to respond with, and creates a return hook (a Chronicle row, a World Phase, a Seed Lineage effect, or an Epoch summary entry) |

### 1.2 Decision rules

1. Total = sum of the six metric scores. Total ≥ 42 is required to proceed; total < 42 is a rejection.
2. A score of 0 on metric 1 (Determinism) or metric 3 (Zero-GC Allocation) is an automatic rejection regardless of total, because each 0 is a violation of Directive 2 or Directive 5 that no other merit offsets.
3. A score of 0 on metric 6 is an automatic rejection for any change to DEOS-Protocol or DEOS-Play, because those modules exist to produce perceptible, actionable, returnable emergence (Pillar 5, GI-5).
4. A change to a registry constant (DEOS section 5.1) is scored like any other change and additionally records the before and after values of every DEOS-F05 metric it affects.
5. The completed rubric is attached to the Pull Request (`.github/PULL_REQUEST_TEMPLATE.md`) with a one-sentence justification per metric; a PR without it is not reviewed.

### 1.3 Worked example

Proposal: add a `mutation_bias` Cell field written by Mutation Catalyst Actions and decaying toward 1.0 in Stage 2 (the registry addition of research/INTERFACE_INSPIRATION.md section D).

| Metric | Score | Justification |
| :--- | :---: | :--- |
| 1. Determinism | 10 | one Q32.32 field per Cell, written in Stage 1 in `(tick, seq)` order and decayed in Stage 2 with a fixed rounding rule |
| 2. Performance | 9 | one multiply-and-clamp per Cell per tick on the existing Stage 2 pass; 8 bytes per Cell |
| 3. Zero-GC Allocation | 10 | the field is part of the pre-allocated Cell SoA |
| 4. Emergent Value | 8 | raises per-gene mutation probability regionally; the resulting Genome drift and its consequences are not predictable from the constant |
| 5. Architectural Simplicity | 9 | one field, one decay equation, one read in Protocol reproduction |
| 6. Player Legibility & Engagement | 9 | a Mutation slider on the Catalyst Palette; Genome-drift Notable Events name the region; a return hook through the first novel trait |
| **Total** | **55 / 60** | accepted |

Player-facing consequence: every change that reaches the player has been asked, in writing, what they will see, what they can do about it, and why they will come back to it.

---

## 2. Revision History
| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 (EESS) | 2026-07-20 | Decision framework and rubric matrix (lineage) | EE Arch Team |
| v0.1.0 (DEOS) | 2026-09-12 | Rebranded to DEOS-F06; metric 6 Player Legibility & Engagement added; rejection threshold raised to 42 of 60; scoring anchors, decision rules, and worked example added; supersedes EESS-0006 | DEOS Arch Team |
