# OIDC production migration: phased verification

The existing SAS-based backfill remains available; the automated multi-year scheduled controller is not migrated or enabled by this PR.

1. Merge this PR after tests/review. Confirm managed identity `btc-quant-lab-github` has `Storage Blob Data Contributor` on `btc-historical-data`, that its federated credential covers `main`, and that `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` exist in GitHub Actions secrets.
2. Actions → **BTC OIDC backfill verification** → Run on `main`, start `2025-09-11`, end exclusive `2025-09-12`, execute **false**. Verify Azure inventory and expected missing one-day window.
3. Rerun the same dates with execute **true**. Expected: 1,440 BTCUSD 1-minute candles fetched, checked, uploaded as one Parquet partition plus a range manifest using `AzureCliCredential`. The controller invokes existing downloader without passing a SAS URL.
4. Run execute **false** on the same date again and verify zero missing minutes and that its range is recognized as stored. Only after confirmation, migrate the scheduled controller in a separately reviewed PR.
5. Keep `BTC_MULTIYEAR_ENABLED` false until explicitly deciding to enable daily runs, verify account charges and set a historical range. Keep the older SAS secret temporarily; no secret deletion is performed.

## Credential behavior

The new `BTC_AZURE_AUTH=oidc` flag requires Azure CLI identity from the prior `azure/login@v3` step, and never falls back to SAS when OIDC fails. A separate `BTC_AZURE_AUTH=sas` path retains legacy behavior. A failed Azure write blocks publication of the manifest, which is uploaded last.

OIDC smoke-test success already established list permission; **write permission has not yet been exercised through OIDC**. Full-scale ingestion and complete cloud-wide validation remain future milestones.
