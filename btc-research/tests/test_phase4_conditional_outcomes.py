import numpy as np
import pandas as pd
import pytest
from src.phase4_conditional_outcomes import forward_labels,_statistics,HORIZONS


def hourly(n=100):
    return pd.DataFrame({"time":np.arange(n,dtype=int)*3600,
       "close":100.0+np.arange(n,dtype=float),
       "regime":["uptrend"]*n,"volume_state":["normal"]*n,
       "trend_score":[2.]*n,"atr_pct":[.01]*n,"volume_ratio":[1.]*n})


def test_forward_labels_exact_horizons():
    f=forward_labels(hourly())
    assert f.loc[0,"return_1h"]==pytest.approx(1/100)
    assert f.loc[0,"return_4h"]==pytest.approx(4/100)
    assert f.loc[0,"return_24h"]==pytest.approx(24/100)
    assert np.isnan(f.loc[99,"return_1h"])


def test_future_gaps_never_get_forward_label():
    x=hourly(70)
    x.loc[40:,"time"]+=3600
    r=forward_labels(x)
    assert np.isnan(r.loc[39,"return_1h"])
    assert np.isnan(r.loc[38,"return_4h"])
    assert np.isfinite(r.loc[41,"return_1h"])


def test_future_changes_do_not_modify_past_regime_feature():
    x=hourly(100)
    y=x.copy()
    y.loc[70:,"close"]+=800
    a=forward_labels(x)
    b=forward_labels(y)
    # End labels are allowed to change, prior *features* must not.
    assert a.loc[:60,"regime"].tolist()==b.loc[:60,"regime"].tolist()
    assert a.loc[:60,"trend_score"].tolist()==b.loc[:60,"trend_score"].tolist()
    assert a.loc[:45,"return_24h"].tolist()==pytest.approx(b.loc[:45,"return_24h"].tolist())


def test_effective_sample_uses_nonoverlapping_anchors():
    x=forward_labels(hourly(150))
    d=_statistics(x,24)
    assert d["observations"]==126
    assert d["nonoverlap_samples"]<d["observations"]
    assert d["nonoverlap_95pct_ci_normal_approx"] is None


def test_reversal_rate_not_reported_for_ranges():
    x=forward_labels(hourly(50))
    x["regime"]="range"
    assert _statistics(x,1)["directional_continuation_fraction"] is None


def test_invalid_horizons_fail():
    with pytest.raises(ValueError):
        forward_labels(hourly(),(0,))
