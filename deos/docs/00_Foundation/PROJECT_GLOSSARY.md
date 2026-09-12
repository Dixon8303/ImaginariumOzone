# Specification: Project Glossary & Terminology (EESS-0004)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | EESS-0004 |
| **Semantic Version** | v0.1.0 |
| **Status** | Approved |
| **Dependencies** | EESS-0001 |

---

## 1. Terminology Standard

| Term | Canonical Definition | Banned / Obsolete Synonyms |
| :--- | :--- | :--- |
| **Entity** | A pure 64-bit numerical identifier representing a discrete object in the world. Holds no data or methods directly. | Object, Actor, Unit, GameObject |
| **Component** | A contiguous, plain-old-data (POD) struct stored in flat arrays representing specific state properties. | Attribute object, Class property |
| **System** | A stateless execution function that queries matching components and transforms their state deterministically. | Manager, Controller, Handler |
| **Tick** | A single discrete atomic step of simulation time ($\Delta t = 1$). | Frame, Turn, Update Step |
| **EE Kernel** | The headless, graphics-free, deterministic simulation runtime engine. | Game Core, Backend, Engine Core |
| **Host Application**| The client wrapper (e.g., *Emergence: The Digital Rise*) handling UI, rendering, and audio. | Game Frontend, Client GUI |
| **Flux ($\Phi$)** | The scalar rate of energy/information transfer between two entities or spatial nodes per tick. | Flow rate, Transfer rate |
| **Progress ($P$)** | The cumulative state transformation metric of a complex system node over time. | Experience, Development Value |
| **Meme-Vector** | A fixed-size array of fixed-point values representing cultural concepts, beliefs, or technological ideas. | Culture variable, Idea stat |
| **Catalyst Action**| A direct injection of energy, information, or environmental change by the user/host application. | Player move, God power, Spell |
| **State Hash** | A 256-bit cryptographic digest (BLAKE3) of all entity component data at the end of a tick. | World checksum, Save hash |
| **Fixed-Point Q32.32**| A 64-bit signed integer representation using 32 bits for integer and 32 bits for fractional parts. | Float, Double |

---

## 2. Revision History
| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 | 2026-07-20 | Canonical terminology baseline | EE Arch Team |
