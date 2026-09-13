# Contributing Guidelines & Engineering Workflow — DEOS: Emergence

Thank you for contributing to **DEOS** (the Deterministic Emergence Operating Specification) and to ***Emergence: The Digital Rise***, the game specified on it. The binding contract is `DEOS.md`; read it before anything else.

---

## 1. Development Rules (Mandatory)
Every contributor (human or AI agent) must strictly obey the following rules when modifying or expanding specifications:

1. **Rule 1: Never Redefine Terminology.** Use the definitions of `DEOS.md` section 4 and `docs/00_Foundation/PROJECT_GLOSSARY.md` (DEOS-F04) verbatim. A banned synonym in a normative sentence is a defect. A genuinely new shared name is proposed for `DEOS.md` section 5 through an ADR (`docs/templates/ADR_TEMPLATE.md`), never coined locally.
2. **Rule 2: Respect the Dependency Order.** `DEOS → Foundation → Core → ECS → Runtime → Protocol → Play → MVS` (`DEOS.md` section 2.2). A module cites only `DEOS.md`, the Foundation, and modules above it; nothing cites DEOS-Play except DEOS-MVS. Never invent a mechanic before its upstream mathematical or data dependency exists (`docs/architecture/SYSTEM_DEPENDENCY_GRAPH.md`).
3. **Rule 3: Standard Requirement Sectioning.** Every specification follows `docs/templates/SPECIFICATION_TEMPLATE.md`, and every new section explicitly documents:
   - Upstream Dependencies
   - Operational Assumptions
   - Subsystem Interactions
   - Failure Modes & Risks
4. **Rule 4: Mandatory Rubric Scoring.** Evaluate every proposed change with the six-metric rubric in `docs/00_Foundation/DECISION_FRAMEWORK.md` (DEOS-F06); the floor is 42 of 60, and a 0 on Determinism or Zero-GC Allocation rejects outright.
5. **Rule 5: Revision Traceability.** Every document update adds a row to that document's `Revision History` table. Retired EESS identifiers appear only in `Supersedes` rows, lineage rows, `DEOS.md` section 3.1, and `CHANGELOG.md`.
6. **Rule 6: Independent Testability.** Every module defines its verification tests in `tests/SPEC_CONSISTENCY_TEST_PLAN.md`, and every defined requirement is listed with its test in `docs/architecture/REQUIREMENT_TRACEABILITY_MATRIX.md`.
7. **Rule 7: Concrete Specifications Only.** Deferred-decision markers, stand-in text, and vague hand-waving are prohibited; `tools/spec_lint.py` rejects them. Every equation is stated in Q32.32 with its rounding and overflow behaviour, every struct lists exact field order, types, and byte sizes, every algorithm has pseudocode or an exact ordering rule, and every threshold has a number.
8. **Rule 8: Every Mechanism States Its Player-Facing Consequence.** Every major mechanism in every module carries one sentence beginning "Player-facing consequence:" that states what the player perceives, does, or returns for (`DEOS.md` section 1.1). A mechanism without one is incomplete, and a mechanism that cannot have one belongs below the Host boundary only if it serves a mechanism that does.
9. **Rule 9: The Linter Must Pass.** `python3 deos/tools/spec_lint.py`, run from the monorepo root, must report 0 errors before any change under `deos/` merges. It enforces the identifier rules of `DEOS.md` section 3: requirements are defined exactly once as `### REQ-PREFIX-nnn: Title` headings inside the module that owns the prefix, every reference resolves, and Document IDs are those of `DEOS.md` section 3.1.

---

## 2. Git Branching Model

- `main`: Immutable, stable specifications (`DEOS-1.0` and tagged releases).
- `develop`: Integration branch for active specification work.
- `docs/*`: Work on module and Foundation specification documents.
- `architecture/*`: Changes to `DEOS.md`, `docs/architecture/`, templates, and tooling.
- `prototype/*`: Code experiments for the MVS build and performance benchmarking.

Commits touching `deos/` are self-contained: nothing under `deos/` imports from or links to any other part of the monorepo, so the subtree can be extracted with `git subtree split -P deos` at any commit.

---

## 3. Specification Quality Gates
Before any Pull Request is merged into `develop`, it must satisfy:
- [ ] `python3 deos/tools/spec_lint.py` reports 0 errors (Rule 9).
- [ ] Zero contradictions with `DEOS.md` or any document in `docs/00_Foundation/`.
- [ ] Every Game-Facing Invariant of `DEOS.md` section 6 that names the changed module is still satisfied, and the change cites the invariants it satisfies (GI-1 through GI-8).
- [ ] Every conformance gate of `DEOS.md` section 7 that the change touches has its evidence updated.
- [ ] All variables, structures, and math equations explicitly typed and defined in Q32.32 terms with rounding and overflow behaviour.
- [ ] Determinism preserved: identical Tick Hashes on x86-64 and ARM64, at 1 and 4 worker threads, attended and in Acceleration.
- [ ] Verified scale feasibility (`MAX_ENTITIES` (1,048,576 at v1.0 scale) within `TICK_BUDGET_MS` (16.6)).
- [ ] Every mechanism carries its "Player-facing consequence:" sentence (Rule 8).
- [ ] Adherence to the standard specification layout (`docs/templates/SPECIFICATION_TEMPLATE.md`).
- [ ] Rubric score recorded in the PR with a one-sentence justification per metric (Rule 4).
