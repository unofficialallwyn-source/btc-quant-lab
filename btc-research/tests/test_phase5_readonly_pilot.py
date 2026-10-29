import json
from src.phase5_readonly_pilot import assess, check_trades, check_book, pilot

def trade_data():
    return {"trades": [{"side": "buy", "price": "100.5", "size": 2, "timestamp": 123456}]}

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

def test_missing_side_blocks_trade_schema():
    x = trade_data()
    del x["trades"][0]["side"]
    assert not check_trades(x)["schema_accepted"]

def test_duplicate_trade_ids_not_certified():
    x = trade_data()
    x["trades"][0]["id"] = 1
    x["trades"].append(dict(x["trades"][0]))
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
