"""Fail-closed Phase 3 promotion gate using frozen training-only optimization evidence.

No validation/holdout candles are loaded; NO_QUALIFYING_CANDIDATE yields a
completed, rejected decision, not a workflow failure.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .phase3_optimize import GRID, MIN_TRADES_PER_FOLD, FOLDS, grid


def _check(flag, message):
    if not flag:
        raise ValueError("Promotion gate rejected invalid evidence: " + message)


def decide(optimization, catalog, source_run_id):
    report = json.loads(Path(optimization).read_text())
    raw_catalog = Path(catalog).read_bytes()
    catalog_data = json.loads(raw_catalog)
    _check(report.get("schema_version") == 1, "unknown report schema")
    _check(report.get("selection_scope") == "training_only", "wrong selection scope")
    _check(report.get("validation_evaluated") is False and
           report.get("holdout_evaluated") is False, "holdout/validation accessed")
    _check(report.get("validation", {}).get("status") == "reserved" and
           report.get("holdout", {}).get("status") == "locked", "unlock status")
    _check(report.get("dataset_catalog_sha256") ==
           hashlib.sha256(raw_catalog).hexdigest(), "dataset catalog checksum")
    _check(catalog_data.get("symbol") == "BTCUSD" and
           catalog_data.get("resolution") == "1m", "unexpected research data")
    _check(report.get("grid") == {k:list(v) for k,v in GRID.items()}, "unexpected grid")
    _check(report.get("min_trades_per_fold") == MIN_TRADES_PER_FOLD,
           "minimum trade requirement differs")
    folds = report.get("folds")
    _check(isinstance(folds,list) and len(folds) == FOLDS, "fold count")
    for i,fold in enumerate(folds):
        start = datetime.fromisoformat(fold["start_utc"])
        end = datetime.fromisoformat(fold["end_exclusive_utc"])
        _check(start.tzinfo is not None and end.tzinfo is not None and start < end,
               "invalid fold timestamps")
        if i:
            _check(folds[i-1]["end_exclusive_utc"] == fold["start_utc"],
                   "noncontiguous folds")
    candidates = report.get("candidates")
    _check(isinstance(candidates,list) and len(candidates) == len(grid()),
           "candidate count")
    expected = grid()
    eligible = []
    for index,c in enumerate(candidates):
        _check(c.get("id") == index+1 and c.get("parameters") == expected[index],
               "candidate identity or parameters")
        observations = c.get("fold_results")
        _check(isinstance(observations,list) and len(observations) == FOLDS,
               "fold results")
        for item in observations:
            for key in ("net_pnl","profit_factor","max_drawdown_pct","trades","return_pct"):
                _check(key in item, "missing metric "+key)
            _check(isinstance(item["trades"],int) and item["trades"] >= 0,
                   "invalid trade count")
            _check(0 <= item["max_drawdown_pct"] <= 100, "invalid drawdown")
            _check(abs(item["net_pnl"] - 1000*item["return_pct"]/100) < .005,
                   "fold net/return mismatch")
        qualifies = all(
            x["trades"] >= MIN_TRADES_PER_FOLD and x["net_pnl"] > 0 and
            x["profit_factor"] is not None and x["profit_factor"] > 1 and
            x["max_drawdown_pct"] <= 25 for x in observations)
        _check(abs(c["worst_fold_return_pct"]-
                   min(x["return_pct"] for x in observations)) < 1e-6,
               "worst-fold return mismatch")
        _check(abs(c["max_fold_drawdown_pct"]-
                   max(x["max_drawdown_pct"] for x in observations)) < 1e-6,
               "fold drawdown mismatch")
        _check(c.get("qualifies") is qualifies, "candidate eligibility mismatch")
        _check(abs(c["all_fold_net_pnl"]-
                   sum(x["net_pnl"] for x in observations)) < 1e-5,
               "fold total mismatch")
        if qualifies:
            eligible.append(c)
    eligible.sort(key=lambda c:(-c["worst_fold_return_pct"],
                                c["max_fold_drawdown_pct"],c["id"]))
    chosen = eligible[0]["id"] if eligible else None
    _check(report.get("selected_candidate_id") == chosen, "selection mismatch")
    expected_decision = ("candidate_for_controlled_validation" if chosen
                         else "NO_QUALIFYING_CANDIDATE")
    _check(report.get("decision") == expected_decision, "decision mismatch")
    _check(str(source_run_id).isdigit() and int(source_run_id)>0, "source run id")
    outcome = "REJECTED_NO_QUALIFYING_CANDIDATE" if chosen is None else "READY_FOR_MANUAL_VALIDATION_REVIEW"
    return {
        "schema_version":1,"phase":"3_step_5","decision":outcome,
        "promotion_authorized":False,
        "validation_executed":False,"holdout_evaluated":False,
        "live_trading_enabled":False,
        "source_workflow_run_id":str(source_run_id),
        "optimization_sha256":hashlib.sha256(Path(optimization).read_bytes()).hexdigest(),
        "catalog_sha256":hashlib.sha256(raw_catalog).hexdigest(),
        "candidates_examined":len(candidates),"qualified_candidates":len(eligible),
        "selected_candidate_id":chosen,
        "reasons":(["No candidate met trade count, net-profit, profit-factor and drawdown requirements in every training fold."]
                   if chosen is None else
                   ["Training gate qualified a candidate; separate human approval and a one-time validation protocol are still required."]),
        "next_research_priority":("Develop materially new entry/exit hypotheses using training data; do not expand grid solely to force qualification."
                                  if chosen is None else
                                  "Freeze selected parameters and seek explicit approval for controlled validation."),
        "limitations":"USD-linear simulation only; actual Delta funding, INR settlement and liquidation not modeled."
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--optimization",required=True)
    p.add_argument("--catalog",required=True)
    p.add_argument("--source-run-id",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    outcome=decide(a.optimization,a.catalog,a.source_run_id)
    path=Path(a.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(outcome,indent=2,allow_nan=False)+"\n")
    print(json.dumps(outcome,indent=2))


if __name__=="__main__":
    main()
