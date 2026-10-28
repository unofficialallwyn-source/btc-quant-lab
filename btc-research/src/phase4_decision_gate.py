"""Fail-closed Phase 4 final decision from archived, training-only fold evidence.

No historical candles, validation data or exchange credentials are needed.
"""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from .phase4_walkforward import MIN_TRADES_PER_FOLD, MAX_DRAWDOWN_PCT, qualify
from .phase4_hypotheses import NAMES, Hypothesis, research_specs
from .phase3_optimize import FOLDS
from .risk_engine import RiskPolicy
from dataclasses import asdict


def ensure(ok, msg):
    if not ok:
        raise ValueError("Phase 4 decision gate rejected evidence: "+msg)


def decide(source_file, catalog_file, source_run_id):
    raw=Path(source_file).read_bytes()
    report=json.loads(raw)
    catalog_raw=Path(catalog_file).read_bytes()
    catalog=json.loads(catalog_raw)
    ensure(report.get("schema_version")==1 and report.get("phase")=="4_step_4","schema or phase")
    ensure(report.get("selection_scope")=="training_only","scope must be training only")
    ensure(report.get("validation_evaluated") is False and report.get("holdout_evaluated") is False,"validation/holdout accessed")
    ensure(report.get("validation")=={"status":"reserved"} and report.get("holdout")=={"status":"locked"},"reserved data unlocked")
    ensure(report.get("promotion_authorized") is False,"unexpected promotion")
    ensure(report.get("dataset_catalog_sha256")==hashlib.sha256(catalog_raw).hexdigest(),"catalog checksum")
    ensure(catalog.get("symbol")=="BTCUSD" and catalog.get("resolution")=="1m","unexpected dataset")
    expected_spec=hashlib.sha256(json.dumps(research_specs(),sort_keys=True).encode()).hexdigest()
    ensure(report.get("hypothesis_spec_sha256")==expected_spec,"hypotheses have changed")
    ensure(report.get("risk_policy")==asdict(RiskPolicy(entry_mode="transition")),"risk settings changed")
    ensure(report.get("min_trades_per_fold")==MIN_TRADES_PER_FOLD and
           report.get("max_drawdown_pct")==MAX_DRAWDOWN_PCT,"acceptance gate changed")
    folds=report.get("folds")
    ensure(isinstance(folds,list) and len(folds)==FOLDS,"fold count")
    for i,fold in enumerate(folds):
        a=datetime.fromisoformat(fold["start_utc"])
        b=datetime.fromisoformat(fold["end_exclusive_utc"])
        ensure(a.tzinfo is not None and b.tzinfo is not None and a<b,"invalid fold boundaries")
        if i:ensure(folds[i-1]["end_exclusive_utc"]==fold["start_utc"],"fold gap or overlap")
    baseline=report.get("cash_no_trade",{}).get("fold_results")
    ensure(isinstance(baseline,list) and len(baseline)==FOLDS,"cash benchmark missing")
    for item in baseline:
        ensure(item.get("trades")==0 and all(item.get(k)==0 for k in
            ("net_pnl","fees","slippage","gross_before_slippage","net_return_pct")),"invalid cash benchmark")
    candidates=report.get("candidates")
    ensure(isinstance(candidates,dict) and set(candidates)==set(NAMES),"unexpected candidates")
    eligible=[]
    failures={}
    for name in NAMES:
        c=candidates[name]
        ensure(c.get("hypothesis")==asdict(Hypothesis(name)),"candidate spec mismatch: "+name)
        outcomes=c.get("fold_results")
        ensure(isinstance(outcomes,list) and len(outcomes)==FOLDS,"fold outcomes missing: "+name)
        fail=[]
        for fold_index,o in enumerate(outcomes,1):
            prefix=f"{name} fold {fold_index}"
            n=o.get("trades")
            ensure(type(n) is int and n>=0,"invalid trade count: "+prefix)
            gross=o.get("gross_before_slippage")
            fees=o.get("fees")
            slippage=o.get("slippage")
            net=o.get("net_pnl")
            ensure(all(type(v) in (float,int) and abs(v)<1e12 and v==v
                for v in (gross,fees,slippage,net)),"invalid ledger numbers: "+prefix)
            ensure(fees>=0 and slippage>=-1e-7,"negative execution costs: "+prefix)
            ensure(abs(gross-fees-slippage-net)<1e-5,"ledger reconciliation: "+prefix)
            ensure(abs(net-10*o["net_return_pct"])<.005,"net return reconciliation: "+prefix)
            ensure(0<=o["max_drawdown_pct"]<=100,"drawdown invalid: "+prefix)
            ensure((o.get("profit_factor") is None) or
                   (type(o["profit_factor"]) in (float,int) and o["profit_factor"]>=0),
                   "invalid profit factor: "+prefix)
            if n<MIN_TRADES_PER_FOLD:fail.append(f"fold_{fold_index}:insufficient_trades")
            if net<=0:fail.append(f"fold_{fold_index}:nonpositive_net_pnl")
            if o["profit_factor"] is None or o["profit_factor"]<=1:fail.append(f"fold_{fold_index}:profit_factor_not_above_one")
            if o["max_drawdown_pct"]>MAX_DRAWDOWN_PCT:fail.append(f"fold_{fold_index}:drawdown_exceeded")
        actual=qualify(outcomes)
        ensure(c.get("qualifies_training_gate") is actual,"candidate gate mismatch: "+name)
        ensure(c.get("total_trades")==sum(o["trades"] for o in outcomes),"trade total mismatch: "+name)
        ensure(abs(c.get("total_net_pnl_independent_folds")-sum(o["net_pnl"] for o in outcomes))<1e-5,
               "net total mismatch: "+name)
        ensure(abs(c.get("worst_fold_return_pct")-min(o["net_return_pct"] for o in outcomes))<1e-6,
               "worst fold mismatch: "+name)
        ensure(abs(c.get("max_fold_drawdown_pct")-max(o["max_drawdown_pct"] for o in outcomes))<1e-6,
               "fold drawdown mismatch: "+name)
        failures[name]=fail
        if actual:eligible.append(name)
    ensure(report.get("qualifying_hypotheses")==eligible,"eligibility list mismatch")
    expected="TRAINING_CANDIDATES_REQUIRE_MANUAL_REVIEW" if eligible else "NO_QUALIFYING_CANDIDATE"
    ensure(report.get("decision")==expected,"decision mismatch")
    ensure(str(source_run_id).isdigit() and int(source_run_id)>0,"source run id")
    return {"schema_version":1,"phase":"4_step_5","decision":
        "REJECTED_NO_QUALIFYING_CANDIDATE" if not eligible else "MANUAL_REVIEW_REQUIRED_NO_PROMOTION",
        "promotion_authorized":False,"validation_evaluated":False,
        "holdout_evaluated":False,"live_trading_enabled":False,
        "source_workflow_run_id":str(source_run_id),
        "source_report_sha256":hashlib.sha256(raw).hexdigest(),
        "dataset_catalog_sha256":hashlib.sha256(catalog_raw).hexdigest(),
        "hypothesis_spec_sha256":expected_spec,
        "candidates_examined":len(candidates),"qualified_candidates":len(eligible),
        "candidate_failures":failures,"qualified_names":eligible,
        "next_research_priority":("Audit entries, exits, and execution-cost attribution; design distinct predeclared hypotheses without tuning failed rules to a favorable result."
         if not eligible else "Freeze candidate and require separate explicit authorization for controlled validation."),
        "limitations":"Simplified USD-linear model; Delta India historical funding, INR settlement, margin and liquidation unmodeled."}


def main():
    p=argparse.ArgumentParser()
    for x in ("walkforward","catalog","source-run-id","output"):p.add_argument("--"+x,required=True)
    a=p.parse_args()
    decision=decide(a.walkforward,a.catalog,a.source_run_id)
    target=Path(a.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(decision,indent=2,allow_nan=False)+chr(10))
    print(json.dumps(decision,indent=2))

if __name__=="__main__":main()
