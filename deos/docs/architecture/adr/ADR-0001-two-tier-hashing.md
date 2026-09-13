# Architecture Decision Record: ADR-0001 Two-Tier State Hashing

| Metadata | Value |
| :--- | :--- |
| **Status** | Accepted |
| **Date** | 2026-09-12 |
| **Author(s)** | DEOS Arch Team |

---

## 1. Context

DEOS section 4 defined the Tick Hash as a BLAKE3-256 Merkle root over Chunk Hashes computed every tick, where a Chunk Hash covers the Chunk's full canonical byte stream (DEOS-ECS REQ-DAT-007). The canonical stream is 28.4 MB per tick at MVS scale and 1.69 GB per tick at v1.0 scale (DEOS-ECS section 11). Hashing 28.4 MB costs roughly 10 ms on one core, twenty times the 0.5 ms per tick that the DEOS-MVS benchmark (10,000 ticks in under 5.0 s) allows; at v1.0 scale a per-tick full hash would need about 100 GB/s of hashing throughput. The original definition is therefore unimplementable within the performance requirements of DEOS-F05.

## 2. Decision

State hashing is split into two tiers (DEOS-Runtime `HASH`):

1. **Tick Hash, every tick.** Each Worker folds the little-endian canonical bytes of everything it writes to buffer B (owner writes, Command applications, spawn and despawn substeps, the IngressOverlay) into 64-bit write folds (REQ-HASH-001). The Tick Hash is BLAKE3-256 over the tick number, all folds in canonical order, the `Ledger`, the `CatalystLedger`, and the `WorldMoodSlot` (REQ-HASH-002). Its input is kilobytes, not megabytes, and it costs under 0.05 ms at any scale. Because buffer B at the end of a tick is a pure function of buffer A and the sequence of writes, identical write folds imply identical state.
2. **Checkpoint Hash, at Checkpoint ticks.** The full Chunk Hashes over the canonical streams are computed at every Checkpoint tick and combined into a Merkle root (REQ-HASH-003); the root is the value stored in `CHECKPOINT` records and compared by `deos_verify`. `CHECKPOINT_INTERVAL` becomes a scale-profile value: 64 ticks at MVS scale (4 ms of hashing every 64 ticks on four threads), and `SNAPSHOT_INTERVAL` (3,600 ticks) at v1.0 scale, where the 1.69 GB stream takes about 0.5 s to hash.

DEOS section 4 is amended: *Tick Hash* is the per-tick digest over write folds; *Checkpoint Hash* is the Merkle root over Chunk Hashes at a Checkpoint tick; *Chunk Hash* is unchanged. DEOS-F04, tools/CODING_STANDARDS.md section 4, and DEOS-F05 carry the same amendment.

## 3. Consequences

### Positive
- Every tick still has a fingerprint, so a Desync is detected within one tick (REQ-HASH-005 rule 3), better than the original design's Checkpoint-granularity detection.
- Verification of a challenge submission remains a full-state proof at every Checkpoint (GI-3).
- The MVS benchmark is achievable, and v1.0 scale is not blocked by hashing bandwidth.

### Negative & Trade-offs
- The per-tick Tick Hash is not a hash of the state bytes; two implementations must agree on the fold function and on exactly which bytes each write path folds. REQ-HASH-001 fixes both, and TS-BENCH-002 compares Tick Hash sequences across platforms and thread counts.
- At v1.0 scale, full-state verification granularity is one simulated day rather than 64 ticks; localization between Checkpoints relies on the Tick Hash ring.
- A 64-bit fold has a collision probability of about 2^-64 per (unit, stage) per tick; the combined Tick Hash is cryptographic, but the folds are not. This is acceptable for desync detection; it is not relied on for adversarial verification, which uses the Checkpoint Hash.

## 4. Compliance & Verification

- TS-BENCH-002: identical Tick Hash and Checkpoint Hash sequences across x86-64/ARM64, 1/4 threads, attended/Acceleration.
- TS-BENCH-001: the fold test vectors of DEOS-Runtime section 7.3.
- `tools/spec_lint.py` warns on the retired phrase "Merkle root over Chunk Hashes every tick".
