"""Phase 5 Step 1: cost and exit diagnostics, training data ONLY.

Replays Phase 4's frozen strategies and risk policy without tuning and
checks every fold against the archived Phase 4 Step 4 outcome.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from .chronological_eval import read_segments
from .phase3_optimize import training_folds
from .phase4_hypotheses import NAMES,Hypothesis,signals
from .risk_engine import RiskPolicy,run_risk

def analyze_ledger(ledger):
    if ledger.empty:
        return {"trades":0,"exit_reasons":{},"winner_count":0,"loser_count":0,
                "avg_hold_minutes":None,"median_hold_minutes":None,"mean_net_pnl":None,
                "breakeven_additional_cost_per_trade":None}
    d=ledger.copy()
    d["hold_minutes"]=(d.exit_time-d.entry_time)/60
    d["gross_positive"]=d.gross_before_slippage>0
    def bucket(g):
        return {"trades":int(len(g)),"gross_before_slippage":float(g.gross_before_slippage.sum()),
           "fees":float(g.fees.sum()),"slippage":float(g.slippage_cost.sum()),
           "net_pnl":float(g.net_pnl.sum()),
           "mean_hold_minutes":float(g.hold_minutes.mean())}
    return {"trades":int(len(d)),"exit_reasons":{str(k):bucket(g) for k,g in d.groupby("exit_reason")},
      "winner_count":int((d.net_pnl>0).sum()),"loser_count":int((d.net_pnl<0).sum()),
      "gross_winner_net_loser_count":int((d.gross_positive&(d.net_pnl<=0)).sum()),
      "avg_hold_minutes":float(d.hold_minutes.mean()),"median_hold_minutes":float(d.hold_minutes.median()),
      "mean_net_pnl":float(d.net_pnl.mean()),
      "mean_gross_before_cost":float(d.gross_before_slippage.mean()),
      "mean_fees":float(d.fees.mean()),"mean_slippage":float(d.slippage_cost.mean()),
      "breakeven_additional_cost_per_trade":float(d.net_pnl.mean())}


def verify_fold(ledger,baseline,metrics):
    sums={key:float(ledger[key].sum()) for key in
          ("gross_before_slippage","fees","slippage_cost","net_pnl")}
    if abs(sums["gross_before_slippage"]-sums["fees"]-sums["slippage_cost"]-sums["net_pnl"])>1e-6:
        raise ValueError("Trade ledger does not reconcile")
    for column,expected in (("gross_before_slippage",sums["gross_before_slippage"]),
        ("fees",sums["fees"]),("slippage",sums["slippage_cost"]),("net_pnl",sums["net_pnl"])):
        if abs(expected-baseline[column])>1e-5:
            raise ValueError("Frozen Phase 4 mismatch: "+column)
    if int(baseline["trades"])!=len(ledger):
        raise ValueError("Frozen Phase 4 trade count mismatch")
    if abs(float(metrics["return_pct"])-float(baseline["net_return_pct"]))>1e-6:
        raise ValueError("Frozen Phase 4 return mismatch")


def evaluate(catalog_dir, phase4_report, output):
    original_bytes=Path(phase4_report).read_bytes()
    frozen=json.loads(original_bytes)
    catalog,pieces=read_segments(catalog_dir)
    raw_catalog=(Path(catalog_dir)/"dataset_catalog.json").read_bytes()
    if frozen.get("phase")!="4_step_4" or frozen.get("selection_scope")!="training_only":
        raise ValueError("Requires frozen Phase 4 training report")
    if frozen.get("validation_evaluated") is not False or frozen.get("holdout_evaluated") is not False:
        raise ValueError("Validation/holdout cannot be used")
    if frozen.get("dataset_catalog_sha256")!=hashlib.sha256(raw_catalog).hexdigest():
        raise ValueError("Catalog checksum does not match frozen Phase 4")
    folds=training_folds(catalog,pieces)
    if len(folds)!=len(frozen["folds"]):
        raise ValueError("Frozen fold count changed")
    risk=RiskPolicy(entry_mode="transition")
    report={"schema_version":1,"phase":"5_step_1","scope":"training_only",
      "validation_evaluated":False,"holdout_evaluated":False,"promotion_authorized":False,
      "live_trading_enabled":False,
      "source_phase4_sha256":hashlib.sha256(original_bytes).hexdigest(),
      "catalog_sha256":hashlib.sha256(raw_catalog).hexdigest(),"strategies":{}}
    records=[]
    for name in NAMES:
        src=frozen["candidates"][name]["fold_results"]
        fold_reports=[]
        for i,(_,_,segments) in enumerate(folds):
            metrics,ledger,_=run_risk(segments,lambda f:signals(f,Hypothesis(name)),risk,"5m")
            verify_fold(ledger,src[i],metrics)
            diag=analyze_ledger(ledger)
            fold_reports.append({"fold":i+1,"metrics":diag,"net_pnl":float(ledger.net_pnl.sum())})
            if not ledger.empty:
                d=ledger.copy()
                d.insert(0,"strategy",name)
                d.insert(1,"fold",i+1)
                records.append(d)
        report["strategies"][name]={"folds":fold_reports,
            "total_trades":sum(x["metrics"]["trades"] for x in fold_reports),
            "combined_net_pnl_independent_folds":sum(x["net_pnl"] for x in fold_reports)}
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    if records:
        pd.concat(records,ignore_index=True).to_csv(root/"training_trade_ledger.csv",index=False)
    else:
        pd.DataFrame(columns=["strategy","fold","entry_time","exit_time","net_pnl"]).to_csv(root/"training_trade_ledger.csv",index=False)
    report["caveats"]=["Historical replay of frozen rejected strategies, no parameter tuning",
      "No future information or validation/holdout price data used",
      "No reliable historical order-book, spread, funding or INR liquidation modeling",
      "Independent $1000 folds; do not compound their PnL"]
    (root/"trade_diagnostics.json").write_text(json.dumps(report,indent=2,allow_nan=False)+chr(10))
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog-dir",required=True)
    p.add_argument("--phase4-report",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    r=evaluate(a.catalog_dir,a.phase4_report,a.output)
    print(json.dumps({"phase":r["phase"],"scope":r["scope"],
      "strategies":{k:{"total_trades":v["total_trades"],"combined_net_pnl_independent_folds":v["combined_net_pnl_independent_folds"]}
         for k,v in r["strategies"].items()},
      "validation_evaluated":False,"holdout_evaluated":False},indent=2))

if __name__=="__main__":main()
