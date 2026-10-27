# Phase 3 — Strategy Research (first increment)

The research engine now offers three predefined **causal** candidate families:

- **Trend:** close beyond the previous lookback high/low with volume multiple confirmation, aligned to the direction of a completed higher-timeframe context candle.
- **Mean reversion:** RSI overbought/oversold and a close outside the prior range, conditioned on completed context direction (contrarian).
- **Volatility breakout:** close outside prior range with current expansion versus past median range and volume confirmation, aligned to higher-timeframe context.

Default signal timeframe 5m and context timeframe 1h. All OHLCV features are derived only from verified continuous 1-minute candles. Both strategy and context timeframe bars must **fully close** before signals can enter the next 1-minute open. Context and indicator warmups reset on real gaps and chronological partition boundaries.

The manual `BTC Phase 3 strategy comparison` GitHub workflow runs all regression tests, assembles SHA-verified data via Azure read-only OIDC, evaluates **training and validation only**, and uploads separate trades/equity CSVs and `strategy_comparison.json`. It preserves the holdout as `locked`; it never trades it.

**Limitations:** This Phase 3 first increment is an exploratory comparison, not optimization or evidence of profit. It retains the baseline linear USD spot-equivalent backtester with static fees and slippage, no funding, contract margin or liquidation simulation. No perpetual strategy is strictly exempt from funding just because the strategy logic does not use funding rates; the next Phase 3 increments should add holding-time limitations and conservative funding-boundary avoidance, plus training-only search and validation control. Do not cherry-pick among repeatedly tested validation outcomes. No live trading or capital allocation.

Run workflow on main with `2024-02-03` through `2026-10-26` (exclusive), signal `5m`, context `1h`. Inspect trade counts, losses, turnover, costs and boundary handling before expanding any parameter search.
