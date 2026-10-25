from src.cloud_backfill import DAY
from src import full_history

def test_dry_run_reports_oldest_gap(monkeypatch,tmp_path):
    # First day stored, next three missing; no actual upload allowed.
    monkeypatch.setattr(full_history,"client_from_url",lambda url:object())
    monkeypatch.setattr(full_history,"inventory",
        lambda client:[{"start":0,"end":DAY,"rows":1440}])
    def forbidden(*args,**kwargs):
        raise AssertionError("dry run downloaded data")
    monkeypatch.setattr(full_history,"execute",forbidden)
    result=full_history.collect_history(0,4*DAY,"dummy",tmp_path,max_windows=2,
        execute_download=False,report=tmp_path/"report.json")
    assert result["covered_minutes"]==1440
    assert result["expected_minutes"]==5760
    assert len(result["executed_windows"])==1
    assert not result["complete"]

def test_upload_and_readback_validation(monkeypatch,tmp_path):
    import pytest
    monkeypatch.setattr(full_history,"client_from_url",lambda url:object())
    calls={"inv":0,"uploads":0}
    def inv(client):
        calls["inv"]+=1
        if calls["inv"]==1:
            return []
        return [{"start":0,"end":DAY,"rows":1440}]
    def upload(*args,**kwargs):
        calls["uploads"]+=1
    monkeypatch.setattr(full_history,"inventory",inv)
    monkeypatch.setattr(full_history,"execute",upload)
    result=full_history.collect_history(0,DAY,"dummy",tmp_path,max_windows=4,
        execute_download=True,report=tmp_path/"report.json")
    assert result["complete"] and calls["uploads"]==1
    assert result["covered_minutes"]==1440

def test_reject_bad_window_cap():
    import pytest
    with pytest.raises(ValueError,match="max_windows"):
        full_history.collect_history(0,DAY,"dummy",".",max_windows=20)
