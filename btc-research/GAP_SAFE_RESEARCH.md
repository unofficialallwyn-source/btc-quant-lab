# Phase 1: Gap-safe BTCUSD research export

## Purpose
Build a reproducible, checksummed dataset from **existing** Azure Blob BTCUSD 1-minute history. No missing-day retries and no invented candles.

Run the manual GitHub workflow **BTC gap-safe research dataset export** on `main` after review, using start `2024-02-03` and exclusive end `2026-10-26`. It exports `dataset_catalog.json` plus `BTCUSD_1m_segment_*.parquet`, uploaded as a GitHub Actions artifact retained for 30 days. It does not alter raw Azure blobs.

## Safety and reproducibility
1. Full initial Azure inventory validates referenced Parquet SHA-256 digests.
2. Each selected partition is fetched, checksummed again, and validated for OHLCV integrity, time ordering and one-minute timestamps.
3. Matching duplicate timestamps are deduplicated; conflicting duplicates fail.
4. Actual missing timestamps create **separate** continuous segment files. Each segment has a SHA-256 checksum, exact UTC bounds and row count in the catalog. No OHLCV values are interpolated.
5. Target coverage and missing UTC intervals are reported even when the dataset is intentionally partial.

This export is **not a backtest**. Any subsequent engine must reset indicator lookbacks and close/clear positions at every segment boundary; it may not hold simulated trades across an unobserved interval.

## Research split policy
Do not select strategies using the entire dataset and then label a later portion an untouched holdout. Use strictly chronological training, validation and untouched evaluation windows; reserve genuinely future days for post-freeze forward evaluation. Avoid overlapping return windows across split boundaries.

The exporter currently builds the full research dataset in RAM; allow enough CI runner memory if the dataset grows significantly. The GitHub artifact is short-lived, not a permanent archive. Keep raw Azure files as the authoritative source.
