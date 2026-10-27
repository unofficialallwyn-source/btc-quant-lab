"""Chronological, gap-safe evaluation with an opt-in untouched holdout.

Time windows are fixed before strategy selection. Boundary segments are cropped;
indicators/positions restart at each partition and every real market-data gap.
"""
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json

import pandas as pd

from .sim_engine import Config, run, breakout_signal
from .research_segments import segments


def boundaries(start, end, train_fraction=0.60, validation_fraction=0.20):
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1 or train_fraction + validation_fraction >= 1:
        raise ValueError("Invalid training/validation fractions")
    if end <= start:
        raise ValueError("Invalid period")
    # Align to UTC day boundaries. Fractions are of elapsed calendar time,
    # not observed candles: missing days cannot move the holdout boundary.
    day=86400
    a=((start+int((end-start)*train_fraction))//day)*day
    b=((start+int((end-start)*(train_fraction+validation_fraction)))//day)*day
    if not start < a < b < end:
        raise ValueError("Period too short for three UTC-day partitions")
    return {"training":(start,a),"validation":(a,b),"holdout":(b,end)}


def read_segments(folder):
    folder=Path(folder)
    catalog=json.loads((folder/"dataset_catalog.json").read_text())
    if catalog.get("symbol")!="BTCUSD" or catalog.get("resolution")!="1m":
        raise ValueError("Unexpected research catalog")
    loaded=[]
    for item in catalog["segments"]:
        name=item["filename"]
        if not isinstance(name,str) or Path(name).name!=name or not name.endswith(".parquet"):
            raise ValueError("Unsafe segment filename")
        raw=(folder/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=item["sha256"]:
            raise ValueError("Segment SHA256 mismatch")
        frame=pd.read_parquet(folder/name)
        if len(frame)!=item["rows"] or frame.empty:
            raise ValueError("Segment row count mismatch")
        start=int(pd.Timestamp(item["start_utc"]).timestamp())
        end=int(pd.Timestamp(item["end_exclusive_utc"]).timestamp())
        if int(frame.time.iloc[0])!=start or int(frame.time.iloc[-1])+60!=end:
            raise ValueError("Segment timestamps differ from catalog")
        loaded.extend(segments(frame))
    return catalog,loaded


def evaluate(folder, output, *, include_holdout=False, config=None,
             signal_fn=breakout_signal, train_fraction=.60,
             validation_fraction=.20):
    catalog,pieces=read_segments(folder)
    start=int(pd.Timestamp(catalog["start_utc"],tz="UTC").timestamp())
    end=int(pd.Timestamp(catalog["end_exclusive_utc"],tz="UTC").timestamp())
    windows=boundaries(start,end,train_fraction,validation_fraction)
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    summary={"schema_version":1,"holdout_evaluated":bool(include_holdout),
        "holdout_policy":"LOCKED: not run unless --include-holdout explicitly supplied",
        "boundaries":{name:{"start_utc":datetime.fromtimestamp(a,timezone.utc).isoformat(),
                              "end_exclusive_utc":datetime.fromtimestamp(b,timezone.utc).isoformat()}
                     for name,(a,b) in windows.items()},
        "strategy":"20-bar channel breakout baseline",
        "config":asdict(config or Config()),"results":{}}
    for name,(lo,hi) in windows.items():
        if name=="holdout" and not include_holdout:
            summary["results"][name]={"status":"locked"}
            continue
        within=[]
        for part in pieces:
            cropped=part.loc[(part.time>=lo)&(part.time<hi)].reset_index(drop=True)
            if not cropped.empty:
                within.append(cropped)
        if not within:
            summary["results"][name]={"status":"no_verified_candles","segments":0}
            continue
        result,trades,equity=run(within,signal_fn,config)
        result["status"]="evaluated"
        result["verified_candles"]=sum(len(x) for x in within)
        summary["results"][name]=result
        trades.to_csv(output/f"{name}_trades.csv",index=False)
        equity.to_csv(output/f"{name}_equity.csv",index=False)
    (output/"evaluation.json").write_text(json.dumps(summary,indent=2)+"\n")
    return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog-dir",required=True)
    p.add_argument("--output",default="data/backtest/chronological")
    p.add_argument("--include-holdout",action="store_true",
                   help="Final evaluation only, after strategy is frozen; never for tuning")
    args=p.parse_args()
    print(json.dumps(evaluate(args.catalog_dir,args.output,
                              include_holdout=args.include_holdout),indent=2))


if __name__=="__main__":
    main()
