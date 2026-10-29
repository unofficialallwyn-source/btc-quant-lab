"""Phase 5 Step 5: bounded public REST snapshot pilot, fail-closed research gate.

No keys, authenticated calls, trade orders, replay, alpha backtests, or holdout access.
One request per public endpoint. Snapshot success is NOT archival continuity.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import requests

BASE = "https://api.india.delta.exchange"
PATHS = {"trades": "/v2/trades/BTCUSD", "book": "/v2/l2orderbook/BTCUSD"}
RESEARCH_DECISION = "NOT_READY_HISTORICAL_TAPE_AND_DEPTH_UNVERIFIED"

def positive(value):
    try:
        d = Decimal(str(value))
        return d.is_finite() and d > 0
    except (ValueError, TypeError, InvalidOperation):
        return False

def check_trades(result):
    issues = []
    records = result.get("trades") if isinstance(result, dict) else None
    if not isinstance(records, list):
        return {"count": 0, "schema_accepted": False, "issues": ["missing_trades_array"],
                "aggressor_side_verified": False, "unique_trade_ids_verified": False}
    timestamps = []
    sides = []
    ids = []
    for idx, trade in enumerate(records):
        if not isinstance(trade, dict):
            issues.append(f"trade_{idx}_not_object")
            continue
        if trade.get("side") not in ("buy", "sell"):
            issues.append(f"trade_{idx}_invalid_aggressor_side")
        else:
            sides.append(trade["side"])
        if not positive(trade.get("price")) or not positive(trade.get("size")):
            issues.append(f"trade_{idx}_invalid_price_or_size")
        t = trade.get("timestamp")
        if not isinstance(t, (int, float)) or isinstance(t, bool) or t <= 0:
            issues.append(f"trade_{idx}_invalid_timestamp")
        else:
            timestamps.append(t)
        if trade.get("id") is not None:
            ids.append(str(trade["id"]))
    ids_ok = len(records) > 0 and len(ids) == len(records) and len(ids) == len(set(ids))
    return {"count": len(records), "schema_accepted": len(records) > 0 and not issues,
            "issues": issues[:100], "aggressor_side_verified": len(records) > 0 and len(sides) == len(records),
            "unique_trade_ids_verified": ids_ok,
            "timestamp_min": min(timestamps) if timestamps else None,
            "timestamp_max": max(timestamps) if timestamps else None,
            "historical_lookback_verified": False}

def check_book(result):
    issues = []
    if not isinstance(result, dict):
        return {"schema_accepted": False, "issues": ["invalid_book_object"]}
    best = {}
    for side in ("buy", "sell"):
        levels = result.get(side)
        if not isinstance(levels, list) or not levels:
            issues.append("missing_" + side + "_levels")
            continue
        prices = []
        for level in levels:
            if not isinstance(level, dict) or not positive(level.get("price")) or not positive(level.get("size")):
                issues.append("invalid_" + side + "_level")
            else:
                prices.append(Decimal(str(level["price"])))
        if prices:
            best[side] = max(prices) if side == "buy" else min(prices)
    if "buy" in best and "sell" in best and best["buy"] >= best["sell"]:
        issues.append("crossed_or_locked_book")
    return {"schema_accepted": not issues, "issues": issues[:100],
            "bid_levels": len(result.get("buy", [])) if isinstance(result.get("buy"), list) else 0,
            "ask_levels": len(result.get("sell", [])) if isinstance(result.get("sell"), list) else 0,
            "last_updated_at_present": result.get("last_updated_at") is not None,
            "snapshot_only": True, "sequence_continuity_verified": False}

def assess(raw):
    trade = raw.get("trades", {})
    book = raw.get("book", {})
    if trade.get("success") is not True or book.get("success") is not True:
        return {"status": "INCOMPLETE_PUBLIC_PILOT", "decision": RESEARCH_DECISION,
                "errors": [k for k in PATHS if raw.get(k, {}).get("success") is not True],
                "historical_trade_archive_verified": False, "historical_depth_archive_verified": False,
                "validation_evaluated": False, "holdout_evaluated": False, "promotion_authorized": False}
    trade_q = check_trades(trade.get("result"))
    book_q = check_book(book.get("result"))
    return {"status": "SNAPSHOT_PILOT_COMPLETE" if trade_q["schema_accepted"] and book_q["schema_accepted"] else "SNAPSHOT_SCHEMA_INCOMPLETE",
            "decision": RESEARCH_DECISION, "trades": trade_q, "book": book_q,
            "historical_trade_archive_verified": False, "historical_depth_archive_verified": False,
            "websocket_sequence_verified": False, "validation_evaluated": False,
            "holdout_evaluated": False, "profitability_evaluated": False, "promotion_authorized": False}

def pilot(output, fetch=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if fetch is None:
        def fetch(path):
            response = requests.get(BASE + path, headers={"Accept": "application/json"},
                                    timeout=12, allow_redirects=False)
            response.raise_for_status()
            return response.json()
    raw = {}
    errors = {}
    inventory = {}
    for key, path in PATHS.items():
        try:
            body = fetch(path)
            if not isinstance(body, dict):
                raise ValueError("non-object API response")
            raw[key] = body
            encoded = (json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
            (output / ("raw_" + key + ".json")).write_bytes(encoded)
            inventory[key] = {"endpoint": path, "sha256": hashlib.sha256(encoded).hexdigest(),
                              "bytes": len(encoded)}
        except (requests.RequestException, ValueError, TypeError) as exc:
            errors[key] = type(exc).__name__
            raw[key] = {"success": False}
    result = assess(raw)
    result["observed_utc"] = datetime.now(timezone.utc).isoformat()
    result["inventory"] = inventory
    result["request_errors"] = errors
    (output / "pilot_gate.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    args = p.parse_args()
    result = pilot(args.output)
    print(json.dumps({"status": result["status"], "decision": result["decision"],
                      "request_errors": result["request_errors"]}, indent=2))
    if result["status"] != "SNAPSHOT_PILOT_COMPLETE":
        raise SystemExit(2)

if __name__ == "__main__":
    main()
