> **DEOS-v0.1.0**
> **Title:** Deterministic Emergence Operating Specification
> **Status:** Draft / Active Specification
> **Reference Implementation:** Emergence: The Digital Rise
> **Repository:** DEOS: Emergence
> **Supersedes:** Emergence Engine Software Specification (EESS) v0.1.0

# DEOS: Emergence

**DEOS** (Deterministic Emergence Operating Specification) is the engineering specification for a deterministic, data-oriented emergence substrate: fixed-point mathematics, an entity-component data layout, a six-stage tick pipeline, and the cognition and society rules that run on top of them, written to be implemented bit-for-bit on any platform.

***Emergence: The Digital Rise*** is the game built on it. The player is a Catalyst who shapes the probabilities, not the people: they warm a coastline, raise mutation in a valley, or seed an idea, then wait to see what a population of autonomous agents makes of it, and read the result in a Chronicle the Kernel wrote itself. There are no quests, no scripts, and no stat tables; every civilization, war, and religion is computed from substrate laws.

The repository is named for both because the two are inseparable by design: the substrate is research-grade, and the product is a game people play compulsively for months. The binding contract is [`DEOS.md`](DEOS.md).

## Why determinism is the product

Every world is a pure function `world(t) = F(MasterSeed, InputLog[0..t])`, reproduced bitwise on x86-64 and ARM64, with 1 or 4 threads, attended or in Acceleration. The game's signature features are consequences of that fact, not features layered over it:

- **Shareable worlds.** A 64-bit Master Seed plus an Input Log reproduces any world on any device; "try this seed, a religion forms by day 40" is a claim anyone can verify.
- **Verified challenges and leaderboards.** A submission is an Input Log; the verifier re-simulates it against its Checkpoints. Cheating is structurally impossible.
- **The Chronicle.** Every significant change is a Notable Event and every agent decision carries a Decision Trace, so the player can rewind, replay, and ask "how did this war start?"
- **Offline catch-up.** Simulated time is a tick count and wall-clock never enters the Kernel; leave overnight and return to an Epoch of consequences that actually happened.
- **The log is the save.** A world persists as (Master Seed, Input Log, optional Snapshot) and nothing else.

## Specification hierarchy

```
DEOS (Deterministic Emergence Operating Specification)
 ├── DEOS-Foundation  Vision · Principles · Pillars · Glossary · Success Criteria · Decision Framework
 ├── DEOS-Core        Mathematical Foundations & Fixed-Tick Rules
 ├── DEOS-ECS         Data Schemas & Entity-Component Architecture
 ├── DEOS-Runtime     Simulation Loop, Threading & State Hashing
 ├── DEOS-Protocol    Agent Cognition, Society Models & Inter-entity Rules
 ├── DEOS-Play        Player Loop, Catalyst Interface, Chronicle & Retention Systems
 └── DEOS-MVS         Minimum Viable Simulation: the first playable, verifiable build
```

Dependency order is `DEOS → Foundation → Core → ECS → Runtime → Protocol → Play → MVS`. A module may cite only `DEOS.md`, the Foundation, and modules above it; nothing cites DEOS-Play except DEOS-MVS.

## Modules

| Module | Document ID | Location | Owns | Prefixes |
| :--- | :--- | :--- | :--- | :--- |
| DEOS-Foundation | DEOS-F01 … DEOS-F06 | [`docs/00_Foundation/`](docs/00_Foundation/) | identity, terminology, rubric, acceptance metrics | — |
| DEOS-Core | DEOS-CORE | [`docs/01_Core/DEOS-Core.md`](docs/01_Core/DEOS-Core.md) | Q32.32 arithmetic, tables, conservation laws, fixed-tick integration, PRNG streams, ordering rules | `LAW` `MATH` `PRNG` `TICK` `ORD` |
| DEOS-ECS | DEOS-ECS | [`docs/02_ECS/DEOS-ECS.md`](docs/02_ECS/DEOS-ECS.md) | EntityID, component catalog, memory pools, mutation rules, command buffers | `ENT` `CMP` `DAT` `MUT` |
| DEOS-Runtime | DEOS-RT | [`docs/03_Runtime/DEOS-Runtime.md`](docs/03_Runtime/DEOS-Runtime.md) | Kernel/Host ABI, six-stage pipeline, threading, Tick Hash, Snapshots, replay, Acceleration | `ARCH` `LOOP` `THR` `HASH` `SNAP` |
| DEOS-Protocol | DEOS-PROTO | [`docs/04_Protocol/DEOS-Protocol.md`](docs/04_Protocol/DEOS-Protocol.md) | perception → utility → action, memory, Meme-Vectors, trust, Institutions, technology, Notable Events | `COG` `SOC` `XL` `EVT` |
| DEOS-Play | DEOS-PLAY | [`docs/05_Play/DEOS-Play.md`](docs/05_Play/DEOS-Play.md) | core and meta loops, Catalyst interface and Budget, Chronicle, sessions, challenges, retention | `PLAY` `CAT` `SES` |
| DEOS-MVS | DEOS-MVS | [`docs/06_Prototype/DEOS-MVS.md`](docs/06_Prototype/DEOS-MVS.md) | scope, acceptance criteria, and benchmarks of the first playable build | `MVS` |

The absorbed EESS documents lived in the module directories as `LEGACY_*.md` files during drafting; they are removed now that every legacy requirement is defined in its absorbing module, and remain in git history as lineage.

## Reading order

1. [`DEOS.md`](DEOS.md): identity, hierarchy, identifier scheme, canonical vocabulary, shared registry, Game-Facing Invariants GI-1 through GI-8, conformance.
2. [`docs/00_Foundation/`](docs/00_Foundation/): Vision (DEOS-F01), Core Principles (DEOS-F02), Design Pillars (DEOS-F03), Glossary (DEOS-F04), Success Criteria (DEOS-F05), Decision Framework (DEOS-F06).
3. The module specifications in dependency order: Core → ECS → Runtime → Protocol → Play → MVS.
4. [`docs/architecture/`](docs/architecture/): the dependency graph, the requirement traceability matrix generated from the modules, and the ADRs ([ADR-0001](docs/architecture/adr/ADR-0001-two-tier-hashing.md) two-tier hashing, [ADR-0002](docs/architecture/adr/ADR-0002-substrate-insolation.md) substrate insolation).
5. [`research/INTERFACE_INSPIRATION.md`](research/INTERFACE_INSPIRATION.md): the interface and experience references and the design commitments each module adopts.

## Directory layout

```
deos/
├── DEOS.md                     root contract (binding)
├── README.md · LICENSE · CHANGELOG.md · ROADMAP.md · CONTRIBUTING.md
├── .github/                    PR and issue templates
├── docs/
│   ├── 00_Foundation/          DEOS-F01 … DEOS-F06
│   ├── 01_Core/                DEOS-CORE
│   ├── 02_ECS/                 DEOS-ECS
│   ├── 03_Runtime/             DEOS-RT
│   ├── 04_Protocol/            DEOS-PROTO
│   ├── 05_Play/                DEOS-PLAY
│   ├── 06_Prototype/           DEOS-MVS
│   ├── architecture/           dependency graph, generated traceability matrix, adr/ (ADR-0001, ADR-0002)
│   └── templates/              specification and ADR templates
├── diagrams/                   Mermaid architecture overview
├── research/                   inspiration references and reading notes
├── tests/                      specification consistency and determinism test plan
└── tools/                      spec_lint.py, gen_rtm.py, and Kernel coding standards
```

## Guidance for contributors and AI agents

Every contribution, human or agent, obeys the nine rules of [`CONTRIBUTING.md`](CONTRIBUTING.md):

1. Never redefine terminology; use `DEOS.md` section 4 and `docs/00_Foundation/PROJECT_GLOSSARY.md` verbatim.
2. Respect the dependency order; never cite a module below your own.
3. Every new section documents upstream dependencies, assumptions, subsystem interactions, and failure modes.
4. Score every change with the rubric in `docs/00_Foundation/DECISION_FRAMEWORK.md`; 42 of 60 is the floor.
5. Add a revision-history row to every document you change.
6. Every module defines its verification tests in `tests/`.
7. Concrete specifications only: every equation in Q32.32 with rounding and overflow behaviour, every struct with exact field order and byte sizes, every threshold with a number.
8. Every mechanism states its player-facing consequence.
9. The linter passes with zero errors before any change under `deos/` merges:

```bash
python3 deos/tools/spec_lint.py          # from the monorepo root
python3 deos/tools/spec_lint.py --warn   # also show banned-synonym and constant-drift warnings
```

Requirements are defined exactly once as `### REQ-PREFIX-nnn: Title` headings under the module that owns the prefix (`DEOS.md` section 3.2) and referenced everywhere else in plain text. Retired EESS identifiers appear only in `Supersedes` rows, lineage rows, and `CHANGELOG.md`.

## Standalone extraction

This subtree is self-contained: it carries its own README, LICENSE, CHANGELOG, CONTRIBUTING, templates, tests, and tooling, and nothing under `deos/` imports from or links to any other component of the monorepo it currently lives in. When the specification graduates it is split out with `git subtree split -P deos` and continues under its own history without modification.

## License

Licensed under the [MIT License](LICENSE).
