"""Phase 3 deterministic risk-policy comparisons (training only by default)."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path
import hashlib

import pandas as pd

from .chronological_eval import read_segments,boundaries
from .strategies import Strategy,signals
from .risk_engine import RiskPolicy,run_risk


def evaluate(catalog_dir,output,signal_tf="5m",context_tf="1h"):
    catalog,pieces=read_segments(catalog_dir)
    start=int(pd.Timestamp(catalog["start_utc"]).timestamp())
    end=int(pd.Timestamp(catalog["end_exclusive_utc"]).timestamp())
    parts=boundaries(start,end)
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    cfg=RiskPolicy()
    report={"schema_version":1,"mode":"training_only_risk_policy_exploration",
        "holdout_evaluated":False,"validation_evaluated":False,
        "holdout":{"status":"locked"},"validation":{"status":"reserved"},
        "dataset_catalog_sha256":hashlib.sha256((Path(catalog_dir)/"dataset_catalog.json").read_bytes()).hexdigest(),
        "risk_policy":asdict(cfg),"strategies":{}}
    lo,hi=parts["training"]
    partition=[p.loc[(p.time>=lo)&(p.time<hi)].reset_index(drop=True) for p in pieces]
    partition=[p for p in partition if not p.empty]
    if not partition:raise ValueError("No training candles")
    for name in ("trend","mean_reversion","volatility_breakout"):
        spec=Strategy(name=name,signal_tf=signal_tf,context_tf=context_tf)
        spec.check()
        metrics,ledger,equity=run_risk(partition,lambda frame:signals(frame,spec),cfg,signal_tf)
        ledger.to_csv(root/f"{name}_training_trades.csv",index=False)
        equity.to_csv(root/f"{name}_training_equity.csv",index=False)
        report["strategies"][name]={"signal_parameters":asdict(spec),"training":metrics,
            "diagnostics":{"net_pnl_check":float(ledger.net_pnl.sum()) if len(ledger) else 0.0,
                "fees_to_initial_equity_pct":100*metrics["fee_total"]/cfg.initial_equity,
                "exit_reason_counts":metrics["exit_reasons"],
                "entry_decisions":metrics["entry_decisions"],
                "total_holding_hours":float((ledger.exit_time-ledger.entry_time).sum()/3600) if len(ledger) else 0.0}}
        if abs(metrics["ending_equity"]-(cfg.initial_equity+float(ledger.net_pnl.sum())))>1e-4:
            raise ValueError("Risk engine balance does not reconcile to ledger")
    (root/"risk_comparison.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog-dir",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--signal-tf",choices=["1m","5m","15m","1h"],default="5m")
    p.add_argument("--context-tf",choices=["5m","15m","1h","4h"],default="1h")
    a=p.parse_args()
    print(json.dumps(evaluate(a.catalog_dir,a.output,a.signal_tf,a.context_tf),indent=2,allow_nan=False))


if __name__=="__main__":
    main()
