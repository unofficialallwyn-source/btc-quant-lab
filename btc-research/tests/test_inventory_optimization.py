"""Ensure optimized collection performs bounded full scans without weakening verification."""
import json
import pytest
from src import gap_aware
from src.cloud_backfill import DAY


class GapClient:
    def list_blobs(self,name_starts_with):
        return []


def test_one_initial_one_final_audit_and_targeted_each_day(monkeypatch,tmp_path):
    client=GapClient()
    monkeypatch.setattr(gap_aware,"client_from_url",lambda _:client)
    calls={"inventory":0,"verified":[],"execute":[]}
    uploaded=[]
    def audit(_):
        calls["inventory"]+=1
        return list(uploaded)
    def execute(lo,hi,url,workspace,**kwargs):
        calls["execute"].append((lo,hi))
        assert kwargs["stored"]==uploaded
    def verify(_,name):
        day=int(name.split("_")[-2])
        calls["verified"].append(day)
        r={"start":day,"end":day+DAY,"name":name,"rows":1440}
        uploaded.append(r)
        return r
    monkeypatch.setattr(gap_aware,"inventory",audit)
    monkeypatch.setattr(gap_aware,"execute",execute)
    monkeypatch.setattr(gap_aware,"verify_manifest",verify)
    result=gap_aware.collect_days(0,3*DAY,"url",tmp_path,max_days=3,
             download=True,report=tmp_path/"report.json")
    assert calls["inventory"]==2
    assert calls["verified"]==[0,DAY,2*DAY]
    assert len(calls["execute"])==3
    assert result["fully_complete"]
    assert result["verified_minutes"]==4320
    assert all(x["state"]=="verified" for x in result["attempts"])


def test_checksum_failure_is_fatal_and_never_credited(monkeypatch,tmp_path):
    client=GapClient()
    monkeypatch.setattr(gap_aware,"client_from_url",lambda _:client)
    monkeypatch.setattr(gap_aware,"inventory",lambda _:[])
    monkeypatch.setattr(gap_aware,"execute",lambda *args,**kwargs:None)
    def invalid(*args):
        raise RuntimeError("Cloud manifest verification failed: SHA mismatch")
    monkeypatch.setattr(gap_aware,"verify_manifest",invalid)
    p=tmp_path/"failure.json"
    with pytest.raises(RuntimeError,match="SHA mismatch"):
        gap_aware.collect_days(0,DAY,"url",tmp_path,max_days=1,
                                download=True,report=p)
    result=json.loads(p.read_text())
    assert result["verified_minutes"]==0
    assert result["error"] and "SHA mismatch" in result["error"]
    assert result["attempts"][0]["state"]=="planned"
    assert result["source_gap_days"]==[]
