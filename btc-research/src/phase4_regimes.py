"""Phase 4 descriptive BTC market-regime research, strictly training-only.

Classifies COMPLETED 1h OHLCV bars using past observations. Labels describe
market conditions, not strategy predictions or executable trade signals.
"""
import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .chronological_eval import read_segments, boundaries
from .multi_timeframe import aggregate, SECONDS


@dataclass(frozen=True)
class RegimeConfig:
    timeframe: str = "1h"
    lookback: int = 24
    atr_period: int = 14
    volume_window: int = 24
    directional_threshold: float = 1.5
    high_volatility_atr_pct: float = .012
    high_volume_ratio: float = 1.5

    def validate(self):
        if self.timeframe not in SECONDS or self.lookback<2 or self.atr_period<2 or self.volume_window<2:
            raise ValueError("Invalid timeframe or lookback")
        if self.directional_threshold<=0 or self.high_volatility_atr_pct<=0 or self.high_volume_ratio<=0:
            raise ValueError("Invalid regime thresholds")


def classify(frame, config=None):
    cfg=config or RegimeConfig()
    cfg.validate()
    bars=aggregate(frame,cfg.timeframe)
    if bars.empty:
        return pd.DataFrame(columns=["time","close","atr_pct","trend_score","volume_ratio","regime","volume_state"])
    b=bars.copy()
    previous=b.close.shift(1)
    ranges=pd.concat([b.high-b.low,(b.high-previous).abs(),(b.low-previous).abs()],axis=1).max(axis=1)
    atr=ranges.rolling(cfg.atr_period,min_periods=cfg.atr_period).mean()
    b["atr_pct"]=atr/b.close
    # Rolling displacement / volatility path: descriptive directional persistence.
    # The previous lookback bars are only observable at the bar's own close.
    displacement=b.close-b.close.shift(cfg.lookback)
    b["trend_score"]=displacement/(atr*np.sqrt(cfg.lookback)).replace(0,np.nan)
    b["volume_ratio"]=b.volume/b.volume.shift(1).rolling(cfg.volume_window,min_periods=cfg.volume_window).mean().replace(0,np.nan)
    ready=np.isfinite(b[["atr_pct","trend_score","volume_ratio"]]).all(axis=1)
    score=b["trend_score"]
    b["regime"]="warmup"
    b.loc[ready&(score>=cfg.directional_threshold),"regime"]="uptrend"
    b.loc[ready&(score<=-cfg.directional_threshold),"regime"]="downtrend"
    b.loc[ready&(score.abs()<cfg.directional_threshold),"regime"]="range"
    b.loc[ready&(b.atr_pct>=cfg.high_volatility_atr_pct),"regime"]="high_volatility_"+b.loc[ready&(b.atr_pct>=cfg.high_volatility_atr_pct),"regime"]
    b["volume_state"]=np.where(~ready,"warmup",
        np.where(b.volume_ratio>=cfg.high_volume_ratio,"elevated","normal"))
    return b[["time","close","atr_pct","trend_score","volume_ratio","regime","volume_state"]]


def evaluate(catalog_dir, output, config=None):
    cfg=config or RegimeConfig()
    cfg.validate()
    catalog,pieces=read_segments(catalog_dir)
    start=int(pd.Timestamp(catalog["start_utc"]).timestamp())
    end=int(pd.Timestamp(catalog["end_exclusive_utc"]).timestamp())
    train_start,train_end=boundaries(start,end)["training"]
    result=[]
    for seg_id,piece in enumerate(pieces):
        cropped=piece.loc[(piece.time>=train_start)&(piece.time<train_end)].reset_index(drop=True)
        if cropped.empty:continue
        classified=classify(cropped,cfg)
        if classified.empty:continue
        classified.insert(0,"segment_id",seg_id)
        result.append(classified)
    if not result:raise ValueError("No training-only completed regime bars")
    all_bars=pd.concat(result,ignore_index=True)
    usable=all_bars[~all_bars.regime.eq("warmup")]
    if usable.empty:raise ValueError("No regime bars after causal warmup")
    counts={str(k):int(v) for k,v in usable.regime.value_counts().items()}
    volume_counts={str(k):int(v) for k,v in usable.volume_state.value_counts().items()}
    transitions=0
    for _,s in usable.groupby("segment_id",sort=False):
        transitions+=int((s.regime!=s.regime.shift(1)).iloc[1:].sum())
    report={"schema_version":1,"phase":"4_step_1","scope":"training_only",
        "validation_evaluated":False,"holdout_evaluated":False,
        "catalog_sha256":hashlib.sha256((Path(catalog_dir)/"dataset_catalog.json").read_bytes()).hexdigest(),
        "config":asdict(cfg),"segment_count":len(result),
        "completed_bars":len(all_bars),"classified_bars":len(usable),
        "warmup_bars":len(all_bars)-len(usable),
        "regime_counts":counts,"volume_counts":volume_counts,
        "regime_transitions":transitions,
        "interpretation":"Descriptive, fixed-threshold past-bar regimes only. No future-return labels or profit claims."}
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    all_bars.to_csv(out/"training_regimes.csv",index=False)
    (out/"regime_summary.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog-dir",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--timeframe",default="1h",choices=tuple(SECONDS))
    a=p.parse_args()
    print(json.dumps(evaluate(a.catalog_dir,a.output,RegimeConfig(timeframe=a.timeframe)),indent=2))


if __name__=="__main__":main()
