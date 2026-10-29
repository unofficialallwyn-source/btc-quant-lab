"""Phase 5 Step 2: frozen-ledger transaction cost accounting counterfactuals.

This is NOT a replay: trade times, quantities, risk decisions and fills remain
fixed. Alternative fee/slippage rates change ledger accounting ONLY. A new
execution simulation is required before claiming achievable returns.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd

FEE_MULTIPLIERS=(0.0,0.5,1.0,1.5,2.0)
SLIPPAGE_MULTIPLIERS=(0.0,0.5,1.0,1.5,2.0)
REQUIRED=("strategy","fold","gross_before_slippage","fees","slippage_cost","net_pnl","entry_time","exit_time")

def validate_ledger(ledger):
    if ledger.empty: raise ValueError("Empty frozen trade ledger")
    if not set(REQUIRED).issubset(ledger.columns):raise ValueError("Missing ledger columns")
    if ledger[list(("gross_before_slippage","fees","slippage_cost","net_pnl"))].isna().any().any():
        raise ValueError("Null trade accounting")
    if not np.isfinite(ledger[["gross_before_slippage","fees","slippage_cost","net_pnl"]].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite accounting")
    if (ledger.fees<0).any() or (ledger.slippage_cost< -1e-7).any():
        raise ValueError("Costs cannot be negative")
    if not np.allclose(ledger.gross_before_slippage-ledger.fees-ledger.slippage_cost,ledger.net_pnl,atol=1e-7,rtol=1e-9):
        raise ValueError("Frozen gross/net ledger mismatch")
    if not set(ledger.fold.unique()).issubset({1,2,3}):
        raise ValueError("Unexpected fold")


def scenario_metrics(ledger,fee_multiplier,slippage_multiplier):
    if fee_multiplier<0 or slippage_multiplier<0:raise ValueError("Negative cost multiplier")
    gross=float(ledger.gross_before_slippage.sum())
    fee=float((ledger.fees*fee_multiplier).sum())
    slip=float((ledger.slippage_cost*slippage_multiplier).sum())
    net=gross-fee-slip
    return {"trades":int(len(ledger)),"gross_before_cost":gross,
      "fees_accounting":fee,"slippage_accounting":slip,"net_accounting":net,
      "mean_net_per_trade":net/len(ledger),
      "gross_positive_net_nonpositive_count":int(((ledger.gross_before_slippage>0)&
        ((ledger.gross_before_slippage-ledger.fees*fee_multiplier-
          ledger.slippage_cost*slippage_multiplier)<=0)).sum())}


def evaluate(ledger_path,phase5_diagnostics_path,output):
    raw=Path(ledger_path).read_bytes()
    diag_raw=Path(phase5_diagnostics_path).read_bytes()
    diag=json.loads(diag_raw)
    if diag.get("phase")!="5_step_1" or diag.get("scope")!="training_only" or diag.get("validation_evaluated") is not False or diag.get("holdout_evaluated") is not False:
        raise ValueError("Requires frozen training-only Phase 5 diagnostics")
    ledger=pd.read_csv(ledger_path)
    validate_ledger(ledger)
    if set(ledger.strategy.unique())!=set(diag["strategies"]):
        raise ValueError("Strategy identities differ from source")
    for strategy,g in ledger.groupby("strategy"):
        source=diag["strategies"][strategy]
        if len(g)!=source["total_trades"] or abs(float(g.net_pnl.sum())-source["combined_net_pnl_independent_folds"])>1e-5:
            raise ValueError("Strategy results do not reconcile to source")
        for index,part in g.groupby("fold"):
            original=source["folds"][int(index)-1]
            if len(part)!=original["metrics"]["trades"] or abs(float(part.net_pnl.sum())-original["net_pnl"])>1e-5:
                raise ValueError("Fold results do not reconcile to source")
    scenarios=[]
    for strategy,g in ledger.groupby("strategy",sort=True):
        for fold,part in g.groupby("fold",sort=True):
            for fee in FEE_MULTIPLIERS:
                for slip in SLIPPAGE_MULTIPLIERS:
                    scenarios.append({"strategy":strategy,"fold":int(fold),
                      "fee_multiplier":fee,"slippage_multiplier":slip,
                      **scenario_metrics(part,fee,slip)})
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(scenarios).to_csv(output/"cost_sensitivity.csv",index=False)
    summary={}
    for name,g in ledger.groupby("strategy",sort=True):
        gross=float(g.gross_before_slippage.sum())
        fee=float(g.fees.sum())
        slip=float(g.slippage_cost.sum())
        summary[name]={"trades":int(len(g)),"gross_before_cost":gross,
          "baseline_fees":fee,"baseline_slippage":slip,"baseline_net":gross-fee-slip,
          "zero_cost_net_counterfactual":gross,
          "maximum_fee_multiplier_if_slippage_zero":max(0.,gross/fee) if gross>0 and fee>0 else None,
          "maximum_slippage_multiplier_if_fees_zero":max(0.,gross/slip) if gross>0 and slip>0 else None,
          "break_even_joint_cost_multiplier":max(0.,gross/(fee+slip)) if gross>0 and fee+slip>0 else None,
          "frozen_fold_zero_cost_net":[float(p.gross_before_slippage.sum()) for _,p in g.groupby("fold",sort=True)],
          "baseline_negative_folds":int(sum(float(p.net_pnl.sum())<=0 for _,p in g.groupby("fold")))}
    report={"schema_version":1,"phase":"5_step_2","scope":"training_only",
      "validation_evaluated":False,"holdout_evaluated":False,"live_trading_enabled":False,
      "source_trade_ledger_sha256":hashlib.sha256(raw).hexdigest(),
      "source_diagnostics_sha256":hashlib.sha256(diag_raw).hexdigest(),
      "source_phase4_sha256":diag.get("source_phase4_sha256"),
      "fee_multipliers":list(FEE_MULTIPLIERS),"slippage_multipliers":list(SLIPPAGE_MULTIPLIERS),
      "scenarios":len(scenarios),"summary":summary,
      "interpretation":"Fixed-trade accounting only. Changing costs in a live or resimulated system would change fills, sizing, stops and future trades. No profitable execution claim.",
      "provenance":"Phase 5 Step 1 training trades replayed and checked against frozen Phase 4."}
    (output/"cost_summary.json").write_text(json.dumps(report,indent=2,allow_nan=False)+chr(10))
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ledger",required=True)
    p.add_argument("--diagnostics",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    report=evaluate(a.ledger,a.diagnostics,a.output)
    print(json.dumps(report,indent=2,allow_nan=False))
if __name__=="__main__":main()
