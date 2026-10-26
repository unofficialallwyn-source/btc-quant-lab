import json
import pytest
from src.cloud_backfill import DAY
from src import full_history

def test_partial_upload_error_still_writes_audited_report(monkeypatch,tmp_path):
    monkeypatch.setattr(full_history,"client_from_url",lambda url:object())
    calls={"inventory":0}
    def inventory(client):
        calls["inventory"]+=1
        return [] if calls["inventory"]==1 else [
            {"start":0,"end":7*DAY,"rows":10080}]
    monkeypatch.setattr(full_history,"inventory",inventory)
    def upload(*args,**kwargs):
        raise ValueError("Missing candles: 2024-02-17T12:00:00Z")
    monkeypatch.setattr(full_history,"execute",upload)
    report=tmp_path/"progress.json"
    with pytest.raises(RuntimeError,match="progress report saved"):
        full_history.collect_history(0,14*DAY,"dummy",tmp_path,max_windows=2,
            execute_download=True,report=report)
    state=json.loads(report.read_text())
    assert state["status"]=="failed"
    assert state["covered_minutes"]==7*1440
    assert state["executed_windows"][0]["state"]=="failed"
    assert "Missing candles" in state["error"]
    assert calls["inventory"]>=2
