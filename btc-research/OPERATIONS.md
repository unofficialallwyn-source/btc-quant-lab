# Running BTCUSD historical ingestion

The workflow `.github/workflows/btc-backfill.yml` can be run manually from the GitHub Actions tab. Pick a **small UTC date window** first (one day); after observing data quality and runtime, process successive dates/months.

## Data ownership and retention
1. This workflow always uploads a GitHub Actions artifact retained for **30 days**. It is **temporary**, not the canonical dataset.
2. To persist partitions privately, create an Azure Blob container and store a container-scoped write-capable SAS URL as repository Actions secret `AZURE_BLOB_CONTAINER_SAS_URL`. Prefer a short-lived SAS with least privilege; rotate it after backfill. Never commit SAS URLs.
3. If that secret is present, the workflow uploads the validated Parquet partitions first, then the manifest as a completion marker. Azure container metadata and overwrite/concurrency protections should be configured for production workloads.
4. If the secret is missing, the Azure upload step is skipped. No durable historical storage is claimed.
5. Do not schedule concurrent overlapping windows: filenames contain only UTC interval; simultaneous writes may race.
6. Workflow is read-only with respect to Delta Exchange trading; market candles come from the public API.

## Validation caveats
The existing collector fails a window if even one minute is absent. Do not fill missing candles with made-up prices. Log exact failing windows, check exchange retention, and investigate legitimate sparse intervals before relaxing validation. This release has no cross-workflow central manifest, no automatically scheduled full-history backfill, and no deployment to an external compute environment.

## Run manually
Actions → BTC historical backfill → Run workflow → start/end UTC dates.
Verify pytest passes, check uploaded artifacts and (if enabled) Azure blobs, then review counts and hashes. Avoid large-range jobs until end-to-end storage has been verified.
