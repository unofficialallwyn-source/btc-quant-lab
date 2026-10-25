# Historical BTCUSD minute ingestion

The script in `src/historical.py` accepts a **caller-provided authenticated Delta candle fetcher** that returns `{'result': [...OHLCV...]}`. It requests no more than 3600 one-minute candles in a single inclusive Delta request, converts to a half-open UTC interval internally, strictly validates continuity and OHLCV, writes atomic Parquet partitions and generates a SHA-256 manifest. A rerun validates and reuses existing partitions.

## Before running

Install `pip install -r requirements.txt` (including `pyarrow`). Connect a real Delta client to `collect(fetcher, start_utc_seconds, end_exclusive_utc_seconds, directory)`. Do not commit credentials. Use 60-second-aligned UTC timestamps. On a missing candle, stop and investigate rather than silently filling prices.

For future months, store the Parquet outputs and manifests in versioned private object storage; code and small manifests are suitable for GitHub. Full historical backfill and a production Delta-client adapter have **not** yet been implemented. No orders are placed.

## Validation status
- Real Delta BTCUSD sample: July 1, 2025 00:00–00:59 UTC, 60 candles returned, zero timestamp gaps.
- Local validation-only test passed; Parquet integration tests require `pyarrow`. It could not be installed in the current isolated test environment; full integration tests remain pending.
