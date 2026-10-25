# Gap-safe BTC historical ingestion (review milestone)

Previously, when a selected seven-day window partly overlapped a verified Azure manifest, the executor raised an error. This change splits the selected window along verified coverage boundaries and fetches only missing UTC-day-aligned ranges.

**Safety:** the existing inventory still downloads and SHA256-verifies referenced Parquet blobs before assigning coverage. Missing subranges are never credited as already stored, and coverage boundaries not aligned to whole UTC days cause a hard failure. Previously covered subranges are skipped and never overwritten by the planner.

## Verification after merging

- Run `python -m pytest -q` (GitHub workflow automatically does this).
- Run `BTC multi-year controller` on `main` with start `2025-09-10`, end exclusive `2025-09-14`, execute **false**. Since Sept 10 and Sept 11 have been uploaded, the report should identify the Sept 12–13 gap.
- Only after verifying the dry run, manually execute this same bounded interval with execute **true**. It should skip Sept 10–11 and fetch Sept 12–13 only.
- Rerun execute **false** to verify all four days are covered.

**No cron activation:** `BTC_MULTIYEAR_ENABLED` remains disabled. No live trading. This PR does not change storage permissions or Azure authentication.

**Limitations:** This change does not add monitoring, automatic report-after-upload refresh, Azure API cost caps, optimized SHA re-verification, or reconciliation of older shared-name legacy manifests. Those require separate milestones before enabling recurring jobs.
