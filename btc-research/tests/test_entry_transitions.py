"""Paired causal entry-mode and gross-to-net execution-cost regressions."""
from dataclasses import replace
import pandas as pd
import pytest
from src.risk_engine import RiskPolicy,run_risk


def frame(n=240,start=3600):
    return pd.DataFrame({"time":[start+60*i for i in range(n)],
        "open":[100.0]*n,"high":[100.2]*n,"low":[99.8]*n,
        "close":[100.0]*n,"volume":[1.0]*n})


def test_level_reentries_but_transition_requires_new_signal():
    cfg=RiskPolicy(atr_period=2,max_hold_minutes=2,cooldown_minutes=0,
        funding_guard_minutes=0,entry_mode="transition")
    signals=lambda f:[1]*len(f)
    new,ledger,_=run_risk([frame()],signals,cfg,"1m")
    old,old_ledger,_=run_risk([frame()],signals,replace(cfg,entry_mode="level"),"1m")
    assert new["trades"]==0
    assert len(ledger)==0
    assert old["trades"]>0
    assert len(old_ledger)==old["trades"]


def test_new_signal_transition_is_single_entry():
    cfg=RiskPolicy(atr_period=2,max_hold_minutes=3,cooldown_minutes=0,
        funding_guard_minutes=0,entry_mode="transition")
    signal=lambda f:[0]*20+[1]*len(f.iloc[20:])
    metrics,ledger,_=run_risk([frame()],signal,cfg,"1m")
    assert metrics["trades"]==1
    assert len(ledger)==1
    assert metrics["entry_decisions"]["entries"]==1


def test_gross_to_net_costs_reconcile():
    cfg=RiskPolicy(atr_period=2,max_hold_minutes=2,cooldown_minutes=0,
        funding_guard_minutes=0,entry_mode="level")
    metrics,ledger,_=run_risk([frame()],lambda f:[1]*len(f),cfg,"1m")
    assert len(ledger)>0
    assert (ledger.slippage_cost>=-1e-7).all()
    assert (ledger.total_execution_cost>=0).all()
    assert ledger.gross_before_slippage.sum()-ledger.slippage_cost.sum()-ledger.fees.sum()==pytest.approx(ledger.net_pnl.sum())
    assert metrics["slippage_total"]==pytest.approx(ledger.slippage_cost.sum())
    assert metrics["ending_equity"]==pytest.approx(cfg.initial_equity+ledger.net_pnl.sum(),abs=1e-5)
    assert sum(x["trades"] for x in metrics["cost_by_exit_reason"].values())==len(ledger)


def test_invalid_entry_mode_fails():
    with pytest.raises(ValueError,match="entry mode"):
        RiskPolicy(entry_mode="always").validate()


def test_transition_resets_on_segment_boundary():
    cfg=RiskPolicy(atr_period=2,max_hold_minutes=3,cooldown_minutes=0,
        funding_guard_minutes=0,entry_mode="transition")
    # One signal transition per segment, no lookback across true gap.
    f1=frame(start=3600)
    f2=frame(start=3600+240*60+3600)
    metrics,ledger,_=run_risk([f1,f2],lambda f:[0]*20+[1]*(len(f)-20),cfg,"1m")
    assert metrics["trades"]==2
