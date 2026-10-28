# Phase 4 Step 5 — Final Fail-Closed Candidate Decision

## Fixed evidence
The only source of strategy-performance evidence is archived training-only Phase 4 Step 4 GitHub Actions run **40735017966**, artifact `btc-phase4-walkforward-40735017966`. It records 143 regression tests passed; three candidate strategies, each tested in three chronological training folds; **zero qualifying strategies** and decision `NO_QUALIFYING_CANDIDATE`.

## Separate final decision
`src.phase4_decision_gate` independently loads that archived `walkforward_report.json` and paired `dataset_catalog.json`, and rejects missing or altered critical fields: schema, scope, catalog checksum, frozen hypothesis specification SHA256, risk settings, exact candidate names, fold chronology, baseline neutrality, min-trade and drawdown thresholds, ledger reconciliation, per-fold P&L/returns, aggregate totals, eligibility, original decision, and locked validation/holdout assertions.

`REJECTED_NO_QUALIFYING_CANDIDATE` is a **successful scientific outcome** that documents no promotion. This gate never accesses 1m price candles or reopens training simulations. It always emits `promotion_authorized=false`, `validation_evaluated=false`, `holdout_evaluated=false`, and `live_trading_enabled=false`. If a future separately frozen source unexpectedly contains a qualifying candidate, this gate records `MANUAL_REVIEW_REQUIRED_NO_PROMOTION`, never automatic approval.

## Reasons in the archived Step 4 run
- High-volatility range continuation: net-negative across all three folds; 257 trades.
- Exhaustion reversal: net-negative across all three folds despite positive combined pre-cost P&L; 152 trades.
- Trend-transition breakout: net-negative across all three folds, plus below 20 trades in two folds; 48 trades.
- Cash/no-trade: zero trades, zero P&L.

## Operator steps
Merge PR after review. Launch `BTC Phase 4 final candidate decision` workflow on `main` using `source_run_id=40735017966`. Check test pass, final decision and archived `final_decision.json`. Do not run controlled validation or holdout without a separately approved protocol for a **qualified** training candidate.

## Research direction after closure
Audit trade-level failure characteristics and the relative contribution of execution costs; propose *materially new* causal hypotheses in a new phase rather than reoptimizing rejected thresholds to manufacture a positive result. Delta India historical funding, INR contract accounting, margin and liquidation are not modeled in current USD-linear research simulator.
