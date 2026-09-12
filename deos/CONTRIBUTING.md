# Contributing Guidelines & Engineering Workflow

Thank you for contributing to the **Emergence Engine Software Specification (EESS)**.

---

## 1. AI Development Rules (Mandatory)
Every contributor (human or AI agent) must strictly obey the following rules when modifying or expanding specifications:

1. **Rule 1: Never Redefine Terminology.** Use existing definitions in `docs/00_Foundation/PROJECT_GLOSSARY.md`.
2. **Rule 2: Respect Dependency Hierarchy.** Never invent mechanics before their upstream physical/mathematical dependencies exist (see `docs/architecture/SYSTEM_DEPENDENCY_GRAPH.md`).
3. **Rule 3: Standard Requirement Sectioning.** Every new spec section must explicitly document:
   - Upstream Dependencies
   - Operational Assumptions
   - Subsystem Interactions
   - Failure Modes & Risks
4. **Rule 4: Mandatory Rubric Scoring.** Evaluate proposed changes using the rubric in `docs/00_Foundation/DECISION_FRAMEWORK.md`.
5. **Rule 5: Revision Traceability.** Every document update must include an entry in its `Revision History` table.
6. **Rule 6: Independent Testability.** Every specified module must define verification tests in `tests/`.
7. **Rule 7: Concrete Specifications Only.** Placeholder text, "TBD", and vague hand-waving are strictly prohibited.

---

## 2. Git Branching Model

- `main`: Immutable, stable specifications (`v1.0` and tagged releases).
- `develop`: Integration branch for active specification work.
- `docs/*`: Work on core specification documentation.
- `architecture/*`: Changes to system dependencies, traceability, or templates.
- `prototype/*`: Code experiments for performance benchmarking.

---

## 3. Specification Quality Gates
Before any Pull Request is merged into `develop`, it must satisfy:
- [ ] Zero contradictions with existing documents in `docs/00_Foundation/`.
- [ ] All variables, structures, and math equations explicitly typed and defined.
- [ ] Verified scale feasibility (capable of targeting $10^6$ active entities).
- [ ] Adherence to standard specification layout (`docs/templates/SPECIFICATION_TEMPLATE.md`).
