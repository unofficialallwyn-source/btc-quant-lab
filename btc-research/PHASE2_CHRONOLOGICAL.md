# Phase 2 milestone 1: chronological research evaluation

Fixed UTC calendar splits of the historical export: earliest **60% training**, next **20% validation**, latest **20% locked holdout**. These boundaries depend only on timestamps, not on how many candles were actually available; gaps cannot silently redistribute time periods.

The evaluator validates SHA-256 for every exported research segment and keeps segments disjoint. It crops candles within each fixed partition, restarts indicators and trading positions at each genuine market-data gap **and at each partition boundary**, and reports separate P&L with an independent USD 1,000 initial balance for each partition.

**Holdout is not run by the GitHub workflow.** The standalone CLI defaults to training+validation only. Only a future explicit `--include-holdout` operation can evaluate it, after strategy parameters and implementation are frozen. Avoid using even baseline holdout results for model selection.

Run GitHub Actions `BTC Phase 2 chronological evaluation` using start `2024-02-03` and exclusive end `2026-10-26`. The artifact contains `evaluation.json`, training/validation trade ledgers, equity curves and source dataset catalog.

Known remaining Phase 2 milestones: (2) multi-timeframe alignment, (3) Delta-specific execution/contract mechanics and funding, (4) improved reporting and reproducibility. The current metrics are still baseline simulation metrics, not deployable performance. No live trading.
