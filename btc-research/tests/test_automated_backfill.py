import json
import pytest
from src.cloud_backfill import DAY
from src import automated_backfill as runner


def payload(state="verified",complete=False):
    return {"attempts":[{"state":state}],"verified_minutes":1440,
            "source_gap_days":[],"fully_complete":complete}


def test_repeats_and_stops_when_only_recorded_gaps_remain(monkeypatch,tmp_path):
    observations=[payload(),payload("source_gap_recorded"),
                  {"attempts":[],"verified_minutes":2880,
                   "source_gap_days":[{"date":"2024-02-20"}],
                   "fully_complete":False}]
    calls=[]
    def batch(*args,**kwargs):
        calls.append(kwargs["report"])
        return observations.pop(0)
    monkeypatch.setattr(runner,"collect_days",batch)
    result=runner.orchestrate(0,4*DAY,"url",tmp_path,max_batches=6,
             execute=True,report=tmp_path/"summary.json")
    assert result["status"]=="all_eligible_days_attempted"
    assert result["all_eligible_days_attempted"] is True
    assert result["fully_complete"] is False
    assert len(calls)==3
    assert result["source_gap_days_count"]==1


def test_failed_batch_keeps_previous_checkpoint(monkeypatch,tmp_path):
    count=[0]
    def batch(*args,**kwargs):
        count[0]+=1
        if count[0]==2:raise PermissionError("OIDC expired")
        return payload()
    monkeypatch.setattr(runner,"collect_days",batch)
    summary=tmp_path/"summary.json"
    with pytest.raises(PermissionError):
        runner.orchestrate(0,4*DAY,"url",tmp_path,max_batches=3,
             execute=True,report=summary)
    data=json.loads(summary.read_text())
    assert data["status"]=="failed"
    assert len(data["batches"])==1
    assert "OIDC expired" in data["error"]


def test_dry_run_does_not_auto_repeat(monkeypatch,tmp_path):
    calls=[]
    def batch(*args,**kwargs):
        calls.append(kwargs["download"])
        return {"attempts":[{"state":"planned"}],"verified_minutes":0,
                "source_gap_days":[],"fully_complete":False}
    monkeypatch.setattr(runner,"collect_days",batch)
    r=runner.orchestrate(0,DAY,"url",tmp_path,max_batches=32,
          execute=False,report=tmp_path/"summary.json")
    assert r["status"]=="dry_run" and calls==[False]


def test_limits(tmp_path):
    with pytest.raises(ValueError):
        runner.orchestrate(0,DAY,"url",tmp_path,max_batches=41)
    with pytest.raises(ValueError):
        runner.orchestrate(0,DAY,"url",tmp_path,max_runtime_minutes=330)
