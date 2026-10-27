import json
import pandas as pd
import pytest
from src.delta_feed_probe import probe
from src.delta_market_inputs import load_inputs


def test_probe_reports_empty_funding_without_inventing_settlements(tmp_path):
    def fetch(symbol,start,end,res):
        if symbol.startswith("FUNDING:"):return []
        return [{"time":t,"close":100000,"high":100002,"low":99998,"open":100000}
                for t in range(start,end,60)]
    report=probe(0,3600,tmp_path,fetch=fetch)
    assert report["probes"]["mark"]["missing"]==0
    assert report["probes"]["funding"]["received"]==0
    assert report["funding_settlements_verified"] is False
    csv=pd.read_csv(tmp_path/"mark_1m.csv")
    assert len(csv)==60
    assert not (tmp_path/"funding_8h.csv").exists()


def test_fixed_fx_policy_requires_historical_verification(tmp_path):
    doc={"mark_source":"Delta exchange historical candle API",
         "funding_source":"Delta verified historical settlements",
         "methodology":"sample close observation",
         "recorded_utc":"2026-10-27T00:00:00Z",
         "fx_policy":"delta_india_fixed_85",
         "fx_policy_reference":"https://guides.delta.exchange/delta-exchange-india-user-guide/account-setup/usd-inr-rate",
         "fx_policy_effective_period_verified":False}
    (tmp_path/"source_manifest.json").write_text(json.dumps(doc))
    (tmp_path/"mark_1m.csv").write_text("time,mark_usd\n0,100000\n")
    (tmp_path/"funding_8h.csv").write_text("time,rate\n0,0.001\n")
    with pytest.raises(ValueError,match="historical period"):
        load_inputs(tmp_path)
    doc["fx_policy_effective_period_verified"]=True
    (tmp_path/"source_manifest.json").write_text(json.dumps(doc))
    _,mark,fx,funding=load_inputs(tmp_path)
    assert float(fx.loc[0])==85
    assert len(mark)==len(fx)
