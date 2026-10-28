"""Small, precommitted training-only walk-forward grid, no validation/holdout.

Every candidate is scored on chronological training folds, avoiding a single
full-training return winner. Outputs diagnostics even when all choices fail.
"""
import argparse, hashlib, itertools, json
from dataclasses import asdict, replace
from pathlib import Path
import pandas as pd
from .chronological_eval import read_segments, boundaries
from .risk_engine import RiskPolicy, run_risk
from .strategies import Strategy
from .signal_quality import QualityPolicy, filtered_signals

# 16 configurations total, fixed *before* examining optimization results.
GRID = {
    "atr_stop_multiple": (2.0, 3.0),
    "max_hold_minutes": (30, 60),
    "cooldown_minutes": (15, 45),
    "min_range_to_roundtrip_cost": (2.0, 3.0),
}
FILTERS = ("trend", "volatility", "volume", "cost")
FOLDS = 3
MIN_TRADES_PER_FOLD = 20


def grid():
    keys = tuple(GRID)
    return [dict(zip(keys, vals)) for vals in itertools.product(*(GRID[k] for k in keys))]


def training_folds(catalog, pieces, folds=FOLDS):
    start = int(pd.Timestamp(catalog["start_utc"]).timestamp())
    end = int(pd.Timestamp(catalog["end_exclusive_utc"]).timestamp())
    train_lo, train_hi = boundaries(start, end)["training"]
    day = 86400
    first, last = train_lo // day, train_hi // day
    edges = [(first + ((last-first)*i)//folds)*day for i in range(folds+1)]
    if len(set(edges)) != folds+1:
        raise ValueError("Training interval too short for folds")
    output = []
    for a,b in zip(edges,edges[1:]):
        segments = [p.loc[(p.time>=a)&(p.time<b)].reset_index(drop=True) for p in pieces]
        segments = [p for p in segments if not p.empty]
        if not segments:raise ValueError("Fold has no candles")
        output.append((a,b,segments))
    return output


def evaluate(catalog_dir, output, signal_tf="5m", context_tf="1h"):
    catalog,pieces = read_segments(catalog_dir)
    folds = training_folds(catalog,pieces)
    spec = Strategy("volatility_breakout",signal_tf=signal_tf,context_tf=context_tf)
    spec.check()
    output = Path(output);output.mkdir(parents=True,exist_ok=True)
    report = {"schema_version":1,"selection_scope":"training_only",
        "validation_evaluated":False,"holdout_evaluated":False,
        "validation":{"status":"reserved"},"holdout":{"status":"locked"},
        "dataset_catalog_sha256":hashlib.sha256((Path(catalog_dir)/"dataset_catalog.json").read_bytes()).hexdigest(),
        "signal":asdict(spec),"grid":GRID,"folds":[],
        "min_trades_per_fold":MIN_TRADES_PER_FOLD,"candidates":[]}
    for a,b,_ in folds:
        report["folds"].append({"start_utc":pd.to_datetime(a,unit="s",utc=True).isoformat(),
            "end_exclusive_utc":pd.to_datetime(b,unit="s",utc=True).isoformat()})
    for index,parameters in enumerate(grid(),1):
        risk = replace(RiskPolicy(entry_mode="transition"),
            atr_stop_multiple=parameters["atr_stop_multiple"],
            max_hold_minutes=parameters["max_hold_minutes"],
            cooldown_minutes=parameters["cooldown_minutes"])
        quality=replace(QualityPolicy(),
            min_range_to_roundtrip_cost=parameters["min_range_to_roundtrip_cost"])
        outcomes=[]
        for _,_,segments in folds:
            metrics,trades,_=run_risk(segments,
                lambda f:filtered_signals(f,spec,FILTERS,quality,risk),risk,signal_tf)
            if abs(metrics["ending_equity"]-risk.initial_equity-float(trades.net_pnl.sum()))>1e-4:
                raise ValueError("Net P&L does not reconcile")
            outcomes.append({"return_pct":metrics["return_pct"],
                "max_drawdown_pct":metrics["max_drawdown_pct"],
                "trades":metrics["trades"],"profit_factor":metrics["profit_factor"],
                "gross_before_slippage":metrics["gross_before_slippage_total"],
                "fees":metrics["fee_total"],"slippage":metrics["slippage_total"],
                "net_pnl":float(trades.net_pnl.sum())})
        valid=all(o["trades"]>=MIN_TRADES_PER_FOLD for o in outcomes)
        profitable=all(o["net_pnl"]>0 and o["profit_factor"] is not None and o["profit_factor"]>1 for o in outcomes)
        # Hard constraints ensure the optimizer can return NO CANDIDATE.
        qualifies=valid and profitable and all(o["max_drawdown_pct"]<=25 for o in outcomes)
        report["candidates"].append({"id":index,"parameters":parameters,
            "risk_policy":asdict(risk),"quality_policy":asdict(quality),
            "fold_results":outcomes,"qualifies":qualifies,
            "worst_fold_return_pct":min(o["return_pct"] for o in outcomes),
            "max_fold_drawdown_pct":max(o["max_drawdown_pct"] for o in outcomes),
            "all_fold_net_pnl":sum(o["net_pnl"] for o in outcomes)})
    eligible=[x for x in report["candidates"] if x["qualifies"]]
    eligible.sort(key=lambda x:(-x["worst_fold_return_pct"],x["max_fold_drawdown_pct"],x["id"]))
    report["selected_candidate_id"]=eligible[0]["id"] if eligible else None
    report["decision"]="candidate_for_controlled_validation" if eligible else "NO_QUALIFYING_CANDIDATE"
    (output/"training_optimization.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog-dir",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--signal-tf",choices=["1m","5m","15m","1h"],default="5m")
    p.add_argument("--context-tf",choices=["5m","15m","1h","4h"],default="1h")
    args=p.parse_args()
    r=evaluate(args.catalog_dir,args.output,args.signal_tf,args.context_tf)
    print(json.dumps({"decision":r["decision"],"selected_candidate_id":r["selected_candidate_id"],
        "folds":r["folds"],"candidates":[{"id":c["id"],"parameters":c["parameters"],
        "qualifies":c["qualifies"],"worst_fold_return_pct":c["worst_fold_return_pct"],
        "max_fold_drawdown_pct":c["max_fold_drawdown_pct"],
        "all_fold_net_pnl":c["all_fold_net_pnl"]} for c in r["candidates"]]},indent=2))

if __name__=="__main__":main()
