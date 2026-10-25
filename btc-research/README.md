# BTC Quant Research

Isolated BTCUSD research workspace. Paper simulations only—no order execution.

## Getting started

Run `pip install -r requirements.txt`, then `python -m src.research --input data/btc_1m.parquet --output results` in this directory. Tests: `pytest -q`.

Data schema: `time` (UTC Unix seconds at candle open), `open`, `high`, `low`, `close`, `volume`. Reject gaps/duplicates/bad OHLCV. Derive completed five-minute bars from minute data. Chronological train/validation/holdout split: 60/20/20. Simulate next-bar entries, fees, slippage and stop-first ambiguous candles. Never optimize on holdout.

Do not put exchange credentials in code. Store large raw Parquet in private object storage / Git LFS, not regular Git. Historical ingestion requires a configured authenticated Delta candle fetcher. This branch contains reproducible scaffolding; a full BTC history download and production-quality backtest validation remain outstanding.
