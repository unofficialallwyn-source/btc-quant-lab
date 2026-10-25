# Scheduled BTC backfill: OIDC rollout

This change migrates the existing `BTC multi-year controller` GitHub Actions workflow from SAS to Azure-managed-identity OIDC credentials. It uses the tested `azure/login@v3` step and sets `BTC_AZURE_AUTH=oidc`; no Azure SAS secret is read by this workflow.

## Safe rollout
1. Leave repository Actions variable `BTC_MULTIYEAR_ENABLED` **unset or false**. Scheduled cron events will be skipped until explicitly enabled.
2. Merge the PR after review.
3. Run `BTC multi-year controller` manually on `main` with start `2025-09-11`, end exclusive `2025-09-12`, execute **false**. Expect 1,440 covered minutes and `next_window: null` with OIDC login, since this date was already uploaded in verified OIDC testing.
4. Run it again on a bounded *new* interval with execute=false to inspect missing coverage. A future real download must be intentionally initiated with execute=true.
5. Verify continued SAS-based workflow compatibility before deleting `AZURE_BLOB_CONTAINER_SAS_URL`; the two legacy backfill workflows still use SAS. Do not delete the secret until those are migrated or retired.
6. Only set `BTC_MULTIYEAR_ENABLED=true` after reviewing API usage, Azure cost, provenance, and earliest available historical dates. Scheduled runs use fixed `2024-03-01` to `2026-10-25` dates; early history is not guaranteed to be complete.

The scheduled workflow does **not** start automatically when merged while the opt-in variable remains false. The previous OIDC verification workflow has already confirmed read, upload and recovery behaviors for September 11, 2025.

## Remaining improvements
- New daily end-date automation (currently intentionally frozen).
- Overall historical coverage reconciliation including legacy manifests.
- Monitoring, retention and spend controls.
- Verify actual earliest available Delta BTCUSD minute history before unattended multi-year backfill.
