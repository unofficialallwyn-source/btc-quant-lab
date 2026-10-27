import pytest
from src.delta_accounting import reaccount_ledger


def trade(**kwargs):
    t={"entry_time":60,"exit_time":120,"side":1,"entry":"100000",
       "exit":"101000","quantity":"0.002"}
    t.update(kwargs)
    return t


def test_reaccount_uses_integer_lots_and_real_fx_observations():
    result=reaccount_ledger([trade()],{60:85,120:85},{60:[]},
                             opening_cash_inr=1000)
    t=result["trades"][0]
    assert t["lots"]==2
    assert t["status"]=="accounted"
    assert float(t["net_pnl_inr"])<170  # fee GST charged on both sides
    assert result["currency"]=="INR"
    assert result["liquidation_modeled"] is False


def test_missing_fx_and_funding_fail_closed():
    with pytest.raises(ValueError,match="FX"):
        reaccount_ledger([trade()],{60:85},{60:[]},opening_cash_inr=1000)
    with pytest.raises(ValueError,match="funding"):
        reaccount_ledger([trade()],{60:85,120:85},{},opening_cash_inr=1000)


def test_no_subminimum_fractional_contracts():
    r=reaccount_ledger([trade(quantity=".0009")],
                       {60:85,120:85},{60:[]},opening_cash_inr=1000)
    assert r["trades"][0]["status"]=="untradeable_subminimum_lot"
    assert r["ending_cash_inr"]=="1000"


def test_insufficient_margin():
    r=reaccount_ledger([trade(quantity="0.5")],
                       {60:85,120:85},{60:[]},opening_cash_inr=100)
    assert r["trades"][0]["status"]=="insufficient_initial_margin"


def test_funding_signed_and_explicit():
    old=trade(exit_time=28860)
    funding={60:[{"time":28800,"mark_usd":"100000",
                  "inr_per_usd":"85","rate":"0.001"}]}
    r=reaccount_ledger([old],{60:85,28860:85},funding,opening_cash_inr=1000)
    assert float(r["trades"][0]["funding_payment_inr"])>0
