"""Causal, predeclared signal quality filters for training-only ablations."""
from dataclasses import dataclass,asdict
import numpy as np
import pandas as pd
from .multi_timeframe import aggregate,SECONDS
from .strategies import _available


@dataclass(frozen=True)
class QualityPolicy:
    trend_strength_min:float=.006
    atr_min_pct:float=.0005
    atr_max_pct:float=.025
    volume_multiple:float=1.5
    min_range_to_roundtrip_cost:float=2.0
    context_lookback:int=12
    atr_period:int=14
    volume_window:int=20

    def validate(self):
        if self.context_lookback<2 or self.atr_period<2 or self.volume_window<2:
            raise ValueError("Invalid lookbacks")
        if not 0<=self.trend_strength_min<1 or not 0<=self.atr_min_pct<self.atr_max_pct<1:
            raise ValueError("Invalid quality thresholds")
        if self.volume_multiple<=0 or self.min_range_to_roundtrip_cost<0:
            raise ValueError("Invalid volume or transaction cost threshold")


def quality_gates(frame,signal_tf,context_tf,policy=None,fee_rate=.0005,slippage_rate=.00025):
    cfg=policy or QualityPolicy()
    cfg.validate()
    if signal_tf not in SECONDS or context_tf not in SECONDS:
        raise ValueError("Unsupported timeframe")
    if SECONDS[context_tf]<SECONDS[signal_tf]:
        raise ValueError("Context shorter than signal")
    n=len(frame)
    if not n:return {k:np.array([],dtype=bool) for k in ("trend","volatility","volume","cost")}
    sig=aggregate(frame,signal_tf).copy()
    ctx=aggregate(frame,context_tf).copy()
    if sig.empty or ctx.empty:
        return {k:np.zeros(n,dtype=bool) for k in ("trend","volatility","volume","cost")}
    trend=(ctx.close/ctx.close.shift(cfg.context_lookback)-1).abs()
    ctx["trend_strength"]=trend
    prev_close=sig.close.shift(1)
    tr=pd.concat([sig.high-sig.low,(sig.high-prev_close).abs(),
                  (sig.low-prev_close).abs()],axis=1).max(axis=1)
    sig["atr_pct"]=tr.rolling(cfg.atr_period,min_periods=cfg.atr_period).mean()/sig.close
    sig["volume_ratio"]=sig.volume/sig.volume.shift(1).rolling(cfg.volume_window,min_periods=cfg.volume_window).mean().replace(0,np.nan)
    # Compare a conservative anticipated signal-bar movement to round-trip fees + adverse slippage.
    # This is a heuristic, not a predicted realized move or funding calculation.
    roundtrip=2*(fee_rate+slippage_rate)
    sig["cost_ratio"]=sig["atr_pct"]/roundtrip if roundtrip>0 else np.inf
    t=frame.time
    trend_arr=_available(ctx,t,SECONDS[context_tf],"trend_strength")
    atr_arr=_available(sig,t,SECONDS[signal_tf],"atr_pct")
    volume_arr=_available(sig,t,SECONDS[signal_tf],"volume_ratio")
    cost_arr=_available(sig,t,SECONDS[signal_tf],"cost_ratio")
    return {"trend":np.isfinite(trend_arr)&(trend_arr>=cfg.trend_strength_min),
            "volatility":np.isfinite(atr_arr)&(atr_arr>=cfg.atr_min_pct)&(atr_arr<=cfg.atr_max_pct),
            "volume":np.isfinite(volume_arr)&(volume_arr>=cfg.volume_multiple),
            "cost":np.isfinite(cost_arr)&(cost_arr>=cfg.min_range_to_roundtrip_cost)}


def filtered_signals(frame,spec,filters,policy=None,risk_policy=None):
    from .strategies import signals
    base=np.asarray(signals(frame,spec),dtype=int)
    if not filters:return base.tolist()
    risk=risk_policy
    gates=quality_gates(frame,spec.signal_tf,spec.context_tf,policy,
        fee_rate=risk.fee_rate if risk else .0005,
        slippage_rate=risk.slippage_rate if risk else .00025)
    allowed=np.ones(len(base),dtype=bool)
    for name in filters:
        if name not in gates:raise ValueError("Unsupported quality filter")
        allowed &= gates[name]
    return np.where(allowed,base,0).tolist()
