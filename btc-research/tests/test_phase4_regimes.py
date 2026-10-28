import numpy as np
import pandas as pd
import pytest
from src.phase4_regimes import RegimeConfig,classify


def candles(n=6000):
    close=np.array([100+i*.002+np.sin(i/90) for i in range(n)])
    return pd.DataFrame({"time":np.arange(n)*60,"open":close,"high":close+.1,
        "low":close-.1,"close":close,"volume":10+np.arange(n)%7})


def test_regime_causal_prefix_invariance():
    f=candles()
    original=classify(f)
    changed=f.copy()
    changed.loc[4800:,"close"]+=1000
    changed.loc[4800:,"open"]+=1000
    changed.loc[4800:,"high"]+=1000
    changed.loc[4800:,"low"]+=1000
    modified=classify(changed)
    x=original[original.time<4800*60]
    y=modified[modified.time<4800*60]
    assert x.regime.tolist()==y.regime.tolist()
    assert x.volume_state.tolist()==y.volume_state.tolist()


def test_no_partial_htf_bars():
    result=classify(candles(181))
    assert len(result)==3


def test_warmup_is_not_classified_as_trend():
    result=classify(candles(120))
    assert set(result.regime)=={"warmup"}


def test_gap_is_rejected_not_interpolated():
    f=candles(1500).drop(index=100)
    with pytest.raises(ValueError,match="missing minute"):
        classify(f)


def test_bad_parameters_rejected():
    with pytest.raises(ValueError,match="Invalid"):
        classify(candles(),RegimeConfig(lookback=1))
