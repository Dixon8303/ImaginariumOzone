# Specification: Data & Memory Layout (EESS-0601)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | EESS-0601 |
| **Semantic Version** | v0.7.0 |
| **Status** | Approved |
| **Dependencies** | EESS-0401, EESS-0501 |

---

## 1. Cache Alignment & Memory Allocation Rules

### REQ-DAT-001: 64-Byte Cache Line Boundary Alignment
All component arrays must be aligned on **64-byte boundaries** (`alignas(64)` in C/C++, `#[repr(align(64))]` in Rust) to match modern CPU cache line sizes and facilitate SIMD auto-vectorization (AVX-512 / ARM Neon).

### REQ-DAT-002: Zero Heap Allocation During Tick
All memory required for entities, components, queues, and state buffers must be **pre-allocated** in fixed contiguous pools during engine initialization. Calling `malloc()`, `free()`, `new`, or GC triggers inside the tick pipeline is strictly illegal.

---

## 2. Memory Budget Allocations
For a runtime instance targeting $1,000,000$ active entities:
- **Entity Identity Table**: $1,000,000 	imes 8 	ext{ bytes} = 8.0 	ext{ MB}$
- **Position Buffer (Double-Buffered)**: $2 	imes (1,000,000 	imes 16 	ext{ bytes}) = 32.0 	ext{ MB}$
- **Energy Buffer (Double-Buffered)**: $2 	imes (1,000,000 	imes 24 	ext{ bytes}) = 48.0 	ext{ MB}$
- **Cognitive Utility Buffer**: $1,000,000 	imes 64 	ext{ bytes} = 64.0 	ext{ MB}$
- **Spatial Grid Partitioning Tree**: $128.0 	ext{ MB}$

---

## 3. Revision History
| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.7.0 | 2026-07-20 | Data layout and cache alignment specs | EE Arch Team |
