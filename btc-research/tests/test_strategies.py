import pandas as pd
import pytest
from src.strategies import Strategy,signals,rsi


def candles(count=600,start=0):
    p=[100+0.025*i for i in range(count)]
    return pd.DataFrame({"time":[start+i*60 for i in range(count)],
       "open":p,"high":[x+0.1 for x in p],"low":[x-0.1 for x in p],
       "close":p,"volume":[5.0]*count})


@pytest.mark.parametrize("name",["trend","mean_reversion","volatility_breakout"])
def test_signals_have_correct_shape_and_no_early_data(name):
    frame=candles()
    spec=Strategy(name,signal_tf="5m",context_tf="1h",lookback=3,volume_window=3)
    output=signals(frame,spec)
    assert len(output)==len(frame)
    assert set(output).issubset({-1,0,1})
    assert all(x==0 for x in output[:60])


def test_future_candles_do_not_change_earlier_signals():
    f=candles(1200)
    spec=Strategy("trend",signal_tf="5m",context_tf="1h",lookback=3,volume_window=3)
    before=signals(f,spec)
    changed=f.copy()
    changed.loc[1000:,"close"]=changed.loc[1000:,"close"]+10000
    changed.loc[1000:,"high"]=changed.loc[1000:,"high"]+10000
    changed.loc[1000:,"open"]=changed.loc[1000:,"open"]+10000
    changed.loc[1000:,"low"]=changed.loc[1000:,"low"]+10000
    assert before[:995]==signals(changed,spec)[:995]


def test_invalid_parameters_fail():
    with pytest.raises(ValueError,match="Unknown"):
        Strategy("curvefit").check()
    with pytest.raises(ValueError,match="Context"):
        Strategy("trend",signal_tf="4h",context_tf="5m").check()


def test_rsi_only_has_past_values():
    x=pd.Series([100+i for i in range(40)],dtype=float)
    v=rsi(x,14)
    y=x.copy();y.iloc[-1]=0
    assert v.iloc[:39].equals(rsi(y,14).iloc[:39])
