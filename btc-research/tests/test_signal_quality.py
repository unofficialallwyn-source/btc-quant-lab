import pandas as pd
import pytest
from src.strategies import Strategy
from src.signal_quality import QualityPolicy,quality_gates,filtered_signals


def candles(n=1500):
    px=[100+i*.01 for i in range(n)]
    return pd.DataFrame({"time":[i*60 for i in range(n)],
      "open":px,"high":[x+.15 for x in px],"low":[x-.15 for x in px],
      "close":px,"volume":[5+(i%13) for i in range(n)]})


def test_quality_gates_are_causal():
    f=candles()
    before=quality_gates(f,"5m","1h")
    changed=f.copy()
    changed.loc[1350:,"close"]+=500
    changed.loc[1350:,"high"]+=500
    changed.loc[1350:,"low"]+=500
    changed.loc[1350:,"open"]+=500
    after=quality_gates(changed,"5m","1h")
    for k in before:
        assert list(before[k][:1340])==list(after[k][:1340])


def test_combined_never_invents_new_direction():
    f=candles()
    spec=Strategy("trend",lookback=3,volume_window=3)
    raw=filtered_signals(f,spec,())
    filtered=filtered_signals(f,spec,("trend","volume","cost"))
    assert all(b==0 or b==a for a,b in zip(raw,filtered))


def test_insufficient_history_is_not_tradeable():
    f=candles(25)
    gates=quality_gates(f,"5m","1h")
    assert all(not x.any() for x in gates.values())


def test_invalid_settings_rejected():
    with pytest.raises(ValueError):
        QualityPolicy(atr_min_pct=.05,atr_max_pct=.01).validate()
    with pytest.raises(ValueError):
        filtered_signals(candles(),Strategy("trend"),("made_up",))
