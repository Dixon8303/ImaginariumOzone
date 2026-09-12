# Specification: System Architecture Specification (EESS-0301)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | EESS-0301 |
| **Semantic Version** | v0.4.0 |
| **Status** | Approved |
| **Dependencies** | EESS-0002, EESS-0201 |

---

## 1. High-Level Subsystem Topology

```
┌────────────────────────────────────────────────────────────────────────┐
│                        EMERGENCE ENGINE KERNEL                         │
│                                                                        │
│  ┌────────────────────┐    ┌────────────────────┐    ┌──────────────┐  │
│  │ Ingress Ring Buffer│    │ Fixed-Point Math   │    │ Seeded PRNG  │  │
│  └─────────┬──────────┘    └────────────────────┘    └──────────────┘  │
│            │                                                           │
│  ┌─────────▼────────────────────────────────────────────────────────┐  │
│  │                    ECS Worker Pipeline Dispatcher                │  │
│  │  [Stage 1: Ingress] -> [Stage 2: Physics] -> [Stage 3: Bio]      │  │
│  │  -> [Stage 4: Cognition] -> [Stage 5: Society] -> [Stage 6: Hash]│  │
│  └─────────┬────────────────────────────────────────────────────────┘  │
│            │                                                           │
│  ┌─────────▼──────────┐                                                │
│  │ Double-Buffer Swap │                                                │
│  └─────────┬──────────┘                                                │
└────────────┼───────────────────────────────────────────────────────────┘
             │ Ring Buffer Egress Event Stream
┌────────────▼───────────────────────────────────────────────────────────┐
│                   HOST APPLICATION / VISUALIZER CLIENT                 │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Kernel / Host Decoupling Specification

### REQ-ARCH-001: Headless Kernel Compilation
The EE Kernel must compile into a standalone dynamic library (`.so`, `.dll`, `.dylib`) or static archive with zero linking to graphics APIs (OpenGL, DirectX, Vulkan, Metal) or windowing systems (SDL, GLFW).

### REQ-ARCH-002: Double-Buffered State Buffer
To allow concurrent visualization and simulation, component storage is double-buffered:
- `Buffer A (Read-Only)`: Exposed to host client for rendering and query streams.
- `Buffer B (Write-Only)`: Modified strictly by ECS worker threads during tick $t$.
- At the end of tick $t$, pointers to Buffer A and Buffer B swap atomically.

---

## 3. Revision History
| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.4.0 | 2026-07-20 | System architecture specification | EE Arch Team |
