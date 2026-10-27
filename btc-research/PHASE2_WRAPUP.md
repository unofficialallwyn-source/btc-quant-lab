# Phase 2 wrap-up — reporting and readiness for strategy research

## Completed
1. Phase 1 checksum-verified gap-safe historical BTCUSD 1m data (1,418,400 observed minutes; no fabricated missing candles).
2. Phase 2 Step 1: chronological 60/20/20 time-based training/validation/untouched holdout.
3. Phase 2 Step 2: causal 1m/5m/15m/1h/4h signal infrastructure, with 1m execution and no unfinished higher-timeframe bars.
4. Phase 2 Step 3 **DEFERRED**: Delta India INR contract primitives and integration tests pass, but historically accurate mark/funding execution remains blocked by unavailable verified funding settlement history and liquidation reconstruction. Public mark candles are accessible. Fixed INR policy must be historically validated. The USD baseline is **not** a Delta contract-accurate backtest.
5. Phase 2 Step 4: `src/performance_report.py` computes deterministic, independently checked performance statistics on training/validation only, SHA-256 hashes inputs, produces JSON, and refuses unlocked holdout evaluations. GitHub Actions `BTC Phase 2 chronological evaluation` runs this report automatically after the simulation.

## Report outputs
- `evaluation.json` — original engine config, boundaries, results.
- `training_trades.csv` / `validation_trades.csv` — detailed fill ledger.
- `training_equity.csv` / `validation_equity.csv` — sampled mark-to-market curve.
- `performance_report.json` — independent verification, drawdown, max drawdown timestamps, trade count, gross profits and losses, fees, expectancy, win rate, profit factor, time in positions, losses in a row, descriptive 1m Sharpe, source SHA-256 digests.
- `dataset_catalog.json` — hashes of original data segments, source coverage, missing periods.

## Guardrails for Phase 3

**No strategy can be guaranteed funding-independent just because its rules do not explicitly reference funding.** A perpetual held over a funding settlement may accrue a real funding transfer. Phase 3 strategies should prefer intraday/short-duration trading, explicitly track holding windows and optionally flatten before funding boundaries once historical settlement schedules are verified. **Do not interpret the existing baseline returns as net of funding**, and do not describe simulated profit without realistic exchange costs.

- Keep the 20% chronological final holdout untouched until strategies are frozen.
- No trading across source gaps; time-close the input HTF bar before entry.
- Don't optimize on validation metrics repeatedly; use training and carefully controlled validation.
- No live orders, no autonomous capital allocation.
- The Step 4 reports are *diagnostic research statistics*; annualized 1m Sharpe uses simplifications during gaps and should not be used alone for deployment readiness.
- Step 3 remains an explicitly documented deferred debt item. Phase 2 research infrastructure can proceed to strategy development after workflow confirmation **with caveats**.

Run the manual `BTC Phase 2 chronological evaluation` workflow on `main` with default start 2024-02-03, exclusive end 2026-10-26, timeframe 5m. Validate unit tests and newly published `performance_report.json` in the artifact.
