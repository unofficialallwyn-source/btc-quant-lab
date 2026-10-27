"""Causal UTC-aligned higher-timeframe signals from gap-free 1m data.

An HTF candle only becomes observable at its END time, never at its open.
Incomplete HTF buckets (including split/gap boundaries) are discarded.
"""
import numpy as np
import pandas as pd

from .sim_engine import breakout_signal

SECONDS={"1m":60,"5m":300,"15m":900,"1h":3600,"4h":14400}


def aggregate(frame, timeframe):
    """Return completed UTC-aligned OHLCV bars with OPEN timestamp in 'time'."""
    if timeframe not in SECONDS:
        raise ValueError("Unsupported timeframe")
    step=SECONDS[timeframe]
    if frame.empty:
        return pd.DataFrame(columns=["time","open","high","low","close","volume"])
    f=frame.sort_values("time").reset_index(drop=True)
    if f.time.isna().any() or f.time.duplicated().any() or (f.time % 60 != 0).any():
        raise ValueError("Invalid minute timestamps")
    if (f.time.diff().iloc[1:] != 60).any():
        raise ValueError("Cannot aggregate across missing minute candles")
    if f[["open","high","low","close","volume"]].isna().any().any():
        raise ValueError("Missing OHLCV values")
    bucket=(f.time.astype("int64")//step)*step
    grouped=f.assign(_bucket=bucket).groupby("_bucket",sort=True)
    result=grouped.agg(time=("time","min"),open=("open","first"),
        high=("high","max"),low=("low","min"),
        close=("close","last"),volume=("volume","sum"),
        count=("time","size"),last=("time","max")).reset_index(drop=True)
    expected=step//60
    complete=((result["time"] % step)==0) & (result["count"]==expected) & (
        result["last"]==result["time"]+step-60)
    result=result.loc[complete,["time","open","high","low","close","volume"]]
    return result.reset_index(drop=True)


def causal_breakout_signal(frame, timeframe="5m", lookback=20):
    """Produce one signal per input minute, using only finished HTF bars.

    A signal first appears on the LAST constituent 1m candle of a completed
    HTF candle; the existing simulator can fill it at the NEXT minute open.
    No indicator warm-up carries across distinct segments or split boundaries.
    """
    if timeframe not in SECONDS:
        raise ValueError("Unsupported timeframe")
    if timeframe=="1m":
        return list(breakout_signal(frame,lookback))
    htf=aggregate(frame,timeframe)
    output=np.zeros(len(frame),dtype="int8")
    if htf.empty:
        return output.tolist()
    htf_signal=np.asarray(breakout_signal(htf,lookback),dtype="int8")
    availability=(htf.time.to_numpy(dtype="int64")+SECONDS[timeframe])
    minute_close=frame.time.to_numpy(dtype="int64")+60
    idx=np.searchsorted(availability,minute_close,side="right")-1
    valid=idx>=0
    output[valid]=htf_signal[idx[valid]]
    return output.tolist()
