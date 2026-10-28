import pandas as pd
import pytest
from src.phase5_failure_diagnostics import analyze_ledger,verify_fold


def ledger():
    return pd.DataFrame([
      {"entry_time":0,"exit_time":600,"exit_reason":"stop","gross_before_slippage":2.,
       "fees":1.,"slippage_cost":.5,"net_pnl":.5},
      {"entry_time":600,"exit_time":1800,"exit_reason":"time_limit","gross_before_slippage":1.,
       "fees":1.,"slippage_cost":.5,"net_pnl":-.5}])


def test_cost_and_exit_reason_accounting():
    d=analyze_ledger(ledger())
    assert d["trades"]==2
    assert d["winner_count"]==1
    assert d["loser_count"]==1
    assert d["gross_winner_net_loser_count"]==1
    assert d["median_hold_minutes"]==15
    assert d["exit_reasons"]["time_limit"]["net_pnl"]==-.5


def test_exact_frozen_replay():
    original={"gross_before_slippage":3.,"fees":2.,"slippage":1.,"net_pnl":0.,
              "trades":2,"net_return_pct":0.}
    verify_fold(ledger(),original,{"return_pct":0.})
    original["fees"]=.25
    with pytest.raises(ValueError,match="Frozen Phase 4 mismatch"):
        verify_fold(ledger(),original,{"return_pct":0.})


def test_empty_ledger():
    assert analyze_ledger(pd.DataFrame())["trades"]==0


def test_corrupt_ledger_rejected():
    bad=ledger()
    bad.loc[0,"net_pnl"]=100.
    with pytest.raises(ValueError,match="does not reconcile"):
        verify_fold(bad,{},{"return_pct":0.})
