---
name: Specification Change Proposal
about: Propose a modification or expansion to a DEOS document
title: '[SPEC] '
labels: 'specification'
assignees: ''
---

### Target Specification Document
Document ID and path, one of: `DEOS.md`; `DEOS-F01` … `DEOS-F06` in `docs/00_Foundation/`; `DEOS-CORE` (`docs/01_Core/`); `DEOS-ECS` (`docs/02_ECS/`); `DEOS-RT` (`docs/03_Runtime/`); `DEOS-PROTO` (`docs/04_Protocol/`); `DEOS-PLAY` (`docs/05_Play/`); `DEOS-MVS` (`docs/06_Prototype/`).

### Proposed Modification
Clear description of the proposed architectural change or addition. Name the requirement IDs it defines, tightens, or references (`REQ-PREFIX-nnn`).

### Rationale
Why is this change required for the substrate or for *Emergence: The Digital Rise*?

### Player-Facing Consequence
One sentence beginning "Player-facing consequence:" stating what the player perceives, does, or returns for because of this change (CONTRIBUTING.md Rule 8).

### Dependencies Affected
List upstream and downstream modules impacted, respecting the order `DEOS → Foundation → Core → ECS → Runtime → Protocol → Play → MVS`.

### Alignment with Core Principles and Game-Facing Invariants
- Directives affected (DEOS-F02, 1 through 12):
- Game-Facing Invariants checklist (`DEOS.md` section 6): GI-1 [ ] · GI-2 [ ] · GI-3 [ ] · GI-4 [ ] · GI-5 [ ] · GI-6 [ ] · GI-7 [ ] · GI-8 [ ] — tick each invariant that names the target module and state how it remains satisfied.
- Determinism and zero-allocation impact:

### Rubric Pre-Score
Six metrics of `docs/00_Foundation/DECISION_FRAMEWORK.md`, 0 to 10 each; total ___/60 (floor 42).

### Linter
- [ ] The proposal, once drafted, passes `python3 deos/tools/spec_lint.py` with 0 errors.
