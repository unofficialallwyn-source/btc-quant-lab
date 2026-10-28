# Phase 3 — Final decision and research handoff

## Result of Step 4
The training-only optimizer workflow [#40621068040](https://github.com/unofficialallwyn-source/btc-quant-lab/actions/runs/40621068040) successfully completed 114 tests and 48 fold evaluations (16 fixed configurations × 3 training folds). Its recorded decision was `NO_QUALIFYING_CANDIDATE`, with `selected_candidate_id=null`. Every candidate failed the predeclared training thresholds.

## Step 5: deterministic promotion gate
This step **does not run validation or the final holdout**. It consumes the archived training optimization JSON and matching SHA-256-verified catalog from the same completed workflow run; validates partition locks, fixed grid, expected fold count/continuity, candidate identities, folds, profit/drawdown/trade qualification, selection ordering and outcome. The output is `phase3_decision.json`, including report hashes and an explicit no-promotion decision.

When no candidate passes, the outcome is `REJECTED_NO_QUALIFYING_CANDIDATE`, with `promotion_authorized=false`, `validation_executed=false`, `holdout_evaluated=false`, `live_trading_enabled=false`. A rejected strategy is a **successful completion of the research gate**, not a reason to loosen criteria or force a winner. If a future *new* training artifact includes a qualifier, the gate can only signal `READY_FOR_MANUAL_VALIDATION_REVIEW`; it never authorizes validation automatically.

## Manual workflow
After PR review and merge, dispatch [BTC Phase 3 final promotion decision](../.github/workflows/btc-phase3-final-decision.yml) on `main`, source run ID `40621068040`. The workflow downloads the source run's immutable archived optimization output (requires the GitHub Actions artifact to remain available), runs all Python tests, and writes the audited decision artifact. It does not authenticate to Azure, read market history, simulate, or send orders.

## Phase 3 progress
1. Signal framework — validated.
2. Initial comparison — validated.
3. Risk engine, diagnostics and causal signal-quality ablations — validated as engineering; no demonstrated net edge.
4. Fixed training-only grid and three-fold gate — validated; no candidate qualified.
5. Audited reject/no-promotion decision — this PR, awaiting workflow validation.

**After validation, Phase 3 closes with no promotable strategy.** The final holdout remains sealed for a future, prospectively selected model after independent validation and additional exchange-specific implementation.

## Handoff to next research phase
Research materially different hypotheses on training data, such as distinguishing trending/ranging market regimes, alternative holding horizons, or cost-aware signal design. Do not repeatedly sweep more parameters on the same observed losses merely to pick a historical winner. Preserve the frozen training report and criteria as negative evidence.

The USD linear engine does not reproduce actual Delta India BTC perpetual contract details: historical funding cash transfers, margin/liquidation behavior, contract-specific settlement and INR policy must be verified separately. No claims of realized profits; no live order placement.
