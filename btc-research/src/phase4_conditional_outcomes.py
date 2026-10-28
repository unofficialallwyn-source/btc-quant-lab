"""Training-only descriptive forward outcomes conditioned on completed-bar regimes.

Future returns are analysis labels ONLY, never strategy features. A label is
valid only if every required hourly candle exists inside the same verified
gap-free training segment. Uncertainty uses non-overlapping anchors.
"""
import argparse,hashlib,json
from dataclasses import asdict
from pathlib import Path
import numpy as np
import pandas as pd
from .chronological_eval import read_segments,boundaries
from .phase4_regimes import classify,RegimeConfig

HORIZONS=(1,4,24)
MIN_EFFECTIVE_SAMPLES=30


def forward_labels(hourly, horizons=HORIZONS):
    """Completed hourly bar t has OHLCV time equal to hour OPEN; close at t+1h."""
    h=hourly.reset_index(drop=True).copy()
    for hours in horizons:
        if hours<1:raise ValueError("Positive horizon required")
        future=h.close.shift(-hours)
        # A missing hourly bucket or segment boundary invalidates the label.
        valid=(h.time.shift(-hours)-h.time==hours*3600)
        h[f"return_{hours}h"]=((future/h.close)-1).where(valid)
        # Forward realized close-to-close volatility, annualization deliberately omitted.
        logs=np.log(h.close/h.close.shift(1))
        squared=logs.pow(2).shift(-1)
        # Rolling sum over future hours (t+1 ... t+h), aligned at t.
        realized=squared.iloc[::-1].rolling(hours,min_periods=hours).sum().iloc[::-1]
        h[f"realized_vol_{hours}h"]=np.sqrt(realized).where(valid)
    return h


def _statistics(group,horizon):
    col=f"return_{horizon}h"
    valid=group.loc[group[col].notna()].copy()
    # Time-anchored non-overlap per segment: conservative confidence estimate,
    # not independent sampling of clustered BTC market environments.
    independent=valid[(valid.time//3600)%horizon==0]
    # Different segments share global UTC alignment, avoiding phase cherry-picking.
    vals=independent[col].to_numpy(dtype=float)
    n=len(vals)
    mean=float(np.mean(vals)) if n else None
    sd=float(np.std(vals,ddof=1)) if n>1 else None
    sem=sd/np.sqrt(n) if sd is not None else None
    ci=[mean-1.96*sem,mean+1.96*sem] if n>=MIN_EFFECTIVE_SAMPLES and sem is not None else None
    # Continuation is defined only for directional regimes; ranges have no direction.
    base=group.regime.astype(str).str.replace("high_volatility_","",regex=False)
    directional=valid.loc[base.loc[valid.index].isin(("uptrend","downtrend"))]
    directions=np.where(base.loc[directional.index].eq("uptrend"),1,-1)
    continuation=float(np.mean(directional[col].to_numpy()*directions>0)) if len(directional) else None
    return {"observations":len(valid),"nonoverlap_samples":n,
       "mean_forward_return":float(valid[col].mean()) if len(valid) else None,
       "median_forward_return":float(valid[col].median()) if len(valid) else None,
       "up_fraction":float((valid[col]>0).mean()) if len(valid) else None,
       "mean_forward_realized_volatility":float(valid[f"realized_vol_{horizon}h"].mean()) if len(valid) else None,
       "directional_continuation_fraction":continuation,
       "nonoverlap_mean":mean,"nonoverlap_95pct_ci_normal_approx":ci,
       "uncertainty_warning":("small effective sample; no confidence interval" if n<MIN_EFFECTIVE_SAMPLES
                              else "normal approximation; overlapping regimes and serial dependence remain")}


def evaluate(catalog_dir,output,config=None):
    cfg=config or RegimeConfig()
    if cfg.timeframe!="1h":raise ValueError("Step 2 currently requires 1h completed bars")
    catalog,pieces=read_segments(catalog_dir)
    start=int(pd.Timestamp(catalog["start_utc"]).timestamp())
    end=int(pd.Timestamp(catalog["end_exclusive_utc"]).timestamp())
    lo,hi=boundaries(start,end)["training"]
    outputs=[]
    for seg_id,piece in enumerate(pieces):
        cropped=piece.loc[(piece.time>=lo)&(piece.time<hi)].reset_index(drop=True)
        if cropped.empty:continue
        b=classify(cropped,cfg)
        if b.empty:continue
        labeled=forward_labels(b)
        labeled.insert(0,"segment_id",seg_id)
        outputs.append(labeled)
    if not outputs:raise ValueError("Empty training regimes")
    data=pd.concat(outputs,ignore_index=True)
    eligible=data[data.regime!="warmup"].copy()
    if eligible.empty:raise ValueError("No classified training observations")
    metrics={}
    for (regime,volume),group in eligible.groupby(["regime","volume_state"],sort=True):
        metrics[f"{regime}__{volume}"]={str(h):_statistics(group,h) for h in HORIZONS}
    # Also aggregate by regime so sparse trend classes remain visible.
    by_regime={str(name):{str(h):_statistics(g,h) for h in HORIZONS}
                for name,g in eligible.groupby("regime",sort=True)}
    scores=eligible.trend_score.replace([np.inf,-np.inf],np.nan).dropna()
    quantiles={str(q):float(scores.quantile(q)) for q in (0,.01,.05,.25,.5,.75,.95,.99,1)}
    report={"schema_version":1,"phase":"4_step_2","scope":"training_only",
      "validation_evaluated":False,"holdout_evaluated":False,
      "catalog_sha256":hashlib.sha256((Path(catalog_dir)/"dataset_catalog.json").read_bytes()).hexdigest(),
      "config":asdict(cfg),"forward_horizons_hours":list(HORIZONS),
      "training_segments":len(outputs),"classified_observations":len(eligible),
      "trend_score_quantiles":quantiles,"by_regime":by_regime,
      "by_regime_and_volume":metrics,
      "warning":"Exploratory forward labels; selection, confidence intervals and multiple comparisons require caution. No executable strategy or cost-adjusted P&L."}
    folder=Path(output);folder.mkdir(parents=True,exist_ok=True)
    data.to_csv(folder/"training_forward_labels.csv",index=False)
    (folder/"conditional_outcomes.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog-dir",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    report=evaluate(args.catalog_dir,args.output)
    print(json.dumps({"phase":report["phase"],"classified_observations":report["classified_observations"],
      "trend_score_quantiles":report["trend_score_quantiles"],
      "by_regime":report["by_regime"],
      "validation_evaluated":False,"holdout_evaluated":False},indent=2))
if __name__=="__main__":main()
