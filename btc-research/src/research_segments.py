"""Partition verified candles into independently backtestable uninterrupted segments."""
import pandas as pd


def segments(frame):
    if frame.empty:
        return []
    ordered=frame.sort_values("time").reset_index(drop=True)
    if ordered.time.duplicated().any():
        raise ValueError("Duplicate candle timestamps")
    if (ordered.time % 60 != 0).any():
        raise ValueError("Misaligned candles")
    group=(ordered.time.diff().fillna(60) != 60).cumsum()
    result=[]
    for _,part in ordered.groupby(group):
        # Never fill data holes with fabricated candles.
        result.append(part.reset_index(drop=True))
    return result


def enforce_continuous(frame):
    pieces=segments(frame)
    if len(pieces)!=1:
        raise ValueError("Research dataset crosses one or more unverified gaps")
    return pieces[0]
