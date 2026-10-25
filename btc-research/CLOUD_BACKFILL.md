# Cloud-aware BTC history backfill

**Prerequisite:** Update `AZURE_BLOB_CONTAINER_SAS_URL` to a **container-scoped User Delegation SAS with Read + List + Create + Write permissions**. The earlier Create+Write-only SAS is insufficient for cloud audit. Keep user-bound SAS disabled and the URL secret. This workflow does not configure or renew SAS automatically.

Actions → **BTC cloud-aware backfill** → Run workflow. First use `2025-07-10` inclusive to `2025-07-17` exclusive, `days=7`, `dry_run=true`. Review the plan, then rerun with `dry_run=false`. Azure manifest is the completion marker, published after verified Parquet uploads.

The inventory examines each new-format cloud manifest and hashes its referenced Parquet blobs. Windows fully covered by successful verified ranges are skipped; partial overlap is rejected instead of silently duplicating intervals. Failed or missing-manifest windows can be retried. If corrupted manifest/data exists, execution fails closed. Legacy July 1 2025 shared-name manifest is not indexed; use newer manifests and avoid overlap.

At most 28 days can be requested per GitHub run. A single seven-day window requests up to six 1,800-candle API partitions. The workflow serializes cloud-aware runs through GitHub Actions concurrency. It does not lock the older manual workflow; avoid running both workflows simultaneously.

This release is **manually dispatched**, not a continuous scheduled multi-year job. It does not install workload-identity federation or perform a comprehensive reconciliation of older legacy manifests. Start with one week; inspect GitHub logs and Azure storage, then scale with nonoverlapping 28-day windows. SAS expiry and storage costs still apply.
