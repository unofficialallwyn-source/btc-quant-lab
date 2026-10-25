# Complete BTCUSD 1-minute history — execution and verification

The source adapter uses public Delta Exchange India BTCUSD perpetual OHLCV candles. On 2026-10-25, spot-checks returned **no one-minute candles** for sampled 2023 dates, 2024-01-01 and 2024-02-01 00:00–01:00 UTC. One-minute candles **were** available from 2024-02-02 12:00 UTC and throughout Feb 3. These samples do NOT prove the first available minute or that every intervening historical minute is present. For now the default start is **2024-02-03 UTC** (the earliest calendar day sampled at 00:00 that returned candles), not a claim of absolute earliest history. Investigate Feb 2 separately before final completeness certification.

## Run bounded uploads

Once PR merged, open Actions → **BTC full-history collection (bounded)** on main. First run **execute=false**, start 2024-02-03, end empty (current UTC day midnight), max_windows 4. Review the oldest missing window and total coverage. Then run **execute=true**, max_windows 4. Each run attempts up to four **28-day** missing windows, uploads checked Parquet shards and manifests, and performs a fresh full SHA256 cloud audit afterward. Rerun as many times as needed; each invocation resumes at the earliest unverified gap. Increase max_windows only after checking run times and API/storage costs. Existing concurrency lock serializes the historical workflows. Execution fails closed if Delta has holes or Azure manifests have corruption.

**Caution:** each inventory run re-downloads every known Parquet file for SHA verification. Cost and time grow with historical coverage. Limit to 1–4 windows until performance is characterized, then improve verification scalability; do not enable unattended runs until this is addressed. Azure ingestion can incur storage/transaction costs and consume API requests.

## Scope

- No live trading or order placement.
- This workflow is manually dispatched only and does not enable `BTC_MULTIYEAR_ENABLED`.
- Cannot complete uploads simply by merging the PR; runs must execute on GitHub and the final `complete=true` report must be checked.
- Source ends at the latest **completed** UTC day to avoid gaps caused by still-forming candles.
- A missing period can mean unavailable source data; do not fill with fabricated OHLCV.
- Current research export may be run on an independently certified complete interval, then advanced to wider periods. Training must be chronological and keep final holdouts untouched.
- Legacy July 1, 2025 manifest is not in the current manifests prefix and will need reconciliation in the strict research exporter.

No Azure credentials are written to logs or committed to the repository.
