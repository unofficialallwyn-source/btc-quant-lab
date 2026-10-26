# BTCUSD gap-aware collection and research safety

The current source has a confirmed missing period around 2024-02-20 18:00 UTC. The source API returned 1,730/1,800 expected minute bars. Retrying the original request did not restore them; surrounding narrow queries also failed to return data.

## Collection policy
- Run the manually dispatched **BTC gap-aware collection (manual)** workflow on main with execute=false first. Then execute=true with max_days=4.
- The gap-aware workflow processes one UTC day at a time. A day either produces a complete SHA256-verified manifest-backed partition or is recorded as unavailable. It **never uploads partial days as full coverage**.
- Gap registry location: `historical/BTCUSD/1m/source_gaps/<day_epoch>.json`. Each item records last-check time, source, and diagnostic. These records are **not manifests**, and do not count as verified historical candle coverage.
- Subsequent runs skip source-gap days unless `retry_gaps=true`; retried days are removed from the gap registry only after a successful full-day upload and cloud read-back audit.
- Network, Azure, auth, format, and corrupt-data errors are **fatal** rather than mislabeled as source data gaps.
- The workflow defaults to 4 days per invocation; it never enables cron jobs or places orders.

## Research
- `research_segments.segments` splits on any missing one-minute timestamp, and `enforce_continuous` rejects discontinuous datasets.
- Strategy simulations must run on individual continuous segments and reset indicators, positions, equity state or use an explicit documented accounting model at each boundary. Do not concatenate segments as though candles were consecutive.
- Existing `research_dataset` still deliberately requires *fully continuous coverage* and fails on missing days. A future isolated-segment research workflow is required to execute full-range cross-gap research.
- `fully_complete=false` is the correct status whenever any minute is missing, even when all retrievable full days have been stored.
- Routine gap rechecks are not enabled; run a separate manual retry after inspecting registry evidence.

## Important limitation
A day containing only a short outage is excluded in full by this conservative initial implementation. Preserving sub-day continuous runs without false completeness requires a future segment-manifest format and compatibility updates to all inventory/verification consumers. Thus this change maximizes integrity, **not** the number of recovered valid candles inside a partial day.
