import json
import pytest
import pandas as pd
from src.cloud_backfill import DAY
from src import gap_aware
from src.research_segments import segments, enforce_continuous

def test_next_day_skips_verified_and_blocked():
    stored=[{"start":0,"end":DAY}]
    assert gap_aware.next_day(stored,{DAY},0,4*DAY)==2*DAY

def test_gap_is_recorded_and_continues(monkeypatch,tmp_path):
    class Client:
        def __init__(self):
            self.gaps={}
        def upload_blob(self,name,data,overwrite):
            self.gaps[name]=json.loads(data)
        def list_blobs(self,name_starts_with):
            return [type("B",(),{"name":k})() for k in self.gaps]
        def get_blob_client(self,name):
            body=json.dumps(self.gaps[name]).encode()
            return type("B",(),{"download_blob":lambda self:type("D",(),{"readall":lambda self:body})()})()
    client=Client()
    monkeypatch.setattr(gap_aware,"client_from_url",lambda url:client)
    monkeypatch.setattr(gap_aware,"inventory",lambda c:[])
    def execute(lo,hi,*args,**kwargs):
        raise ValueError("Missing candles: example")
    monkeypatch.setattr(gap_aware,"execute",execute)
    r=gap_aware.collect_days(0,2*DAY,"fake",tmp_path,max_days=2,download=True,report=tmp_path/"progress.json")
    assert len(r["source_gap_days"])==2
    assert not r["fully_complete"]
    assert len(client.gaps)==2

def test_non_source_error_not_hidden(monkeypatch,tmp_path):
    class Client:
        def list_blobs(self,name_starts_with):return []
    monkeypatch.setattr(gap_aware,"client_from_url",lambda url:Client())
    monkeypatch.setattr(gap_aware,"inventory",lambda c:[])
    monkeypatch.setattr(gap_aware,"execute",lambda *a,**kw:(_ for _ in ()).throw(PermissionError("Azure denied")))
    with pytest.raises(RuntimeError,match="PermissionError"):
        gap_aware.collect_days(0,DAY,"fake",tmp_path,max_days=1,download=True,report=tmp_path/"progress.json")
    assert json.loads((tmp_path/"progress.json").read_text())["error"]

def test_research_must_not_cross_gap():
    frame=pd.DataFrame({"time":[0,60,180,240],"close":[1,2,3,4]})
    assert [len(x) for x in segments(frame)]==[2,2]
    with pytest.raises(ValueError,match="unverified gaps"):
        enforce_continuous(frame)
