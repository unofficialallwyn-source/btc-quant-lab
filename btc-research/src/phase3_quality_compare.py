"""Predeclared training-only filter ablation; never evaluates validation/holdout."""
import argparse,hashlib,json
from pathlib import Path
from dataclasses import asdict
import pandas as pd
from .chronological_eval import read_segments,boundaries
from .risk_engine import RiskPolicy,run_risk
from .strategies import Strategy
from .signal_quality import QualityPolicy,filtered_signals

ABLATIONS={"baseline":(),"trend":("trend",),"volatility":("volatility",),
    "volume":("volume",),"cost":("cost",),"combined":("trend","volatility","volume","cost")}

def evaluate(catalog_dir,output,signal_tf="5m",context_tf="1h"):
    catalog,pieces=read_segments(catalog_dir)
    start=int(pd.Timestamp(catalog["start_utc"]).timestamp())
    end=int(pd.Timestamp(catalog["end_exclusive_utc"]).timestamp())
    lo,hi=boundaries(start,end)["training"]
    train=[p.loc[(p.time>=lo)&(p.time<hi)].reset_index(drop=True) for p in pieces]
    train=[p for p in train if not p.empty]
    if not train:raise ValueError("Empty training partition")
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    risk=RiskPolicy(entry_mode="transition")
    quality=QualityPolicy()
    report={"schema_version":1,"holdout_evaluated":False,"validation_evaluated":False,
        "holdout":{"status":"locked"},"validation":{"status":"reserved"},
        "catalog_sha256":hashlib.sha256((Path(catalog_dir)/"dataset_catalog.json").read_bytes()).hexdigest(),
        "risk_policy":asdict(risk),"quality_policy":asdict(quality),
        "note":"Fixed predeclared training-only exploratory filter ablation, no funding/liquidation",
        "strategies":{}}
    for name in ("trend","mean_reversion","volatility_breakout"):
        spec=Strategy(name,signal_tf=signal_tf,context_tf=context_tf)
        results={}
        for tag,gates in ABLATIONS.items():
            metrics,trades,_=run_risk(train,
                lambda f:filtered_signals(f,spec,gates,quality,risk),risk,signal_tf)
            if abs(metrics["ending_equity"]-risk.initial_equity-float(trades.net_pnl.sum()))>1e-4:
                raise ValueError("Ledger reconciliation mismatch")
            results[tag]={"filters":list(gates),"metrics":metrics}
        report["strategies"][name]={"signal":asdict(spec),"ablations":results}
    (root/"quality_ablation.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog-dir",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--signal-tf",default="5m",choices=["1m","5m","15m","1h"])
    p.add_argument("--context-tf",default="1h",choices=["5m","15m","1h","4h"])
    a=p.parse_args()
    r=evaluate(a.catalog_dir,a.output,a.signal_tf,a.context_tf)
    print(json.dumps({"holdout_evaluated":r["holdout_evaluated"],
        "validation_evaluated":r["validation_evaluated"],
        "strategies":{name:{tag:{"trades":x["metrics"]["trades"],"return_pct":x["metrics"]["return_pct"],
        "gross_before_slippage":x["metrics"]["gross_before_slippage_total"],
        "fees":x["metrics"]["fee_total"],"slippage":x["metrics"]["slippage_total"]}
        for tag,x in data["ablations"].items()} for name,data in r["strategies"].items()}},indent=2))
if __name__=="__main__":main()
