# BTC Quant Lab

Research-first BTCUSD strategy development, with historical Delta Exchange OHLCV data, reproducible backtests, and out-of-sample evaluation.

> **Status:** Research prototype. No validated profitable strategy. No live order execution.

## Project layout

- `btc-research/src/ingest.py`: batch-fetch interface, candle quality checks, 1-minute to 5-minute aggregation.
- `btc-research/src/research.py`: initial Donchian breakout benchmark, hypothetical $1,000 equity, transaction costs and chronological split.
- `btc-research/tests/`: small initial ingestion tests.
- `btc-research/results/`: generated outputs (not checked into Git).

## Reproducible experiment

```bash
cd btc-research
python -m pip install -r requirements.txt
pytest -q
python -m src.research --input data/btc_1m.parquet --output results
```

Input Parquet columns: `time, open, high, low, close, volume` (UTC candle-open Unix seconds). Continuous historical data must be downloaded and audited before treating any performance report as valid. The research command *does not* fetch data automatically and must not be confused with a live-trading system.

## Data storage decision

Keep raw 1-minute candles in private versioned object storage as partitioned Parquet (such as `BTCUSD/1m/year=2024/month=03/part.parquet`). Commit only dataset manifests, SHA-256 checksums, reproducible fetch code and compact results to Git. Never store API credentials or multi-gigabyte historical datasets in ordinary Git history.

Recommended manifest fields: symbol, venue, resolution, start/end UTC, row count, gap count, duplicate count, SHA-256 and data-source version. The exact earliest available Delta historical minute candle has **not** been established.

## Research acceptance criteria

1. Complete, reproducible BTCUSD 1-minute ingest with restartable windows and UTC continuity checks.
2. Compare resampled OHLCV against native 5-minute and 4-hour exchange samples.
3. Honor next-bar execution, no look-ahead, round-trip fees, realistic stop assumptions, max leverage and drawdown controls.
4. Chronological train / validation / untouched holdout with immutable configs and a trade ledger.
5. Evaluate regime-by-regime and reject strategies that do not generalize.

## Existing application

This repository also contains the older **CompTrail / PayLens Next.js salary calculator** in its root-level `app/`, `components/`, `lib/` and other frontend files. It is preserved for safety and is **not part of BTC Quant Lab**. After confirmation that it is no longer needed, remove it in a separate explicitly scoped PR; do not silently erase working application code.

## Historical code status

The starter backtest is research scaffolding, not a production-quality simulator, and the historical dataset has not yet been committed or fully reconstructed.

---
Educational and experimental research only. Results never guarantee profits.
