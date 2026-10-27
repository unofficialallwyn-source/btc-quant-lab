"""Deterministic gap and look-ahead controls for UTC multi-timeframe inputs."""
import pandas as pd
import pytest

from src.multi_timeframe import aggregate,causal_breakout_signal,SECONDS


def candles(start, count, prices=None):
    prices=prices or [100.0]*count
    return pd.DataFrame({
        "time":[start+i*60 for i in range(count)],
        "open":prices,"high":[x+1 for x in prices],
        "low":[x-1 for x in prices],"close":prices,
        "volume":[2.0]*count})


@pytest.mark.parametrize("timeframe,n",list(SECONDS.items()))
def test_utc_aggregation_and_volume(timeframe,n):
    minutes=n//60
    f=candles(0,minutes)
    out=aggregate(f,timeframe)
    assert len(out)==1
    assert int(out.iloc[0].time)==0
    assert out.iloc[0].volume==2*minutes


def test_partial_boundary_bucket_is_never_exported():
    f=candles(60,9)
    bars=aggregate(f,"5m")
    assert len(bars)==1
    assert bars.iloc[0].time==300


def test_gap_rejected_rather_than_construct_false_htf_bar():
    frame=candles(0,10).drop(index=4).reset_index(drop=True)
    with pytest.raises(ValueError,match="missing minute"):
        aggregate(frame,"5m")


def test_htf_breakout_unavailable_until_finished_and_no_future_leak():
    # With one historical 5m bar establishing the channel, a second bar
    # creates a breakout ONLY once its final minute has closed.
    values=[100]*5+[100]*4+[120]+[100]*5
    frame=candles(0,15,[float(v) for v in values])
    signal=causal_breakout_signal(frame,"5m",lookback=1)
    assert signal[:9]==[0]*9
    assert signal[9]==1
    assert signal[10]==1  # last completed HTF signal remains known
    modified=frame.copy()
    modified.loc[14,"close"]=500.
    assert causal_breakout_signal(modified,"5m",lookback=1)[:14]==signal[:14]


def test_signals_restart_after_segment_and_reject_invalid_timeframe():
    frame=candles(0,10,[100.]*5+[120.]*5)
    with pytest.raises(ValueError,match="Unsupported"):
        aggregate(frame,"90m")
    assert causal_breakout_signal(frame.iloc[:5].copy(),"5m",lookback=1)==[0]*5
