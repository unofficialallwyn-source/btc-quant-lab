"""Run predefined Phase 3 strategies over training and validation ONLY.

Research comparisons are exploratory. Do not use final holdout for selection.
"""
import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
import pandas as pd

from .chronological_eval import boundaries,read_segments
from .sim_engine import Config,run
from .strategies import Strategy,signals

NAMES=("trend","mean_reversion","volatility_breakout")


def evaluate(catalog_dir,output, *, names=NAMES,signal_tf="5m",context_tf="1h"):
    catalog,pieces=read_segments(catalog_dir)
    start=int(pd.Timestamp(catalog["start_utc"]).timestamp())
    end=int(pd.Timestamp(catalog["end_exclusive_utc"]).timestamp())
    windows=boundaries(start,end)
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    report={"schema_version":1,"holdout_evaluated":False,
        "holdout":{"status":"locked"},
        "data_catalog_sha256":hashlib.sha256((Path(catalog_dir)/"dataset_catalog.json").read_bytes()).hexdigest(),
        "model":"USD linear PnL simulation; fees and slippage; no funding, no margin/liquidation",
        "policy":"exploratory training/validation comparison, not profitability evidence",
        "signal_tf":signal_tf,"context_tf":context_tf,
        "strategies":{}}
    for name in names:
        spec=Strategy(name=name,signal_tf=signal_tf,context_tf=context_tf)
        spec.check()
        results={}
        for partition in ("training","validation"):
            a,b=windows[partition]
            within=[p.loc[(p.time>=a)&(p.time<b)].reset_index(drop=True) for p in pieces]
            within=[p for p in within if not p.empty]
            if not within:
                raise ValueError("Missing evaluated partition")
            metrics,ledger,curve=run(within,lambda frame:signals(frame,spec),Config())
            ledger.to_csv(out/f"{name}_{partition}_trades.csv",index=False)
            curve.to_csv(out/f"{name}_{partition}_equity.csv",index=False)
            results[partition]={**metrics,"candles":sum(len(p) for p in within)}
        report["strategies"][name]={"parameters":asdict(spec),"results":results}
    (out/"strategy_comparison.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog-dir",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--signal-tf",default="5m",choices=["1m","5m","15m","1h"])
    p.add_argument("--context-tf",default="1h",choices=["5m","15m","1h","4h"])
    a=p.parse_args()
    report=evaluate(a.catalog_dir,a.output,signal_tf=a.signal_tf,context_tf=a.context_tf)
    print(json.dumps(report,indent=2,allow_nan=False))


if __name__=="__main__":
    main()
