import json
from pathlib import Path
import pandas as pd
import pytest

from src.delta_sim_engine import run_delta,DeltaSimConfig
from src.delta_market_inputs import load_inputs,coverage_report
from src.delta_public_history import fetch_candles


def candles(n=35,base=0):
    return pd.DataFrame({"time":[base+60*i for i in range(n)],
      "open":[100000.]*n,"high":[100010.]*n,"low":[99990.]*n,
      "close":[100000.]*n,"volume":[1.]*n})


def observations(f):
    return (pd.Series(100000.,index=f.time.to_numpy()),
            pd.Series(85.,index=f.time.to_numpy()))


def test_integrated_engine_inr_fills_and_fees():
    f=candles()
    mark,fx=observations(f)
    def signals(frame):
        return [1]+[0]*(len(frame)-1)
    result,ledger,curve=run_delta([f],signals,mark,fx,{},DeltaSimConfig())
    assert result["currency"]=="INR"
    assert result["trade_count"]==1
    assert ledger.iloc[0].lots>=1
    assert result["total_fee_inr"]>0
    assert result["ending_equity_inr"]<85000
    assert len(curve)==len(f)


def test_missing_mark_and_fx_fail_closed():
    f=candles()
    mark,fx=observations(f)
    with pytest.raises(ValueError,match="Missing mark"):
        run_delta([f],lambda f:[0]*len(f),mark.iloc[:-1],fx,{})
    with pytest.raises(ValueError,match="Missing FX"):
        run_delta([f],lambda f:[0]*len(f),mark,fx.iloc[:-1],{})


def test_missing_funding_fails_closed_for_open_position():
    f=candles(n=8,base=28800-3*60)
    mark,fx=observations(f)
    with pytest.raises(ValueError,match="Missing verified funding"):
        run_delta([f],lambda f:[1]+[0]*(len(f)-1),mark,fx,{})
    result,trades,_=run_delta([f],lambda f:[1]+[0]*(len(f)-1),
                              mark,fx,{28800:0.001})
    assert result["net_funding_paid_inr"]>0


def test_insufficient_margin_skips_risky_entry():
    f=candles()
    mark,fx=observations(f)
    result,ledger,_=run_delta([f],lambda f:[1]+[0]*(len(f)-1),
             mark,fx,{},DeltaSimConfig(initial_inr="2"))
    assert ledger.empty
    assert result["ending_equity_inr"]==2.


def test_csv_manifest_must_be_real_and_time_aligned(tmp_path):
    (tmp_path/"source_manifest.json").write_text(json.dumps({
     "mark_source":"Delta India API","fx_source":"Independent rates",
     "funding_source":"Observed settlement rates",
     "methodology":"exact observed as-of minute",
     "recorded_utc":"2026-10-27T00:00:00Z","synthetic":True}))
    for filename,header,val in (("mark_1m.csv","mark_usd",100000),
      ("fx_1m.csv","inr_per_usd",85),("funding_8h.csv","rate",0.0001)):
        (tmp_path/filename).write_text(f"time,{header}\n0,{val}\n")
    with pytest.raises(ValueError,match="Synthetic"):
        load_inputs(tmp_path)
    obj=json.loads((tmp_path/"source_manifest.json").read_text())
    obj["synthetic"]=False
    (tmp_path/"source_manifest.json").write_text(json.dumps(obj))
    _,mark,fx,funding=load_inputs(tmp_path)
    f=candles(n=1)
    assert coverage_report([f],mark,fx,funding)["complete"]


def test_public_fetch_pagination_and_no_invented_candles():
    class Response:
        status_code=200
        def raise_for_status(self):pass
        def json(self):
            return {"success":True,"result":[{"time":0,"close":100},
                {"time":60,"close":101}]}
    class Session:
        def get(self,*a,**k):
            assert k["params"]["symbol"]=="MARK:BTCUSD"
            return Response()
    got=fetch_candles("MARK:BTCUSD",0,120,session=Session())
    assert len(got)==2
    assert got[1]["time"]==60
