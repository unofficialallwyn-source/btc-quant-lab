import numpy as np
import pandas as pd
import pytest

from src.phase4_hypotheses import Hypothesis,NAMES,signals,research_specs


def candles(n=6000):
    close=100+np.arange(n)*.002+np.sin(np.arange(n)/23)*.15
    return pd.DataFrame({"time":np.arange(n,dtype=np.int64)*60,
        "open":close-.01,"high":close+.12,"low":close-.12,
        "close":close,"volume":30+(np.arange(n)%23)})


@pytest.mark.parametrize("name",NAMES)
def test_shape_domain_and_no_warmup_trades(name):
    sig=signals(candles(),Hypothesis(name))
    assert len(sig)==6000
    assert set(sig).issubset({-1,0,1})
    assert all(x==0 for x in sig[:60*24])


@pytest.mark.parametrize("name",NAMES)
def test_causal_prefix_unchanged_by_future_price(name):
    original=candles()
    changed=original.copy()
    changed.loc[5400:,"close"]+=1000
    changed.loc[5400:,"open"]+=1000
    changed.loc[5400:,"high"]+=1000
    changed.loc[5400:,"low"]+=1000
    a=signals(original,Hypothesis(name))
    b=signals(changed,Hypothesis(name))
    assert a[:5340]==b[:5340]


def test_no_partial_context():
    # 1h regime requires 24 completed hourly bars for trend warmup.
    for name in NAMES:
        assert not any(signals(candles(1400),Hypothesis(name)))


def test_gaps_rejected_not_filled():
    data=candles(2500).drop(index=200)
    with pytest.raises(ValueError,match="missing minute"):
        signals(data,Hypothesis("hv_range_continuation"))


def test_invalid_spec_rejected():
    with pytest.raises(ValueError,match="Unknown hypothesis"):
        Hypothesis("made_up").validate()
    with pytest.raises(ValueError,match="freeze"):
        Hypothesis(NAMES[0],signal_tf="1m").validate()


def test_manifest_frozen_and_no_lookahead():
    m=research_specs()
    assert set(m["hypotheses"])==set(NAMES)
    assert m["validation_evaluated"] is False
    assert m["holdout_evaluated"] is False
    assert m["risk_policy_for_future_testing"]["entry_mode"]=="transition"
