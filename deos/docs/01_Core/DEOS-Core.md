# Specification: Mathematical Foundations & Fixed-Tick Rules (DEOS-CORE)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | DEOS-CORE |
| **Semantic Version** | v0.1.0 |
| **Status** | Draft |
| **Dependencies** | DEOS, DEOS-F01, DEOS-F02, DEOS-F03, DEOS-F04, DEOS-F05, DEOS-F06 |
| **Supersedes** | EESS-0101 (REQ-LAW-001…003), EESS-0201 (REQ-MATH-001…004) |
| **Reserved Prefixes** | `LAW`, `MATH`, `PRNG`, `TICK`, `ORD` |

---

## 1. Purpose

DEOS-Core defines the arithmetic, the universal laws, the clock, the randomness, and the ordering rules that every other module computes with. Everything above it (ECS, Runtime, Protocol, Play, MVS) is a consumer of the five prefixes reserved here. A world is `world(t) = F(MasterSeed, InputLog[0..t])` (GI-1) only because the operations in this document have exactly one answer for every input on every platform; this document is therefore written so that two implementers who never speak produce bit-identical Tick Hashes.

Player-facing consequence: a seed a friend pastes into chat, a challenge submitted as an Input Log, and an Epoch caught up after a night away all resolve to the same world because addition, multiplication, exponentials, diffusion, and dice are specified here to the last bit.

## 2. Scope

**Included.** Q32.32 representation and every primitive operation on it (§7.1); the seven function tables and their build rules (§7.2); the energy ledger, entropy accounting, radiation, insolation, diffusion, coupling, material decay, and `mutation_bias` decay of Stage 2 (§7.3); fixed-tick integration and the Stage 2 sub-step order (§7.4); PCG64, the seed hierarchy, per-Chunk streams, per-slot substreams and the draw functions (§7.5); canonical iteration, tie-break, reduction and hashing orders (§7.6); conformance vectors (§7.7).

**Excluded.** Component layouts and buffer mechanics (DEOS-ECS); the tick pipeline outside Stage 2, threading, the Tick Hash Merkle combination, Snapshots (DEOS-RT); every rule of Stages 3–5 (DEOS-PROTO); the Catalyst interface (DEOS-PLAY). Where this document names a Stage other than 2 it states an obligation those modules must satisfy, not a rule it defines for them.

## 3. Dependencies

| Document | Used for |
| :--- | :--- |
| DEOS §4, §5 | vocabulary; `FIXED_FORMAT`, `TICK_RATE_HZ`, `CHUNK_SIZE`, `GRID_W`, `GRID_H`, `MAX_ENTITIES`, `PRNG`, `HASH`; the Substrate Cell field list of §5.3; the tick pipeline of §5.2 |
| DEOS §6 | GI-1, GI-3, GI-4 name this module |
| DEOS-F02 | Directive 2 (no floating point), 6 (explicit temporal order), 7 (data ownership), 8 (seeded PRNG isolation), 12 (the log is the save) |
| DEOS-F04 | Tick, Flux, Meme-Vector, Catalyst Action, State Hash, Q32.32 |
| `research/INTERFACE_INSPIRATION.md` §C3, §D | the `mutation_bias` Cell field this module decays; the Cosmic family's Stage 1 expansion consumes the Substrate stream defined in §7.5 |

## 4. Definitions

| Term | Definition |
| :--- | :--- |
| `fx_t` | The C name of a Q32.32 value: `int64_t` whose integer value is `raw / 2^32`. |
| ulp | One unit in the last place of Q32.32: `2^-32`, raw value 1. |
| `i128` | A signed 128-bit integer. Used for products, quotients, and ledger sums. Never stored in a component. |
| Raw value | The `int64_t` bit pattern of an `fx_t`, written in hexadecimal with a `0x` prefix and 16 digits. |
| Rotation | The angle unit of this specification: 1.0 is one full circle. `fx_sin_rot(u)` is `sin(2π·u)`. |
| Cell Chunk | `CHUNK_SIZE` consecutive Cells in row-major index order (`index = y·GRID_W + x`). The unit of parallelism and of hashing for the Substrate, mirroring the entity Chunk. |
| Slot | The position of an entity within its Chunk (`0 … CHUNK_SIZE−1`), or of a Cell within its Cell Chunk. |
| Account | Any field that holds substrate energy: a Cell `energy` field, a Cell `temperature` field, an `EnergyState.current`, an `InstitutionState.pooled_energy`, or `Ledger.heat_sink`. |
| Usable account | An account other than a `temperature` field. |
| `X⁰`, `X¹` | For a Substrate field `X`: its value at Stage 2 entry (after Stage 1 has been resolved) and the value Stage 2 produces for Stage 3 entry. |
| Stream | A PCG64 generator instance: a 128-bit state and a 128-bit odd increment. |
| Substream | A Stream positioned at a fixed offset of `2^32` draws per Slot within a Chunk Stream. |

## 5. Assumptions

1. The target compilers expose a 128-bit integer type (`__int128` on GCC and Clang, or an explicit `(hi, lo)` pair with carry) and a 64×64→128 multiply. ARM64 (`umulh`/`mul`) and x86-64 (`mul r64`) both do.
2. `int64_t` arithmetic shift right is arithmetic (sign-propagating) on every supported compiler; an implementation that cannot guarantee this must emulate it (`(x >> n) | (x < 0 ? ~(~0ULL >> n) : 0)`).
3. Every Q32.32 array is 64-byte aligned and pre-allocated (DEOS-ECS, `DAT`); this document never allocates.
4. The grid is `GRID_W × GRID_H` Cells with a closed boundary: a Cell on the edge has three neighbours, a corner Cell two, and no flux crosses the boundary.
5. All ledger accounts are bounded (REQ-LAW-012) so that Stage 2 can never saturate; the saturation rules of §7.1 are nevertheless total functions and are what Stages 3–5 rely on.
6. BLAKE3 (32-byte output, plain and keyed modes) is available in the implementation language; its output is the reference for every derived seed.

---

## 6. Requirements

Requirements are defined in §6 with their normative text; §7 gives the algorithms they bind to, §8 the layouts. A requirement heading appears exactly once in this repository.

### 6.1 Universal laws (`LAW`)

### REQ-LAW-001: Conservation of Energy

Energy cannot be created or destroyed within the simulation runtime. The total energy of the closed simulation system at tick `t+1` equals the total energy at tick `t`, plus external Catalyst energy inputs, minus radiant dissipation:

`E_total(t+1) = E_total(t) + E_cat(t) + E_sun(t) − E_rad(t)`

DEOS tightening (ADR-0002): `E_sun` is the Substrate insolation credit of REQ-LAW-013, the world's only renewable input; `E_total`, `E_cat`, `E_sun`, and `E_rad` are `i128` sums of Q32.32 raw values computed in the order of REQ-ORD-004, the equality is exact integer equality, and it is evaluated every tick at Stage 6 per REQ-LAW-004. There is no tolerance.

Player-facing consequence: every unit of energy the player sees in a settlement, a granary, or a glowing Cell came from the founding endowment or from a Catalyst Action they paid for; scarcity is never a script and abundance is never a gift (GI-7, GI-8).

### REQ-LAW-002: Entropy Accumulation

Every energy transfer or conversion process incurs an entropy cost (`ΔS > 0`), converting usable potential energy into thermal dissipation energy.

DEOS tightening: the thermal dissipation energy of a Cell is its `temperature` field, measured in the same Q32.32 energy unit as `energy` (heat capacity 1 per Cell). Every transfer between usable accounts pays `FX_ENTROPY_TAX` of its amount, never less than 1 ulp, into the `temperature` of the destination Cell (REQ-LAW-005). Entropy is accounted as the `i128` sums `s_tick` and `s_total` of §8.3; `s_total` is monotone non-decreasing.

### REQ-LAW-003: Discrete Temporal Progression

Time advances strictly in discrete integer ticks (`Δt = 1`). Continuous differential equations are solved using explicit fixed-step integration in Q32.32 math.

DEOS tightening: the integration scheme is explicit Euler with unit step (REQ-TICK-002); no rule in any module may contain a `Δt` factor, a step subdivision, or an implicit solve.

### REQ-LAW-004: The Energy Ledger

1. Every change to an account is either a **transfer** (a debit of amount `a` from one account and a credit of exactly `a` to one or more accounts, all in the same tick and the same stage), a **Catalyst credit or debit** recorded in `e_cat`, or a **radiant debit** recorded in `e_rad`. No other write to an account is permitted in any module.
2. When a transfer of `a` is split into parts (an entropy share, a capacity spillover, a fee), every part but the last is computed by Q32.32 multiplication and the **last part is computed by subtraction from `a`**. The rounding residue therefore always lands in the last part, and the parts sum to `a` exactly. The last part of every split is a `temperature` credit (heat); this is the rule that closes the ledger with zero residue.
3. A credit that would raise a usable account above its capacity (`EnergyState.max_capacity`, `FX_CELL_ENERGY_CAP`, or the Institution cap DEOS-PROTO defines) delivers the capacity remainder to the account and the excess to the `temperature` of the destination Cell in the same operation.
4. An account is never destroyed with a non-zero balance. When an entity dies or is recycled, `EnergyState.current` is transferred (taxed per REQ-LAW-005) to the `energy` of the Cell at its position through a `CELL_ENERGY_DELTA` deposit; when an Institution dissolves, `pooled_energy` is transferred likewise to the Cell of its founding position. DEOS-PROTO and DEOS-ECS must perform these transfers in the same tick as the destruction.
5. At Stage 6, before hashing, the Kernel computes `E_total(t+1)` per §7.3.1 and checks `E_total(t+1) == e_total + e_cat + e_sun − e_rad`. On inequality the Kernel sets `Ledger.fault = 1`, still completes the tick (so the faulty tick is itself reproducible), and DEOS-RT handles the fault. `Ledger.fault` is never cleared by the Kernel.
6. The Cell of an entity is `(clamp(floor(x), 0, GRID_W−1), clamp(floor(y), 0, GRID_H−1))` of its `Position2D`.

Player-facing consequence: a famine is legible because the energy went somewhere the player can find in the Chronicle (radiated, taxed into heat, hoarded by an Institution), never because a number was rounded away.

### REQ-LAW-005: Entropy Tax on Transfers

For every transfer of amount `a > 0` between usable accounts: `heat = fx_mul(a, FX_ENTROPY_TAX)`; if `heat == 0` then `heat = 1`; `delivered = a − heat`. `heat` is credited to the `temperature` of the destination Cell (transfers performed inside Stage 2) or to `Ledger.heat_sink` (transfers applied at Command barriers by DEOS-ECS, and every own-write loss booked to a Chunk ledger: metabolism, upkeep, clamps, damage) and added to `s_tick`; `delivered` is credited to the destination account (subject to REQ-LAW-004 rule 3). `FX_ENTROPY_TAX = 2^-6` (raw `0x0000000004000000`). Transfers of `a ≤ 0` are illegal and a debug assertion. Catalyst credits and debits pay no tax; radiant debits pay no tax; insolation credits pay no tax. `heat_sink` is a thermal account of the world with heat capacity 1, radiates like a Cell (REQ-LAW-006), and is included in `E_total`.

### REQ-LAW-006: Radiant Dissipation

Every tick, in Stage 2 sub-step 2g, every Cell radiates `rad = fx_mul(T, FX_RAD_COEFF)` from its `temperature` field `T`, with `FX_RAD_COEFF = 2^-10` (raw `0x0000000000400000`), and in sub-step 2j the `heat_sink` radiates `rad_sink = fx_mul(heat_sink, FX_RAD_COEFF)` likewise (`heat_sink` is bounded by `E_total` and therefore fits `fx_t`). `rad` and `rad_sink` are debited and added to `e_rad`. Radiation is the only path by which energy leaves the world, and insolation (REQ-LAW-013) is the only path by which energy enters it without a Catalyst Action. A Cell whose `temperature` is below 1,024 ulp radiates nothing.

Player-facing consequence: heat glows and fades on a fixed half-life of about 710 ticks (12 real seconds at speed 1×); a solar flare the player triggers is visibly transient, and the Chronicle can show exactly how much of it was lost to the sky.

### REQ-LAW-007: Heat Diffusion

Heat diffuses between 4-neighbour Cells by the explicit scheme of §7.3.3. The per-edge coefficient is the minimum of the two Cells' conductivities, so the flux computed by both endpoint Cells is bit-identical and antisymmetric. The stability bound of the explicit 4-neighbour scheme is `κ_edge ≤ 1/4`; DEOS fixes `FX_HEAT_KAPPA = 2^-3` (raw `0x0000000020000000`) and constructs the conductivity so that `κ_edge ≤ 2^-3` always holds, giving a margin of 2× and a provably non-negative, non-oscillating field.

Player-facing consequence: warmth spreads from a heated region at a visible, steady front, and a cold snap the player applies to one region reaches its neighbours over a readable number of ticks rather than instantly.

### REQ-LAW-008: Moisture Diffusion and Runoff

Moisture diffuses between 4-neighbour Cells with `FX_MOIST_KAPPA = 2^-4` (raw `0x0000000010000000`) and additionally runs downhill along each edge by `min(fx_mul(FX_RUNOFF, Δelevation), M_high >> 3)` with `FX_RUNOFF = 2^-6` (raw `0x0000000004000000`), per §7.3.4. The combined outflow of a Cell in one tick never exceeds three quarters of its moisture, so `moisture` never goes negative. Moisture is conserved: `M_total = Σ moisture + atmosphere` (an `i128` sum in the order of REQ-ORD-004) changes only by Catalyst writes, and Stage 6 checks `M_total(t+1) == m_total + m_cat` exactly, setting `Ledger.fault = 3` on inequality.

Player-facing consequence: rain the player summons on a mountain runs into the valleys over the following ticks and pools where the elevation is lowest; rivers and lakes are consequences of elevation, not painted features.

### REQ-LAW-009: Temperature–Moisture Coupling

1. **Evaporation.** In sub-step 2e each Cell evaporates `evap = fx_mul(M, rate)` where `rate = min(fx_mul(T, FX_EVAP_COEFF), FX_EVAP_MAX)`, `FX_EVAP_COEFF = 2^-16` (raw `0x0000000000010000`), `FX_EVAP_MAX = 2^-2`. `evap` leaves the Cell and enters the atmosphere reservoir.
2. **Precipitation.** In sub-step 2d the reservoir releases `rain_total = (atmosphere⁰ × FX_PRECIP_COEFF) >> 32` with `FX_PRECIP_COEFF = 2^-8` (raw `0x0000000001000000`), divided equally over all `GRID_W × GRID_H` Cells by floor division; the remainder stays in the reservoir.
3. **Conductivity.** A Cell's heat conductivity rises with moisture: `κ_c = fx_mul(FX_HEAT_KAPPA, COND[material] + (min(M, FX_MOIST_CAP) >> 10))` with `FX_MOIST_CAP = 256.0` (raw `0x0000010000000000`), so the wet term is at most `0.25` and `κ_c ≤ 2^-3`.

Player-facing consequence: hot regions dry out and the water comes back as rain everywhere; wet ground spreads heat faster than rock, so the same Catalyst Action has different reach in a marsh and a desert.

### REQ-LAW-010: Materials, Decay, and Transitions

Materials are the four rows of §8.5. Each tick, in sub-step 2f, a Cell converts `decay = fx_mul(E, DECAY[material])` of its `energy` into `temperature` (an entropy credit added to `s_tick`). In sub-step 2a a Cell of material WATER whose `T⁰ < FX_FREEZE_T` becomes ICE, and a Cell of material ICE whose `T⁰ ≥ FX_THAW_T` becomes WATER, with `FX_FREEZE_T = 2.0` (raw `0x0000000200000000`) and `FX_THAW_T = 6.0` (raw `0x0000000600000000`). SOIL and ROCK never transition. A `material_id ≥ 4` at Stage 2 entry sets `Ledger.fault = 2`.

Player-facing consequence: a stockpile left on wet ground spoils faster than one on rock, and a lake the player freezes stays frozen until the heat the player or the Substrate delivers crosses a threshold they can read.

### REQ-LAW-011: Decay of `mutation_bias` toward 1.0

Each tick, in sub-step 2h, every Cell's `mutation_bias` field `b` moves toward `ONE`: `d = fx_mul(ONE − b, FX_BIAS_DECAY)`; if `d == 0` and `b ≠ ONE` then `d = (b > ONE) ? −1 : +1`; `b¹ = b + d`. `FX_BIAS_DECAY = 2^-12` (raw `0x0000000000100000`), a half-life of 2,839 ticks. The field is clamped to `[0.25, 4.0]` (raw `0x0000000040000000` … `0x0000000400000000`) by the Stage 1 write rule DEOS-PLAY and DEOS-RT own; decay never leaves that range and reaches exactly `ONE` in finitely many ticks.

Player-facing consequence: the Mutation slider is a push, not a setting; the player watches volatility ebb back to baseline over about 47 real seconds at speed 1× and must spend Catalyst Budget to keep a region volatile (GI-8: the fade is visible, never hidden).

### REQ-LAW-012: Field Bounds and Invariants

| Field or sum | Bound | Enforced by |
| :--- | :--- | :--- |
| Cell `energy`, `temperature`, `moisture` | `≥ 0` | §7.3 positivity proofs; Stage 1 rejects a write below 0 |
| Cell `energy` | `≤ FX_CELL_ENERGY_CAP = 2^20` (raw `0x0000100000000000`) | REQ-LAW-004 rule 3 |
| Cell `elevation` | `[0, FX_ELEV_MAX = 4096.0]` (raw max `0x0000100000000000`) | Stage 1 clamp |
| Cell `mutation_bias` | `[0.25, 4.0]` | REQ-LAW-011 |
| `E_total` | `≤ FX_WORLD_ENERGY_MAX = 2^30` (raw `0x4000000000000000`) | world generation endowment and Stage 1 refusal of a Catalyst credit that would exceed it |
| Σ `moisture` + `atmosphere` | `≤ FX_WORLD_MOISTURE_MAX = 2^30` | as above |

Because every account is bounded by `E_total ≤ 2^30 < 2^31`, no Q32.32 add in Stage 2 can saturate; a `FX_FLAG_SAT` raised by a Stage 2 sub-step is a defect.

### REQ-LAW-013: Substrate Insolation

Each tick, in sub-step 2i, every Cell receives `sun = fx_mul(FX_INSOLATION, LAT[y])`, credited to its `energy` field under REQ-LAW-004 rule 3 (the capacity remainder to `energy`, the excess to `temperature`) and added to `e_sun`. `FX_INSOLATION = 2^-7` (raw `0x0000000002000000`) energy per Cell per tick. `LAT[y]` is the latitude weight of row `y`: `LAT[y] = 0x0000000040000000 + fx_mul(0x0000000180000000, fx_sin_rot(fx_div(fx_from_int(y) + FX_HALF, fx_from_int(GRID_H)) >> 1))`, that is `0.25 + 1.5·sin(π·(y + 0.5)/GRID_H)`, in `[0.25, 1.75]`, 1.75 at the equatorial rows and 0.25 at the polar rows (mean ≈ 1.2); the table is built once at initialization by that exact formula and is not hashed. Insolation is the renewable input that lets a world persist through an Epoch of Acceleration without a Catalyst Action; at MVS scale it delivers about 614 energy per tick, enough to sustain roughly 9,000 Agents at the mean metabolic rate (ADR-0002); at equilibrium `e_sun == e_rad` and `Σ temperature = e_sun / FX_RAD_COEFF`, a mean Cell temperature near 9.6 before diffusion, with the polar rows at about `FX_FREEZE_T` and the equator well above `FX_THAW_T`. Stage 1 refuses a Catalyst credit that would raise `E_total` above `FX_WORLD_ENERGY_MAX` (REQ-LAW-012); insolation cannot breach the bound because a Cell at `FX_CELL_ENERGY_CAP` spills to `temperature`, and radiation grows with `Σ temperature` until it equals `e_sun`.

Player-facing consequence: a world left overnight is alive when the player returns because the sun kept it fed; the Catalyst's energy injections are perturbations on top of a living baseline, never life support, and the player can read `e_sun` and `e_rad` in the Epoch summary as the world's breath (GI-4, GI-7).

### 6.2 Q32.32 arithmetic (`MATH`)

### REQ-MATH-001: Representation Format

All continuous variables (positions, energy levels, utility scores, probabilities) are stored as signed 64-bit integers (`int64_t`), where the upper 32 bits represent the signed integer component and the lower 32 bits the fractional component (`1 / 2^32 ≈ 2.328 × 10^-10` precision).

```
 63                                32 31                                 0
┌────────────────────────────────────┬────────────────────────────────────┐
│      Signed Integer (32-bit)       │       Fractional (32-bit)          │
└────────────────────────────────────┴────────────────────────────────────┘
```

DEOS tightening: the value of raw `r` is `r / 2^32` in two's complement (the fraction is always non-negative: raw `0xFFFFFFFF80000000` is `−0.5`). The named constants are:

| Name | Value | Raw (hexadecimal) |
| :--- | :--- | :--- |
| `FX_ONE` | 1.0 | `0x0000000100000000` |
| `FX_HALF` | 0.5 | `0x0000000080000000` |
| `FX_EPS` | 2^-32 (1 ulp) | `0x0000000000000001` |
| `FX_MAX` | 2^31 − 2^-32 | `0x7FFFFFFFFFFFFFFF` |
| `FX_MIN` | −2^31 | `0x8000000000000000` |
| `FX_LN2` | ln 2 | `0x00000000B17217F7` |
| `FX_LOG2E` | 1 / ln 2 | `0x0000000171547652` |
| `FX_PI` | π | `0x00000003243F6A88` |
| `FX_TWO_PI` | 2π | `0x00000006487ED511` |
| `FX_INV_TWO_PI` | 1 / 2π | `0x0000000028BE60DB` |
| `FX_E` | e | `0x00000002B7E15162` |

`FX_LN2` is `floor(2^32 · L(1/3))` and `FX_LOG2E` is `floor(2^32 / L(1/3))` with `L` the series of §7.2.3; `FX_PI` is `floor(2^32 · Π)` with `Π` the rational of §7.2.5; `FX_E` is `floor(2^32 · X(1))` with `X` the series of §7.2.6. They were generated by the build procedure of REQ-MATH-010.

### REQ-MATH-002: The Flux Equation

The rate of energy/information flux `Φ_{i,j}` from entity `i` to node `j` is governed by the utility gradient difference and the conductivity `α`:

`Φ_{i,j} = α · E_i · 1 / (1 + e^{−k·(U_j − U_i)})`

where the exponential term is computed by a deterministic lookup table with fixed-point linear interpolation.

DEOS tightening: the whole factor `1 / (1 + e^{−z})` is the logistic `fx_logistic(z)` of REQ-MATH-015, whose 8,193-entry table over `[−16, 16]` refines the 16-entry lineage table (the lineage grid of step 2 is the sub-sampled rows `SIG[512·i]`). The evaluation order is fixed:

```
d   = fx_sub(U_j, U_i);
z   = fx_mul(k, d);
s   = fx_logistic(z);
phi = fx_mul(fx_mul(alpha, E_i), s);
```

`Φ` is then transferred under REQ-LAW-004 and REQ-LAW-005; `Φ > E_i` is clamped to `E_i` by the caller before the transfer.

### REQ-MATH-003: Utility Scoring Function

The utility score `U(a)` for an agent evaluating action choice `a` is `U(a) = Σ_{k=0}^{N−1} w_k · f_k(S)`, where `w_k` is the weight of internal need `k` and `f_k(S)` is the state satisfaction curve evaluated in Q32.32.

DEOS tightening: `N = NEED_COUNT`; `f_k(S) ∈ [0, FX_ONE]`; `w_k ∈ [−2^15, 2^15]` so that no term exceeds `2^15` and the sum of eight terms cannot saturate; the sum is accumulated with `fx_add` in ascending `k`, starting from 0:

```
U = 0;
for k in 0 .. NEED_COUNT-1:  U = fx_add(U, fx_mul(w[k], f[k]));
```

The action with the greatest `U` is chosen; ties resolve to the lowest action index (REQ-ORD-002). The three largest `|w_k · f_k|` terms, ties to the lowest `k`, are the Decision Trace contributors DEOS-PROTO writes.

### REQ-MATH-004: PCG64 Implementation and Per-System Seed Derivation

Floating-point `rand()` functions are strictly banned. System workers use **PCG64** initialized with deterministic per-system seeds derived from the Master Seed:

`Seed_system = BLAKE3(MasterSeed ∥ SystemID ∥ Tick)`

DEOS tightening: the generator is PCG64 XSL-RR 128/64 exactly as REQ-PRNG-001 defines it (the Xoshiro256** alternative named in the lineage is withdrawn); the byte layout of the hash input is `LE64(MasterSeed) ∥ LE32(SystemID) ∥ LE64(Tick)` (20 bytes) per REQ-PRNG-002; the 32-byte `Seed_system` is a key from which every Chunk Stream of that system and tick is derived (REQ-PRNG-002), never a generator state by itself.

### REQ-MATH-005: Saturating Addition and Subtraction

`fx_add(a, b)` returns the mathematically exact sum when it lies in `[FX_MIN, FX_MAX]` and otherwise the nearer of `FX_MIN` and `FX_MAX`. `fx_sub(a, b)` is likewise the saturated exact difference (`fx_sub(0, FX_MIN) = FX_MAX`). Detection is by the sign rule (`((a ^ r) & (b ^ r)) < 0` for the wrapped sum `r`), by `__builtin_add_overflow`, or by an `i128` intermediate; the result is identical.

Overflow-flag policy: every saturating operation that saturates sets the sticky bit `FX_FLAG_SAT` in the calling worker's `fx_flags` (§8.1). The flags are cleared at tick start, combined by bitwise OR in ascending Chunk order at the Stage 6 barrier into `fx_flags_tick`, and emitted through egress as a diagnostic. `fx_flags` is never read by any Kernel decision and is never hashed; saturation is deterministic in its own right, so the flag exists only to make silent clipping visible to the developer.

### REQ-MATH-006: Multiplication

`fx_mul(a, b)`: compute the exact 128-bit product `p = (i128)a × (i128)b`, then `q = p >> 32` as an arithmetic shift (truncation toward negative infinity, i.e. `floor(a·b / 2^32)`), then saturate `q` to `[FX_MIN, FX_MAX]` (setting `FX_FLAG_SAT` on saturation). The rounding rule is floor and not round-half-even because floor is a single shift with no tie case, no sticky-bit inspection, and no data-dependent branch, so it cannot diverge across compilers or SIMD lanes; its systematic bias of at most 1 ulp per multiplication is absorbed by the last-part-by-subtraction rule of REQ-LAW-004, which is why the ledger closes despite it.

### REQ-MATH-007: Division

`fx_div(a, b)`: if `b == 0`, set `FX_FLAG_DIVZERO` and return `FX_MAX` when `a > 0`, `FX_MIN` when `a < 0`, `0` when `a == 0`. Otherwise compute `n = (i128)a << 32` and `q = floor(n / b)` (truncation toward negative infinity, chosen so that `fx_div` and `fx_mul` round the same way and `fx_div(x, FX_ONE) == x` for every `x`); an implementation whose `i128` division truncates toward zero computes `q0 = n / b, r = n − q0·b` and subtracts 1 from `q0` when `r ≠ 0` and `(r < 0) ≠ (b < 0)`. Saturate `q` to `[FX_MIN, FX_MAX]`.

### REQ-MATH-008: Comparison, Sign, and Conversion

| Operation | Rule |
| :--- | :--- |
| `fx_lt`, `fx_le`, `fx_eq`, `fx_min`, `fx_max`, `fx_clamp` | signed `int64_t` comparison of raw values |
| `fx_abs(a)` | `a < 0 ? fx_neg(a) : a`; `fx_abs(FX_MIN) = FX_MAX` (saturates, sets `FX_FLAG_SAT`) |
| `fx_neg(a)` | `fx_sub(0, a)`; `fx_neg(FX_MIN) = FX_MAX` |
| `fx_from_int(int32_t i)` | `(int64_t)i << 32`; exact |
| `fx_from_int64(int64_t i)` | `i` clamped to `[−2^31, 2^31 − 1]` then shifted; saturates |
| `fx_to_int_floor(a)` | `a >> 32` (arithmetic), returns `int32_t` |
| `fx_to_int_round(a)` | `fx_add(a, FX_HALF) >> 32`; halves round toward `+∞` |
| `fx_floor(a)` | `a & 0xFFFFFFFF00000000` |
| `fx_frac(a)` | `a & 0x00000000FFFFFFFF`; always in `[0, FX_ONE)` |
| `fx_shl(a, n)` | `(i128)a << n` saturated; `fx_shr(a, n)` is arithmetic |

### REQ-MATH-009: Intermediate Widths and Implementation Constraints

1. Every intermediate of every Q32.32 expression is an `int64_t` or an `i128`; no other width and no floating-point type may appear in the Kernel (Directive 2).
2. 128-bit operations are explicit: `(i128)a * b`, `(i128)a << 32`, and `i128` division are written as such in source; an implementation without a native type provides `mul_64x64_128`, `shl_64_to_128`, and `div_128_by_64` with the semantics of REQ-MATH-006 and REQ-MATH-007.
3. Compiler flags that permit reassociation, contraction, or value-changing optimization are prohibited for Kernel translation units: no `-ffast-math`, no `-ffp-contract=fast`, no FMA contraction, no `-fassociative-math`. Integer arithmetic is not subject to these flags, but the rule guards mixed units and the build system must enforce it.
4. Source-level evaluation order is the specification: `fx_mul(fx_mul(a, b), c)` is not interchangeable with `fx_mul(a, fx_mul(b, c))`, and every formula in this document is written in the order it must be evaluated.
5. Signed overflow of a plain `int64_t` add is undefined behaviour in C; Kernel code uses `fx_add` or unsigned wrapping arithmetic, never a raw signed add whose overflow is possible.

### REQ-MATH-010: Function Table Construction

Every function table is built at build time (or at Kernel initialization, before tick 0) from the exact integer or rational rule given in §7.2 for that table, using arbitrary-precision integer arithmetic, and never from floating-point evaluation. Each entry is `floor(2^32 · v)` where `v` is the exact rational value the rule defines. The reference tables were generated with Python `fractions.Fraction` and integer arithmetic by the procedure of §7.2; an implementation proves conformance by matching the BLAKE3-256 digest of each table's little-endian `int64_t` bytes (§7.2.8) and the first eight entries published per table. Tables are immutable after initialization and are not part of any hashed state.

The common interpolation rule for a table `T` of `N+1` entries at uniform spacing, an index `i ∈ [0, N)` and a remainder `r ∈ [0, 2^s)`:

```
y = T[i] + (((T[i+1] - T[i]) * r) >> s);        // int64 product, arithmetic shift (floor)
```

`|T[i+1] − T[i]| < 2^33` and `r < 2^24` in every table, so the product fits in `int64_t` and no `i128` is needed.

### REQ-MATH-011: Exponential

`fx_exp(x)` computes `e^x` by the algorithm of §7.2.2 using `FX_EXP2_TABLE` (4,097 entries of `2^f`, `f = i/4096`). Domain: `x ∈ [−32, 22)`; `x ≥ 22·FX_ONE` returns `FX_MAX` and `x ≤ −32·FX_ONE` returns `0` (both set `FX_FLAG_DOMAIN`); results that overflow inside the domain saturate to `FX_MAX`. Worst-case error: `|fx_exp(x) − e^x| ≤ 2^n · 2^-26 + 2^-31` where `n = floor(x · log2 e)`.

### REQ-MATH-012: Natural Logarithm

`fx_ln(x)` computes `ln x` by the algorithm of §7.2.3 using `FX_LN_TABLE` (4,097 entries of `ln(1 + j/4096)`) and `FX_LN2`. Domain: `x > 0`; `x ≤ 0` returns `FX_MIN` and sets `FX_FLAG_DOMAIN`. Worst-case error: `|fx_ln(x) − ln x| ≤ 2^-25`.

### REQ-MATH-013: Square Root

`fx_sqrt(x)` computes `√x` by the algorithm of §7.2.4 using `FX_SQRT_TABLE` (3,073 entries of `√(1 + j/1024)` over `[1, 4]`). Domain: `x ≥ 0`; `x < 0` returns `0` and sets `FX_FLAG_DOMAIN`; `fx_sqrt(0) = 0`. Worst-case error: `|fx_sqrt(x) − √x| ≤ 2^k · 2^-24 + 2^-31` where `k = floor((msb(x) − 32) / 2)`.

### REQ-MATH-014: Sine and Cosine in Rotations

`fx_sin_rot(u)` computes `sin(2π·u)` for an angle `u` in rotations and `fx_cos_rot(u) = fx_sin_rot(u + 0x40000000)` (wrapping `uint64_t` addition of a quarter rotation, never saturating), by the algorithm of §7.2.5 using `FX_SIN_TABLE` (1,025 entries over the first quadrant). Domain: all of Q32.32; only the fractional 32 bits of `u` are used, so the functions are exactly periodic and never clamp. Worst-case error: `≤ 2^-21`. Radian inputs are converted by `fx_mul(theta, FX_INV_TWO_PI)` before the call.

### REQ-MATH-015: Logistic

`fx_logistic(z)` computes `1 / (1 + e^{−z})` by the algorithm of §7.2.6 using `FX_SIG_TABLE` (8,193 entries at spacing `1/256` over `[−16, 16]`). Domain: `[−16, 16]`; inputs beyond are clamped to the table ends (`SIG[0] = 0x00000000000001E3`, `SIG[8192] = 0x00000000FFFFFE1C`) without a flag. `fx_logistic(0) = FX_HALF` exactly. Worst-case error: `≤ 2^-22`.

### REQ-MATH-016: Reciprocal

`fx_rcp(x)` computes `1/x` by the algorithm of §7.2.7 using `FX_RCP_TABLE` (4,097 entries of `1/(1 + j/4096)`). Domain: `x ≠ 0`; `x == 0` returns `FX_MAX` and sets `FX_FLAG_DIVZERO`; a negative `x` is evaluated on `|x|` and the result negated, so `fx_rcp(−x) == fx_neg(fx_rcp(x))`; results beyond `FX_MAX` saturate. Worst-case error: `|fx_rcp(x) − 1/x| ≤ 2^-e · 2^-25 + 2^-31` where `e = msb(|x|) − 32`. `fx_div` is the exact reference for every formula in every module; a formula uses `fx_rcp` only where its owning module names `fx_rcp` explicitly.

### REQ-MATH-017: Conformance Vectors

An implementation reproduces every row of §7.7 bit-for-bit and every table digest of §7.2.8. The vectors were generated by the same Python procedure that generated the tables; they are the `Core determinism vectors` gate of DEOS §7.

### 6.3 Fixed-tick time (`TICK`)

### REQ-TICK-001: The Tick Is the Only Clock

Simulated time is the `uint64_t` tick counter `t`. Tick 0 is the state after world generation; stepping tick `t` produces state `t+1`. No Kernel function reads a wall clock, a CPU timestamp, a render interval, or `TICK_RATE_HZ`. `TICK_RATE_HZ` is a Host presentation constant that decides how often the Host calls the step function at speed 1×; it appears in no Kernel formula, table, or constant. Derived spans (`TICKS_PER_DAY`, `TICKS_PER_EPOCH`) are integer divisions of `t` performed by the Host or by DEOS-PLAY for presentation (GI-4).

Player-facing consequence: a world stepped at 64× on a fast machine, at 1× on a phone, or headlessly overnight is the same world at the same tick; the speed dial changes only how long the player waits (GI-4).

### REQ-TICK-002: Explicit Euler With Unit Step

Every rate in every module is a per-tick quantity and every integration is `x(t+1) = x(t) + rate(t)` evaluated in Q32.32 with the rounding of REQ-MATH-006. There is no `Δt` factor, no sub-stepping, no adaptive step, and no implicit solve. A rule that needs a slower time scale expresses it through a smaller per-tick constant, never through a step size.

### REQ-TICK-003: Stage 2 Sub-step Order

Stage 2 executes the ten sub-steps of §7.4.1 in the listed order, each over every Cell Chunk, with a barrier after each sub-step. Sub-steps 2b and 2c read neighbour values only from `X⁰`; every other sub-step reads and writes only the Cell it is processing (the latest value of each field) and accumulates per-Cell-Chunk partial sums. The partial sums are combined at the end of Stage 2 in ascending Cell Chunk order (REQ-ORD-004).

### REQ-TICK-004: Acceleration Identity

The Kernel step is a pure function `step(S_t, InputLog entries stamped t) → S_{t+1}` whose only inputs are the two arguments; the Master Seed is part of `S_t`. Acceleration is the Host calling `step` in a loop with egress disabled. Because no term of any equation in this document depends on wall-clock, speed level, `TICK_RATE_HZ`, thread count, or egress state, and because `Δt = 1` is a constant, the sequence of states and Tick Hashes produced under Acceleration is identical to attended stepping by construction. No Kernel field may be written as a function of egress ring occupancy or backpressure.

Player-facing consequence: the overnight catch-up the player returns to is not an estimate; it is the same computation they would have watched, and its Checkpoints verify against any other player's run of the same log (GI-3, GI-4).

### 6.4 Randomness (`PRNG`)

### REQ-PRNG-001: PCG64 XSL-RR 128/64 Generator

A Stream is `(state: u128, inc: u128)` with `inc` odd. The multiplier is `PCG_MULT = 0x2360ED051FC65DA44385DF649FCCF645`. One draw is:

```
state  = (state * PCG_MULT + inc) mod 2^128;                     // advance first
hi     = (uint64_t)(state >> 64);  lo = (uint64_t)state;
rot    = (unsigned)(state >> 122);                               // top 6 bits
output = rotr64(hi ^ lo, rot);                                   // rotate right by rot
```

This is the `pcg_setseq_128_xsl_rr_64_random_r` function of the PCG C reference: advance, then output from the new state. A Stream loaded from a 32-byte key (REQ-PRNG-002) is used as loaded, with no seeding steps.

### REQ-PRNG-002: Seed Hierarchy and Byte Layout

```
seed_input   = LE64(MasterSeed) ∥ LE32(SystemID) ∥ LE64(Tick)          // 20 bytes
Seed_system  = BLAKE3-256(seed_input)                                   // 32 bytes (REQ-MATH-004)
chunk_input  = LE32(ChunkIndex)                                         // 4 bytes
StreamKey    = BLAKE3-256-keyed(key = Seed_system, data = chunk_input)  // 32 bytes
state        = LE128(StreamKey[0..16))
inc          = LE128(StreamKey[16..32)) | 1
```

`LEn` is little-endian encoding in `n` bits. `SystemID` is the `uint32_t` of §8.4. `ChunkIndex` is the entity Chunk index or the Cell Chunk index. Every (system, tick, Chunk) triple therefore has its own Stream (DEOS §5.1 `PRNG`), computed independently by the worker that processes the Chunk; two workers never share a Stream and no Stream survives a tick boundary. A Snapshot needs no generator state beyond the Master Seed and the tick, which is why the Snapshot's PRNG content is the derivation tuple.

### REQ-PRNG-003: Per-Slot Substreams

Within a Chunk Stream `(state₀, inc)`, Slot `s` uses the Substream `(base_s, inc)` where `base_0 = state₀` and `base_{s+1} = (A_STRIDE · base_s + inc · G_STRIDE) mod 2^128`, with

```
A_STRIDE = 0x433BEF4314F16A9453CD8FBC00000001     // PCG_MULT^(2^32) mod 2^128
G_STRIDE = 0xD74683C909AF5D98B461C97F00000000     // (PCG_MULT^(2^32) − 1)/(PCG_MULT − 1) mod 2^128
```

`base_{s+1}` is exactly the state of the Chunk Stream after `2^32` draws from `base_s`, so Slot substreams are disjoint segments of one full-period PCG64 cycle. A data-dependent number of draws by one Slot (a rejection loop, a variable number of offspring) cannot move any other Slot's draws, because each Slot starts from a fixed offset, not from wherever the previous Slot stopped. Draws that are not tied to a Slot (a Chunk-level choice) use Substream index `CHUNK_SIZE`. No Slot may make more than `2^20` draws in one stage (debug assertion). The per-tick cost is one 128-bit multiply-add per Slot when Slots are iterated in ascending order; §7.5.2 gives the general jump algorithm and constants for verification.

Player-facing consequence: when the player whispers a belief to one agent and that agent alone rolls more dice this tick, its neighbours' births, deaths, and choices are unchanged; a Catalyst Action perturbs exactly what it targets and nothing else, and the player can prove it by diffing two Chronicles.

### REQ-PRNG-004: Draw Functions

| Function | Rule | Draws consumed |
| :--- | :--- | :--- |
| `next_u64()` | REQ-PRNG-001 | 1 |
| `bounded(n)` | `n == 0 → 0` with no draw; else `threshold = (2^64 − n) mod n` (computed as `(0 − n) mod n` in `uint64_t`); loop `{ x = next_u64(); if x ≥ threshold return x mod n; }`. Unbiased: exactly `floor(2^64 / n)` accepted values fall on each residue. | 1 + rejections; expected < 2 |
| `uniform_q32()` | `next_u64() >> 32`, a raw Q32.32 in `[0, FX_ONE)`, uniform on the `2^32` grid | 1 |
| `bernoulli(p)` | `p` clamped to `[0, FX_ONE]`; return `uniform_q32() < p`. `p = 0` is never true, `p = FX_ONE` is always true; the draw is consumed in both cases. | 1 |
| `weighted(w[0..N))` | weights are non-negative raw Q32.32 with `Σw < 2^64` (`N ≤ 256`, each `w ≤ 2^55`, enforced by the caller); `t = Σw` in ascending index; `r = bounded(max(t, 1))`; return the smallest `k` with `w[0] + … + w[k] > r`. Zero-weight entries are never chosen; if `t == 0` the result is index 0. | 1 + rejections |

Every function consumes at least one draw whenever `n ≥ 1` or `N ≥ 1`, so the draw count of a code path is data-independent except through `bounded`'s rejection loop, which REQ-PRNG-003 isolates per Slot.

### REQ-PRNG-005: Stream Use Discipline

1. A system draws only from the Stream of its own `SystemID`, the current tick, and the Chunk it is processing (Directive 8). Drawing from another system's Stream, from another tick's Stream, or from a global generator is non-conformant.
2. Draws are made in canonical Slot order (REQ-ORD-001) within a Chunk; the order of draws within a Slot is the order of the owning module's rule text.
3. Core's Stage 2 rules of v0.1.0 make no draws; the `SUBSTRATE` Stream (SystemID 1) exists for the Stage 1 Cosmic expansion of DEOS-RT and DEOS-PLAY, which draws from Cell Chunk Streams of SystemID 1 at the tick of ingress.
4. World generation at tick 0 uses SystemID 0 with `Tick = 0`.

### REQ-PRNG-006: Generator and Derivation Test Vectors

An implementation reproduces the vectors of §7.5.4 (raw generator), §7.5.5 (derived Stream for Master Seed `0x0123456789ABCDEF`, SystemID 2, Tick 0, Chunk 0), and §7.5.6 (Slot 1 Substream).

### 6.5 Deterministic ordering (`ORD`)

### REQ-ORD-001: Canonical Iteration Order

Entities are iterated in ascending Chunk index and, within a Chunk, ascending Slot. Cells are iterated in ascending Cell Chunk index and, within it, ascending Cell index (`y·GRID_W + x`). Any loop whose side effects depend on order (writes, draws, accumulation, command emission) iterates in this order. A parallel implementation may process Chunks concurrently only where the per-Chunk work is independent of other Chunks' writes in the same sub-step (Directive 7); the result must equal the sequential canonical order.

### REQ-ORD-002: Tie-break Rule

Every argmax, argmin, and "first that satisfies" over entities resolves ties to the lowest EntityID; over Cells to the lowest Cell index; over actions, needs, or table rows to the lowest index. The comparison is on the value first and the identifier second, never on address, insertion time, or thread.

### REQ-ORD-003: Stable Sort

Every sort in the Kernel is stable with the identifier as the final key, so its output is a total order independent of the algorithm. An unstable sort may be used only if the key already includes the identifier as its last component.

### REQ-ORD-004: Reduction Order

A sum, minimum, maximum, or bitwise-OR over many elements is computed as: a sequential fold in canonical order within each Chunk (or Cell Chunk) producing one partial per Chunk, followed by a sequential fold of the partials in ascending Chunk index. Tree reductions, SIMD horizontal reductions that change association, and reductions whose grouping depends on the number of workers are prohibited. Integer addition is associative, so this rule matters for saturating folds and for `i128` overflow checks; it is nevertheless mandatory everywhere so that a future change of element type cannot introduce a Desync.

### REQ-ORD-005: Hashing Order

The byte sequence that any hash over Kernel state consumes is, in order: entity Chunks in ascending index; within a Chunk, the components present in its archetype in the catalog order of DEOS §5.3 (`Position2D`, `EnergyState`, `Lifecycle`, `Genome`, `Needs`, `Perception`, `Memory`, `Decision`, `MemeVector`, `TrustEdges`, `Affiliation`, `InstitutionState`); within a component, its SoA field arrays in declared order, each over ascending Slot; then Cell Chunks in ascending index with fields in the order `energy`, `temperature`, `moisture`, `elevation`, `material_id`, `mutation_bias`; then the global record (`Ledger` of §8.3, then the tick counter). Every multi-byte value is little-endian. How the leaves combine into Chunk Hashes and the Tick Hash is DEOS-RT's (`HASH`).

### REQ-ORD-006: Prohibited Dependencies

No Kernel decision, value, draw, or ordering may depend on: the number of worker threads; wall-clock or CPU time; the numeric value of a pointer or address; iteration order of any hash table or set; uninitialized memory; padding bytes; the platform's endianness (all serialized values are little-endian by rule); the availability of SIMD; or egress state. A code path that consults any of these for anything but diagnostics is non-conformant.

### REQ-ORD-007: Cell Chunk Layout

The Substrate is divided into `ceil(GRID_W · GRID_H / CHUNK_SIZE)` Cell Chunks of `CHUNK_SIZE` consecutive Cells in row-major order (64 at MVS scale, 1,024 at v1.0 scale). Cell Chunk `c` holds Cells `[c·CHUNK_SIZE, (c+1)·CHUNK_SIZE)`. Neighbour reads in sub-steps 2b and 2c cross Cell Chunk boundaries freely because they read only `X⁰`; writes never cross them.

---

## 7. Algorithms & Mathematics

### 7.1 Q32.32 primitives

```c
typedef int64_t fx_t;
typedef __int128 i128;

static inline fx_t fx_sat(i128 v) {
    if (v > (i128)INT64_MAX) { fx_flag_set(FX_FLAG_SAT); return INT64_MAX; }
    if (v < (i128)INT64_MIN) { fx_flag_set(FX_FLAG_SAT); return INT64_MIN; }
    return (fx_t)v;
}
fx_t fx_add(fx_t a, fx_t b) { return fx_sat((i128)a + (i128)b); }
fx_t fx_sub(fx_t a, fx_t b) { return fx_sat((i128)a - (i128)b); }
fx_t fx_mul(fx_t a, fx_t b) { return fx_sat(((i128)a * (i128)b) >> 32); }   /* arithmetic shift */
fx_t fx_div(fx_t a, fx_t b) {
    if (b == 0) { fx_flag_set(FX_FLAG_DIVZERO); return a > 0 ? INT64_MAX : (a < 0 ? INT64_MIN : 0); }
    i128 n = (i128)a << 32;
    i128 q = n / b, r = n - q * b;                 /* C truncates toward zero */
    if (r != 0 && ((r < 0) != (b < 0))) q -= 1;    /* correct to floor */
    return fx_sat(q);
}
```

Worked rounding cases (all in §7.7): `fx_mul(−1 ulp, 0.5) = −1 ulp` (floor of −0.5 ulp), `fx_mul(+1 ulp, 0.5) = 0`, `fx_div(−1, 3) = 0xFFFFFFFFAAAAAAAA` (floor of −1/3), `fx_div(1, 3) = 0x0000000055555555`.

### 7.2 Function tables

All seven tables share REQ-MATH-010's build discipline. `msb(v)` is the index of the highest set bit of a positive `int64_t` (`63 − clz64(v)`). Throughout, `>>` on a signed value is an arithmetic shift.

#### 7.2.1 Table summary

| Table | Entries | Spacing | Argument grid | Index bits / remainder bits | Bytes |
| :--- | ---: | :--- | :--- | :--- | ---: |
| `FX_EXP2_TABLE` | 4,097 | 1/4096 | `2^f`, `f ∈ [0, 1]` | 12 / 20 | 32,776 |
| `FX_LN_TABLE` | 4,097 | 1/4096 | `ln(1 + u)`, `u ∈ [0, 1]` | 12 / 20 | 32,776 |
| `FX_SQRT_TABLE` | 3,073 | 1/1024 | `√m`, `m ∈ [1, 4]` | 12 (0…3071) / 22 | 24,584 |
| `FX_SIN_TABLE` | 1,025 | 1/4096 rotation | `sin(2π·q)`, `q ∈ [0, 1/4]` | 10 / 20 | 8,200 |
| `FX_SIG_TABLE` | 8,193 | 1/256 | `σ(z)`, `z ∈ [−16, 16]` | 13 / 24 | 65,544 |
| `FX_RCP_TABLE` | 4,097 | 1/4096 | `1/(1 + u)`, `u ∈ [0, 1]` | 12 / 20 | 32,776 |

Total 196,656 bytes; every table fits in L2 cache.

#### 7.2.2 `fx_exp` — build rule and algorithm

Build rule: `EXP2[i] = ⌊2^32 · 2^(i/4096)⌋` for `i = 0 … 4096`, computed exactly as the largest integer `m` with `m^4096 ≤ 2^(131072 + i)` (an integer 4096-th root; no transcendental evaluation is involved). `EXP2[0] = FX_ONE`, `EXP2[4096] = 2·FX_ONE` exactly.

```
fx_t fx_exp(fx_t x) {
    if (x >= 22 * FX_ONE)  { fx_flag_set(FX_FLAG_DOMAIN); return FX_MAX; }
    if (x <= -32 * FX_ONE) { fx_flag_set(FX_FLAG_DOMAIN); return 0; }
    fx_t   t   = fx_mul(x, FX_LOG2E);                 /* x · log2(e), floor */
    int64_t n  = t >> 32;                             /* floor: n in [-47, 32) */
    uint32_t f = (uint32_t)(t & 0xFFFFFFFF);          /* fraction of 2^f, in [0,1) */
    uint32_t i = f >> 20, r = f & 0xFFFFF;
    int64_t y  = EXP2[i] + (((EXP2[i+1] - EXP2[i]) * (int64_t)r) >> 20);   /* y in [2^32, 2^33) */
    if (n >= 0) return fx_sat((i128)y << n);          /* saturates when n >= 31 */
    return (-n < 64) ? (y >> -n) : 0;                 /* arithmetic shift, floor toward 0 */
}
```

First eight entries: `0x0000000100000000 0x00000001000B175E 0x0000000100162F39 0x000000010021478E 0x00000001002C605E 0x00000001003779A9 0x000000010042936F 0x00000001004DADB1`.

Error: the linear interpolation error of `2^f` on spacing `h = 2^-12` is at most `h²/8 · max|f''| = 2^-27 · (ln 2)²·2 < 2^-27` relative, plus at most 2 ulp of rounding, scaled by `2^n`; the measured worst case over 300,000 samples is `2^-27.2 · 2^n + 2 ulp`, and REQ-MATH-011 states the bound `2^n · 2^-26 + 2^-31`.

#### 7.2.3 `fx_ln` — build rule and algorithm

Build rule: `L(z) = 2 · Σ_{k=0}^{30} z^(2k+1) / (2k+1)` evaluated exactly in rationals; `LN[j] = ⌊2^32 · L(j / (8192 + j))⌋` for `j = 0 … 4096` (this is `ln(1 + j/4096)` with truncation error below `10^-31`). `LN[0] = 0`; `LN[4096] = FX_LN2`.

```
fx_t fx_ln(fx_t x) {
    if (x <= 0) { fx_flag_set(FX_FLAG_DOMAIN); return FX_MIN; }
    int p = msb(x);                                    /* 0..62 */
    int k = p - 32;                                    /* x = 2^k · m, m in [1,2) */
    int64_t m = (p >= 32) ? (x >> (p - 32)) : (x << (32 - p));   /* raw in [2^32, 2^33) */
    uint32_t u = (uint32_t)(m - FX_ONE);               /* fraction of m, 32 bits */
    uint32_t j = u >> 20, r = u & 0xFFFFF;
    int64_t y = LN[j] + (((LN[j+1] - LN[j]) * (int64_t)r) >> 20);
    return fx_add((int64_t)k * FX_LN2, y);              /* k·ln2 + ln m; |k| <= 32, product < 2^38 */
}
```

First eight entries: `0x0000000000000000 0x00000000000FFF80 0x00000000001FFE00 0x00000000002FFB80 0x00000000003FF801 0x00000000004FF382 0x00000000005FEE04 0x00000000006FE787`.

Error: interpolation `≤ h²/8 = 2^-27`, plus `|k| · 1 ulp` from `FX_LN2` (`≤ 32 ulp`), plus 2 ulp; measured worst case `2^-26.1`; bound `2^-25`.

#### 7.2.4 `fx_sqrt` — build rule and algorithm

Build rule: `SQRT[j] = ⌊2^32 · √(1 + j/1024)⌋ = isqrt(2^54 · (1024 + j))` for `j = 0 … 3072`, an exact integer square root. `SQRT[0] = FX_ONE`, `SQRT[1024] = 0x000000016A09E667`, `SQRT[3072] = 2·FX_ONE`.

```
fx_t fx_sqrt(fx_t x) {
    if (x < 0)  { fx_flag_set(FX_FLAG_DOMAIN); return 0; }
    if (x == 0) return 0;
    int p = msb(x), e = p - 32, k = e >> 1;            /* floor(e/2); x = 2^(2k) · m, m in [1,4) */
    int sh = 2 * k;
    int64_t m = (sh >= 0) ? (x >> sh) : (x << -sh);    /* raw in [2^32, 2^34) */
    uint64_t u = (uint64_t)(m - FX_ONE);               /* [0, 3·2^32) */
    uint32_t j = (uint32_t)(u >> 22), r = (uint32_t)(u & 0x3FFFFF);   /* j in 0..3071 */
    int64_t y = SQRT[j] + (((SQRT[j+1] - SQRT[j]) * (int64_t)r) >> 22);
    return (k >= 0) ? fx_sat((i128)y << k) : (y >> -k);   /* k in [-16, 15]; y << 15 < 2^48 */
}
```

First eight entries: `0x0000000100000000 0x00000001001FFE00 0x00000001003FF801 0x00000001005FEE06 0x00000001007FE00F 0x00000001009FCE1F 0x0000000100BFB835 0x0000000100DF9E55`.

Error: interpolation `≤ h²/8 · max|f''| = 2^-23 · 1/4 = 2^-25` on `m`, measured `2^-25.0 · 2^k + 2 ulp`; bound `2^k · 2^-24 + 2^-31`.

#### 7.2.5 `fx_sin_rot`, `fx_cos_rot` — build rule and algorithm

Build rule: `Π = 4·(4·A(1/5) − A(1/239))` with `A(x) = Σ_{k=0}^{40} (−1)^k x^(2k+1)/(2k+1)` (Machin's formula, exact rationals); `S(x) = Σ_{k=0}^{20} (−1)^k x^(2k+1)/(2k+1)!`; `SIN[i] = ⌊2^32 · S(Π · i / 2048)⌋` for `i = 0 … 1024`. `SIN[0] = 0`; `SIN[1024]` evaluates to exactly `FX_ONE` (the rational exceeds 1 by `1.9 × 10^-35`). The table covers the first quadrant; the other three are derived by symmetry.

```
static int64_t sin_q(uint32_t w) {                      /* w in [0, 2^30] = [0, 1/4] rotation */
    uint32_t i = w >> 20, r = w & 0xFFFFF;
    if (i == 1024) return SIN[1024];
    return SIN[i] + (((SIN[i+1] - SIN[i]) * (int64_t)r) >> 20);
}
fx_t fx_sin_rot(fx_t u) {
    uint32_t f = (uint32_t)((uint64_t)u & 0xFFFFFFFF);  /* fractional rotation; integer part discarded */
    uint32_t q = f >> 30, w = f & 0x3FFFFFFF;
    switch (q) {
        case 0: return  sin_q(w);
        case 1: return  sin_q(0x40000000 - w);
        case 2: return -sin_q(w);
        default: return -sin_q(0x40000000 - w);
    }
}
fx_t fx_cos_rot(fx_t u) { return fx_sin_rot((fx_t)((uint64_t)u + 0x40000000ULL)); }
```

First eight entries: `0x0000000000000000 0x00000000006487EA 0x0000000000C90FC5 0x00000000012D9782 0x0000000001921F0F 0x0000000001F6A65F 0x00000000025B2D61 0x0000000002BFB406`.

Error: spacing `2π/4096` rad gives interpolation `≤ (2π/4096)²/8 = 2.9 × 10^-7`; measured `2^-21.7`; bound `2^-21`.

#### 7.2.6 `fx_logistic` — build rule and algorithm

Build rule: `X(y) = Σ_{k=0}^{96} y^k / k!` (exact rationals; truncation error below `10^-35` for `|y| ≤ 16`); `SIG[i] = ⌊2^32 / (1 + X(16 − i/256))⌋` for `i = 0 … 8192`, i.e. `σ(z_i)` at `z_i = −16 + i/256`. `SIG[4096] = FX_HALF` exactly.

```
fx_t fx_logistic(fx_t z) {
    if (z <= -16 * FX_ONE) return SIG[0];
    if (z >=  16 * FX_ONE) return SIG[8192];
    uint64_t raw = (uint64_t)(z + 16 * FX_ONE);         /* [0, 32·2^32) */
    uint32_t i = (uint32_t)(raw >> 24), r = (uint32_t)(raw & 0xFFFFFF);
    return SIG[i] + (((SIG[i+1] - SIG[i]) * (int64_t)r) >> 24);
}
```

First eight entries: `0x00000000000001E3 0x00000000000001E5 0x00000000000001E7 0x00000000000001E9 0x00000000000001EA 0x00000000000001EC 0x00000000000001EE 0x00000000000001F0`.

Error: `max|σ''| = 0.0962` gives interpolation `≤ (1/256)²/8 · 0.0962 = 1.84 × 10^-7`; measured `2^-22.4`; bound `2^-22`.

#### 7.2.7 `fx_rcp` — build rule and algorithm

Build rule: `RCP[j] = ⌊2^44 / (4096 + j)⌋` for `j = 0 … 4096` (exact integer division; equals `⌊2^32 / (1 + j/4096)⌋`). `RCP[0] = FX_ONE`, `RCP[4096] = FX_HALF`.

```
fx_t fx_rcp(fx_t x) {
    if (x == 0) { fx_flag_set(FX_FLAG_DIVZERO); return FX_MAX; }
    int neg = x < 0;
    fx_t a = neg ? fx_abs(x) : x;                       /* fx_abs(FX_MIN) = FX_MAX */
    int p = msb(a), e = p - 32;                          /* a = 2^e · m, m in [1,2) */
    int64_t m = (e >= 0) ? (a >> e) : (a << -e);
    uint32_t u = (uint32_t)(m - FX_ONE), j = u >> 20, r = u & 0xFFFFF;
    int64_t y = RCP[j] + (((RCP[j+1] - RCP[j]) * (int64_t)r) >> 20);   /* 1/m in (2^31, 2^32] */
    fx_t res = (e >= 0) ? (y >> e) : fx_sat((i128)y << -e);
    return neg ? fx_neg(res) : res;
}
```

First eight entries: `0x0000000100000000 0x00000000FFF000FF 0x00000000FFE003FF 0x00000000FFD008FE 0x00000000FFC00FFC 0x00000000FFB018F8 0x00000000FFA023F2 0x00000000FF9030EA`.

Error: interpolation `≤ h²/8 · 2 = 2^-27` on `m`; measured `2^-26.0 · 2^-e + 2 ulp`; bound `2^-e · 2^-25 + 2^-31`.

#### 7.2.8 Table digests

BLAKE3-256 over each table's entries serialized as little-endian `int64_t`, in index order:

| Table | Last entry | BLAKE3-256 |
| :--- | :--- | :--- |
| `FX_EXP2_TABLE` | `0x0000000200000000` | `fe2af48460df1eca80726613c0ea870db16dc72073abf3e74cd0e1e52af49eaf` |
| `FX_LN_TABLE` | `0x00000000B17217F7` | `f0cabe79ed334ef36dbfd15e4eecc69fac6d0a93f23fff6384c744ba663d148e` |
| `FX_SQRT_TABLE` | `0x0000000200000000` | `93d84093f7e669bf5ebd4d5af1e7f7b02a2612b20700dd9d479e27e9231b42ca` |
| `FX_SIN_TABLE` | `0x0000000100000000` | `1543ec8bdd644575c5355b74ddf2f7c0f1b0fbfd4a7e9b1aaa5a27594ad7bfcf` |
| `FX_SIG_TABLE` | `0x00000000FFFFFE1C` | `5ffa7e140d0e65109704a87e96ac52b050d7143917fc1de54ac95394125d8c9d` |
| `FX_RCP_TABLE` | `0x0000000080000000` | `b2dce8d2ac3e4ae3a5f835b2f4ab1b4d59afbd99d88a38b8d5106cb6ad2cf321` |

The generator was a Python 3 script using `fractions.Fraction`, `math.isqrt`, integer `pow`, and the `blake3` package; every value above is reproducible from the build rules alone.

### 7.3 Universal laws in Stage 2

#### 7.3.1 Ledger totals

```
E_total = Σ_cells (energy + temperature)                 -- i128, canonical Cell order, per Cell Chunk partials
        + Σ_entities EnergyState.current                  -- alive entities, canonical entity order
        + Σ_institutions InstitutionState.pooled_energy   -- canonical entity order
        + heat_sink                                       -- the world's thermal account (REQ-LAW-005)
```

Partials are combined in ascending Chunk index (REQ-ORD-004): entity Chunk partials first, then Cell Chunk partials. Stage 6 computes `E_total(t+1)` from the buffer about to be hashed, evaluates REQ-LAW-004 rule 5, then stores `e_total = E_total(t+1)`, `m_total = M_total(t+1)`, and `e_cat = e_sun = e_rad = s_tick = m_cat = 0` for the next tick. `M_total` is `Σ_cells moisture` (Cell Chunk partials, ascending) plus `atmosphere`.

#### 7.3.2 The transfer primitive

Every module moves energy only through this primitive (REQ-LAW-004, REQ-LAW-005):

```
xfer(src, dst, cap_dst, a, heat_cell, taxed):          -- a > 0, all fx_t
    src   -= a                                          -- debit; src >= a is the caller's precondition
    heat   = taxed ? max(fx_mul(a, FX_ENTROPY_TAX), 1) : 0
    give   = a - heat                                   -- last part by subtraction
    room   = cap_dst - dst
    if give > room: heat += give - room; give = room    -- spillover is heat, by subtraction
    dst   += give
    temperature[heat_cell] += heat
    s_tick += heat
```

`src`, `dst`, `temperature[heat_cell]` are all accounts; the six writes happen in the same stage and the same Chunk pass; `Σ(debits) == Σ(credits)` holds exactly by construction.

#### 7.3.3 Heat diffusion (sub-step 2b)

For Cell `c` with material `m_c` and neighbours in the fixed order N `(x, y−1)`, W `(x−1, y)`, E `(x+1, y)`, S `(x, y+1)`, omitting neighbours outside the grid:

```
kappa(c) = fx_mul(FX_HEAT_KAPPA, COND[m_c] + (fx_min(M⁰_c, FX_MOIST_CAP) >> 10))   -- <= 2^-3
flux(c, n):
    ke = fx_min(kappa(c), kappa(n))                       -- symmetric: both endpoints compute the same ke
    d  = T⁰_n - T⁰_c                                      -- no overflow: both in [0, 2^30]
    return d >= 0 ? fx_mul(ke, d) : -fx_mul(ke, -d)       -- magnitude floored, sign applied after
T¹_c = T⁰_c + flux(c,N) + flux(c,W) + flux(c,E) + flux(c,S)   -- plain int64 adds in this order
```

Both endpoints of an edge compute `flux` from the same two `X⁰` values with the same integer formula, so `flux(c, n) == −flux(n, c)` bit-for-bit and `Σ T¹ == Σ T⁰` exactly; each Cell writes only its own slot (Directive 7). Positivity: outflow `≤ Σ_e ke·T⁰_c ≤ 4 · 2^-3 · T⁰_c = T⁰_c / 2`, and flooring the magnitude only reduces outflow, so `T¹_c ≥ T⁰_c / 2 ≥ 0`. Stability: with `ke ≤ 2^-3` every `T¹_c` is a convex combination of `T⁰` values; the explicit 4-neighbour scheme's bound is `ke ≤ 1/4`.

#### 7.3.4 Moisture diffusion and runoff (sub-step 2c)

```
flux_m(c, n):
    d  = M⁰_n - M⁰_c
    fd = d >= 0 ? fx_mul(FX_MOIST_KAPPA, d) : -fx_mul(FX_MOIST_KAPPA, -d)
    if      elev⁰_c > elev⁰_n: fr = -fx_min(fx_mul(FX_RUNOFF, elev⁰_c - elev⁰_n), M⁰_c >> 3)
    else if elev⁰_n > elev⁰_c: fr =  fx_min(fx_mul(FX_RUNOFF, elev⁰_n - elev⁰_c), M⁰_n >> 3)
    else                       fr = 0
    return fd + fr
M¹_c = M⁰_c + flux_m(c,N) + flux_m(c,W) + flux_m(c,E) + flux_m(c,S)
```

Outflow `≤ 4·(M⁰_c/16) + 4·(M⁰_c/8) = 3·M⁰_c/4`, so `M¹_c ≥ M⁰_c/4 ≥ 0`. Antisymmetry and exact conservation hold as in §7.3.3.

#### 7.3.5 Precipitation (2d) and evaporation (2e)

```
2d (once, before the Cell pass):  rain_total = (atmosphere⁰ * FX_PRECIP_COEFF) >> 32     -- i128 floor
                                  rain_cell  = rain_total / (GRID_W * GRID_H)            -- i128 floor, fits int64
    per Cell:                     M¹_c += rain_cell
2e per Cell:                      rate = fx_min(fx_mul(T¹_c, FX_EVAP_COEFF), FX_EVAP_MAX)
                                  evap = fx_mul(M¹_c, rate);  M¹_c -= evap;  evap_partial[chunk] += evap
end of Stage 2:                   atmosphere¹ = atmosphere⁰ - rain_cell * (GRID_W * GRID_H) + Σ_chunks evap_partial
```

`rate ≤ 1/4` so `M¹_c ≥ 0`. `rain_cell` is identical for every Cell; the division remainder stays in the reservoir, which is why the moisture ledger `Σ M + atmosphere` is exact.

#### 7.3.6 Material transition (2a), decay (2f), radiation (2g), bias decay (2h)

```
2a: if m_c == WATER and T⁰_c <  FX_FREEZE_T: m¹_c = ICE
    if m_c == ICE   and T⁰_c >= FX_THAW_T:   m¹_c = WATER
    if m_c >= 4: Ledger.fault = 2
2f: decay = fx_mul(E_c, DECAY[m¹_c]);  E¹_c = E_c - decay;  T¹_c += decay;  s_partial[chunk] += decay
2g: rad   = fx_mul(T¹_c, FX_RAD_COEFF); T¹_c -= rad;        rad_partial[chunk] += rad
2h: d = fx_mul(FX_ONE - b_c, FX_BIAS_DECAY); if d == 0 and b_c != FX_ONE: d = (b_c > FX_ONE) ? -1 : 1;  b¹_c = b_c + d
2i: sun = fx_mul(FX_INSOLATION, LAT[y]); room = FX_CELL_ENERGY_CAP - E¹_c; give = fx_min(sun, room);
    E¹_c += give;  T¹_c += sun - give;  sun_partial[chunk] += sun          -- REQ-LAW-013; spillover is heat by subtraction
```

Sub-step 2j folds `s_partial`, `rad_partial`, `evap_partial`, `sun_partial`, and the Cell energy/temperature/moisture partials in ascending Cell Chunk index into `s_tick`, `e_rad`, `atmosphere¹`, `e_sun`, and the Stage 6 totals, then radiates the heat sink: `rad_sink = fx_mul((fx_t)heat_sink, FX_RAD_COEFF); heat_sink −= rad_sink; e_rad += rad_sink`. The heat sink is credited by DEOS-RT step 6.4a with the tick's Chunk-ledger sums (`dissipated + dropped`, DEOS-ECS REQ-MUT-009) before `E_total(t+1)` is computed.

Player-facing consequence: every Stage 2 rule is a handful of integer operations per Cell with a constant the player can perturb through the Climate and Resource families, which is what makes the Substrate a thing to play with rather than a backdrop.

### 7.4 Fixed-tick integration

#### 7.4.1 Stage 2 sub-step table (REQ-TICK-003)

| # | Sub-step | Reads | Writes | Neighbour access |
| :--- | :--- | :--- | :--- | :--- |
| 2a | material transition | `T⁰`, `material⁰` | `material¹` | none |
| 2b | heat diffusion | `T⁰`, `M⁰`, `material⁰` | `T¹` | 4-neighbour, `X⁰` only |
| 2c | moisture diffusion + runoff | `M⁰`, `elev⁰` | `M¹` | 4-neighbour, `X⁰` only |
| 2d | precipitation | `atmosphere⁰` | `M¹` | none |
| 2e | evaporation | `T¹`, `M¹` | `M¹`, `evap_partial` | none |
| 2f | material decay | `E⁰`, `material¹` | `E¹`, `T¹`, `s_partial` | none |
| 2g | radiation | `T¹` | `T¹`, `rad_partial` | none |
| 2h | `mutation_bias` decay | `b⁰` | `b¹` | none |
| 2i | insolation | `E¹`, `LAT` | `E¹`, `T¹`, `sun_partial` | none |
| 2j | ledger partials | all `X¹` | Chunk partials → `Ledger` | none |

A barrier follows each row. Rows 2a–2i are embarrassingly parallel over Cell Chunks; row 2j's cross-Chunk fold is sequential in ascending Cell Chunk index.

#### 7.4.2 Why Acceleration equals attended stepping

The state after `n` calls is `step^n(S_0, log)`. The Host's speed level, `TICK_RATE_HZ`, and whether a renderer reads the read buffer between calls are not arguments of `step`; the only difference between attended play and Acceleration is the real time elapsed between calls, which no Kernel value observes (REQ-TICK-001, REQ-ORD-006). The Tick Hash sequence is therefore identical, and `MIN_ACCELERATION` is a throughput promise, not a semantic mode.

### 7.5 PRNG

#### 7.5.1 SystemID assignment

| SystemID | Name | Stage | Owner of draw rules |
| :--- | :--- | :--- | :--- |
| 0 | `WORLDGEN` | tick 0 | DEOS-RT (world generation), DEOS-MVS |
| 1 | `SUBSTRATE` | 1 (Cosmic expansion), 2 | Core (no draws in v0.1.0), DEOS-RT/DEOS-PLAY for expansion |
| 2 | `BIOLOGY` | 3 | DEOS-PROTO |
| 3 | `COGNITION` | 4 | DEOS-PROTO |
| 4 | `SOCIETY` | 5 | DEOS-PROTO |
| 5–15 | reserved | — | Core |
| 16–255 | assignable | — | DEOS-PROTO and DEOS-RT, by table in their documents |

#### 7.5.2 Jump-ahead and the stride constants

The affine map for advancing a Stream by `delta` draws is computed by the PCG reference algorithm:

```
advance_affine(delta, inc):                      -- returns (A, C): state' = A·state + C  mod 2^128
    cur_mult = PCG_MULT; cur_plus = inc; acc_mult = 1; acc_plus = 0
    while delta > 0:
        if delta & 1: acc_mult = acc_mult·cur_mult;  acc_plus = acc_plus·cur_mult + cur_plus
        cur_plus = (cur_mult + 1)·cur_plus;  cur_mult = cur_mult·cur_mult;  delta >>= 1
    return (acc_mult, acc_plus)
```

With `inc = 1` the returned `acc_plus` is the geometric sum `G(delta)`, and for any `inc` the map is `A(delta)·state + inc·G(delta)`. Published constants:

| delta | `A` | `G` |
| :--- | :--- | :--- |
| `2^32` (`A_STRIDE`, `G_STRIDE`) | `0x433BEF4314F16A9453CD8FBC00000001` | `0xD74683C909AF5D98B461C97F00000000` |
| `2^16` (for a unit test that can also step 65,536 times) | `0x0798A3D8B10DC72E60121CD58FBC0001` | `0x5D57B94AFAF08E7663A72983C97F0000` |

Check: from the raw Stream of §7.5.4, `A(2^16)·state + inc·G(2^16) = 0xE5EF0697F4A3CD92DA0739C190AECDEF`, which equals the state after 65,536 single steps.

#### 7.5.3 Weighted choice pseudocode

```
weighted(stream, w[0..N)):
    t = 0;  for k in 0..N-1: t += w[k]                     -- uint64, caller guarantees no wrap
    r = bounded(stream, t == 0 ? 1 : t)
    acc = 0
    for k in 0..N-1: acc += w[k]; if r < acc: return k
    return 0
```

#### 7.5.4 Raw generator vectors

Stream loaded directly (no seeding steps): `state = 0x0123456789ABCDEF0123456789ABCDEF`, `inc = 0xDA3E39CB94B95BDB1F52DB0F81D7DA45`.

| Draw | Output |
| :--- | :--- |
| `next_u64()` #1 | `0xB8AA3AC5CEA8F9A1` |
| `next_u64()` #2 | `0xC881A9F04427AD36` |
| `next_u64()` #3 | `0x4ADA3607DCBDC244` |
| `next_u64()` #4 | `0xD2B7D0E2BF07CC04` |
| state after 4 draws | `0x2EBBED56813B079E903CF8AEBF5B210B` |
| `uniform_q32()` first (fresh Stream) | `0x00000000B8AA3AC5` |
| `bernoulli(0.25)` first (fresh) | false |
| `bounded(10)` first (fresh; `threshold = 6`) | 3 |
| `bounded(6)` ×4 (fresh; `threshold = 4`) | 1, 4, 4, 0 |
| `bounded(1000000007)` ×4 (fresh; `threshold = 582344008`) | 124112474, 845847153, 369904693, 702222510 |
| `weighted([1.0, 2.0, 3.0])` first (fresh) | 2 |

#### 7.5.5 Derived Stream vectors

Master Seed `0x0123456789ABCDEF`, SystemID 2 (`BIOLOGY`), Tick 0, Chunk 0. Exact bytes hashed:

```
seed_input  (20 bytes) = efcdab8967452301 02000000 0000000000000000
Seed_system (BLAKE3)   = f0829596808d082ac94ff2ba0fe340a203eb680de3dc5155f124b528f5dc2175
chunk_input (4 bytes)  = 00000000
StreamKey (keyed)      = 2f4509e11f70418a3f2c6c4c91b12062d5a942700880c36b048ab6d630e36f41
state = 0x6220B1914C6C2C3F8A41701FE109452F      inc = 0x416FE330D6B68A046BC380087042A9D5
```

First four outputs: `0xA8D1190586EE5928 0xBDA86B234ADE2BCC 0x99C51CC3FD1D2410 0xDFA08232A6208E12`. These were computed with the `blake3` Python package (keyed mode for the second hash) and the pure-integer PCG64 of §7.5.4.

#### 7.5.6 Substream vector

Slot 1 of the Stream above: `base_1 = A_STRIDE·state + inc·G_STRIDE mod 2^128 = 0x7AD9EFBB1B60C1DBC477FD4EE109452F`; its first two outputs are `0x1CDF852E1DCDA747 0xF075E91FA83966F6`.

### 7.6 Ordering in practice

```
for chunk in 0 .. n_chunks-1:                       -- may run on any worker
    stream = derive(master, system, tick, chunk)
    base = stream.state
    for slot in 0 .. CHUNK_SIZE-1:                  -- ascending; base advances by 2^32 draws per slot
        sub = { base, stream.inc }
        process(entity(chunk, slot), &sub)          -- writes own slot only; cross-entity writes go to the command buffer
        base = A_STRIDE*base + stream.inc*G_STRIDE
    partial[chunk] = fold over slots                -- sequential
barrier
for chunk in 0 .. n_chunks-1: total = fold(total, partial[chunk])   -- sequential, ascending
```

### 7.7 Conformance vectors (REQ-MATH-017)

All values are raw hexadecimal Q32.32 unless marked as integers.

| Operation | Input A | Input B | Expected | Note |
| :--- | :--- | :--- | :--- | :--- |
| add | `0x0000000100000000` | `0x0000000080000000` | `0x0000000180000000` | 1 + 0.5 |
| add | `0x7FFFFFFFFFFFFFFF` | `0x0000000100000000` | `0x7FFFFFFFFFFFFFFF` | saturates |
| add | `0x8000000000000000` | `0xFFFFFFFFFFFFFFFF` | `0x8000000000000000` | saturates |
| sub | `0x0000000100000000` | `0x0000000180000000` | `0xFFFFFFFF80000000` | 1 − 1.5 |
| sub | `0x8000000000000000` | `0x0000000100000000` | `0x8000000000000000` | saturates |
| sub | `0x0000000000000000` | `0x8000000000000000` | `0x7FFFFFFFFFFFFFFF` | saturates |
| mul | `0x0000000180000000` | `0xFFFFFFFDC0000000` | `0xFFFFFFFCA0000000` | 1.5 × −2.25 = −3.375 |
| mul | `0x0000000055555555` | `0x0000000300000000` | `0x00000000FFFFFFFF` | floor |
| mul | `0xFFFFFFFFFFFFFFFF` | `0x0000000080000000` | `0xFFFFFFFFFFFFFFFF` | floor of −0.5 ulp |
| mul | `0x0000000000000001` | `0x0000000080000000` | `0x0000000000000000` | floor of +0.5 ulp |
| mul | `0x0010000000000000` | `0x0010000000000000` | `0x7FFFFFFFFFFFFFFF` | 2^20 × 2^20 saturates |
| mul | `0x8000000000000000` | `0xFFFFFFFF00000000` | `0x7FFFFFFFFFFFFFFF` | saturates |
| div | `0x0000000100000000` | `0x0000000300000000` | `0x0000000055555555` | 1/3 |
| div | `0xFFFFFFFF00000000` | `0x0000000300000000` | `0xFFFFFFFFAAAAAAAA` | −1/3, floor |
| div | `0x0000000780000000` | `0x0000000280000000` | `0x0000000300000000` | 7.5 / 2.5 |
| div | `0x0000000100000000` | `0x0000000000000000` | `0x7FFFFFFFFFFFFFFF` | divide by zero |
| div | `0x0000000100000000` | `0x0000000000000001` | `0x7FFFFFFFFFFFFFFF` | saturates |
| abs | `0x8000000000000000` | — | `0x7FFFFFFFFFFFFFFF` | saturates |
| neg | `0x8000000000000000` | — | `0x7FFFFFFFFFFFFFFF` | saturates |
| to_int_floor | `0xFFFFFFFF80000000` | — | −1 (integer) | |
| to_int_round | `0xFFFFFFFF80000000` | — | 0 (integer) | half toward +∞ |
| to_int_round | `0x0000000080000000` | — | 1 (integer) | |
| sqrt | `0x0000000100000000` | — | `0x0000000100000000` | |
| sqrt | `0x0000000200000000` | — | `0x000000016A09E667` | |
| sqrt | `0x0000000300000000` | — | `0x00000001BB67AE85` | |
| sqrt | `0x0000000080000000` | — | `0x00000000B504F333` | |
| sqrt | `0x0000000A00000000` | — | `0x00000003298B075A` | |
| sqrt | `0x00000123456789AB` | — | `0x0000001111110EF0` | |
| exp | `0x0000000000000000` | — | `0x0000000100000000` | |
| exp | `0x0000000100000000` | — | `0x00000002B7E15180` | e, 30 ulp above `FX_E` |
| exp | `0xFFFFFFFF00000000` | — | `0x000000005E2D58DD` | |
| exp | `0x00000000B17217F7` | — | `0x00000001FFFFFFFD` | exp(ln 2) |
| exp | `0x0000000A00000000` | — | `0x0000560A773FC000` | |
| exp | `0xFFFFFFFB00000000` | — | `0x0000000001B993FE` | |
| exp | `0x0000001600000000` | — | `0x7FFFFFFFFFFFFFFF` | domain clamp |
| ln | `0x0000000100000000` | — | `0x0000000000000000` | |
| ln | `0x0000000200000000` | — | `0x00000000B17217F7` | |
| ln | `0x0000000A00000000` | — | `0x000000024D763774` | |
| ln | `0x0000000080000000` | — | `0xFFFFFFFF4E8DE809` | |
| ln | `0x0000000000000000` | — | `0x8000000000000000` | domain |
| logistic | `0x0000000000000000` | — | `0x0000000080000000` | |
| logistic | `0x0000000100000000` | — | `0x00000000BB26A7AE` | |
| logistic | `0xFFFFFFFE00000000` | — | `0x000000001E84152B` | |
| logistic | `0x0000000380000000` | — | `0x00000000F87EFE5F` | |
| logistic | `0x0000001400000000` | — | `0x00000000FFFFFE1C` | clamp |
| logistic | `0xFFFFFFF000000000` | — | `0x00000000000001E3` | |
| rcp | `0x0000000200000000` | — | `0x0000000080000000` | |
| rcp | `0x0000000300000000` | — | `0x0000000055555555` | |
| rcp | `0x0000000040000000` | — | `0x0000000400000000` | |
| rcp | `0xFFFFFFF900000000` | — | `0xFFFFFFFFDB6DB6DC` | −1/7 |
| rcp | `0x0000000000000000` | — | `0x7FFFFFFFFFFFFFFF` | divide by zero |
| sin_rot | `0x0000000000000000` | — | `0x0000000000000000` | |
| sin_rot | `0x0000000040000000` | — | `0x0000000100000000` | quarter rotation |
| sin_rot | `0x0000000080000000` | — | `0x0000000000000000` | half rotation |
| sin_rot | `0x00000000C0000000` | — | `0xFFFFFFFF00000000` | |
| sin_rot | `0x0000000010000000` | — | `0x0000000061F78A9A` | 1/16 rotation |
| sin_rot | `0x00000000AB000000` | — | `0xFFFFFFFF2141FA9D` | |
| cos_rot | `0x0000000000000000` | — | `0x0000000100000000` | |
| cos_rot | `0x0000000010000000` | — | `0x00000000EC835E79` | |
| bias_decay | `0x0000000400000000` | — | `0x00000003FFD00000` | one tick from 4.0 |
| bias_decay | `0x0000000040000000` | — | `0x00000000400C0000` | one tick from 0.25 |
| bias_decay | `0x0000000100000005` | — | `0x0000000100000004` | minimum step |
| entropy_tax | `0x0000006400000000` | — | heat `0x0000000190000000`, delivered `0x0000006270000000` | 100.0 transferred |
| entropy_tax | `0x0000000000000005` | — | heat `0x0000000000000001`, delivered `0x0000000000000004` | minimum heat |
| bounded(10) | Stream of §7.5.4 | — | 3 (integer) | first call |

---

## 8. Data Structures

### 8.1 Arithmetic flags (per worker)

```c
typedef uint32_t fx_flags_t;               /* per worker; cleared at tick start */
#define FX_FLAG_SAT      0x1u              /* a saturating op saturated */
#define FX_FLAG_DIVZERO  0x2u              /* fx_div / fx_rcp by zero */
#define FX_FLAG_DOMAIN   0x4u              /* fx_ln <= 0, fx_sqrt < 0, fx_exp outside [-32, 22) */
```

Combined into `fx_flags_tick` (`uint32_t`) at the Stage 6 barrier by OR in ascending Chunk index; emitted, never hashed.

### 8.2 Stream and 128-bit integer

```c
typedef struct { uint64_t lo; int64_t hi; } i128_t;      /* 16 bytes, little-endian pair */
typedef struct {                                         /* 32 bytes */
    uint64_t state_lo;   /* offset 0  */
    uint64_t state_hi;   /* offset 8  */
    uint64_t inc_lo;     /* offset 16 */  /* bit 0 is always 1 */
    uint64_t inc_hi;     /* offset 24 */
} PcgStream;
```

### 8.3 Ledger (global record, hashed last per REQ-ORD-005)

```c
typedef struct {                 /* 176 bytes; every field Q32.32-scaled i128 unless noted */
    i128_t e_total;              /* offset 0   E_total at the last committed tick */
    i128_t e_cat;                /* offset 16  this tick's Catalyst credits minus debits (Stage 1) */
    i128_t e_rad;                /* offset 32  this tick's radiant debits (sub-step 2g) */
    i128_t s_tick;               /* offset 48  this tick's heat credits */
    i128_t s_total;              /* offset 64  cumulative heat credits since tick 0; monotone */
    i128_t atmosphere;           /* offset 80  moisture reservoir */
    i128_t m_cat;                /* offset 96  this tick's Catalyst moisture credits minus debits */
    i128_t m_total;              /* offset 112 M_total at the last committed tick */
    i128_t e_sun;                /* offset 128 this tick's insolation credits (sub-step 2i, REQ-LAW-013) */
    i128_t heat_sink;            /* offset 144 the world's thermal account: barrier-side entropy tax and own-write losses (REQ-LAW-005) */
    uint32_t fault;              /* offset 160 0 none · 1 LEDGER_MISMATCH · 2 INVALID_MATERIAL · 3 MOISTURE_MISMATCH */
    uint32_t pad0;               /* offset 164 zero */
    uint64_t pad1;               /* offset 168 zero */
} Ledger;
```

### 8.4 Seed derivation input

```c
typedef struct {                 /* 20 bytes, packed, serialized little-endian in this order */
    uint64_t master_seed;        /* offset 0  */
    uint32_t system_id;          /* offset 8  §7.5.1 */
    uint64_t tick;               /* offset 12 */
} SeedInput;
typedef struct { uint32_t chunk_index; } ChunkInput;      /* 4 bytes */
```

### 8.5 Substrate fields and material table

```c
#define N_CELLS (GRID_W * GRID_H)
typedef struct {                 /* SoA; each array 64-byte aligned; index = y*GRID_W + x */
    int64_t  energy[N_CELLS];        /* Q32.32, [0, FX_CELL_ENERGY_CAP] */
    int64_t  temperature[N_CELLS];   /* Q32.32 thermal energy, >= 0 */
    int64_t  moisture[N_CELLS];      /* Q32.32, >= 0 */
    int64_t  elevation[N_CELLS];     /* Q32.32, [0, FX_ELEV_MAX] */
    uint8_t  material_id[N_CELLS];   /* 0..3; array padded to a 64-byte multiple */
    int64_t  mutation_bias[N_CELLS]; /* Q32.32, [0.25, 4.0], default FX_ONE */
} SubstrateFields;

typedef struct {                 /* 16 bytes */
    int64_t cond;                /* Q32.32 conductivity multiplier */
    int64_t decay;               /* Q32.32 per-tick energy decay rate */
} MaterialRow;
```

| id | Name | `COND` | `DECAY` | Transition |
| :--- | :--- | :--- | :--- | :--- |
| 0 | WATER | 0.75 (`0x00000000C0000000`) | 2^-12 (`0x0000000000100000`) | → ICE when `T⁰ < FX_FREEZE_T` |
| 1 | SOIL | 0.50 (`0x0000000080000000`) | 2^-14 (`0x0000000000040000`) | none |
| 2 | ROCK | 0.25 (`0x0000000040000000`) | 2^-16 (`0x0000000000010000`) | none |
| 3 | ICE | 0.50 (`0x0000000080000000`) | 2^-18 (`0x0000000000004000`) | → WATER when `T⁰ ≥ FX_THAW_T` |

### 8.6 Core constants (registry of this module)

| Constant | Value | Raw | Requirement |
| :--- | :--- | :--- | :--- |
| `FX_ENTROPY_TAX` | 2^-6 | `0x0000000004000000` | REQ-LAW-005 |
| `FX_RAD_COEFF` | 2^-10 | `0x0000000000400000` | REQ-LAW-006 |
| `FX_HEAT_KAPPA` | 2^-3 | `0x0000000020000000` | REQ-LAW-007 |
| `FX_MOIST_KAPPA` | 2^-4 | `0x0000000010000000` | REQ-LAW-008 |
| `FX_RUNOFF` | 2^-6 | `0x0000000004000000` | REQ-LAW-008 |
| `FX_EVAP_COEFF` | 2^-16 | `0x0000000000010000` | REQ-LAW-009 |
| `FX_EVAP_MAX` | 2^-2 | `0x0000000040000000` | REQ-LAW-009 |
| `FX_PRECIP_COEFF` | 2^-8 | `0x0000000001000000` | REQ-LAW-009 |
| `FX_MOIST_CAP` | 256.0 | `0x0000010000000000` | REQ-LAW-009 |
| `FX_FREEZE_T` | 2.0 | `0x0000000200000000` | REQ-LAW-010 |
| `FX_THAW_T` | 6.0 | `0x0000000600000000` | REQ-LAW-010 |
| `FX_BIAS_DECAY` | 2^-12 | `0x0000000000100000` | REQ-LAW-011 |
| `FX_INSOLATION` | 2^-7 | `0x0000000002000000` | REQ-LAW-013 |
| `FX_CELL_ENERGY_CAP` | 2^20 | `0x0000100000000000` | REQ-LAW-012 |
| `FX_ELEV_MAX` | 4096.0 | `0x0000100000000000` | REQ-LAW-012 |
| `FX_WORLD_ENERGY_MAX` | 2^30 | `0x4000000000000000` | REQ-LAW-012 |
| `FX_WORLD_MOISTURE_MAX` | 2^30 | `0x4000000000000000` | REQ-LAW-012 |
| `PCG_MULT` | — | `0x2360ED051FC65DA44385DF649FCCF645` | REQ-PRNG-001 |
| `A_STRIDE`, `G_STRIDE` | — | §7.5.2 | REQ-PRNG-003 |
| `SUBSTREAM_STRIDE` | 2^32 draws | — | REQ-PRNG-003 |

---

## 9. Subsystem Interfaces

All functions are pure with respect to Kernel state except for the per-worker `fx_flags` and the explicit output arguments. Names are binding for the C ABI DEOS-RT exposes; other languages keep the names and semantics.

```c
/* Arithmetic (REQ-MATH-005 … 008) */
fx_t fx_add(fx_t a, fx_t b);      fx_t fx_sub(fx_t a, fx_t b);
fx_t fx_mul(fx_t a, fx_t b);      fx_t fx_div(fx_t a, fx_t b);
fx_t fx_abs(fx_t a);              fx_t fx_neg(fx_t a);
fx_t fx_min(fx_t a, fx_t b);      fx_t fx_max(fx_t a, fx_t b);      fx_t fx_clamp(fx_t x, fx_t lo, fx_t hi);
fx_t fx_from_int(int32_t i);      fx_t fx_from_int64(int64_t i);
int32_t fx_to_int_floor(fx_t a);  int32_t fx_to_int_round(fx_t a);
fx_t fx_floor(fx_t a);            fx_t fx_frac(fx_t a);
fx_t fx_shl(fx_t a, unsigned n);  fx_t fx_shr(fx_t a, unsigned n);
fx_flags_t fx_flags_get(void);    void fx_flags_clear(void);         void fx_flag_set(fx_flags_t f);

/* Tables (REQ-MATH-010 … 016) */
void fx_tables_init(void);        /* builds or loads the six tables; verifies §7.2.8 digests; before tick 0 */
fx_t fx_exp(fx_t x);  fx_t fx_ln(fx_t x);  fx_t fx_sqrt(fx_t x);
fx_t fx_sin_rot(fx_t u);  fx_t fx_cos_rot(fx_t u);  fx_t fx_logistic(fx_t z);  fx_t fx_rcp(fx_t x);

/* PRNG (REQ-PRNG-001 … 004) */
void     prng_derive(uint64_t master_seed, uint32_t system_id, uint64_t tick, uint32_t chunk, PcgStream *out);
void     prng_substream_next(PcgStream *base_in_out);         /* base <- A_STRIDE*base + inc*G_STRIDE */
void     prng_advance(PcgStream *s, uint64_t delta);          /* §7.5.2 */
uint64_t prng_next_u64(PcgStream *s);
uint64_t prng_bounded(PcgStream *s, uint64_t n);
fx_t     prng_uniform_q32(PcgStream *s);
int      prng_bernoulli(PcgStream *s, fx_t p);
uint32_t prng_weighted(PcgStream *s, const fx_t *w, uint32_t n);

/* Ledger and Substrate (REQ-LAW-004 … 012, REQ-TICK-003) */
void ledger_xfer(fx_t *src, fx_t *dst, fx_t cap_dst, fx_t amount, int64_t *heat_cell_temperature, i128_t *s_partial, int taxed);
void ledger_catalyst_energy(Ledger *l, fx_t *account, fx_t cap, fx_t delta, int64_t *heat_cell_temperature);  /* Stage 1 use; records e_cat */
void ledger_catalyst_moisture(Ledger *l, int64_t *moisture, fx_t delta);                                     /* Stage 1 use; records m_cat */
void substrate_stage2(const SubstrateFields *x0, SubstrateFields *x1, Ledger *l, uint32_t cell_chunk);       /* sub-steps 2a–2i for one Cell Chunk; called per sub-step by DEOS-RT's dispatcher */
void substrate_stage2_fold(Ledger *l, uint32_t n_cell_chunks);                                               /* sub-step 2j */
int  ledger_stage6_check(Ledger *l, const i128_t *chunk_partials, uint32_t n_chunks);                       /* returns fault code */
```

Obligations on other modules, stated once here and referenced by them:

| Module | Obligation |
| :--- | :--- |
| DEOS-ECS (`MUT`) | command-buffer resolution preserves REQ-ORD-001 order and REQ-LAW-004 pairing (a transfer command carries both accounts) |
| DEOS-RT (`LOOP`, `THR`, `HASH`, `SNAP`) | dispatches Stage 2 per §7.4.1 with barriers; combines partials per REQ-ORD-004; feeds hashes per REQ-ORD-005; performs the Stage 6 check; handles `Ledger.fault`; rejects Catalyst writes that violate REQ-LAW-012; derives Streams per REQ-PRNG-002 |
| DEOS-PROTO (`COG`, `SOC`, `XL`) | every energy movement is a DEOS-ECS Command (which applies REQ-LAW-005 at the barrier) or an own-write loss booked to the Chunk ledger; utility sums per REQ-MATH-003; draws per REQ-PRNG-005; death and dissolution transfers per REQ-LAW-004 rule 4 |
| DEOS-PLAY (`CAT`) | Catalyst payloads are Q32.32; Climate and Resource writes are ledger credits and debits (`e_cat`, `m_cat`); `mutation_bias` writes are clamped to `[0.25, 4.0]` |

---

## 10. Failure Cases & Risk Mitigation

| Case | Behaviour | Mitigation |
| :--- | :--- | :--- |
| Saturation in Stage 3–5 arithmetic | value clips to `FX_MAX`/`FX_MIN`, `FX_FLAG_SAT` set, simulation continues deterministically | bounds on weights (REQ-MATH-003) and accounts (REQ-LAW-012); egress diagnostic surfaces the count |
| Saturation in Stage 2 | impossible under REQ-LAW-012; if observed, a defect | debug assertion on `FX_FLAG_SAT` after each Stage 2 sub-step |
| Division by zero | `FX_MAX`/`FX_MIN`/0 by sign, `FX_FLAG_DIVZERO` | callers test the denominator; `fx_logistic` and tables never divide at runtime |
| Domain violation (`ln ≤ 0`, `sqrt < 0`, `exp` out of range) | defined clamp value, `FX_FLAG_DOMAIN` | domain tables in §6.2; callers clamp before the call where the domain is known |
| Ledger inequality at Stage 6 | `Ledger.fault = 1`; tick completes and hashes; DEOS-RT halts or reports | REQ-LAW-004 rule 2 makes inequality impossible for conforming code; the check catches non-conforming writes at the tick they occur |
| Invalid `material_id` | `Ledger.fault = 2` | Stage 1 validation of Resource writes |
| Moisture inequality at Stage 6 | `Ledger.fault = 3`; tick completes and hashes | REQ-LAW-008 antisymmetry and the reservoir remainder rule make inequality impossible for conforming code |
| Diffusion instability | impossible: `κ_edge ≤ 2^-3 < 1/4` | constants are fixed here; a change requires re-proving §7.3.3 |
| Negative field from rounding | impossible: magnitudes are floored before the sign is applied | proofs in §7.3.3, §7.3.4, §7.3.5 |
| Table mismatch between implementations | Desync at the first table-using tick | `fx_tables_init` verifies the §7.2.8 digests and refuses to start on mismatch |
| Stream reuse across threads | Desync | Streams are derived per Chunk from immutable inputs; there is nothing to share |
| Slot exceeding `2^32` draws | Substream overlap with the next Slot | `2^20` draws per stage per Slot, asserted in debug builds; a rejection loop of `bounded` exceeds 64 iterations with probability below `2^-64` |
| Compiler reassociation or contraction | Desync between platforms | REQ-MATH-009 flags; CI builds with `-Werror` on the prohibited flags and runs §7.7 on both architectures |
| Heat never radiating from Cells below 1,024 ulp of temperature | a floor of `≤ 2^-22` energy units per Cell persists | negligible; accounted exactly because it is still in `E_total` |
| Energy system running down in a long absence | the world cools and slows without input | REQ-LAW-013 insolation (ADR-0002) supplies a renewable input; equilibrium `e_sun == e_rad` is approached with the radiation half-life of about 710 ticks |

---

## 11. Performance & Scalability Targets

| Item | MVS scale (256×256, 2^14 entities) | v1.0 scale (1,024×1,024, 2^20 entities) |
| :--- | :--- | :--- |
| Stage 2 integer operations per Cell | ≈ 70 (2b: 4 edges × 6 ops; 2c: 4 × 9; local steps ≈ 20) | same |
| Stage 2 cost, single thread | 65,536 Cells × 70 ≈ 4.6 M ops ≈ 1.2 ms | 1 M Cells ≈ 73 M ops ≈ 18 ms; 4 workers ≈ 4.6 ms of the 16.6 ms budget |
| Substrate memory (two buffers) | 2 × 65,536 × 41 B ≈ 5.4 MB | 2 × 1 M × 41 B ≈ 86 MB |
| Function tables | 196,656 bytes, read-only, shared | same |
| Stream derivations per tick | 5 systems × (16 + 64) Chunks = 400 keyed hashes ≈ 0.1 ms | 5 × (1,024 + 1,024) = 10,240 ≈ 2 ms across workers (each worker derives its own) |
| Substream advance | 1 × 128-bit mul-add per Slot per system ≈ 4 ns | 4 M per tick ≈ 16 ms single thread, ≈ 4 ms on 4 workers; folded into the per-entity pass that already touches the Slot |
| Ledger fold | 80 `i128` adds | 2,048 `i128` adds |
| Table calls | `fx_exp`, `fx_ln`, `fx_sqrt`, `fx_rcp`: ≈ 15 ns; `fx_logistic`, `fx_sin_rot`: ≈ 8 ns | same |

The MVS benchmark (10,000 ticks under 5.0 s) budgets 0.5 ms per tick in total; Stage 2 at MVS scale consumes about a quarter of it on one thread.

---

## 12. Future Expansion

1. **Seasonal insolation.** REQ-LAW-013 uses a static latitude table. A seasonal term scaling `LAT[y]` by axial tilt as a function of `t` would give worlds winters; it changes only the `LAT` lookup and needs no ledger change.
2. **Erosion.** Elevation is static in v0.1.0. A runoff-driven erosion rule (moving `elevation` from high to low Cells in proportion to `fr`) fits sub-step 2c with an elevation ledger.
3. **Orographic precipitation.** Replacing uniform `rain_cell` with an elevation- and temperature-weighted distribution whose weights sum exactly to `rain_total` by the last-part-by-subtraction rule.
4. **SIMD and GPU diffusion.** Sub-steps 2b and 2c are lane-parallel with no cross-lane reduction; a vectorized or GPU implementation is conformant when it reproduces §7.7 and the Tick Hashes, which the per-edge integer formula makes possible because integer lanes have no rounding mode.
5. **Wider table sets.** `fx_pow`, `fx_atan2_rot` for Protocol perception if DEOS-PROTO requests them; they follow REQ-MATH-010 and add their digests to §7.2.8.
6. **Substream stride.** `2^32` draws per Slot is generous; a `2^24` stride would halve nothing today and is retained for the day a Slot needs a long rejection sequence.

---

## 13. Revision History

| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.1.0 | 2026-09-12 | Initial DEOS draft; absorbs EESS-0101 (REQ-LAW-001…003) and EESS-0201 (REQ-MATH-001…004); REQ-LAW-013 insolation added per ADR-0002 at integration | DEOS Arch Team |
