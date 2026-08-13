# HoneyDrip × Robinhood Trading MCP — Execution Playbook

Claude Code reads this file when executing trades via the Robinhood Trading MCP.

---

## Setup (one-time, on your local machine)

```bash
claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
```

Then in Claude Code: `/mcp` → select `robinhood-trading` → authenticate with your Robinhood credentials.

---

## Running the engine

```bash
export HONEYDRIP_ARMED=YES
export HONEYDRIP_MODE=live_mcp
export HONEYDRIP_EQUITY_ESTIMATE=<your account equity in USD>
python -m honeydrip_bot.engine
```

This writes approved signals to `honeydrip_bot/pending_signals.json`. Then ask Claude Code:

> "Execute the pending HoneyDrip signals using the Robinhood MCP."

---

## Execution workflow (Claude Code follows this)

1. **Read pending signals**
   ```
   Read honeydrip_bot/pending_signals.json
   ```

2. **Check account**
   Use Robinhood MCP `get_account` to verify buying power and current equity.
   If equity is significantly different from the engine's estimate, re-run risk sizing.

3. **For each approved signal:**

   a. **Get quote** — confirm current price is within 2% of signal price
      ```
      robinhood-trading: get_quote(symbol=<ticker>)
      ```

   b. **Confirm position size** — shares are pre-calculated by risk_manager.py
      Verify: `shares × current_price ≤ equity × 0.05` (5% position cap)

   c. **Place order**
      ```
      robinhood-trading: place_order(
          symbol=<ticker>,
          quantity=<shares>,
          side=<buy|sell>,
          type=market,
          time_in_force=day
      )
      ```

   d. **Log the trade**
      After each execution, call `trade_logger.log_trade()` with the result:
      ```python
      from honeydrip_bot.trade_logger import log_trade
      log_trade({
          "ticker": signal["ticker"],
          "action": signal["action"],
          "shares": signal["risk"]["shares"],
          "signal_source": signal.get("source", "honey_drip"),
          "mode": "live_mcp",
          "execution_result": {
              "order_id": <robinhood order id>,
              "status": <filled|pending|rejected>,
              "fill_price": <actual fill price or None>,
              "realized_pnl": 0.0,  # update when position closes
          },
      })
      ```

4. **Clear pending signals** after all executions
   ```python
   import os
   os.remove("honeydrip_bot/pending_signals.json")
   ```

---

## Managing open positions — AAPL Stabilized Pro exit rules

The active strategy (`signal_bridge.py`) has a defined exit plan. When a position
is open, on each check (at minimum once per trading day):

1. Get current position from Robinhood MCP (`get_positions`) — note entry price
2. Get current quote and the highest price since entry (from daily bars)
3. Call the exit evaluator:
   ```python
   from honeydrip_bot.signal_bridge import evaluate_exit
   result = evaluate_exit(entry_price, current_close, highest_high_since_entry)
   ```
4. If `result["exit"]` is `True` → place a market sell for the full position,
   log the trade with `realized_pnl`, and record `result["reason"]`
5. If `False` → hold; `result["stop_price"]` is the current effective stop

Exit rules encoded in `evaluate_exit`:

| Condition | Action |
|-----------|--------|
| Close ≥ entry × 1.20 | Sell — 20% target reached |
| Peak profit ≥ 3% | Stop moves to breakeven |
| Peak profit ≥ 6% | Stop trails 3% below close |
| Close ≤ stop | Sell — defensive exit (initial stop: entry × 0.955) |

---

## Risk rules — enforce before every order

| Rule | Limit |
|------|-------|
| Max position size | 5% of account equity |
| Max daily realized loss | 2% of account equity |
| Min account equity to trade | $1,000 |
| Min signal confidence | 60% |

If any rule would be violated by the order, **skip it** and log the rejection reason.

---

## Safeguards

- Never place an order if `HONEYDRIP_ARMED != "YES"` in the environment
- Never exceed the pre-calculated `shares` value from `pending_signals.json`
- If Robinhood MCP returns an error, log it and stop — do not retry automatically
- All trades must be logged regardless of fill status
