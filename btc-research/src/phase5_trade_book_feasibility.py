"""Phase 5 Step 4: fail-closed Delta India trade/depth data feasibility audit.

This is an evidence registry, not a historical availability guarantee or a strategy test.
No network calls, credentials, orders, validation reads or holdout reads.
"""
import argparse
import json
from pathlib import Path

SOURCES = {
    "historical_ohlcv": {
        "interface": "GET /v2/history/candles",
        "availability": "documented_historical_candles",
        "supports_order_flow": False,
        "notes": "Candle volume does not identify the aggressor or resting liquidity.",
    },
    "public_recent_trades": {
        "interface": "GET /v2/trades/{symbol}",
        "availability": "documented_public_trades_endpoint",
        "supports_order_flow": "unverified",
        "notes": "Do not infer archival retention, bounded start/end access, or aggressor-side completeness.",
    },
    "current_orderbook": {
        "interface": "GET /v2/l2orderbook/{symbol}",
        "availability": "documented_current_snapshot",
        "supports_order_flow": "unverified",
        "notes": "Current snapshot is not historical book reconstruction.",
    },
    "stream_trades": {
        "interface": "public websocket trades",
        "availability": "documented_live_stream",
        "supports_order_flow": "requires_schema_and_reconnect_verification",
        "notes": "Must test trade IDs, aggressor semantics, clock precision, duplicates and gaps.",
    },
    "stream_depth": {
        "interface": "public websocket ob_l2, ob_updates",
        "availability": "documented_live_stream",
        "supports_order_flow": "requires_snapshot_update_validation",
        "notes": "ob_l2 is top levels; ob_updates snapshots and increments need sequence and reconnect checks.",
    },
    "historical_trade_archive": {
        "interface": "historical time-bounded raw public trades",
        "availability": "NOT_VERIFIED",
        "supports_order_flow": False,
        "notes": "Do not equate recent trades API with multi-year archived tape.",
    },
    "historical_depth_archive": {
        "interface": "historical time-bounded depth snapshots and updates",
        "availability": "NOT_VERIFIED",
        "supports_order_flow": False,
        "notes": "No archival data supplier, SLA or retention verified.",
    },
}
DOCS = ["https://docs.delta.exchange/", "https://www.delta.exchange/blog/guide-to-api-trading-with-delta-india"]
REQUIRED_TRADE = ("symbol", "exchange_timestamp", "trade_id", "price", "size", "aggressor_side")
REQUIRED_BOOK = ("symbol", "exchange_timestamp", "sequence", "action", "bids", "asks")

def validate_sample(sample, kind):
    """Validate normalized candidate records, never silently coerce missing provenance."""
    fields = REQUIRED_TRADE if kind == "trade" else REQUIRED_BOOK if kind == "book" else None
    if fields is None:
        raise ValueError("Unsupported record kind")
    if not isinstance(sample, dict):
        raise ValueError("Record must be an object")
    missing = [key for key in fields if key not in sample or sample[key] is None]
    if missing:
        return {"accepted": False, "missing": missing, "reason": "missing_required_fields"}
    if kind == "trade":
        if sample["aggressor_side"] not in ("buy", "sell"):
            return {"accepted": False, "missing": [], "reason": "unverified_aggressor"}
        if not isinstance(sample["price"], (int, float)) or not isinstance(sample["size"], (int, float)) or isinstance(sample["price"], bool) or isinstance(sample["size"], bool) or not (0 < sample["price"] < float("inf") and 0 < sample["size"] < float("inf")):
            return {"accepted": False, "missing": [], "reason": "invalid_trade_price_or_size"}
    else:
        if sample["action"] not in ("snapshot", "update") or not isinstance(sample["bids"], list) or not isinstance(sample["asks"], list):
            return {"accepted": False, "missing": [], "reason": "invalid_book_event"}
    if not isinstance(sample["exchange_timestamp"], int) or isinstance(sample["exchange_timestamp"], bool) or sample["exchange_timestamp"] <= 0:
        return {"accepted": False, "missing": [], "reason": "invalid_exchange_timestamp"}
    return {"accepted": True, "missing": [], "reason": "schema_only_not_quality_certified"}

def audit():
    return {
        "phase": "5_step_4", "status": "DOCUMENTATION_LEVEL_FEASIBILITY_ONLY",
        "venue": "Delta Exchange India", "instrument": "BTCUSD",
        "sources": SOURCES, "documentation": DOCS,
        "required_trade_fields": list(REQUIRED_TRADE), "required_book_fields": list(REQUIRED_BOOK),
        "next_checks": [
            "Verify recent trade response fields, side semantics, pagination, timestamp units, and historical lookback against real read-only responses",
            "Verify websocket trade and orderbook schemas, snapshot/sequence continuity, rate limits, reconnect behavior and UTC alignment",
            "Ask exchange or licensed vendor for multi-year historical trades/depth retention, pricing, contracts and redistribution rules",
            "Acquire a small training-only pilot before building gap-aware capture and quality certification",
            "Model fees, contract units, spread, adverse selection and funding before testing any alpha hypotheses",
        ],
        "historical_trade_archive_verified": False,
        "historical_depth_archive_verified": False,
        "validation_evaluated": False, "holdout_evaluated": False,
        "profitability_evaluated": False, "trading_enabled": False,
        "promotion_authorized": False,
        "decision": "HISTORICAL_ORDER_FLOW_RESEARCH_BLOCKED_UNTIL_DATA_CERTIFIED"
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    args = p.parse_args()
    path = Path(args.output)
    path.mkdir(parents=True, exist_ok=True)
    report = audit()
    (path / "trade_book_feasibility.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"decision": report["decision"], "sources": len(SOURCES), "historical_trade_archive_verified": False, "historical_depth_archive_verified": False}, indent=2))

if __name__ == "__main__":
    main()
