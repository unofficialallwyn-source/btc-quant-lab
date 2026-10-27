# Risk engine forensic diagnostics — Phase 3 Step 3 follow-up

GitHub run 40550535747 passed 100 tests but produced deeply negative **training** returns:
- Trend: -99.6108%, 3550 trades, $613.91 fees.
- Mean reversion: -92.2636%, 1884 trades, $648.20 fees.
- Volatility breakout: -98.6381%, 2800 trades, $638.07 fees.

These are facts from the recorded workflow output; a successful software test is **not** proof of economically sound execution.

## Questions answered by next manual run

The runner now emits per-strategy `exit_reason_counts` (stop, target, stop_gap, target_gap, funding_guard, time_limit, segment_end); `entry_decisions` (candidate signals, successful entries, blocked for cooldown, funding guard, daily loss lockout, ATR warmup/invalid distance, balance); average trade holding minutes; fees as a percentage of initial equity; and an explicit realized-ledger vs final cash reconciliation. Inconsistent P&L fails the workflow.

Possible causes to inspect *after* seeing the actual counts:
1. ATR stops on 5m candles may be too tight relative to typical BTC movement and fee/slippage, permitting many small-loss entries.
2. A position closed after 60 minutes or at the assumed funding guard may be re-entered repeatedly whenever the previous-bar signal remains nonzero.
3. 15-minute cooldown is shorter than a sustained trend signal.
4. Daily entry lockout is not a stop-loss on active positions and resets by UTC calendar date.
5. Strategy signals may not represent transitions; repeated continuation signals can create high turnover.

These are hypotheses, **not validated root causes**. Do not adjust parameters or call the strategies profitable until the reports establish causes. The model remains simplified USD linear P&L with no verified Delta funding, liquidation or INR settlement. UTC 8-hour funding schedule is an unverified guard assumption.

## Next run
After reviewer approval and merge, dispatch the existing `BTC Phase 3 risk controls training validation` workflow on main, with `start=2024-02-03`, `end=2026-10-26` (exclusive), `signal_tf=5m`, `context_tf=1h`. Examine the new diagnostics in the uploaded `risk_comparison.json`. The workflow still evaluates training only: validation and final holdout remain locked.
