import pandas as pd
import pytest

from src.risk_engine import RiskPolicy,run_risk,completed_atr,_near_funding


def frame(n=180,start=3600):
    return pd.DataFrame({"time":[start+60*i for i in range(n)],
        "open":[100.0]*n,"high":[100.2]*n,"low":[99.8]*n,
        "close":[100.0]*n,"volume":[1.0]*n})


def fixed_signal(f):
    return [1]*len(f)


def test_atr_only_completed_higher_timeframes():
    f=frame(30,start=3600)
    atr=completed_atr(f,"5m",2)
    assert atr.iloc[0:9].isna().all()
    assert atr.iloc[9]>0


def test_time_limit_closes_position_without_next_segment_leak():
    f=frame()
    cfg=RiskPolicy(max_hold_minutes=3,cooldown_minutes=100,
        funding_guard_minutes=0,atr_period=2)
    result,trades,equity=run_risk([f],fixed_signal,cfg,"5m")
    assert len(trades)>0
    assert "time_limit" in trades.exit_reason.to_list()
    assert (trades.exit_time-trades.entry_time).max()<=3*60
    assert result["funding_modeled"] is False


def test_signal_cannot_open_within_funding_guard():
    # 8h boundary exactly 28800 sec
    f=frame(21,start=28800-10*60)
    cfg=RiskPolicy(funding_guard_minutes=15,atr_period=2)
    _,trades,_=run_risk([f],fixed_signal,cfg,"1m")
    assert len(trades)==0
    assert _near_funding(28800,15)


def test_invalid_config_rejected():
    with pytest.raises(ValueError):
        RiskPolicy(max_exposure=2).validate()
    with pytest.raises(ValueError):
        RiskPolicy(max_hold_minutes=0).validate()


def test_gap_is_rejected():
    f=frame(30).drop(index=10).reset_index(drop=True)
    with pytest.raises(ValueError,match="Gap"):
        run_risk([f],fixed_signal,RiskPolicy(),"1m")
