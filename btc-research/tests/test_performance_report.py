import json
import pandas as pd
import pytest
from src.performance_report import build_report, _metrics


def sample(folder):
    folder.mkdir()
    detail={"config":{"initial_equity":1000,"fee_rate":0.0005,
                       "slippage_rate":0.00025},
            "signal_timeframe":"5m","execution_timeframe":"1m",
            "holdout_evaluated":False,
            "results":{"holdout":{"status":"locked"}}}
    for name in ("training","validation"):
        ledger=pd.DataFrame([{"entry_time":60,"exit_time":120,"side":1,
               "gross_pnl":30,"fees":2,"net_pnl":28}])
        curve=pd.DataFrame({"time":[0,60,120],"equity":[1000,950,1028]})
        ledger.to_csv(folder/f"{name}_trades.csv",index=False)
        curve.to_csv(folder/f"{name}_equity.csv",index=False)
        detail["results"][name]={"status":"evaluated",
          "ending_equity":1028,"return_pct":2.8,"trades":1}
    (folder/"evaluation.json").write_text(json.dumps(detail))


def test_report_reconciles_and_excludes_holdout(tmp_path):
    root=tmp_path/"eval"
    sample(root)
    r=build_report(root)
    assert not r["holdout_evaluated"]
    assert "holdout" not in r["partitions"]
    assert r["partitions"]["training"]["max_drawdown_pct"]==pytest.approx(5.0,abs=1e-9)
    assert r["partitions"]["training"]["expectancy_per_trade"]==28
    assert r["partitions"]["validation"]["total_fees"]==2
    assert (root/"performance_report.json").exists()


def test_report_rejects_unlocked_holdout(tmp_path):
    root=tmp_path/"eval"
    sample(root)
    p=root/"evaluation.json"
    d=json.loads(p.read_text())
    d["holdout_evaluated"]=True
    p.write_text(json.dumps(d))
    with pytest.raises(ValueError,match="locked holdout"):
        build_report(root)


def test_malformed_trade_ledger_fails(tmp_path):
    root=tmp_path/"eval"
    sample(root)
    p=root/"validation_trades.csv"
    t=pd.read_csv(p)
    t.loc[0,"net_pnl"]=999
    t.to_csv(p,index=False)
    with pytest.raises(ValueError,match="reconcile"):
        build_report(root)


def test_loss_streak_and_profit_factor():
    ledger=pd.DataFrame([
        {"entry_time":0,"exit_time":60,"side":1,"gross_pnl":-10,"fees":0,"net_pnl":-10},
        {"entry_time":60,"exit_time":120,"side":1,"gross_pnl":-5,"fees":0,"net_pnl":-5},
        {"entry_time":120,"exit_time":180,"side":1,"gross_pnl":30,"fees":0,"net_pnl":30}])
    curve=pd.DataFrame({"time":[0,60,120,180],"equity":[1000,990,985,1015]})
    m=_metrics(ledger,curve,1000)
    assert m["max_consecutive_losses"]==2
    assert m["profit_factor"]==2
    assert m["win_rate_pct"]==pytest.approx(100/3)


def test_missing_trade_rows_supported():
    ledger=pd.DataFrame(columns=["entry_time","exit_time","side","gross_pnl","fees","net_pnl"])
    curve=pd.DataFrame({"time":[0,60],"equity":[1000,1000]})
    m=_metrics(ledger,curve,1000)
    assert m["trades"]==0 and m["profit_factor"] is None
