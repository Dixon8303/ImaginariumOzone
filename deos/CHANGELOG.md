# Changelog
All notable changes to **DEOS: Emergence** (the Deterministic Emergence Operating Specification and its reference game, *Emergence: The Digital Rise*) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] DEOS - 2026-09-12
### Changed
- **Rebrand.** The Emergence Engine Software Specification (EESS) becomes **DEOS**, the Deterministic Emergence Operating Specification. The repository is named **DEOS: Emergence** because the substrate and the game are inseparable by design: the substrate is research-grade and the product is a game people play compulsively (`DEOS.md` section 1.1). Determinism is stated as the product: shareable worlds, verified challenges, the Chronicle, offline catch-up, and legibility are each a consequence of `world(t) = F(MasterSeed, InputLog[0..t])`.
- **Hierarchy.** Seven modules in dependency order: DEOS-Foundation → DEOS-Core → DEOS-ECS → DEOS-Runtime → DEOS-Protocol → DEOS-Play → DEOS-MVS (`DEOS.md` section 2). The eight EESS specification directories collapse into `docs/01_Core/`, `docs/02_ECS/`, `docs/03_Runtime/`, and `docs/06_Prototype/`, with the absorbed EESS documents preserved as `LEGACY_*.md` lineage files.
- **Foundation.** DEOS-F01 Vision rewritten for the game-first identity, with "Determinism as Product" and the Five Phases frame. DEOS-F02 adds Directive 11 (Legibility is a Requirement) and Directive 12 (The Log is the Save). DEOS-F03 rewords Pillar 4 around "shape the probabilities, not the people" and adds Pillar 5 (Playable Emergence). DEOS-F04 mirrors the `DEOS.md` section 4 vocabulary and refines State Hash to Tick Hash. DEOS-F05 adds Playability Metrics and assumed Product Targets. DEOS-F06 adds rubric metric 6 (Player Legibility & Engagement) and raises the rejection threshold to 42 of 60.
- **Repository documents.** README, ROADMAP, CONTRIBUTING (Rules 8 and 9), PR and issue templates, the architecture diagram, coding standards (hashing and ordering rules), the specification template, and the test plan are rewritten in DEOS terms.

### Added
- **`DEOS.md`**: the binding root contract with identity, hierarchy, the identifier scheme (Document IDs, `REQ-PREFIX-nnn`, reserved prefixes per module), canonical vocabulary, the shared registry (constants, tick pipeline, component catalog, record headers), Game-Facing Invariants GI-1 through GI-8, and conformance gates.
- **DEOS-Protocol** (`docs/04_Protocol/`): agent cognition, society models, cross-layer coupling, and the Notable Event taxonomy. Prefixes `COG`, `SOC`, `XL`, `EVT`.
- **DEOS-Play** (`docs/05_Play/`): the player loop, Catalyst interface and Budget, Chronicle presentation, sessions and offline catch-up, challenges and Seed Lineage, retention metrics, engagement ethics. Prefixes `PLAY`, `CAT`, `SES`.
- **DEOS-MVS** (`docs/06_Prototype/`): the first playable, verifiable build, absorbing the EESS prototype specification. Prefix `MVS`.
- **`tools/spec_lint.py`**: enforces Document ID validity, single definition of every requirement under its owning module, resolution of every requirement reference, confinement of retired EESS identifiers to lineage contexts, the no-deferred-text rule, and relative-link resolution; warns on banned synonyms and registry-constant drift.
- **`research/INTERFACE_INSPIRATION.md`**: the operator's interface and experience references transcribed into design commitments C1 through C10 and the registry additions they required (`mutation_bias`, `WorldMood`, `WORLD_PHASE_REACHED`, composite Catalyst kinds).
- **Test plan**: TS-SPEC-004 (identifier lint), TS-BENCH-003 (Epoch catch-up), TS-PLAY-001 (legibility), TS-PLAY-002 (event cadence).

### Lineage
- Every EESS document maps to a DEOS document in the table of `DEOS.md` section 3.1: EESS-0001 through EESS-0006 become DEOS-F01 through DEOS-F06; EESS-0101 and EESS-0201 are absorbed by DEOS-CORE; EESS-0301 and EESS-0501 by DEOS-RT; EESS-0401 and EESS-0601 by DEOS-ECS; EESS-0701 by DEOS-MVS; the EESS-1000 milestone is renamed DEOS-1.0.
- Existing requirements (`LAW`, `MATH`, `ARCH`, `ENT`, `LOOP`, `DAT`) keep their IDs and meaning; they may be tightened, never contradicted.

---

## Lineage (pre-DEOS)

### [0.1.0] EESS - 2026-07-20
#### Added
- Initial Release of the **Emergence Engine Software Specification (EESS)** repository layout.
- Decoupled engine specification layer (**Emergence Engine**) from reference application (**Emergence: The Digital Rise**).
- **00_Foundation Specs**: Vision, Core Principles, Design Pillars, Glossary, Success Criteria, Decision Framework.
- **01_Universal_Laws**: Conservation of mass-energy, entropy accumulation, discrete temporal progression.
- **02_Mathematics**: Q32.32 fixed-point math standard, Flux equation, Progress equation, utility functions, PCG64 PRNG spec.
- **03_Architecture**: Kernel/Host boundary separation, multi-stage ECS execution pipeline, double-buffered state swapping.
- **04_Entity_Model**: 64-bit EntityID structure, Struct of Arrays (SoA) component architecture, archetype taxonomy.
- **05_Simulation_Loop**: Deterministic 6-stage tick ordering, parallel worker chunk dispatching, bitwise state hash verification.
- **06_Data_Model**: Cache line alignment rules, zero-allocation contiguous pool allocators, memory budget specs.
- **07_Prototype**: Minimum Viable Simulation (MVS) parameters, 10,000 tick headless benchmark definition.
- **Architecture Tools**: `SYSTEM_DEPENDENCY_GRAPH.md`, `REQUIREMENT_TRACEABILITY_MATRIX.md`, `ADR_TEMPLATE.md`, `SPECIFICATION_TEMPLATE.md`.
- **Engineering Tools**: `CODING_STANDARDS.md`, `SPEC_CONSISTENCY_TEST_PLAN.md`, Mermaid architecture diagrams.
