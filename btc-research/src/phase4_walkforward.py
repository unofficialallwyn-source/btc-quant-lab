"""Phase 4 Step 4: frozen three-hypothesis, training-only walk-forward audit.

Each fold is a disjoint calendar slice of the original training partition.
Signal calculations and positions reset on folds/gaps. No tuning or validation.
"""
import argparse, hashlib, json
from dataclasses import asdict
from pathlib import Path
import pandas as pd
from .chronological_eval import read_segments
from .phase3_optimize import training_folds
from .phase4_hypotheses import Hypothesis, NAMES, research_specs, signals
from .risk_engine import RiskPolicy, run_risk

MIN_TRADES_PER_FOLD=20
MAX_DRAWDOWN_PCT=25.0

def fold_metrics(segments, hypothesis=None):
    risk=RiskPolicy(entry_mode="transition")
    fn=(lambda frame: [0]*len(frame)) if hypothesis is None else (
        lambda frame: signals(frame,hypothesis))
    metrics, ledger, curve=run_risk(segments,fn,risk,"5m")
    net=float(ledger.net_pnl.sum())
    gross=float(ledger.gross_before_slippage.sum())
    fees=float(ledger.fees.sum())
    slip=float(ledger.slippage_cost.sum())
    if abs(gross-fees-slip-net)>1e-6:
        raise AssertionError("Gross-to-net ledger failed reconciliation")
    if abs(risk.initial_equity+net-metrics["ending_equity"])>1e-4:
        raise AssertionError("End-equity reconciliation failed")
    return {"trades":len(ledger),"gross_before_slippage":gross,
        "fees":fees,"slippage":slip,"net_pnl":net,
        "net_return_pct":metrics["return_pct"],
        "profit_factor":metrics["profit_factor"],
        "max_drawdown_pct":metrics["max_drawdown_pct"],
        "win_rate_pct":metrics["win_rate_pct"],
        "gross_expectancy_per_trade":gross/len(ledger) if len(ledger) else None,
        "net_expectancy_per_trade":net/len(ledger) if len(ledger) else None,
        "exit_reasons":metrics["exit_reasons"]}


def qualify(results):
    return all(x["trades"]>=MIN_TRADES_PER_FOLD and x["net_pnl"]>0 and
               x["profit_factor"] is not None and x["profit_factor"]>1 and
               x["max_drawdown_pct"]<=MAX_DRAWDOWN_PCT for x in results)


def evaluate(catalog_dir,output):
    catalog,pieces=read_segments(catalog_dir)
    folds=training_folds(catalog,pieces)
    policies=research_specs()
    risk=RiskPolicy(entry_mode="transition")
    report={"schema_version":1,"phase":"4_step_4","selection_scope":"training_only",
      "validation_evaluated":False,"holdout_evaluated":False,
      "validation":{"status":"reserved"},"holdout":{"status":"locked"},
      "dataset_catalog_sha256":hashlib.sha256((Path(catalog_dir)/"dataset_catalog.json").read_bytes()).hexdigest(),
      "hypothesis_spec_sha256":hashlib.sha256(json.dumps(policies,sort_keys=True).encode()).hexdigest(),
      "risk_policy":asdict(risk),"min_trades_per_fold":MIN_TRADES_PER_FOLD,
      "max_drawdown_pct":MAX_DRAWDOWN_PCT,"folds":[],"candidates":{}}
    for start,end,_ in folds:
        report["folds"].append({"start_utc":pd.to_datetime(start,unit="s",utc=True).isoformat(),
          "end_exclusive_utc":pd.to_datetime(end,unit="s",utc=True).isoformat()})
    report["cash_no_trade"]={"fold_results":[fold_metrics(seg) for _,_,seg in folds],
        "interpretation":"Cash held with no positions: flat zero-PnL benchmark; not an eligible trading candidate."}
    for name in NAMES:
        spec=Hypothesis(name)
        results=[fold_metrics(seg,spec) for _,_,seg in folds]
        report["candidates"][name]={"hypothesis":asdict(spec),"fold_results":results,
            "total_trades":sum(r["trades"] for r in results),
            "total_net_pnl_independent_folds":sum(r["net_pnl"] for r in results),
            "worst_fold_return_pct":min(r["net_return_pct"] for r in results),
            "max_fold_drawdown_pct":max(r["max_drawdown_pct"] for r in results),
            "qualifies_training_gate":qualify(results)}
    qualified=[n for n in NAMES if report["candidates"][n]["qualifies_training_gate"]]
    report["qualifying_hypotheses"]=qualified
    report["decision"]="TRAINING_CANDIDATES_REQUIRE_MANUAL_REVIEW" if qualified else "NO_QUALIFYING_CANDIDATE"
    report["promotion_authorized"]=False
    report["warnings"]=[
        "Independent $1000 USD fold portfolios; summed PnL is not a continuous investable portfolio.",
        "Precommitted hypotheses; training success is not validation success or statistical significance.",
        "Actual Delta India funding, INR settlement, margin and liquidation not modeled."]
    target=Path(output);target.mkdir(parents=True,exist_ok=True)
    (target/"walkforward_report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+chr(10))
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog-dir",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    r=evaluate(a.catalog_dir,a.output)
    print(json.dumps({"decision":r["decision"],"qualified":r["qualifying_hypotheses"],
       "validation_evaluated":False,"holdout_evaluated":False,
       "cash_no_trade":r["cash_no_trade"],
       "candidates":{name:{"fold_results":v["fold_results"],
          "qualifies_training_gate":v["qualifies_training_gate"]}
          for name,v in r["candidates"].items()}},indent=2,allow_nan=False))
if __name__=="__main__":
    main()
