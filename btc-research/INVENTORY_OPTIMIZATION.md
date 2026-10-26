# Optimized gap-aware Azure inventory

## Before
The manual gap-aware workflow re-downloaded and SHA-256 checked **every existing manifest and referenced Parquet blob** before each new UTC day, again after every successful upload, and once at the end. The number of scans grew with history length.

## After
The workflow now performs:
1. One complete verified Azure inventory at run start.
2. Per-day data validation and upload with the already verified in-memory inventory; **no full scan in the daily execute path**.
3. A targeted download and SHA-256 verification of the newly published daily manifest and its referenced Parquet blob(s). The new day is added to the in-memory inventory **only after verification**.
4. One complete SHA-256 inventory scan at run end and a durable report even on failures.

Source-gap days are still recorded separately; they do not increase verified coverage. A failed checksum, unexpected manifest range, authorization error or final audit fails the job. Full-history completion remains false until all minutes are present. The existing full-history workflow continues to use its previous conservative audit implementation.

## Performance expectation
For a 28-day run, full-dataset checksum scans are reduced from dozens to **two**, plus one targeted manifest verification for each successfully uploaded day. Actual runtime must be measured against the previous ~hour-long runs after merging.

## Manual validation
Run `BTC gap-aware collection (manual)` with `max_days=4`, `execute=false` first, then `max_days=4`, `execute=true` and verify the final artifact shows `audit_strategy`, `initial_audit_complete=true`, correct verified-minute delta, and no `audit_error`. Keep automatic scheduling disabled.
