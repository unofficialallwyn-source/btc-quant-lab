# Phase 5 Step 2 — Transaction-Cost Sensitivity (frozen historical ledger)

## Source-backed motivation
The private research library `unofficialallwyn-source/quant-resources` has extracted text files that are now readable. We inspected:

- [Algorithmic Trading From Beginner to Advanced](https://github.com/unofficialallwyn-source/quant-resources/blob/main/extracted-text/Algorithmic%20Trading%20From%20Beginner%20to%20Advanced.txt): section **3.4 Broker realism: commission, slippage, sizers** explicitly presents simulated commission, per-fill slippage and position sizing. The book's chapters **15** and **16** concern rolling/walk-forward stability and stress tests. This motivates separate cost dimensions, but does not provide validated BTC-specific rates.
- [Ernest P. Chan, Algorithmic Trading: Winning Strategies and Their Rationale](https://github.com/unofficialallwyn-source/quant-resources/blob/main/extracted-text/ALGORITHMIC%20TRADING2.txt): the introductory text explicitly cautions that example code without transaction costs and performance measured in-sample can mislead. The preface references Chan's separate earlier book, *Quantitative Trading*. There is no exact repository title `Algorithmic Trading and Quantitative Trading` in the inventory, so do not present these as a single publication.

These are **source-derived methodological observations**, not endorsements of strategy profitability. We will continue reading additional relevant chapters when designing new hypotheses in later Phase 5 steps.

## Experiment
Use the Phase 5 Step 1 training-only archived artifact from workflow **40802892631**. Load its `training_trade_ledger.csv` and `trade_diagnostics.json`; verify trade counts, gross/net accounting and per-fold results. No Azure data is read.

For each of the three previously rejected Phase 4 strategy families × each original training fold, compute every combination of these *predeclared* fee and slippage multipliers independently: **0, 0.5, 1, 1.5, 2×**. This yields 3 × 3 × 25 = **225 scenario rows**. Save `cost_sensitivity.csv` and `cost_summary.json` including per-strategy break-even joint cost multiplier where gross return is positive. A strategy with gross return <=0 has no feasible positive cost rate under this fixed-trade counterfactual.

These results are **fixed-trade accounting counterfactuals, not executions or full historical re-simulations**: changing a fee, spread or slippage assumption would alter fills, position sizing, stops, balance and future trade decisions. This report cannot prove achievable profitability, even at zero costs.

## Boundaries
- No strategy threshold changes or parameter optimization.
- No validation / holdout data or live trading.
- No claims about executable bid-ask liquidity; that requires historical market microstructure data.
- Existing simplified USD-linear cost ledger omits Delta India historical funding, INR settlement, liquidation and margin behavior.

## Run
After PR approval and merge: dispatch [BTC Phase 5 execution cost sensitivity](https://github.com/unofficialallwyn-source/btc-quant-lab/actions/workflows/btc-phase5-cost-sensitivity.yml) on `main` with `source_run_id=40802892631`. Review test suite and archived summary. Use results to determine whether a material strategy edge survives assumed costs; do **not** promote a rejected strategy.
