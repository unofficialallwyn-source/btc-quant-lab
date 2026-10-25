# BTCUSD minute historical backfill

Read-only Delta India public endpoint: `GET https://api.india.delta.exchange/v2/history/candles`.

From `btc-research/` install dependencies with `python -m pip install -r requirements.txt`, then use:

```bash
python -m src.backfill --start 2025-07-01 --end 2025-07-03
```

Dates are UTC, start inclusive, end exclusive. The downloader requests at most 1800 minute bars at once, validates every minute, persists verified Parquet partitions and a SHA-256 manifest; re-running validates existing partitions before resuming. The download stops on missing candle data rather than synthesizing prices.

To backfill the proposed complete interval, use `--start 2024-03-01 --end 2026-10-25` **only after confirming the actual first available minute**, and expect substantial API requests and storage requirements. Run this command from a network-enabled machine with the listed Python dependencies installed. The research CLI never places trades.

**Current milestone status:** adapter and CLI implemented, mock tests run locally (3 passed). The ChatGPT isolated execution runtime cannot access the external Delta host and lacks pyarrow, so the full historical Parquet backfill has NOT been executed or saved to cloud storage. The Delta MCP interface separately confirmed market history is available. Configure persistent object storage separately rather than committing raw candles to GitHub.
