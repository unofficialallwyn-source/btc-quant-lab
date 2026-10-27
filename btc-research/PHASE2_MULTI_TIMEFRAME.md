# Phase 2 Step 2 — Causal multi-timeframe signal infrastructure

**Available signal intervals:** `1m`, `5m`, `15m`, `1h`, `4h`.

The trusted research input remains the verified, gap-safe BTCUSD 1-minute segment collection. Aggregation is aligned to absolute UTC boundaries (`time // timeframe_seconds`), using first open, max high, min low, last close, and sum volume. **Only full higher-timeframe buckets are kept**. A bucket beginning or ending inside a segment, historical gap or train/validation split is discarded rather than treated as a complete candle.

Signal generation uses a causal 20-bar channel-breakout baseline on finished higher-timeframe bars. A bar opening at `t` with duration `D` is **not observable until t+D**; only then is its close-derived signal exposed to the 1-minute simulation. The simulation may enter on the **following** 1-minute bar's open. Before any higher-timeframe bar has fully closed, higher-timeframe signals are zero. Indicators restart at each real data gap and evaluation partition boundary. The **holdout remains locked** in the GitHub workflow.

The new `--timeframe` choice in the manual GitHub workflow `BTC Phase 2 chronological evaluation` selects the timeframe of the signal. Execution is still at **1-minute resolution**: stop/target checks use the original 1-minute candles. The default manual workflow choice is `5m`; standalone CLI default remains `1m` for backward compatibility.

Backtests using different signal timeframes are *engineering comparisons*, not verified profitable strategies. Existing engine limitations remain: simplified linear P&L, no funding, Delta-contract margin/liquidation, queue position or depth. These exchange-specific rules are planned for Phase 2 Step 3.

No missing-day recovery, scheduled jobs, holdout evaluation or live trading.
