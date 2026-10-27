# Phase 3 forensic increment: transition-only entries and execution-cost attribution

After diagnostic run #40556107474, the investigation identified sustained candidate entry signals and excessive trading as a possible driver of negative performance. We are testing that hypothesis, **not declaring a fix profitable**.

## Paired experiment
The existing risk engine behavior (`entry_mode="level"`) remains the default for backward compatibility. The training-only `phase3_risk_compare.py` runner executes each of the three signal families twice on identical verified data, signal parameters, fee/slippage settings, ATR settings and risk policies:
- `level`: legacy behavior; after a close and cooldown, may open a fresh trade while the same nonzero signal persists.
- `transition`: an entry is eligible only when the previously completed signal changes from zero/opposite into nonzero. A transition rejected for cooldown, funding guard or risk lockout is **not queued for later**. Each gap-separated segment resets signal history. Signals still trigger next-minute open fills.

## Cost accounting
Each trade now records `gross_before_slippage`, `slippage_cost`, `fees`, `total_execution_cost`, `net_pnl`, and its actual `exit_reason`. The training report includes cost and P&L totals per exit reason, and checks:

`gross_before_slippage - slippage - fees = realized net P&L = ending equity - initial equity`.

This enables attribution of exchange fees versus simulated adverse slippage. These cost assumptions are not proven Delta historical fills. No funding charges or liquidation model is implied by boundary guards.

## Workflow and constraints
Rerun manual `BTC Phase 3 risk controls training validation` with `2024-02-03` to exclusive `2026-10-26`, 5m signals, 1h context. The workflow compares both entry modes for each strategy, archives six trading ledgers and six equity curves plus `risk_comparison.json`. Runs only the training partition; validation and holdout remain reserved/locked. Do **not** optimize against or repeatedly inspect them.

Evaluate whether transitions reduce entries and trading costs *and* whether they materially change gross edge and risk-adjusted outcomes. Strategy profitability is not established by cutting trading frequency alone. Live trading remains disabled.
