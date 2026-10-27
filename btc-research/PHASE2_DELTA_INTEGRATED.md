# Phase 2 Step 3 — Integrated Delta India BTCUSD historical research

## Scope now implemented
- `src/delta_sim_engine.py`: INR-denominated, isolated research engine with 0.001 BTC integer-lot rounding, margin reservation checks, maker/taker primitives (all simulated fills currently **taker**), trading fees plus GST, observed minute mark-price maintenance tests, UTC 8h funding debits/credits, configurable adverse slippage and separate gap-flat trades.
- Each simulated trade enters at the **next 1m bar open** after a *completed* 1m/5m/15m/1h/4h signal; stop/target collision resolves stop first. The terminal bar exits positions. Historical trades and equity are exported separately for training and validation.
- `src/delta_market_inputs.py`: strict timestamp coverage and provenance checks. Requires contemporaneous 1-minute `mark_1m.csv`, `fx_1m.csv`, 8-hour observed funding settlement `funding_8h.csv`, `source_manifest.json`. No interpolated/made-up prices, no assumed constant FX and no silently zero funding.
- `src/delta_eval.py`: independently starts training/validation with INR 85,000 by default, preserves the chronologically locked holdout, writes coverage and results with source provenance.
- `src/delta_public_history.py`: bounded/retried public, **read-only** Delta India historical mark/funding *candle* acquisition at /v2/history/candles (up to 2000/page). Raw funding candles **must not be treated as settlement events without reconciliation**.
- `src/delta_external_blob.py`: read-only Azure OIDC staging of private external data. Manual single workflow `BTC Phase 2 Step 3 integrated Delta validation` runs all tests, reexports checksum-verified BTC price dataset, and then optionally stages external feeds and simulates.

## Historical data readiness (not yet demonstrated)
BTCUSD 1-minute traded OHLCV in Azure does **not** contain actual INR/USD conversion, mark prices or timestamped funding settlement rates. Thus the single workflow defaults to a documented `BLOCKED_MISSING_EXTERNAL_MARK_FX_FUNDING` readiness report; it **does not** claim realistic backtest results or fabricate missing data. Unit/integration tests can pass independently.

To obtain historical research outputs, place reviewed datasets under one common Azure Blob prefix (the existing Azure OIDC identity needs read permissions):
- `mark_1m.csv`: columns `time,mark_usd`; **one observed mark value per minute timestamp**, UTC Unix seconds, not a proxy traded close.
- `fx_1m.csv`: columns `time,inr_per_usd`; **one timestamped externally sourced INR/USD observation per minute**. Historical daily RBI references do not prove each minute's FX settlement rate and should not be forward-filled without explicitly adopting and documenting a proxy model.
- `funding_8h.csv`: `time,rate` rows at *observed* UTC funding timestamps divisible by 28800, signed decimal settlement rates (0.001 means +0.1%). Public `FUNDING:BTCUSD` candles alone may not unambiguously represent these settlement events.
- `source_manifest.json` with nonempty fields `mark_source`, `fx_source`, `funding_source`, `methodology`, `recorded_utc`, and optional `synthetic:false`.

The readiness gate requires coverage for all training and validation price minutes **and** candidate 8-hour funding boundaries, even if a strategy is flat at those times. Real evaluation fails if any required observation is missing, invalid or contradicts the expected alignment.

Dispatch [GitHub Actions](../../.github/workflows/btc-phase2-step3-integrated.yml) on `main`, start `2024-02-03`, exclusive end `2026-10-26`, timeframe `5m`; when reviewed external inputs are available, provide their **relative Azure Blob prefix** in the optional input. Without that prefix, the workflow validates the implementation and archives a machine-readable evidence-gap report.

## Accuracy limits
**This is a constrained research model, not a verified exchange-matching or liquidation engine.** Delta's public contract page describes mark-based margin/liquidation, tiered margin scaling, and fair-price marks. This engine throws `UNMODELLED_LIQUIDATION` when a maintenance breach is observed at a 1m mark; **it never invents a liquidation fill or post-liquidation equity**. Within-bar mark-price excursions, maker queue fill probabilities, varying fee tiers, exchange slippage under stressed conditions, funding event ordering, and historical contract/spec revisions remain unknown. Position exposures are conservatively capped at 1x, and >USD 100,000 tier margin remains unsupported and raises. The entry/exit fill prices are *simulated*, not actual order-book fills.

The existing $1,000 USD engine remains available unchanged for baseline comparisons; the INR research model must not directly compare raw capital/returns without distinguishing the currencies. The final holdout is never evaluated in this workflow. No live order permissions, real orders, or scheduled trading.
