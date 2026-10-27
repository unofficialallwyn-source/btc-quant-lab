"""Run Delta INR research evaluation; never unlock final holdout.

External market data is mandatory. Results contain provenance and coverage
report. This process refuses incomplete historical inputs rather than making
up FX, mark, or funding data.
"""
import argparse
import json
from pathlib import Path

from .chronological_eval import read_segments,boundaries
from .multi_timeframe import causal_breakout_signal
from .delta_market_inputs import load_inputs,coverage_report
from .delta_sim_engine import run_delta,DeltaSimConfig
import pandas as pd


def evaluate_delta(catalog_dir,external_dir,output,timeframe="5m",initial_inr="85000"):
    if timeframe not in ("1m","5m","15m","1h","4h"):
        raise ValueError("Unsupported timeframe")
    catalog,pieces=read_segments(catalog_dir)
    bounds=boundaries(int(pd.Timestamp(catalog["start_utc"]).timestamp()),
                      int(pd.Timestamp(catalog["end_exclusive_utc"]).timestamp()))
    # Never even load holdout candle rows into simulation.
    trainval=[p.loc[(p.time>=bounds["training"][0]) &
                    (p.time<bounds["validation"][1])].reset_index(drop=True)
              for p in pieces]
    trainval=[p for p in trainval if not p.empty]
    manifest,mark,fx,funding=load_inputs(external_dir)
    report=coverage_report(trainval,mark,fx,funding)
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    (out/"input_coverage.json").write_text(json.dumps(report,indent=2)+"\n")
    if not report["complete"]:
        raise ValueError("External historical inputs incomplete: see input_coverage.json")
    summary={"schema_version":1,"currency":"INR","timeframe":timeframe,
             "holdout_evaluated":False,"source_manifest":manifest,
             "results":{}}
    signal=lambda f:causal_breakout_signal(f,timeframe)
    for name in ("training","validation"):
        lo,hi=bounds[name]
        within=[p.loc[(p.time>=lo)&(p.time<hi)].reset_index(drop=True)
                for p in trainval]
        within=[p for p in within if not p.empty]
        if not within:
            summary["results"][name]={"status":"no_verified_candles"}
            continue
        metrics,trades,equity=run_delta(within,signal,mark,fx,funding,
                                       DeltaSimConfig(initial_inr=initial_inr))
        summary["results"][name]=metrics
        trades.to_csv(out/f"{name}_trades.csv",index=False)
        equity.to_csv(out/f"{name}_equity.csv",index=False)
    summary["results"]["holdout"]={"status":"locked"}
    (out/"delta_evaluation.json").write_text(json.dumps(summary,indent=2)+"\n")
    return summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--catalog-dir",required=True)
    parser.add_argument("--external-dir",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--timeframe",choices=["1m","5m","15m","1h","4h"],default="5m")
    parser.add_argument("--initial-inr",default="85000")
    a=parser.parse_args()
    print(json.dumps(evaluate_delta(a.catalog_dir,a.external_dir,a.output,
                        a.timeframe,a.initial_inr),indent=2))


if __name__=="__main__":
    main()
