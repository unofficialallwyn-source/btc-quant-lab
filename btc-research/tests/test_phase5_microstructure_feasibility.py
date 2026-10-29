import json
import pytest
from src.phase5_microstructure_feasibility import audit,evaluate

def catalog():
    return {"schema_version":1,"symbol":"BTCUSD","resolution":"1m",
      "status":"gap_safe_partial","coverage_pct":98.1,
      "verified_minutes":120,"continuous_segments":2,
      "segments":[{"rows":60},{"rows":60}]}

def test_only_bar_proxies_available():
    r=audit(catalog())
    assert r["measurements"]["bar_return"]["status"]=="available_proxy"
    for name in ["trade_signed_volume_delta","quoted_bid_ask_spread","order_book_depth_imbalance","absorption"]:
        assert r["measurements"][name]["status"]=="requires_new_historical_data"
    assert r["validation_evaluated"] is False
    assert r["holdout_evaluated"] is False

def test_inconsistent_verified_rows_fail_closed():
    x=catalog()
    x["verified_minutes"]=125
    with pytest.raises(ValueError,match="mismatch"):
        audit(x)

def test_unknown_catalog_rejected():
    x=catalog()
    x["resolution"]="ticks"
    with pytest.raises(ValueError,match="Unexpected"):
        audit(x)

def test_writes_valid_json(tmp_path):
    inp=tmp_path/"dataset_catalog.json"
    inp.write_text(json.dumps(catalog()))
    result=evaluate(inp,tmp_path/"out")
    r=json.loads((tmp_path/"out"/"microstructure_feasibility.json").read_text())
    assert result==r
    assert len(r["measurements"])==10
