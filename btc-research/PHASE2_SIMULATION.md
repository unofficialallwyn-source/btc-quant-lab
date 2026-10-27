# Phase 2: Conservative simulation-only backtesting baseline

The engine reads Phase 1 **verified SHA-256 gap-safe Parquet segments**. No missing historical days are recovered. It evaluates a causal 20-bar channel breakout on 1-minute candles. Signal at the **close** of one candle may fill only at the **next candle open**. Execution includes adverse slippage and entry/exit notional fees. Stop/target collisions resolve **stop first**. Each segment starts flat and any open position is closed on its last observed candle, without pretending that trades continued through missing time. Equity and a full trade ledger are generated.

Initial equity: USD 1,000. Default fees 0.05% per side and simulated slippage 0.025% per fill. Stop distance 1%, profit target twice the stop, per-trade stop-risk budget 0.5% of current equity, notional limited to 1x.

**Important modeling limitation:** This is a simple linear spot-equivalent BTC P&L sandbox; shorts use a simplified convention. It does **not** model Delta Exchange India BTCUSD contract specifications, real margin, maintenance margin/liquidation, funding, spread and depth, order-book queueing, or true exchange fills. Therefore results are not deployable exchange performance and **must not** be used to justify real trading.

The initial full-span backtest is a **smoke/baseline measurement, not out-of-sample performance**. The next PR should implement fixed chronological research/validation/untouched holdout windows, timeframes, funding/contract mechanics, mark-to-market margin, reproducible evaluation reports, and more realistic entry/exit execution.

Run manual GitHub Actions workflow `BTC Phase 2 simulation baseline` with start `2024-02-03`, exclusive end `2026-10-26`. This reassembles verified Azure data and writes `metrics.json`, `trades.csv`, `equity.csv` as a temporary GitHub artifact. No live trading; no scheduled collection.

Do not infer causality from a custom `signal_fn` without independently checking it for future leakage. The built-in breakout signal uses trailing levels only.
