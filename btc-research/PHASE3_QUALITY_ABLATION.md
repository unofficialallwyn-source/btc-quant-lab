# Phase 3: Predeclared Signal Quality Ablation

## Objective
Assess whether excluding low-quality trades improves **gross trading expectancy** and net results, without using validation or holdout observations for model selection. Historical baseline run #40563083493 showed transition-only strategies losing 91.8%–99.4% on training after modeled execution costs.

## Fixed experiment
For each of the three existing strategies (trend, mean reversion, volatility breakout) under unchanged risk settings and causal 5m signal / 1h context, compare six filter variants:
- baseline (no additional quality filter)
- completed 1h context absolute trend-strength >= 0.6% measured over prior 12 completed context bars
- 5m 14-bar ATR fraction between 0.05% and 2.5%
- completed 5m relative volume >= 1.5x past 20 completed 5m volumes
- 5m ATR >= 2x estimated round-trip fees plus slippage; **heuristic**, not forward price prediction
- all four together

These thresholds were **predeclared before seeing experimental results**. Signal generation uses only fully closed higher-timeframe observations. The filter masks signals; a filtered-out signal is not queued for future entry. The transition-entry engine then uses next-minute execution. Training-only ablation output `quality_ablation.json` includes trade count, gross before slippage, slippage, fees, net returns, drawdown and P&L reconciliation per variant.

## Non-goals / caveats
- Do not interpret lower trade count alone as an improvement. Analyze gross pre-cost expectancy and net cost together.
- A pass/fail comparison of six variants is exploratory hypothesis screening, **not parameter optimization** or statistical significance evidence.
- No real historic funding charges; fund guard is a scheduling assumption. Delta INR contract rounding/margin and liquidation remain unmodeled.
- Test on training only; validation and holdout remain reserved. No live trades.
- Date-split and gap-boundary resets inherited from existing framework.

## Workflow
After PR review/merge, dispatch `BTC Phase 3 signal quality ablation` on `main` with start `2024-02-03`, exclusive end `2026-10-26`, signal timeframe `5m`, context `1h`. Inspect full test suite and `quality_ablation.json` artifact before Step 4 optimization.
