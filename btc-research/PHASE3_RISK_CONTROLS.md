# Phase 3 Step 3 — Risk and duration controls

Phase 3 comprises five milestones. The first two (signal framework and fixed-candidate comparison) passed in GitHub run #40545031560. **Three milestones remained at the start of this work:** (3) risk/holding-time controls, (4) training-only optimization, (5) controlled validation and shortlist.

`risk_engine.py` is an independent, research-only linear USD P&L engine for the fixed Phase 3 strategy signals, with:
- ATR derived from fully completed signal-timeframe candles (default lookback 14, ATR stop distance 2x).
- Maximum holding period 60 minutes; time-based forced exit at subsequent 1m open.
- Entry cooldown of 15 minutes after exit.
- 2% daily loss-based **entry lockout**; it does **not** guarantee a maximum daily realized loss during an open position or jumps.
- Conservative boundary guard: no new entries within 10 minutes of each assumed 00:00/08:00/16:00 UTC funding event; closes existing simulated positions at bar open when guard begins. Funding calendar is a guard assumption, **not** observed historical funding data.
- All gap boundaries flatten positions and reset causal indicator calculations.
- Default risk fraction 0.5%, max notional exposure 1x, slippage 0.025% and taker fees 0.05% each side.

`phase3_risk_compare.py` executes the three existing predefined strategies **on the training partition only**. Unlike our initial exploratory Phase 3 run, the validation data is reserved for later controlled evaluation. Final holdout is never evaluated. It exports risk-managed training trades and equity plus `risk_comparison.json`.

The manual GitHub workflow `BTC Phase 3 risk controls training validation` runs regression tests, verifies the Azure historical dataset and writes training-only evidence; name refers to validating risk-control implementation, **not** running the historical validation partition.

Important limitations: USD-linear P&L is not actual Delta BTCUSD contract settlement. Funding debits and liquidation risk are **not** modeled; a boundary embargo only reduces, not proves elimination of, funding exposure. There is no deployment or live order placement. The strategy signals are not profitable yet and parameter optimization may fail. Do not choose Phase 3 parameters by repeatedly inspecting validation or touching holdout.

Run after PR merge with start `2024-02-03`, exclusive end `2026-10-26`, signal `5m`, context `1h`. Review tests and research metrics before any optimization.
