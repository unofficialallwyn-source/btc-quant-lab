# Phase 4 Step 4 — Cost-Aware Training-Only Walk-Forward Evaluation

## Purpose
Test the three hypotheses frozen in Phase 4 Step 3, without tuning their settings after inspecting Phase 4's exploratory regime diagnostics. No validation or holdout market data is evaluated.

## Experiment
- Existing verified BTCUSD 1m historical catalog, SHA256-checked segments and original chronological 60% training partition.
- Three disjoint UTC calendar-time training folds, with indicators and positions reset between folds and natural data gaps.
- Three frozen hypotheses: high-volatility range continuation, exhaustion reversal, and trend-transition breakout.
- One no-trade cash baseline with exactly zero gross, fees, slippage and net P&L.
- Each fold starts a fresh $1,000 simplified USD portfolio. **Sum of fold P&L is not a continuous portfolio backtest.**
- Risk engine uses the unchanged Phase 4 hypothesis policy: next-minute entry after closed HTF signal, transition-only entries, ATR stop 2x, target 2R, max hold 60m, cooldown 15m, risk .5% equity, 1x exposure, modeled .05% per-side fees and .025% per-side slippage, funding *time guard* (not settled cash funding).
- Metrics per fold: gross before slippage, slippage, fees, net, gross/net expectancy per trade, returns, profit factor, max drawdown, win rate and exit reasons; enforce ledger and ending-equity reconciliation.

## Frozen eligibility
Any candidate must satisfy **in each of the three folds**:
- >=20 closed trades;
- positive net P&L;
- profit factor >1;
- maximum drawdown <=25%.

The result is either `NO_QUALIFYING_CANDIDATE` or `TRAINING_CANDIDATES_REQUIRE_MANUAL_REVIEW`. This research runner **never authorizes a promotion or evaluates validation/holdout**. There is no forced winner or optimizer sweep.

## Caveats
Training-only evaluation is exploratory, and historical returns are not a forecast. No exchange-accurate Delta India BTC perpetual historical funding, margin, liquidation or INR contract ledger. The results are a simplified USD linear research model. Cost estimates may diverge from realized execution.

## Operation
Once PR is approved/merged, dispatch `BTC Phase 4 cost aware walkforward` on main using 2024-02-03 inclusive to 2026-10-26 exclusive (signal_tf 5m, context_tf 1h; these are frozen within strategy specs). Check regression tests, the artifact `walkforward_report.json`, fold-by-fold metrics and decision before Phase 4 Step 5.

## Phase 4 progress
1. Market regime foundation — validated.
2. Regime-conditioned outcomes — validated.
3. Three frozen strategy hypotheses — validated.
4. Training-only cost-aware walk-forward — **this PR, pending workflow**.
5. Candidate gate and controlled validation — pending; validation only after qualified candidate is reviewed and frozen.
