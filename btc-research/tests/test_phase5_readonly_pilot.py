import json
from src.phase5_readonly_pilot import assess, check_trades, check_book, pilot

def trade_data():
    return [{"buyer_role": "taker", "seller_role": "maker", "price": "100.5", "size": 2, "timestamp": 1793250194000000}]

def book_data():
    return {"buy": [{"price": "100", "size": "2"}],
            "sell": [{"price": "101", "size": "3"}], "last_updated_at": 123456}

def test_snapshots_never_certify_history():
    r = assess({"trades": {"success": True, "result": trade_data()},
                "book": {"success": True, "result": book_data()}})
    assert r["status"] == "SNAPSHOT_PILOT_COMPLETE"
    assert not r["historical_trade_archive_verified"]
    assert not r["historical_depth_archive_verified"]
    assert not r["promotion_authorized"]
    assert not r["holdout_evaluated"]

def test_missing_role_blocks_trade_schema():
    x = trade_data()
    del x[0]["buyer_role"]
    assert not check_trades(x)["schema_accepted"]

def test_duplicate_trade_ids_not_certified():
    x = trade_data()
    x[0]["id"] = 1
    x.append(dict(x[0]))
    assert not check_trades(x)["unique_trade_ids_verified"]

def test_book_cannot_be_crossed():
    x = book_data()
    x["sell"][0]["price"] = "99"
    assert not check_book(x)["schema_accepted"]

def test_missing_endpoint_fails_closed():
    x = assess({"trades": {"success": False}, "book": {"success": True, "result": book_data()}})
    assert x["status"] == "INCOMPLETE_PUBLIC_PILOT"
    assert not x["promotion_authorized"]

def test_capture_provenance_and_no_credentials(tmp_path):
    def fetch(path):
        if "trades" in path:
            return {"success": True, "result": trade_data()}
        return {"success": True, "result": book_data()}
    r = pilot(tmp_path, fetch=fetch)
    assert r["status"] == "SNAPSHOT_PILOT_COMPLETE"
    assert json.loads((tmp_path / "raw_trades.json").read_text())["success"]
    assert r["inventory"]["trades"]["sha256"]
    assert not r["holdout_evaluated"]

def test_rest_observed_roles_map_to_aggressor_without_fabricating_ids():
    x = trade_data()
    x.append({"buyer_role": "maker", "seller_role": "taker", "price": "100", "size": 3, "timestamp": 1793250193000000})
    result = check_trades(x)
    assert result["schema_accepted"] is True
    assert result["aggressor_side_verified"] is True
    assert result["unique_trade_ids_verified"] is False
    assert result["timestamp_unit"] == "epoch_microseconds"

def test_milliseconds_or_inconsistent_roles_rejected():
    x = trade_data()
    x[0]["timestamp"] = 1793250194000
    assert not check_trades(x)["schema_accepted"]
    x = trade_data()
    x[0]["seller_role"] = "taker"
    assert not check_trades(x)["schema_accepted"]
