# Multi-run BTC historical backfill plan

## Confirmed smoke test
GitHub Actions run 40182232923 validated 1,440 BTCUSD 1-minute candles for July 1 2025, and logged two successful Azure Blob uploads. The *previous* uploader placed a shared manifest at `historical/BTCUSD/1m/BTCUSD_1m_manifest.json`; it is preserved as legacy smoke-test metadata.

## Changed in this PR
- Every newly uploaded run has a unique cloud manifest: `historical/BTCUSD/1m/manifests/BTCUSD_1m_<start>_<end>.json`. Existing partitions retain their time-stamped names.
- Publish the complete-run manifest **after** all parquet partitions pass SHA-256 verification and upload.
- Validate each run's partition boundaries are contiguous.
- Reject date ranges over seven days. Use multiple sequential GitHub Actions runs, typically 1–7 days each.
- A failed run may be rerun with the *same exact dates*. Local partitions resume within that single job; separate Actions runners start with an empty workspace and re-download data. Cloud writes are idempotent for identical inputs but are not yet verified against existing blob hashes.
- Do not overlap differently sized date windows: a shared UTC candle range may otherwise be stored under different partition names. Run serially and record start/end ranges.

## Important constraints
This increment does **not** download the full history, inspect Azure inventory, renew the expiring SAS, or create a multi-year orchestration service. It makes manually executed multi-run ingestion safer. Azure SAS needs upload permissions; obtaining a central read-only audit later will require additional authorization. Keep historical Parquet private. Do not place SAS URLs in issues, logs, or source.

## Next operators' sequence
1. Merge PR after CI/test review.
2. Run July 2–3 2025; verify the Azure manifest has the unique range name.
3. Run a seven-day batch only after the smaller test passes.
4. Backfill chronologically in nonoverlapping seven-day windows, beginning at earliest *confirmed* available minute.
5. Produce a cloud-wide gap/hash coverage report before research uses this history.
