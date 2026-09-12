# Emergence Engine Coding & Determinism Standards

All simulation runtime code written for the **Emergence Engine Kernel** must enforce these standards:

---

## 1. Math Rules (Strict Determinism)
- **NO FLOATING POINT TYPES**: The keywords `float` and `double` are forbidden in kernel files.
- Use `Fixed64` (`Q32.32`) for all fractional calculations.
- Transcendentals ($\sin, \cos, \exp, \ln$) must use fixed lookup tables with linear interpolation.

## 2. Memory Rules (Zero Allocation)
- No `malloc()`, `realloc()`, `free()`, `new`, or `delete` inside `tick()` pipelines.
- Use custom stack/pool allocators pre-allocated during `EE_Kernel_Init()`.

## 3. Threading Rules
- Worker threads execute over contiguous memory slices (Chunks of 1,024 entities).
- No cross-thread dynamic mutex locking during tick pipeline. All system outputs write to double-buffered output slices assigned exclusively per worker thread.
