# Multi-year BTCUSD data controller

This workflow audits previously uploaded Azure range manifests, merges verified UTC intervals into a consolidated coverage report, and selects the oldest unfilled UTC interval, limited to **28 days per run**. Downloading occurs in 7-day batches. If the job fails, the next execution recomputes the Azure inventory; successfully uploaded ranges are skipped.

## Safe rollout

1. Keep the repository Actions variable `BTC_MULTIYEAR_ENABLED` absent or `false` initially. The daily scheduled trigger is gated by this variable and **will not download data until explicitly enabled**.
2. Update the `AZURE_BLOB_CONTAINER_SAS_URL` secret with a valid **non-user-bound User Delegation SAS** permitting Read, List, Create and Write. Expiration on October 31, 2026 must be managed; this code does not renew SAS credentials.
3. Actions -> **BTC multi-year controller** -> Run workflow. Set start `2025-08-14`, end `2025-09-11`, execute **false** for an initial coverage-only audit.
4. Review the `btc-coverage-<run_id>` artifact and job output. Once the report is credible, rerun with execute **true** to download one missing interval (up to 28 days).
5. Only after verifying Azure upload and billing, add the GitHub Actions **repository variable** `BTC_MULTIYEAR_ENABLED=true` to allow a daily scheduled run. The scheduled bounds are `2024-03-01` inclusive to `2026-10-25` exclusive, so the job eventually attempts historical coverage back to March 2024. These dates are intentionally frozen for reproducibility; edit the workflow to extend coverage.
6. The scheduler has a single concurrency group shared with the cloud-aware workflow, avoiding parallel controller writes. Do not run the *older* `btc-backfill.yml` concurrently; it does not share the lock.
7. Monitor failures in Actions. Missing candles or malformed manifests cause the run to fail rather than fabricate missing market data.

## Output

`data/coverage.json` summarizes merged verified intervals, missing UTC intervals, total covered vs expected minute counts, and next selected window. It is archived as a 30-day GitHub artifact. The Azure stored manifests remain the source of truth. Cloud inventory recalculates SHA-256 over all referenced blob bytes, which may become slow and incur transaction/egress costs as coverage grows.

## Limitations

The controller is intentionally not enabled by default. It has not yet been executed through GitHub Actions. Older July 1 2025 smoke-test metadata used a legacy manifest path that the newer inventory does not index. The code does not automatically configure Azure workload identity, automatically rotate SAS tokens, guarantee historical availability before the first verified date, or generate strategy backtests. If API history has discontinuities, human investigation is required.
