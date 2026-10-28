# Phase 4 Step 2 — Regime-Conditioned Price and Volume Analysis

## Objective
Determine whether the **descriptive** regimes built in Phase 4 Step 1 correspond to different subsequent BTC price behavior in the **training partition only**. These are outcome labels for scientific research, never trade entry features or an executable strategy.

## Frozen protocol
- Verified BTCUSD 1-minute segments assembled via existing catalog and SHA256 integrity checks; crop to original 60% training interval, with feature warmups and future-return windows reset at every gap and training split.
- Regime classifier unchanged: completed hourly candles, 24-hour normalized displacement trend score, ATR percentage, relative hourly volume; predeclared regime and elevated-volume thresholds.
- Forward close-to-close returns over **1, 4, 24 hours** measured starting from the classified hour's **close**, not its open; future observation must be exactly the requested time offset in the same segment.
- Realized future volatility from sum of future hourly log-return squares (not annualized).
- Return statistics: count, arithmetic mean, median, positive fraction and mean realized volatility; for uptrend/downtrend also directional continuation fraction. Ranges have no assumed direction.
- Grouped comparisons: regime alone and regime × normal/elevated volume. Report raw trend-score quantiles (0,1,5,25,50,75,95,99,100%) **without adjusting thresholds in this run**.
- Non-overlapping UTC hour anchors for each horizon; approximate normal 95% confidence interval only with at least **30** such anchors. These are still not fully independent because market states cluster and multiple comparisons occur. Report insufficiency explicitly.

## Artifacts
`training_forward_labels.csv`: descriptive features with next-1/4/24h outcomes, null for unavailable future; may **never** be used as a live signal input.
`conditional_outcomes.json`: metadata, catalog fingerprint, sample counts, score distributions and grouped metrics.

## Guardrails
This is **research on training data, not evidence of a profitable strategy**. No executed orders, transaction-cost-adjusted P&L or validation/holdout evaluation. Low trending-class support from Step 1 (only 202 directional hours) requires explicit caution. No adaptive parameter fitting or threshold changes based on this single report.

Actual Delta India BTCUSD funding settlements, mark-to-market, INR accounting and liquidation were deferred in Phase 2 and cannot be inferred from these outcomes.

## Workflow
Review/merge this PR, then manually dispatch `BTC Phase 4 conditional outcomes research` on `main`, inputs start `2024-02-03`, end exclusive `2026-10-26`, signal timeframe `5m` (unused), context timeframe `1h` (classifier fixed). Run regression suite and inspect group counts, intervals and artifact before proposing Step 3 hypotheses.

## Progress
1. Market-regime foundation — validated, workflow #40624861531.
2. Regime-conditioned returns/volume analysis — **this PR**.
3. New strategy hypotheses — pending.
4. Cost-aware walk-forward tests — pending.
5. Candidate gate and controlled validation — pending.
