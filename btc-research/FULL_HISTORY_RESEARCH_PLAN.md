# Historical ingestion to strategy research

## Verified state and limits
Latest GitHub run 40217122307 verified 5,760/5,760 minutes for Sept 10–13, 2025 with OIDC; historical ingestion runs account for 75 consecutive days since July 1, 2025. An older July 1 manifest used a different path and is not indexed by the current `inventory`, so the **strict reproducible research export starts on July 2, 2025** until legacy ingestion is reconciled.

## Research-first usage
After merge, run **BTC research dataset export**, initially start `2025-07-02` and end exclusive `2025-09-14`. The workflow checks SHA256 manifest-backed partitions, requires *complete* continuous minute coverage, writes local audited Parquet for the job, then runs the existing research-only 5-minute Donchian baseline. The artifact uploads metrics, trade ledgers and data provenance summary; it does **not** upload the bulk Parquet to GitHub artifacts or create orders. Azure remains the authoritative dataset.

This baseline is exploratory and should not be promoted to production based on in-sample results. Evaluate data quality, walk-forward splits, fees, slippage, latency, regime sensitivity and untouched holdouts before any strategy claims.

## Entire history: responsible sequence
- Keep `BTC_MULTIYEAR_ENABLED` unset until an explicit user-approved budget and history start are established. The daily controller can ingest up to 28 missing days per run after user enables it; that would take many runs for multiple years. No connector available here can initiate a fresh workflow_dispatch. Do not equate committing workflow code with downloading data.
- Current controller hard-codes historical end `2026-10-25` for scheduled runs and must be updated separately to use a moving UTC cutoff before indefinitely enabling a schedule.
- Delta's actual earliest available public candle date must be verified. An earlier failed response doesn't prove absence of all older candles. Do not manufacture missing historical minutes. If history is unavailable, report it and stop.
- Cloud inventory SHA256 download checks repeat on every run. Before scaling, add indexed manifests or cached verified evidence to reduce Azure read costs.
- Legacy July 1 and fragmented coverage require cloud-wide reconciliation; the exporter fails closed if there are gaps.
- After export has run and historical expansion is validated, build multiple candidates and apply train/validation/held-out walk-forward evaluation, not optimization against a single holdout period.
