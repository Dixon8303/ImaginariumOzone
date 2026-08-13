# RS OPTIONS RESEARCH & EXECUTION ENGINE v2.0

## Relative Strength + Regime + Volatility + Risk + Execution + Learning

**Status:** Research/engineering specification  
**Primary objective:** Discover, validate, and—only after passing explicit safety gates—execute a repeatable options day-trading strategy centered on hierarchical relative strength.

---

# 0. SYSTEM MANDATE

Build an institutional-style research and execution platform for short-horizon listed-options trading.

The system must optimize for:

1. Positive net expectancy.
2. Controlled maximum drawdown.
3. Robustness across market regimes.
4. Realistic execution assumptions.
5. Statistical validity.
6. Parameter stability.
7. Strict capital preservation.
8. Complete auditability.
9. Explicit separation of research from production.
10. The ability to disable itself when data, execution, or model conditions become unsafe.

The system is **not** permitted to optimize for maximum historical return, maximum win rate, or maximum trade frequency as a standalone objective.

The system must treat every strategy as a hypothesis until validated out of sample.

> **Research first. Paper second. Shadow third. Production last.**

---

# 1. CORE SYSTEM PHILOSOPHY

The engine operates on:

**Macro Regime → Market Regime → Sector Regime → Relative Strength → Setup → Volatility → Option Structure → Risk → Execution → Telemetry → Learning**

The engine must never begin with an option contract and construct a thesis afterward.

The correct sequence is:

1. Understand the market.
2. Identify the regime.
3. Identify relative strength/weakness.
4. Identify a defined setup.
5. Determine whether the option structure is appropriate.
6. Calculate risk.
7. Estimate conditional expectancy.
8. Execute only if all gates pass.

---

# 2. SYSTEM ARCHITECTURE

```text
                         ┌───────────────────────┐
                         │      DATA ENGINE      │
                         │ Market + Options +    │
                         │ Macro + Corporate    │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   DATA INTEGRITY      │
                         │ Freshness + Completeness│
                         │ Timestamp Alignment   │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │     MACRO ENGINE      │
                         │ Expected/Actual/       │
                         │ Surprise/Event State  │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │    REGIME ENGINE      │
                         │ Trend/Vol/Momentum/   │
                         │ Breadth/Liquidity     │
                         └───────────┬───────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
          ┌──────────────────┐              ┌──────────────────┐
          │  MARKET ENGINE   │              │  SECTOR ENGINE   │
          │ SPY/QQQ/IWM/etc. │              │ ETF/Industry     │
          └─────────┬────────┘              └────────┬─────────┘
                    └────────────────┬────────────────┘
                                     ▼
                         ┌───────────────────────┐
                         │      RS ENGINE        │
                         │ Market + Sector +     │
                         │ Beta-Adjusted +       │
                         │ Persistence/Accel.    │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │     SETUP ENGINE      │
                         │ RS-01 ... RS-N        │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   OPTIONS ENGINE      │
                         │ Delta/Gamma/Theta/    │
                         │ Vega/IV/DTE/Spread/   │
                         │ Expected Move         │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │     RISK ENGINE       │
                         │ Position Size +       │
                         │ Scenario Loss +       │
                         │ Portfolio Exposure    │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │  PROBABILITY / EV     │
                         │ Conditional Outcome   │
                         │ Distribution           │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ EXECUTION GATE        │
                         │ All hard/soft gates   │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ EXECUTION ENGINE      │
                         │ Paper / Shadow / Live │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ TELEMETRY ENGINE      │
                         │ Full event/trade log  │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ LEARNING ENGINE       │
                         │ Attribution + Testing │
                         │ Drift + Research      │
                         └───────────────────────┘
```

---

# 3. OPERATING MODES

The engine must support four mutually distinct operating modes.

## 3.1 RESEARCH

Purpose:

- hypothesis generation;
- feature engineering;
- backtesting;
- parameter experiments;
- model development.

No brokerage connection required.

Research may use broad experimentation.

## 3.2 PAPER

Real-time data and real-time signals.

No capital is deployed.

Orders are simulated using live quotes and the production execution model.

## 3.3 SHADOW

The system generates production-intended orders but does not transmit them.

The engine compares:

- intended fill;
- simulated fill;
- market movement;
- liquidity;
- latency.

Shadow mode must remain active long enough to establish that live behavior resembles the backtest.

## 3.4 PRODUCTION

Real capital.

Production configuration must be immutable except through an approved version-release process.

---

# 4. HARD RISK CONSTANTS

These are non-negotiable.

```python
MAX_TRADE_RISK_PCT = 0.01
MAX_PORTFOLIO_DRAWDOWN_PCT = 0.10
MAX_SINGLE_UNDERLYING_EXPOSURE_PCT = 0.05

DAILY_LOSS_LIMIT_PCT = configurable
MAX_OPEN_POSITIONS = configurable
MAX_CONCURRENT_RISK_PCT = configurable
```

## Required behavior

### Trade risk breach

Reject trade.

### Portfolio drawdown breach

Freeze all new trading.

### Single-underlying exposure breach

Reject additional exposure.

### Daily loss breach

Stop trading for session.

### Data integrity breach

Stop trading immediately.

### Broker/API integrity breach

Stop trading immediately.

### Model/configuration mismatch

Stop trading immediately.

---

# 5. RISK MODEL

## 5.1 Per-Trade Risk

The system must define:

**maximum modeled loss per trade before entry.**

The system must never rely on average historical loss as a risk control.

Required constraint:

```text
WorstCaseModeledLossPerTrade <= MAX_TRADE_RISK
```

The risk model must incorporate:

- option premium;
- technical invalidation;
- modeled option repricing;
- spread;
- slippage;
- commissions;
- fees;
- gap/execution stress assumptions.

---

# 6. OPTION SCENARIO PRICING

The engine must not assume that a $1 move in the underlying creates a fixed option-premium change.

For each proposed position, calculate option value under at least these scenarios:

### Base

Underlying reaches invalidation.

### Stress A

Underlying reaches invalidation plus adverse slippage.

### Stress B

Underlying reaches invalidation while IV moves adversely.

### Stress C

Underlying reaches invalidation with additional time decay.

### Stress D

Liquidity deteriorates and exit occurs near the bid.

The engine should use an appropriate option-pricing model to estimate theoretical values and Greeks, while clearly labeling model-derived values as estimates.

For each scenario:

```text
Estimated Exit Premium
- Entry Premium
- Slippage
- Fees
= Net P&L
```

---

# 7. POSITION SIZING

```python
risk_budget = account_equity * MAX_TRADE_RISK_PCT

risk_per_contract = abs(
    entry_price -
    conservative_estimated_exit_price
) * contract_multiplier

risk_per_contract += estimated_slippage_cost
risk_per_contract += fees_per_contract

contracts = floor(risk_budget / risk_per_contract)
```

Then enforce:

```text
contracts >= 1
contracts <= max_position_limit
total_underlying_exposure <= MAX_SINGLE_UNDERLYING_EXPOSURE
total_portfolio_risk <= MAX_CONCURRENT_RISK
```

If no valid contract quantity remains:

**REJECT TRADE.**

---

# 8. MARKET REGIME ENGINE

Do not represent regime as a single crude label.

The regime must be a vector.

```json
{
  "trend": "bullish | neutral | bearish",
  "volatility": "low | normal | elevated | extreme",
  "momentum": "positive | neutral | negative",
  "liquidity": "normal | thin | stressed",
  "breadth": "strong | mixed | weak",
  "macro": "risk_on | neutral | risk_off"
}
```

The engine may additionally generate a human-readable composite:

- Trending Bull
- Trending Bear
- Range
- High Volatility
- Transitional

But the underlying vector must remain available for analysis.

---

# 9. MARKET INPUTS

At minimum:

- SPY
- QQQ
- IWM
- VIX or suitable volatility proxy
- Treasury yields
- sector ETFs
- market breadth where available

Timeframes:

- 1-minute
- 5-minute
- 15-minute
- daily context

The system must avoid using future information.

---

# 10. MACRO ENGINE

The macro engine must track scheduled events and their outcomes.

Each event should include:

```json
{
  "event": "CPI",
  "timestamp": "ISO-8601",
  "expected": 0.0,
  "actual": null,
  "prior": 0.0,
  "surprise": null,
  "tier": 1,
  "status": "scheduled | released | revised"
}
```

## Macro surprise

When actual data becomes available:

```text
surprise = actual - expected
```

Where appropriate, use standardized surprise measures rather than raw differences.

---

# 11. MACRO EVENT STATES

Instead of a single 60-minute blackout:

## PRE_EVENT

Within configurable pre-event window.

Default:

**60 minutes**

Behavior:

- reduce trade eligibility;
- require elevated confidence;
- optionally prohibit new positions.

## EVENT_WINDOW

Default:

**15 minutes before through configurable post-release window.**

Default behavior:

**No new trades.**

## POST_EVENT

Trading may resume only when:

- quote quality normalizes;
- spread normalizes;
- market structure stabilizes;
- regime is recalculated;
- volatility state is recalculated.

The system must explicitly distinguish:

**event risk**

from:

**post-event opportunity.**

---

# 12. RELATIVE STRENGTH ENGINE

Relative strength must be hierarchical.

## 12.1 Market RS

```text
RS_market = stock_return - benchmark_return
```

## 12.2 Sector RS

```text
RS_sector = stock_return - sector_return
```

## 12.3 Beta-Adjusted RS

Estimate rolling beta:

```text
beta = Cov(stock, benchmark) / Var(benchmark)
```

Then:

```text
RS_beta_adjusted =
stock_return - beta * benchmark_return
```

## 12.4 Industry RS

Where data is available:

```text
RS_industry = stock_return - industry_return
```

---

# 13. DYNAMIC BENCHMARK SELECTION

Benchmark selection should depend on the underlying.

Examples:

```text
Broad market → SPY
Growth/technology → QQQ
Small cap → IWM
Semiconductor → SMH/SOXX
Financials → XLF
Energy → XLE
Healthcare → XLV
```

The engine may retain SPY as a universal reference, but should never assume SPY is the only relevant benchmark.

---

# 14. RS PERSISTENCE

Track:

- RS magnitude;
- RS duration;
- RS acceleration;
- RS consistency;
- RS response during market pullbacks;
- RS volume confirmation.

Example:

```text
RS Persistence = percentage of observed windows in which RS remains positive.
```

The exact feature definition must be versioned and tested.

---

# 15. RS STRESS TEST

A high-value signal is:

**Market weakens → stock refuses to weaken.**

The engine should measure:

```text
benchmark drawdown
stock drawdown
relative drawdown
VWAP retention
higher-low retention
volume behavior
subsequent breakout probability
```

This becomes a dedicated setup family.

---

# 16. SETUP ENGINE

Initial setup library:

## RS-01 — MARKET WEAKNESS ABSORPTION

Conditions:

- benchmark weak;
- stock materially stronger;
- sector not contradicting;
- stock maintains key structure;
- volume confirms;
- subsequent market stabilization or reversal.

## RS-02 — RS BREAKOUT

Conditions:

- persistent positive RS;
- resistance defined;
- breakout;
- volume expansion;
- market/sector confirmation.

## RS-03 — RS VWAP RECLAIM

Conditions:

- stock demonstrates relative strength;
- VWAP reclaim;
- higher-low structure;
- volume confirmation.

## RS-04 — RS PULLBACK CONTINUATION

Conditions:

- established RS;
- controlled pullback;
- no major RS deterioration;
- continuation trigger.

## RS-05 — SECTOR DIVERGENCE

Conditions:

- stock outperforms benchmark;
- stock outperforms sector;
- structural breakout or continuation.

Each setup must have its own:

- entry;
- invalidation;
- target logic;
- option-selection rules;
- regime compatibility;
- expected holding period.

---

# 17. OPTIONS ENGINE

For each candidate, evaluate:

- expiration;
- DTE;
- strike;
- Delta;
- Gamma;
- Theta;
- Vega;
- IV;
- IV Rank;
- IV Percentile;
- IV term structure;
- bid;
- ask;
- midpoint;
- spread;
- volume;
- open interest;
- expected move;
- moneyness.

---

# 18. DELTA

Initial research range:

```text
0.40–0.80
```

Do not hardcode 0.50–0.70 as universally optimal.

Subdivide into research buckets:

```text
0.40–0.50
0.50–0.60
0.60–0.70
0.70–0.80
```

Performance must be evaluated by:

- setup;
- regime;
- DTE;
- IV environment.

Production Delta limits may only be selected after out-of-sample validation.

---

# 19. GAMMA

Track Gamma as a first-class risk variable.

The engine must flag:

- high-gamma contracts;
- 0DTE;
- 1DTE;
- near-ATM exposure.

Gamma must influence:

- position sizing;
- expected P&L sensitivity;
- stop behavior;
- execution urgency.

---

# 20. THETA

Theta must be quantitative.

Track:

```text
theta_per_contract
theta_as_pct_of_premium
theta_burden_over_expected_holding_period
```

Reject or downgrade contracts when modeled theta consumption is excessive relative to expected movement.

Thresholds must be empirically validated.

---

# 21. VEGA

Track sensitivity to IV changes.

The engine must run an adverse-IV scenario.

Example:

```text
Base IV
IV - 5 points
IV - 10 points
IV + 5 points
IV + 10 points
```

For catalyst trades, IV behavior becomes a mandatory part of the expectancy calculation.

---

# 22. IV RANK AND IV PERCENTILE

Store both.

Do not treat them as interchangeable.

Each must be calculated against appropriate historical distributions.

Prefer distributions segmented by:

- underlying;
- DTE/tenor;
- moneyness where data permits.

---

# 23. IV TERM STRUCTURE

Track:

- 1D;
- 7D;
- 14D;
- 30D;
- 60D;
- longer available tenors.

Identify:

- normal structure;
- front-loaded volatility;
- backwardation;
- event premium.

---

# 24. CATALYST PROTOCOL

When a Tier 1 catalyst exists:

The engine must determine:

1. Is the trade before or after the catalyst?
2. Is IV elevated?
3. How much of the expected move is priced?
4. What is the expected move?
5. What is the historical post-event move?
6. Is the option exposed to IV crush?
7. Is the strategy designed to benefit from volatility expansion, contraction, or direction?

A generic long-option trade must not automatically pass simply because a catalyst exists.

---

# 25. LIQUIDITY ENGINE

Minimum requirements should evaluate:

- absolute spread;
- spread percentage;
- volume;
- open interest;
- quote freshness;
- depth where available.

Initial spread rule:

```text
spread_pct <= 10%
```

But production thresholds should be tested.

A contract with a 5% spread and almost no depth may still be worse than a contract with a 7% spread and excellent liquidity.

---

# 26. EXPECTED MOVE

Approximate expected move:

```text
Expected Move ≈
Underlying Price × IV × sqrt(DTE / 365)
```

Use as a contextual estimate, not a guaranteed forecast.

Store:

```text
expected_move_dollars
expected_move_percent
distance_to_target_as_expected_move
```

A trade requiring an implausibly large move relative to the priced expected move should be penalized or rejected.

---

# 27. TRADE PROBABILITY ENGINE

The system must eventually estimate conditional probabilities such as:

```text
P(+1R)
P(+2R)
P(+3R)
P(stop)
P(time_exit)
```

based on comparable historical conditions.

Example output:

```json
{
  "P_plus_1R": 0.68,
  "P_plus_2R": 0.51,
  "P_plus_3R": 0.29,
  "P_stop": 0.32
}
```

The system must not present these as universal probabilities.

They are estimates conditioned on the historical sample and model version.

---

# 28. EXPECTANCY

Basic:

```text
E = Pw * AvgWin - Pl * AvgLoss
```

Net expectancy:

```text
E_net =
Pw * (AvgWin - WinningFriction)
-
Pl * (AvgLoss + LosingFriction)
-
Fees
```

Express results in:

- dollars;
- percentage;
- R multiples.

The canonical strategy metric should be:

**Net Expectancy per Trade in R.**

---

# 29. R-MULTIPLE FRAMEWORK

Define:

```text
1R = maximum planned trade risk
```

Then record:

```text
+0.5R
+1R
+2R
+3R
-1R
```

This normalizes trades across different account sizes and contract prices.

---

# 30. TRADE SCORING

Retain a 10-point interpretability score.

However, it must not be the final decision engine.

Suggested components:

| Category | Points |
|---|---:|
| Macro Alignment | 0–2 |
| Regime Compatibility | 0–2 |
| Technical Structure | 0–2 |
| Relative Strength | 0–2 |
| Options Structure | 0–1 |
| Liquidity | 0–1 |

Total:

**10**

The original "catalyst" point is moved into contextual logic rather than automatically rewarded.

A catalyst is not inherently bullish.

---

# 31. CORRELATION CONTROL

The score must not double-count related variables.

The engine should calculate feature correlations and monitor:

- macro/regime correlation;
- market/sector correlation;
- RS/technical correlation;
- IV/volatility correlation.

Feature attribution should be reported.

---

# 32. RISK PENALTY SCORE

Add a separate penalty model.

Examples:

```text
Major macro event imminent: -3
Extreme IV: -2
Poor liquidity: -3
Contradictory sector: -2
Unstable market regime: -2
Insufficient volume: -2
Excessive theta burden: -2
Required move too large: -3
Data quality issue: HARD REJECT
```

Then:

```text
NetOpportunityScore =
OpportunityScore - RiskPenalty
```

---

# 33. HARD GATES VS SOFT GATES

## HARD GATES

Any failure = reject.

Examples:

- risk limit;
- data integrity;
- broker connectivity;
- invalid quote;
- impossible spread;
- insufficient capital;
- portfolio drawdown;
- daily loss limit;
- maximum exposure;
- invalid option chain.

## SOFT GATES

A failure reduces confidence.

Examples:

- weak sector confirmation;
- elevated IV;
- marginal RS;
- lower volume;
- imperfect technical structure.

This prevents one imperfect feature from automatically destroying every otherwise valid trade.

---

# 34. EXECUTION ENGINE

The execution engine must support:

- limit orders;
- configurable price offsets;
- timeout;
- cancel/replace;
- partial fills;
- maximum slippage;
- liquidity recheck;
- emergency exit;
- broker/API health check.

The engine must never chase a trade indefinitely.

---

# 35. ENTRY EXECUTION

Before sending:

1. Recheck underlying quote.
2. Recheck option quote.
3. Recheck spread.
4. Recheck Greeks.
5. Recheck risk.
6. Recheck macro event state.
7. Recheck position exposure.
8. Recalculate contract quantity.

If any material variable changes:

**Re-score/re-price before execution.**

---

# 36. EXIT EXECUTION

Exit conditions may include:

- technical invalidation;
- predefined target;
- structural trailing stop;
- time stop;
- volatility failure;
- thesis invalidation;
- system emergency;
- daily risk shutdown.

The engine must distinguish:

**planned exit**

from:

**forced risk exit.**

---

# 37. TRAILING-STOP RESEARCH

Test at minimum:

### Structure trail

Previous higher low/lower high.

### VWAP trail

Exit on confirmed VWAP failure.

### ATR trail

Volatility-adjusted stop.

### R-based trail

Example research policy:

```text
+1R → protective adjustment
+2R → structural trail
+3R → aggressive trail
```

These are hypotheses only.

Select using out-of-sample MFE/MAE evidence.

---

# 38. MAE/MFE ENGINE

For every trade calculate:

```text
MAE_dollars
MFE_dollars

MAE_R
MFE_R

time_to_MFE
time_to_MAE
```

Use this data to determine:

- whether stops are too tight;
- whether targets are too conservative;
- whether winners tend to continue;
- optimal trailing behavior.

---

# 39. TIME-OF-DAY ENGINE

Segment trades by:

- opening period;
- morning trend;
- midday;
- afternoon;
- final hour.

Do not assume any period is inherently superior.

The system must learn:

```text
Setup × Regime × TimeOfDay
```

expectancy.

---

# 40. BACKTEST ENGINE

The backtester must be event-driven.

It must simulate information availability at the exact timestamp.

At time T, the system may only access information that would have been known at T.

---

# 41. REQUIRED HISTORICAL DATA

For realistic options backtesting:

### Underlying

- tick or sufficiently granular OHLCV;
- corporate actions;
- splits;
- dividends.

### Options

- historical chains;
- strikes;
- expiration;
- bid;
- ask;
- last;
- volume;
- open interest;
- IV or sufficient data to reconstruct it;
- Greeks or sufficient data to reconstruct them.

### Macro

- timestamp;
- expected;
- actual;
- prior;
- revisions.

### Market Context

- benchmarks;
- sectors;
- volatility indices;
- Treasury yields.

---

# 42. EXECUTION MODEL

Backtests must not assume fills at the last traded price.

Default conservative assumptions:

### Long entry

Fill near:

```text
mid + configurable_fraction_of_spread
```

### Long exit

Fill near:

```text
mid - configurable_fraction_of_spread
```

### Stress mode

Use bid/ask boundaries.

All assumptions must be configurable and reported.

---

# 43. SLIPPAGE MODEL

Model slippage as a function of:

- spread;
- volume;
- volatility;
- order size;
- liquidity;
- time of day.

Do not use a universal fixed slippage number unless validated.

---

# 44. LOOK-AHEAD BIAS PROTECTION

The backtester must prevent use of:

- future prices;
- future IV;
- future volume;
- future option-chain observations;
- revised macro information unavailable at the time;
- today's survivorship universe for historical dates.

---

# 45. SURVIVORSHIP BIAS PROTECTION

The historical universe must include securities that later:

- delisted;
- merged;
- failed;
- changed ticker;
- changed corporate structure.

Otherwise results will be artificially optimistic.

---

# 46. WALK-FORWARD VALIDATION

Required pipeline:

```text
TRAIN → VALIDATE → TEST → ROLL FORWARD
```

Example:

```text
Train: 2018–2022
Validation: 2023
Test: 2024
Then roll forward.
```

The exact periods depend on available data.

Production parameters must be selected using only information available before the production test period.

---

# 47. MONTE CARLO

Run thousands of randomized trade-order simulations.

Report:

- median drawdown;
- 95th percentile drawdown;
- worst simulated drawdown;
- longest losing streak;
- probability of reaching maximum drawdown;
- probability of capital impairment.

---

# 48. PARAMETER STABILITY

A parameter is suspicious when a tiny change creates a huge performance change.

Test neighborhoods around every production parameter.

Prefer:

**performance plateaus**

over:

**performance spikes.**

Example:

Bad:

```text
Delta 0.61 = +180%
Delta 0.60 = +12%
Delta 0.62 = +9%
```

Better:

```text
Delta 0.55–0.70 consistently positive
```

---

# 49. OBJECTIVE FUNCTION

Do not optimize raw profit.

Primary optimization target:

```text
Net Expectancy
```

with penalties for:

- maximum drawdown;
- volatility of returns;
- turnover;
- slippage sensitivity;
- parameter complexity;
- regime dependence;
- instability.

Conceptually:

```text
Objective =
NetExpectancy
- DrawdownPenalty
- ExecutionPenalty
- ComplexityPenalty
- InstabilityPenalty
```

---

# 50. COMPLEXITY PENALTY

A strategy requiring 75 tightly tuned parameters should be considered less robust than a simpler strategy with similar performance.

Prefer:

**fewer features + stronger evidence**

over:

**maximum feature count.**

---

# 51. REGIME-SPECIFIC REPORTING

Every backtest must report:

```text
Bull Trend
Bear Trend
Range
High Volatility
Low Volatility
Macro Event
Post-Macro
```

and compare:

- expectancy;
- win rate;
- average win;
- average loss;
- drawdown;
- trade count.

---

# 52. SETUP-SPECIFIC REPORTING

Every setup must have independent statistics.

Example:

```text
RS-01
Trades: 1,200
Expectancy: +0.31R
Win rate: 48%
Avg win: 1.8R
Avg loss: 1.0R
Max DD: 8.2R
```

No setup should be hidden inside aggregate performance.

---

# 53. STRATEGY HEALTH MONITOR

Production monitoring must continuously calculate:

- rolling expectancy;
- rolling win rate;
- rolling average win;
- rolling average loss;
- rolling drawdown;
- slippage;
- fill quality;
- regime distribution;
- setup distribution.

Compare live performance with validated historical ranges.

---

# 54. DRIFT DETECTION

Flag when live behavior materially deviates from research.

Examples:

```text
Live spread > historical spread
Live slippage > historical slippage
Live expectancy < confidence band
Live MFE lower than historical
Live MAE higher than historical
RS feature distribution shifted
IV distribution shifted
```

A drift warning does not automatically imply strategy failure.

But it should trigger review.

---

# 55. KILL-SWITCH HIERARCHY

## LEVEL 0 — DATA KILL

Bad/stale/incomplete data.

**Immediate stop.**

## LEVEL 1 — TRADE KILL

Single trade violates risk rules.

**Reject trade.**

## LEVEL 2 — SETUP KILL

Specific setup exhibits statistically abnormal degradation.

**Disable setup.**

## LEVEL 3 — STRATEGY KILL

Rolling net expectancy materially negative beyond predefined confidence criteria.

**Disable strategy.**

## LEVEL 4 — PORTFOLIO KILL

Maximum drawdown reached.

**Freeze system.**

---

# 56. DATA INTEGRITY ENGINE

Reject trading when:

- quote timestamp is stale;
- underlying quote unavailable;
- option quote unavailable;
- bid/ask invalid;
- Greeks unavailable beyond tolerance;
- economic calendar unavailable when macro gating is required;
- benchmark data unavailable;
- broker connection unhealthy;
- timestamps cannot be synchronized;
- market status is ambiguous.

Default behavior:

**FAIL CLOSED.**

---

# 57. TELEMETRY SCHEMA

Every signal, rejected trade, paper trade, shadow trade, and live trade must be logged.

```json
{
  "Trade_ID": "UUID",
  "Strategy_Version": "STRING",
  "Timestamp": "ISO-8601",
  "Mode": "research|paper|shadow|production",

  "Underlying": {
    "Ticker": "STRING",
    "Price": 0.0,
    "Return_1m": 0.0,
    "Return_5m": 0.0,
    "Return_15m": 0.0,
    "Return_1h": 0.0,
    "Volume": 0,
    "Relative_Volume": 0.0,
    "VWAP": 0.0,
    "ATR": 0.0,
    "Beta": 0.0
  },

  "Market_Context": {
    "SPY_Return": 0.0,
    "QQQ_Return": 0.0,
    "IWM_Return": 0.0,
    "VIX": 0.0,
    "Treasury_Yield": 0.0,
    "Sector_Return": 0.0,
    "Industry_Return": 0.0,
    "Market_Breadth": 0.0
  },

  "Relative_Strength": {
    "Benchmark": "SPY",
    "RS_Market": 0.0,
    "RS_Sector": 0.0,
    "RS_Industry": 0.0,
    "RS_Beta_Adjusted": 0.0,
    "RS_Persistence": 0.0,
    "RS_Acceleration": 0.0,
    "RS_Volume_Confirmation": 0.0
  },

  "Regime": {
    "Trend": "STRING",
    "Volatility": "STRING",
    "Momentum": "STRING",
    "Liquidity": "STRING",
    "Breadth": "STRING",
    "Macro": "STRING",
    "Composite": "STRING"
  },

  "Macro": {
    "Event": "STRING",
    "Tier": 0,
    "Minutes_To_Event": 0,
    "Expected": null,
    "Actual": null,
    "Prior": null,
    "Surprise": null,
    "State": "STRING"
  },

  "Setup": {
    "Setup_ID": "RS-01",
    "Technical_Trigger": "STRING",
    "Catalyst": "STRING",
    "Entry_Condition": "STRING",
    "Invalidation_Condition": "STRING"
  },

  "Option": {
    "Symbol": "STRING",
    "Expiration": "YYYY-MM-DD",
    "DTE": 0,
    "Strike": 0.0,
    "Moneyness": 0.0,
    "Bid": 0.0,
    "Ask": 0.0,
    "Mid": 0.0,
    "Volume": 0,
    "Open_Interest": 0,
    "Delta": 0.0,
    "Gamma": 0.0,
    "Theta": 0.0,
    "Vega": 0.0,
    "IV": 0.0,
    "IV_Rank": 0.0,
    "IV_Percentile": 0.0,
    "Expected_Move": 0.0,
    "Spread_Percentage": 0.0
  },

  "Risk": {
    "Account_Equity": 0.0,
    "Max_Trade_Risk": 0.0,
    "Invalidation_Price": 0.0,
    "Estimated_Option_Exit": 0.0,
    "Worst_Case_Loss": 0.0,
    "Contract_Quantity": 0,
    "Total_Risk": 0.0,
    "Underlying_Exposure": 0.0,
    "Portfolio_Risk": 0.0
  },

  "Scoring": {
    "Opportunity_Score": 0,
    "Risk_Penalty": 0,
    "Net_Score": 0,
    "Estimated_P_Win": 0.0,
    "Estimated_P_Stop": 0.0,
    "Expected_Value_R": 0.0
  },

  "Execution": {
    "Expected_Entry": 0.0,
    "Actual_Entry": 0.0,
    "Expected_Exit": 0.0,
    "Actual_Exit": 0.0,
    "Entry_Slippage": 0.0,
    "Exit_Slippage": 0.0,
    "Fees": 0.0,
    "Fill_Time_MS": 0,
    "Exit_Reason": "STRING"
  },

  "Result": {
    "PnL": 0.0,
    "Return_Pct": 0.0,
    "R_Multiple": 0.0,
    "MAE": 0.0,
    "MAE_R": 0.0,
    "MFE": 0.0,
    "MFE_R": 0.0,
    "Time_To_MAE": 0,
    "Time_To_MFE": 0
  }
}
```

---

# 58. SIGNAL LOGGING

Rejected opportunities must also be logged.

This is critical.

A rejected signal should record:

```text
Signal_ID
Timestamp
Ticker
Setup
Score
Risk
Option
Reject_Reason
```

Otherwise the system only learns from trades it took.

The system needs to learn from:

**trades taken**

and:

**trades deliberately rejected.**

---

# 59. LEARNING ENGINE

The learning engine must analyze:

```text
Setup
×
Regime
×
Time
×
RS
×
IV
×
DTE
×
Delta
×
Liquidity
```

and estimate conditional outcomes.

It should answer:

- Which setups work?
- Under which regimes?
- Which Delta ranges?
- Which DTE ranges?
- Which IV environments?
- Which time windows?
- Which sectors?
- Which market conditions?
- Which exit methods?

---

# 60. LEARNING ENGINE SAFETY

The learning engine may:

- propose hypotheses;
- identify patterns;
- recommend experiments;
- generate reports.

It may **not automatically alter production parameters.**

Production changes require:

1. New version.
2. Backtest.
3. Walk-forward.
4. Out-of-sample validation.
5. Monte Carlo.
6. Parameter-stability check.
7. Paper validation.
8. Shadow validation.
9. Human approval or explicit release policy.

---

# 61. STRATEGY VERSION CONTROL

Every production configuration must have a version.

Example:

```text
RS_OPTIONS_v1.0
RS_OPTIONS_v1.1
RS_OPTIONS_v2.0
```

Store:

- parameters;
- code commit;
- data version;
- training window;
- validation window;
- test window;
- approval timestamp.

Never silently overwrite a validated configuration.

---

# 62. PRODUCTION RELEASE GATE

A candidate strategy must satisfy all required criteria.

Example:

```text
[ ] Positive net expectancy
[ ] Positive expectancy after realistic slippage
[ ] Acceptable maximum drawdown
[ ] Positive walk-forward expectancy
[ ] Positive out-of-sample expectancy
[ ] Monte Carlo survivability
[ ] Parameter stability
[ ] Multiple-regime validation
[ ] Adequate sample size
[ ] Paper trading validation
[ ] Shadow execution validation
[ ] Data integrity validation
[ ] Broker execution validation
```

A single mandatory failure blocks production.

---

# 63. RESEARCH REPORT

Every completed experiment should generate:

## Executive Summary

- hypothesis;
- result;
- conclusion.

## Dataset

- symbols;
- dates;
- resolution;
- options data;
- macro data.

## Strategy

- rules;
- parameters;
- assumptions.

## Performance

- trades;
- expectancy;
- win rate;
- average win;
- average loss;
- profit factor;
- drawdown.

## Risk

- max DD;
- Monte Carlo;
- losing streak.

## Execution

- spread;
- slippage;
- fill assumptions.

## Robustness

- walk-forward;
- out-of-sample;
- parameter stability.

## Regime Analysis

- bull;
- bear;
- range;
- high vol;
- macro events.

## Recommendation

- reject;
- research further;
- paper;
- shadow;
- production candidate.

---

# 64. THE META-STRATEGY

The central decision framework is:

```text
REGIME
  ↓
Which setup historically works here?
  ↓
Which underlying demonstrates the strongest valid RS?
  ↓
Is the technical structure actionable?
  ↓
Is volatility favorable?
  ↓
Which option structure best expresses the thesis?
  ↓
What is the realistic loss distribution?
  ↓
What is the conditional expected value?
  ↓
Does execution preserve the edge?
  ↓
TRADE / NO TRADE
```

The system must be capable of returning:

**NO TRADE**

without treating that as a failure.

---

# 65. THE PRIMARY ALPHA HYPOTHESIS

The initial research hypothesis is:

> Stocks demonstrating persistent, statistically significant relative strength versus both the broad market and their sector—particularly while the market experiences temporary weakness—may have an increased probability of continued outperformance when market conditions stabilize, provided that technical structure, liquidity, volatility, and option pricing remain favorable.

This is a hypothesis.

It must be tested.

---

# 66. PRIMARY RESEARCH VARIABLES

The first research sweep should investigate:

### Relative Strength

- RS magnitude;
- RS persistence;
- RS acceleration;
- beta-adjusted RS;
- sector RS;
- industry RS.

### Market

- SPY trend;
- QQQ trend;
- breadth;
- VIX;
- market volatility.

### Technical

- VWAP;
- opening range;
- breakout;
- retest;
- higher-low structure;
- volume.

### Options

- Delta;
- Gamma;
- Theta;
- Vega;
- IV;
- IV Rank;
- IV Percentile;
- DTE;
- expected move;
- spread.

### Time

- market open;
- morning;
- midday;
- afternoon;
- final hour.

---

# 67. FIRST EXPERIMENT MATRIX

Do not optimize everything simultaneously.

Run controlled experiments.

## Experiment A

RS magnitude.

## Experiment B

RS persistence.

## Experiment C

Sector confirmation.

## Experiment D

Beta-adjusted RS.

## Experiment E

VWAP confirmation.

## Experiment F

Volume threshold.

## Experiment G

Delta bucket.

## Experiment H

DTE bucket.

## Experiment I

IV percentile.

## Experiment J

Time of day.

## Experiment K

Regime.

## Experiment L

Exit method.

Each experiment should isolate variables wherever possible.

---

# 68. ANTI-OVERFITTING RULE

No parameter may be selected because it produces the highest historical return alone.

A parameter should be preferred when:

1. It improves expectancy.
2. Improvement persists out of sample.
3. It survives realistic transaction costs.
4. It remains profitable across nearby parameter values.
5. It does not depend on one unusual historical period.
6. It improves risk-adjusted performance.

---

# 69. MINIMUM SAMPLE SIZE

Do not trust a setup with:

```text
12 trades
```

even if it produces:

```text
+8R
```

Sample size thresholds should be configurable.

Production promotion should require enough observations to estimate the distribution with reasonable confidence.

---

# 70. CONFIDENCE INTERVALS

Where appropriate, report uncertainty.

Instead of:

> Win rate = 63%

report:

> Win rate = 63%, with confidence interval based on sample size and statistical method.

Likewise for expectancy.

The system must distinguish:

**observed performance**

from:

**estimated underlying performance.**

---

# 71. STRATEGY DEGRADATION

The engine must distinguish:

### Random bad streak

Normal variance.

### Regime change

Strategy may still work under original conditions but those conditions have disappeared.

### Edge decay

The conditional relationship itself is weakening.

### Execution degradation

The signal works but trading costs increased.

These require different responses.

---

# 72. CAPITAL ALLOCATION

Do not allocate equal capital to every setup automatically.

After validation, allocation may be based on:

```text
Expected Value
Confidence
Drawdown
Correlation
Liquidity
Regime Compatibility
```

But all allocations remain bounded by the global risk architecture.

---

# 73. CORRELATED POSITIONS

The engine must recognize that:

```text
NVDA call
AMD call
SMH call
QQQ call
```

may represent highly correlated risk.

The 5% single-underlying rule is not enough.

Add:

**factor/cluster exposure limits.**

Example:

```text
Technology factor exposure
Semiconductor cluster exposure
Broad market beta exposure
```

The system should not accidentally create a 15% effective portfolio bet while every individual trade remains under 5%.

---

# 74. PORTFOLIO RISK

Track:

```text
Gross exposure
Net directional exposure
Delta exposure
Gamma exposure
Vega exposure
Theta exposure
Sector exposure
Factor exposure
Underlying exposure
Correlated-cluster exposure
```

This converts the system from isolated trade management into portfolio risk management.

---

# 75. PRODUCTION DASHBOARD

Display:

## MARKET

- SPY
- QQQ
- IWM
- VIX
- yields
- breadth

## REGIME

- trend;
- volatility;
- momentum;
- liquidity;
- breadth;
- macro.

## OPPORTUNITIES

- ticker;
- setup;
- RS;
- sector RS;
- score;
- probability;
- EV;
- option.

## RISK

- account equity;
- daily P&L;
- drawdown;
- open risk;
- portfolio Delta/Gamma/Vega/Theta.

## EXECUTION

- pending orders;
- fills;
- slippage;
- broker health.

## SYSTEM

- data health;
- model version;
- strategy version;
- kill-switch status.

---

# 76. DEFAULT DECISION LOGIC

Pseudocode:

```python
def evaluate_candidate(candidate):

    if not data_integrity_ok(candidate):
        return REJECT("DATA_INTEGRITY")

    if not broker_health_ok():
        return REJECT("BROKER_HEALTH")

    if portfolio_drawdown_exceeded():
        return FREEZE("PORTFOLIO_DRAWDOWN")

    if daily_loss_limit_exceeded():
        return HALT("DAILY_LOSS")

    macro_state = evaluate_macro()

    if macro_state.hard_block:
        return REJECT("MACRO_EVENT")

    regime = evaluate_regime(candidate)

    rs = evaluate_relative_strength(candidate)

    setup = evaluate_setup(candidate, regime, rs)

    if not setup.valid:
        return REJECT("SETUP_INVALID")

    option_candidates = scan_option_chain(candidate)

    option = select_option(
        option_candidates,
        delta_range=RESEARCH_RANGE,
        dte_range=RESEARCH_RANGE,
        iv_context=True,
        liquidity=True
    )

    if option is None:
        return REJECT("OPTION_INVALID")

    risk = calculate_scenario_risk(
        candidate,
        option,
        invalidation=setup.invalidation
    )

    if risk.worst_case > max_trade_risk():
        return REJECT("RISK_LIMIT")

    probability = estimate_conditional_outcomes(
        candidate,
        regime,
        setup,
        option
    )

    ev = calculate_net_expectancy(
        probability,
        risk,
        execution_costs()
    )

    opportunity_score = calculate_opportunity_score(
        regime,
        setup,
        rs,
        option
    )

    risk_penalty = calculate_risk_penalty(
        macro_state,
        regime,
        option,
        liquidity_state()
    )

    net_score = opportunity_score - risk_penalty

    if not meets_production_threshold(ev, net_score):
        return REJECT("INSUFFICIENT_EDGE")

    quantity = calculate_position_size(risk)

    if quantity < 1:
        return REJECT("POSITION_TOO_LARGE_FOR_RISK")

    return AUTHORIZE(
        candidate=candidate,
        option=option,
        quantity=quantity,
        expected_value=ev,
        score=net_score
    )
```

---

# 77. ABSOLUTE PRODUCTION RULE

No component may override the Risk Engine.

Not:

- probability;
- score;
- catalyst;
- technical strength;
- machine-learning confidence;
- historical expectancy.

If risk says:

**NO**

the system says:

**NO.**

---

# 78. MACHINE LEARNING POLICY

Machine learning may eventually be used for:

- conditional probability estimation;
- regime classification;
- feature interaction discovery;
- anomaly detection;
- drift detection.

It must not initially be used as an opaque "buy/sell" oracle.

First build:

**interpretable deterministic baseline.**

Then compare ML against it.

If ML cannot outperform the baseline out of sample after costs:

**do not deploy ML.**

---

# 79. BASELINE STRATEGY

The first production candidate should remain simple:

```text
Market/sector aligned RS
+
persistent divergence
+
valid technical setup
+
reasonable IV
+
liquid option
+
defined invalidation
+
positive net expectancy
```

Only after proving this baseline should complexity be added.

---

# 80. WHAT SUCCESS LOOKS LIKE

The project succeeds if it can eventually produce a statement such as:

> Under regime X, for setup RS-04, when beta-adjusted relative strength exceeds threshold Y, sector confirmation is present, volume exceeds Z, IV percentile is within range A–B, DTE is within range C–D, and Delta is within range E–F, historical out-of-sample trades generated positive net expectancy after realistic spread and slippage assumptions, with maximum drawdown within the system's risk budget.

That is a research conclusion.

Not a prediction.

---

# 81. FINAL SYSTEM LAWS

### LAW 1
**Capital preservation outranks opportunity.**

### LAW 2
**Risk is defined before reward.**

### LAW 3
**Every trade must have an invalidation condition.**

### LAW 4
**Average loss is not a risk limit.**

### LAW 5
**Every trade must survive realistic execution costs.**

### LAW 6
**SPY is not the only benchmark.**

### LAW 7
**Relative strength must be measured hierarchically.**

### LAW 8
**IV is part of the trade thesis.**

### LAW 9
**Delta, Gamma, Theta, Vega, DTE, and IV must be evaluated together.**

### LAW 10
**A catalyst is context, not an automatic bullish/bearish signal.**

### LAW 11
**No future information may enter a historical simulation.**

### LAW 12
**No parameter earns production status from in-sample performance alone.**

### LAW 13
**A strategy must survive walk-forward testing.**

### LAW 14
**A strategy must survive realistic slippage.**

### LAW 15
**The engine must be willing to say NO TRADE.**

### LAW 16
**Production parameters must be version controlled.**

### LAW 17
**The learning engine may propose; it may not silently alter production.**

### LAW 18
**Data uncertainty is a reason to stop, not improvise.**

### LAW 19
**Winning trades do not prove an edge.**

### LAW 20
**The only acceptable production edge is one that survives out-of-sample evidence.**

---

# 82. IMPLEMENTATION ROADMAP

## PHASE 1 — DATA FOUNDATION

Build:

- market data ingestion;
- options chain ingestion;
- historical storage;
- macro calendar;
- sector mapping;
- corporate-action handling;
- timestamp normalization;
- data-integrity service.

**No trading.**

---

## PHASE 2 — RESEARCH ENGINE

Build:

- regime engine;
- hierarchical RS;
- setup engine;
- option filters;
- Greeks;
- IV analytics;
- expected move;
- risk engine.

**No trading.**

---

## PHASE 3 — EVENT-DRIVEN BACKTESTER

Build:

- point-in-time simulation;
- option-chain replay;
- realistic fills;
- slippage;
- commissions;
- MAE/MFE;
- walk-forward;
- Monte Carlo.

**No trading.**

---

## PHASE 4 — RESEARCH DISCOVERY

Run the experiment matrix.

Identify:

- robust RS thresholds;
- best regimes;
- best setups;
- Delta ranges;
- DTE ranges;
- IV conditions;
- time windows;
- exit methods.

**No trading.**

---

## PHASE 5 — PAPER

Run real-time signals.

Measure:

- signal frequency;
- quote quality;
- execution assumptions;
- live vs historical feature distributions.

**No capital.**

---

## PHASE 6 — SHADOW

Run production-intended orders without transmitting them.

Measure:

- intended fills;
- simulated fills;
- slippage;
- latency;
- missed opportunities;
- execution drift.

**No capital.**

---

## PHASE 7 — MICRO PRODUCTION

Only after validation.

Use the smallest practical capital allocation.

The objective is not profit.

The objective is:

**validate that the production system behaves like the research system.**

---

## PHASE 8 — CONTROLLED SCALE

Increase capital only when:

- live expectancy remains within validated range;
- drawdown remains acceptable;
- execution costs remain acceptable;
- no significant model drift occurs.

---

# 83. FINAL ARCHITECTURAL OBJECTIVE

The completed platform is not merely:

**an options scanner.**

It is:

> **A closed-loop quantitative research, risk, execution, telemetry, and learning system that continuously tests whether relative strength creates a statistically exploitable options edge without allowing the learning process to compromise capital controls.**

The core loop is:

```text
OBSERVE
   ↓
CLASSIFY
   ↓
MEASURE
   ↓
FILTER
   ↓
MODEL
   ↓
RISK
   ↓
EXECUTE
   ↓
MEASURE OUTCOME
   ↓
COMPARE TO EXPECTATION
   ↓
DETECT DRIFT
   ↓
RESEARCH
   ↓
VALIDATE
   ↓
VERSION
   ↓
DEPLOY
```

**The engine's greatest advantage should ultimately be its ability to discover when its own assumptions stop working.**
