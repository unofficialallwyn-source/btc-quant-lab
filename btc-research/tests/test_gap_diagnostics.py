import json
import pandas as pd
import pytest
from src.historical import collect, validate

def rows(start,end):
    return [dict(time=t,open=10.,high=11.,low=9.,close=10.,volume=1.) for t in range(start,end,60)]

def test_missing_timestamp_diagnostics():
    frame=pd.DataFrame(rows(0,300)).drop(index=2).reset_index(drop=True)
    with pytest.raises(ValueError,match="1970-01-01T00:02:00"):
        validate(frame,0,300)

def test_incomplete_response_retried_then_succeeds(tmp_path,monkeypatch):
    monkeypatch.setattr('src.historical.time.sleep',lambda _:None)
    calls=[]
    def fetcher(symbol,resolution,start,end):
        calls.append(start)
        data=rows(start,end+60)
        return {'result':data[:-1] if len(calls)==1 else data}
    output=collect(fetcher,0,300,tmp_path,window_minutes=5)
    assert len(calls)==2 and output[0]['rows']==5

def test_persistent_gap_fails_without_manifest(tmp_path,monkeypatch):
    monkeypatch.setattr('src.historical.time.sleep',lambda _:None)
    calls=[]
    def fetcher(symbol,resolution,start,end):
        calls.append(start)
        return {'result':rows(start,end+60)[:-1]}
    with pytest.raises(ValueError,match="Missing candles"):
        collect(fetcher,0,300,tmp_path,window_minutes=5)
    assert len(calls)==3
    assert not (tmp_path/'BTCUSD_1m_manifest.json').exists()
