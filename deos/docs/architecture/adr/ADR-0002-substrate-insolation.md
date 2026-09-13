# Architecture Decision Record: ADR-0002 Substrate Insolation

| Metadata | Value |
| :--- | :--- |
| **Status** | Accepted |
| **Date** | 2026-09-12 |
| **Author(s)** | DEOS Arch Team |

---

## 1. Context

DEOS-Core v0.1.0 as drafted specified a closed energy system: the only energy entering a world was Catalyst credits (`e_cat`) and the only exit was radiation (`e_rad`), with Cell energy decaying into heat at material-dependent rates (SOIL half-life about 11,000 ticks, three simulated days). A world stepped through an Epoch of Acceleration (108,000 ticks) without Catalyst input would therefore lose most of its usable energy to heat and radiation, and its population would starve while the player was away. That contradicts the offline catch-up return hook (DEOS section 1.1, DEOS-F01 section 3.4 item 4) and GI-8 (no hidden scarcity): the player would return to a dead world through no action of their own, and the only remedy would be to keep paying Catalyst Budget as life support. DEOS-Core section 12 had deferred an insolation source to a future ADR.

## 2. Decision

Add REQ-LAW-013 to DEOS-Core: every Cell receives `sun = fx_mul(FX_INSOLATION, LAT[y])` per tick in a new Stage 2 sub-step 2i, credited to `energy` (spillover to `temperature`) and accounted in a new `Ledger.e_sun` field (the `Ledger` grows from 144 to 160 bytes). REQ-LAW-001 becomes `E_total(t+1) = E_total(t) + E_cat(t) + E_sun(t) − E_rad(t)` and the Stage 6 check includes `e_sun`. `FX_INSOLATION = 2^-8` energy per Cell per tick; `LAT[y] = 0.5 + sin(π·(y + 0.5)/GRID_H)` in `[0.5, 1.5]`. The former sub-step 2i (ledger partials) becomes 2j.

Sizing: at MVS scale the world receives about 256 energy per tick, which sustains roughly 8,500 organisms at a mean metabolic rate of 0.03 per tick, near the tick-0 population DEOS-MVS specifies, so carrying capacity is set by the sun and modulated by the Catalyst rather than dictated by the founding endowment. Equilibrium `e_sun == e_rad` gives a mean Cell temperature of 4.0, between `FX_FREEZE_T` (2.0) and `FX_THAW_T` (6.0), so the latitude gradient yields frozen poles and a temperate belt without any authored climate map.

## 3. Consequences

### Positive
- Worlds persist through absences; the Catalyst is a perturbation, never life support (GI-4, GI-8).
- Climate emerges from latitude, elevation, and material alone (Pillar 1).
- The conservation ledger stays exact: insolation is a credited term, not an exception.

### Negative & Trade-offs
- The world is no longer closed; "no energy from nowhere" becomes "no energy except the sun", which the Chronicle's Epoch summary shows as `e_sun` and `e_rad`.
- `FX_INSOLATION` is a pacing constant that MVS playtesting will tune; every change re-runs the DEOS-F05 seed sample.
- The `Ledger` layout change bumps nothing else (the record was not yet serialized anywhere); Snapshot section 17 of DEOS-Runtime carries the 160-byte record.

## 4. Compliance & Verification

- TS-BENCH-002 includes an Epoch without Catalyst Actions: population at tick 108,000 must be at least 50 % of the tick-0 population in 90 of 100 seeds (added to TS-PLAY-002 as the persistence check).
- The Stage 6 conservation check with `e_sun` runs every tick; `Ledger.fault = 1` halts on any inequality.
