# Phase 3 Step 4 — Constrained Training-Only Optimization

## Status and scope
Phase 3 consists of five steps:
1. Strategy framework — validated.
2. Initial three-strategy comparison — validated.
3. Risk controls, diagnostics and quality-filter ablation — validated as research tooling; not profitable.
4. Training-only parameter optimization — **this PR**, pending CI and research results.
5. Controlled single-pass validation and shortlist — pending.

Historical research is simulation-only. Step 3 of Phase 2 (exchange-accurate funding/contract execution) remains deferred. The validation and final holdout partitions remain reserved.

## Pre-registered grid
Target is *only* volatility breakout, with all four causal quality gates enabled and transition-only entry logic. Training performance from ablation workflow #40617952461 was -23.0183% despite positive $55.54 model gross before slippage; it is not a successful strategy.

Fixed grid, 16 candidates:
- ATR stop multiple: 2.0 or 3.0
- Maximum holding minutes: 30 or 60
- Cooldown minutes: 15 or 45
- Minimum ATR to estimated round-trip cost: 2.0 or 3.0

All other parameters and costs stay fixed. Three consecutive UTC calendar-time folds subdivide only the original chronological **training** window; historical data gaps are preserved and no signals cross folds. Each fold starts with an independent $1,000 USD-simulated portfolio (not a continuous out-of-sample wealth curve).

## Decision rules
A candidate is eligible *only if every training fold* has at least 20 trades, net realized P&L greater than zero, profit factor >1, and maximum drawdown <=25%. Among eligible candidates, rank by highest minimum-fold return, then lower maximum-fold drawdown, then fixed candidate ID. If none qualifies, return `NO_QUALIFYING_CANDIDATE`; **do not force a winner**.

Outputs `training_optimization.json` with per-fold net, modeled gross P&L, fees, slippage, trade count, drawdown, profit factor, parameters, data catalog SHA256 and decision.

## Guardrails and next steps
- Training-only exploratory optimization is **not a guarantee of statistical robustness**; even multiple folds share market history and parameter search introduces selection bias.
- No validation results used for tuning. Only once a candidate and thresholds are frozen should Step 5 run a single controlled validation and decide whether to reject or shortlist.
- Holdout stays locked until much later, following a fixed protocol; no live order placement.
- Fees/slippage are simplified assumptions. Actual Delta India BTCUSD funding, INR settlement, liquidation, margin and contract details have not been accounted for; results cannot be called exchange-realistic.

After reviewer approval and merge, dispatch `BTC Phase 3 training-only optimization` on `main` with 2024-02-03 to 2026-10-26 exclusive, 5m signal, 1h context. Check the full test suite and decision/report before proceeding.
