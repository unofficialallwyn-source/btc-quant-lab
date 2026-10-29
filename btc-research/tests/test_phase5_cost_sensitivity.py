import json
import pandas as pd
import pytest
from src.phase5_cost_sensitivity import scenario_metrics,validate_ledger,evaluate

def sample():
    return pd.DataFrame([
      dict(strategy="a",fold=1,entry_time=0,exit_time=60,
        gross_before_slippage=3.,fees=1.,slippage_cost=.5,net_pnl=1.5),
      dict(strategy="a",fold=1,entry_time=120,exit_time=180,
        gross_before_slippage=-1.,fees=1.,slippage_cost=.5,net_pnl=-2.5)])

def test_baseline_and_zero_cost():
    x=sample()
    validate_ledger(x)
    assert scenario_metrics(x,1.,1.)["net_accounting"]==-1.
    assert scenario_metrics(x,0.,0.)["net_accounting"]==2.
    assert scenario_metrics(x,.5,1.)["net_accounting"]==0.

def test_corrupted_accounting_rejected():
    x=sample()
    x.loc[0,"net_pnl"]=10.
    with pytest.raises(ValueError,match="gross/net"):
        validate_ledger(x)

def test_negative_cost_scenario_rejected():
    with pytest.raises(ValueError,match="Negative"):
        scenario_metrics(sample(),-1,1)

def test_end_to_end_source_provenance(tmp_path):
    x=sample()
    ledger=tmp_path/"training_trade_ledger.csv"
    x.to_csv(ledger,index=False)
    source={"phase":"5_step_1","scope":"training_only",
      "validation_evaluated":False,"holdout_evaluated":False,
      "source_phase4_sha256":"test",
      "strategies":{"a":{"total_trades":2,
        "combined_net_pnl_independent_folds":-1.,
        "folds":[{"net_pnl":-1.,"metrics":{"trades":2}}]}}}
    diag=tmp_path/"trade_diagnostics.json"
    diag.write_text(json.dumps(source))
    result=evaluate(ledger,diag,tmp_path/"output")
    assert result["scenarios"]==25
    assert result["summary"]["a"]["zero_cost_net_counterfactual"]==2.
    assert result["validation_evaluated"] is False
    source["strategies"]["a"]["total_trades"]=3
    diag.write_text(json.dumps(source))
    with pytest.raises(ValueError,match="reconcile"):
        evaluate(ledger,diag,tmp_path/"output")
