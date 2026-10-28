# Phase 4 Step 3 — Frozen Strategy Hypotheses

This step specifies three **new**, causal research hypotheses. It deliberately does not access market history or simulate P&L. The previous regime analyses (Phase 4 Steps 1–2) were descriptive training-only studies, not trading proof.

## Frozen strategies
All signals use fully completed 5m OHLCV and completed 1h regime context; missing indicator warmup, gaps, absent context, volume below 1.5x trailing average, or ATR below 2x modeled round-trip fee+slippage mean **no trade**.

1. **High-volatility range continuation:** within a completed high-volatility-range hourly context, enter long on a finished 5m price breakout above the prior 12-bar high and bullish body; short below the corresponding low with bearish body. Requires 5m relative volume and cost-movement filters.
2. **Exhaustion reversal:** within a completed ordinary ranging hourly context, require the preceding completed 5m RSI below 25 for a long, or above 75 for a short; current completed candle reverses direction and price vs preceding close. Volume and cost filters apply.
3. **Trend-transition breakout:** an hourly normalized trend score crosses +1.0 (long) or -1.0 (short) from the other side of the threshold; require aligned finished 5m channel breakout, volume and cost filters.

These are hypotheses only, not evidence of predictive advantage. The trend-transition threshold is predeclared for this new hypothesis and is not a silent recalibration of the Step 1 descriptive threshold of ±1.5.

## Frozen risk and exit proposal for Step 4
Transition-only entries, one position at a time, ATR(14) stop 2x and 2R target, 60-minute maximum holding, 15-minute cooldown, simulated adverse slippage 0.025% per side, fees 0.05% per side, fixed 0.5% equity risk/trade and max 1x exposure. Existing simulator additionally applies 10-minute funding-boundary guard around assumed 00/08/16 UTC settlement periods. These assumptions remain a **simplified USD research model**, not Delta India exchange-accurate economics.

## Separation of research stages
- **Step 3**: source code, unit tests, frozen `hypothesis_spec.json` artifact; do not evaluate returns or optimize thresholds.
- **Step 4**: run all three frozen hypotheses against *training-only*, gap-safe chronological folds. Include a cash/no-trade reference and compare gross-before-slippage, fees, slippage, net return, trade counts, expectancy, max drawdown and robustness. Reject strategies that fail, do not widen the grid merely to force success.
- **Step 5**: only if fixed training gates pass and human review authorizes a frozen candidate, conduct controlled validation. Holdout remains locked.

No live trading, no validation/holdout access; no historical funding, INR margin or liquidation modeling. Output `hypothesis_spec.json` can be audited before backtests.
