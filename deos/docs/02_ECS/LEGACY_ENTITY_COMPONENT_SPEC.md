# Specification: Entity Component Model (EESS-0401)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | EESS-0401 |
| **Semantic Version** | v0.5.0 |
| **Status** | Approved |
| **Dependencies** | EESS-0004, EESS-0301 |

---

## 1. Entity Identifier Layout

### REQ-ENT-001: 64-bit Packed EntityID
An `EntityID` is a pure 64-bit integer bitfield holding index, generation, and archetype bits:

```
 63                       32 31               16 15                    0
┌───────────────────────────┬───────────────────┬───────────────────────┐
│     Array Index (32-bit)  │ Generation (16-bit)│  Archetype Tag (16-bit)│
└───────────────────────────┴───────────────────┴───────────────────────┘
```

- **Array Index (32-bit)**: Allows indexing up to $4,294,967,295$ simultaneous entities.
- **Generation (16-bit)**: Handles slot reuse and prevents stale references.
- **Archetype Tag (16-bit)**: Fast categorization bitmask (0x01: Physical, 0x02: Biological, 0x04: Cognitive, 0x08: Cultural).

---

## 2. Core Component Schemas (Struct of Arrays Layout)

### REQ-ENT-002: Position Component (`Position2D`)
```c
struct Position2DBuffer {
    int64_t x[MAX_ENTITIES]; // Q32.32
    int64_t y[MAX_ENTITIES]; // Q32.32
};
```

### REQ-ENT-003: Energy Component (`EnergyState`)
```c
struct EnergyStateBuffer {
    int64_t current_energy; // Q32.32
    int64_t max_capacity;   // Q32.32
    int64_t metabolic_rate; // Q32.32
};
```

---

## 3. Revision History
| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.5.0 | 2026-07-20 | Entity layout and SoA spec | EE Arch Team |
