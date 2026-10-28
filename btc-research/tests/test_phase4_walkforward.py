import pytest
import pandas as pd
from src.phase4_walkforward import qualify,fold_metrics,MIN_TRADES_PER_FOLD
from src.phase4_hypotheses import Hypothesis,NAMES


def test_qualification_is_strict_and_per_fold():
    good={"trades":MIN_TRADES_PER_FOLD,"net_pnl":10.,
          "profit_factor":1.1,"max_drawdown_pct":5}
    assert qualify([dict(good) for _ in range(3)])
    for mutation in ({"trades":0},{"net_pnl":0},{"profit_factor":1.0},
                     {"max_drawdown_pct":25.01},{"profit_factor":None}):
        rows=[dict(good) for _ in range(3)]
        rows[1].update(mutation)
        assert not qualify(rows)


def test_no_trade_baseline_has_zero_pnl():
    frame=pd.DataFrame({"time":[3600+i*60 for i in range(180)],
       "open":[100.]*180,"high":[101.]*180,"low":[99.]*180,
       "close":[100.]*180,"volume":[5.]*180})
    r=fold_metrics([frame])
    assert r["trades"]==0
    assert r["net_pnl"]==0
    assert r["gross_before_slippage"]==0
    assert r["fees"]==0
    assert r["slippage"]==0


def test_hypothesis_names_predeclared():
    assert len(NAMES)==3
    for n in NAMES:Hypothesis(n).validate()
