# Phase 4 — Strategy Discovery and Market-Regime Research

## Objectives and gates
Phase 3 closed with **no qualifying model**, not a profitable strategy. Phase 4 must discover genuinely new price/volume hypotheses without leaking reserved data or exhaustively tuning prior failed strategies.

1. **Market-regime foundation (this PR):** describe BTC behavior using completed 1h candles. Output frozen, training-only regime distribution and per-bar features.
2. **Regime-conditioned diagnostics:** measure future returns and realized execution-cost distribution by regime with strict horizons, purge/embargo and no leaking labels into features; report sample counts and uncertainty.
3. **New strategy hypotheses:** predeclare a small number of distinct entry/exit mechanisms using the evidence. Include explicit no-trade baseline.
4. **Cost-aware training-only experiments:** walk-forward testing and robustness across calendar folds, gap-safe implementation and transaction-cost stress.
5. **Controlled candidate promotion:** if and only if training gate passes, freeze strategy, use a single validation evaluation; final holdout remains sealed until the final research protocol.

## Step 1 methodology
For each gap-free training segment, aggregate verified 1m BTC OHLCV to completed UTC-aligned 1h candles. Rolling feature warmups reset per segment. Calculate:
- ATR percentage (14 completed bars) using true range;
- directional displacement divided by ATR and square root of 24 bars, a descriptive trend score;
- volume relative to preceding 24 completed hourly volume observations.

Predeclared thresholds: absolute trend score >=1.5 implies directional trend (sign labels up/down); otherwise range. ATR percentage >=1.2% adds a high-volatility prefix. Volume ratio >=1.5x adds an elevated-volume label. These **are exploratory heuristic regimes**, not calibrated probabilities or market predictions.

The script produces training_regimes.csv and regime_summary.json with count distributions, transition counts, per-segment classification and catalog SHA-256. Features are computed after a complete candle closes, so decisions could only occur at or after that close. No profit, forward returns, forecasting, strategy simulation or execution claims in Step 1.

## Safeguards
Read data using checked catalog SHA256 and pre-existing gap-safe segments, crop to the original chronological 60% training split. Neither validation nor final holdout is evaluated. No live orders. Phase 2 Step 3 actual Delta contract funding/INR/margin/liquidation accounting remains deferred.

## Workflow
After reviewer approval and merge, manually dispatch [BTC Phase 4 market regime foundation](../.github/workflows/btc-phase4-market-regimes.yml) on main with start 2024-02-03, exclusive end 2026-10-26, context_tf 1h (signal_tf is unused by this descriptive step). Check regression suite and research artifact before Step 2.
