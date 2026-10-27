"""Phase 3 research signals; all decisions use completed candles only.

Each signal vector is aligned to the 1-minute execution bars. Higher-timeframe
features are available only after their UTC-close and reset across gaps/splits.
No funding assumptions, holdout access or live trading.
"""
from dataclasses import dataclass,asdict
import numpy as np
import pandas as pd
from .multi_timeframe import aggregate,SECONDS


@dataclass(frozen=True)
class Strategy:
    name: str
    signal_tf: str = "5m"
    context_tf: str = "1h"
    lookback: int = 20
    rsi_period: int = 14
    rsi_low: float = 30
    rsi_high: float = 70
    volume_window: int = 20
    volume_multiple: float = 1.25

    def check(self):
        if self.name not in ("trend","mean_reversion","volatility_breakout"):
            raise ValueError("Unknown strategy")
        if self.signal_tf not in SECONDS or self.context_tf not in SECONDS:
            raise ValueError("Unsupported timeframe")
        if SECONDS[self.context_tf]<SECONDS[self.signal_tf]:
            raise ValueError("Context timeframe must not be smaller than signal")
        if self.lookback<3 or self.rsi_period<2 or self.volume_window<2:
            raise ValueError("Insufficient lookback")
        if not 0<self.rsi_low<self.rsi_high<100 or self.volume_multiple<=0:
            raise ValueError("Invalid indicator thresholds")


def rsi(close,period):
    change=close.diff()
    # Past+current completed close only; Wilder EMA with a conservative warmup.
    gain=change.clip(lower=0).ewm(alpha=1/period,adjust=False,min_periods=period).mean()
    loss=(-change.clip(upper=0)).ewm(alpha=1/period,adjust=False,min_periods=period).mean()
    out=100-100/(1+gain/loss.replace(0,np.nan))
    out=out.mask((loss==0)&(gain>0),100).mask((gain==0)&(loss>0),0)
    return out


def _available(htf,minute_times,seconds,column):
    """As-of join last fully CLOSED HTF bar; never uses future partial candle."""
    out=np.full(len(minute_times),np.nan,dtype=float)
    if htf.empty:return out
    known=htf.time.to_numpy(dtype="int64")+seconds
    at=minute_times.to_numpy(dtype="int64")+60
    idx=np.searchsorted(known,at,side="right")-1
    ok=idx>=0
    values=htf[column].to_numpy(dtype=float)
    out[ok]=values[idx[ok]]
    return out


def signals(frame,spec):
    spec.check()
    if frame.empty:return []
    signal=aggregate(frame,spec.signal_tf)
    context=aggregate(frame,spec.context_tf)
    if signal.empty or context.empty:return [0]*len(frame)
    s=signal.copy()
    c=context.copy()
    prev_high=s.high.shift(1).rolling(spec.lookback,min_periods=spec.lookback).max()
    prev_low=s.low.shift(1).rolling(spec.lookback,min_periods=spec.lookback).min()
    v_ref=s.volume.shift(1).rolling(spec.volume_window,min_periods=spec.volume_window).mean()
    s["rsi"]=rsi(s.close,spec.rsi_period)
    s["vol_ok"]=(s.volume>=v_ref*spec.volume_multiple).astype(float)
    s["range"]=s.high-s.low
    s["range_prev"]=s["range"].shift(1).rolling(spec.lookback,min_periods=spec.lookback).median()
    c["direction"]=np.sign(c.close-c.close.shift(spec.lookback))
    if spec.name=="trend":
        s["long"]=(s.close>prev_high)&(s["vol_ok"]>0)
        s["short"]=(s.close<prev_low)&(s["vol_ok"]>0)
    elif spec.name=="mean_reversion":
        s["long"]=(s["rsi"]<spec.rsi_low)&(s.close<prev_low)
        s["short"]=(s["rsi"]>spec.rsi_high)&(s.close>prev_high)
    else:
        s["long"]=(s.close>prev_high)&(s["range"]>s["range_prev"]*1.5)&(s["vol_ok"]>0)
        s["short"]=(s.close<prev_low)&(s["range"]>s["range_prev"]*1.5)&(s["vol_ok"]>0)
    minutes=frame.time
    long=_available(s.assign(long=s.long.astype(float)),minutes,SECONDS[spec.signal_tf],"long")
    short=_available(s.assign(short=s.short.astype(float)),minutes,SECONDS[spec.signal_tf],"short")
    trend=_available(c,minutes,SECONDS[spec.context_tf],"direction")
    result=np.zeros(len(frame),dtype=int)
    # Context is optional for mean reversion only when warmed up; no silent
    # forward-looking context. Opposite context for mean reversion is intended.
    if spec.name=="mean_reversion":
        result[(long==1)&(trend<0)]=1
        result[(short==1)&(trend>0)]=-1
    else:
        result[(long==1)&(trend>0)]=1
        result[(short==1)&(trend<0)]=-1
    return result.tolist()
