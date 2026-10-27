"""Forensic regression checks on risk-engine decision counts and accounting."""
import pytest
from src.risk_engine import RiskPolicy,run_risk
from tests.test_risk_engine import frame,fixed_signal


def test_entry_accounting_and_diagnostic_counts():
    cfg=RiskPolicy(atr_period=2,max_hold_minutes=3,cooldown_minutes=5,
                   funding_guard_minutes=0)
    metrics,trades,_=run_risk([frame(180)],fixed_signal,cfg,"1m")
    counts=metrics["entry_decisions"]
    assert counts["signals"]>=counts["entries"]>0
    assert counts["blocked_cooldown"]>0
    assert sum(metrics["exit_reasons"].values())==len(trades)
    assert metrics["average_hold_minutes"] is not None
    assert metrics["ending_equity"]==pytest.approx(cfg.initial_equity+trades.net_pnl.sum(),abs=1e-5)
    assert metrics["fee_total"]==pytest.approx(trades.fees.sum())
    assert not metrics["funding_modeled"]


def test_daily_lockout_prevents_further_entries():
    cfg=RiskPolicy(atr_period=2,max_hold_minutes=1,cooldown_minutes=0,
        daily_loss_limit_fraction=.000001,funding_guard_minutes=0)
    metrics,trades,_=run_risk([frame(180)],fixed_signal,cfg,"1m")
    assert metrics["entry_decisions"]["blocked_daily_loss"]>0
    assert metrics["entry_decisions"]["entries"]==len(trades)
