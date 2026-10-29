import json
from src.phase5_trade_book_feasibility import audit, validate_sample, main

def test_historical_archives_are_not_assumed():
    r = audit()
    assert r["historical_trade_archive_verified"] is False
    assert r["historical_depth_archive_verified"] is False
    assert r["validation_evaluated"] is False
    assert r["holdout_evaluated"] is False
    assert r["promotion_authorized"] is False
    assert r["sources"]["current_orderbook"]["availability"] == "documented_current_snapshot"

def test_missing_aggressor_rejected():
    x = dict(symbol="BTCUSD", exchange_timestamp=123, trade_id="1", price=100, size=1)
    result = validate_sample(x, "trade")
    assert not result["accepted"]
    assert "aggressor_side" in result["missing"]

def test_unverified_aggressor_rejected():
    x = dict(symbol="BTCUSD", exchange_timestamp=123, trade_id="1", price=100, size=1, aggressor_side="unknown")
    assert validate_sample(x, "trade")["accepted"] is False

def test_valid_trade_only_schema_certified():
    x = dict(symbol="BTCUSD", exchange_timestamp=123, trade_id="1", price=100, size=1, aggressor_side="sell")
    assert validate_sample(x, "trade")["reason"] == "schema_only_not_quality_certified"

def test_invalid_book():
    x = dict(symbol="BTCUSD", exchange_timestamp=123, sequence=1, action="update", bids={}, asks=[])
    assert validate_sample(x, "book")["accepted"] is False

def test_reject_bad_kind():
    import pytest
    with pytest.raises(ValueError):
        validate_sample({}, "candles")
