# Phase 5 Step 1 — Frozen Trade Failure Diagnostics and Research Sources

## Purpose
Explain *why* the three rejected Phase 4 BTC hypotheses failed, without tweaking thresholds or unlocking validation. The research inputs are the source artifact from completed Phase 4 Step 4 run **40735017966** and the same verified 1m historical catalog. Each strategy is replayed with the original RiskPolicy and frozen Hypothesis specification on the original three disjoint training folds. Replayed trade counts, gross profit before slippage, fees, slippage, net P&L, and fold return must reconcile against Phase 4's archived results or the run fails.

## Outputs
- `training_trade_ledger.csv`: each executed training-fold trade, UTC Unix entry and exit times, strategy, fold, side, exit reason, gross P&L, fees, slippage, net P&L and holding interval (derivable from timestamps). CSV includes NO validation/holdout trades.
- `trade_diagnostics.json`: fold-level exit reason counts and net/gross/cost attribution, winners vs losers, gross-positive/net-nonpositive count, holding-time summaries and breakeven average cost gap.
- Source report and catalog SHA256 hashes allow future audit.
- This first diagnostic stage **does not** measure intra-trade MAE/MFE or actual exchange order-book spreads; obtaining those robustly is a separately scoped follow-up.

## Bibliography — first directly inspected extracted text
These passages are from `quant-resources/extracted-text/`; PDF source rights remain with authors and owners.

1. **THE PROBABILITY OF BACKTEST OVERFITTING.txt**, Bailey et al. (2015): its abstract questions whether conventional holdouts alone reliably prevent backtest overfitting and proposes a probability-of-backtest-overfitting framework. Implication for us: no repeated ex-post strategy tuning to manufacture a passing training result. [Source](https://github.com/unofficialallwyn-source/quant-resources/blob/main/extracted-text/THE%20PROBABILITY%20OF%20BACKTEST%20OVERFITTING.txt)
2. **Risk and Return in High-Frequency Trading .txt**, Baron et al. (2017): its abstract reports an association between relative latency and HFT performance through information and risk-management channels. This is **not direct evidence about BTC profitability**; it cautions against treating 1m OHLCV simulation as a credible model of high-speed execution. [Source](https://github.com/unofficialallwyn-source/quant-resources/blob/main/extracted-text/Risk%20and%20Return%20in%20High-Frequency%20Trading%20.txt)
3. **Market microstructure and market liquidity.txt**, Muranaga and Shimizu: its abstract, based on an artificial-market simulation, emphasizes that different liquidity indicators need not move consistently together. Implication: we should not infer true executable liquidity from OHLCV volume alone. [Source](https://github.com/unofficialallwyn-source/quant-resources/blob/main/extracted-text/Market%20microstructure%20and%20market%20liquidity.txt)

These notes use **only the inspected abstracts**, not claims that the full books/papers have been analyzed. The `quant-resources` repo currently contains 50 PDFs and 51 extracted TXT files. Short or missing text extractions require separate quality review before detailed source-based hypothesis implementation.

## Research boundaries
- Source repository `quant-resources` is read-only, used only for cited research notes.
- `btc-quant-lab` is the implementation repo; source data and proprietary book texts are **not copied into code**.
- No trade proposal, parameter optimization, validation/holdout evaluation or live execution.
- USD-linear simplified risk engine still lacks historical Delta India funding, INR settlement, liquidation and realistic depth/spread modeling.

## Execute after review
Merge this PR and manually dispatch `BTC Phase 5 trade failure diagnostics` on main. Default dataset UTC range: **2024-02-03** to **2026-10-26 exclusive**. Keep `source_run_id=40735017966`. Check regression tests, frozen matching and uploaded `btc-phase5-diagnostics-<runid>` artifact. Investigate any mismatch before drawing conclusions.

## Next research steps
Use the actual diagnostic distributions to decide whether the dominant failure mechanism was costs, adverse exits, trade scarcity or flawed entry selection. Only then propose materially different, predeclared alpha hypotheses for separate training testing.
