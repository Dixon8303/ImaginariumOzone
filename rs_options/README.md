# rs_options_risk — Foundational Risk Engine (v0.2)

Reference implementation of the Risk Engine for the **RS Options Research & Execution Engine spec v2.2**. Pure Python 3.10+, zero dependencies (pytest for tests only).

v0.2 (assessment response): `BrokerReconciler` (debounced, fail-conservative, EFFECTIVE_BP = min(model, broker)), session-start canary suite (§61), rejection forensics via `gate_margins` (§63), and the `EDGE_FASTER_THAN_PIPE` latency-class gate (§38).

## Spec Mapping

| Module | Spec Sections | Responsibility |
|---|---|---|
| `config.py` | §4, §8, §36, §38 | Hard risk constants + subsystem configuration |
| `models.py` | §6–§9, §62 | Domain objects, decision record, telemetry blocks |
| `scenario.py` | §6 | Black-Scholes stress grid (Base + Stress A–D) at invalidation |
| `margin.py` | §8 | Margin_Impact: BP gates, T+1 settlement, GFV, PDT; `BrokerReconciler` (debounced lower-of-two) |
| `canary.py` | §61 | Session-start self-test: must-reject synthetics; any authorization = Level 0 halt |
| `tax.py` | §36 | Wash-sale ledger, 30-day lookback, Q4 escalation, year-end hard block |
| `latency.py` | §38 | Latency ladder (GREEN/YELLOW/RED/BLACK) with hysteresis; fail-closed when uncalibrated |
| `vol_surface.py` | §25 | RR25 / BF25, skew percentiles, skew-state classification |
| `engine.py` | §5–§7, §35, §81–§82 | Gate composition: `evaluate()` → AUTHORIZE / FORCE_SHADOW / REJECT / FREEZE / HALT |
| `sql/clickhouse_schema.sql` | §46 | OPRA-scale OLAP reference DDL |

## Gate Order (engine.py)

```
data integrity → broker health → latency (BLACK→HALT, RED→SHADOW) →
portfolio drawdown → daily loss → macro block → max positions →
edge half-life vs measured pipe (EDGE_FASTER_THAN_PIPE) →
scenario worst-case ≤ 1% budget → position sizing → exposure caps
(underlying / cluster / concurrent) → margin & buying power →
wash-sale gate → skew/latency/tax penalties → score + EV thresholds →
AUTHORIZE
```

Every decision carries `gate_margins` (distance-to-pass per gate) so rejections are diagnosable: edge absent vs edge eaten by friction (§63).

Nothing downstream can override a risk rejection (spec §82).

## Run

```bash
python -m pytest tests/ -q     # unit tests
python demo.py                 # sample evaluation → telemetry JSON
```

## Deliberate Boundaries

- **Long-premium structures only.** Short-structure margin needs validated broker-formula adapters (spec §8) — prohibited until then.
- **Every threshold marked CALIBRATE** (latency bands, stress magnitudes, slippage fraction, fees) is a research placeholder. Calibrate in Paper/Shadow before any production use (LAW 12).
- **Uncalibrated latency monitor reports RED** → production evaluations return FORCE_SHADOW, never live authorization.
- **Tax module produces flags for a tax professional.** It is not tax advice.
- Black-Scholes values are model estimates and labeled as such (spec §6).
