"""Phase 5 Step 3: catalog-only, fail-closed market microstructure feasibility.

This audits data availability, NOT market microstructure values or performance.
No validation/holdout reads, no invented order flow from OHLCV.
"""
import argparse,hashlib,json
from pathlib import Path

SUPPORTED_FIELDS=frozenset(("time","open","high","low","close","volume"))
MEASURES={
 "bar_return":{"inputs":["close"],"status":"available_proxy","caution":"OHLCV price change; not signed order flow"},
 "bar_range":{"inputs":["high","low"],"status":"available_proxy","caution":"High-low bar range; not executable spread"},
 "bar_volume":{"inputs":["volume"],"status":"available_proxy","caution":"Aggregated traded volume; direction unavailable"},
 "realized_bar_volatility":{"inputs":["close"],"status":"available_proxy","caution":"Candle-based volatility; subject to sampling and microstructure noise"},
 "trade_signed_volume_delta":{"inputs":["aggressor_side","trade_size"],"status":"requires_new_historical_data","caution":"Cannot infer aggressor side from candle direction"},
 "trade_count_imbalance":{"inputs":["aggressor_side","trade_id"],"status":"requires_new_historical_data","caution":"Candle volume does not reveal buy/sell initiated trade counts"},
 "quoted_bid_ask_spread":{"inputs":["best_bid","best_ask","quote_timestamp"],"status":"requires_new_historical_data","caution":"High-low candle range is not the bid-ask spread"},
 "order_book_depth_imbalance":{"inputs":["bid_levels","ask_levels","book_timestamp"],"status":"requires_new_historical_data","caution":"Requires time-synchronized order-book snapshots or updates"},
 "trade_to_quote_impact":{"inputs":["aggressor_side","trade_price","trade_timestamp","best_bid","best_ask","quote_timestamp"],"status":"requires_new_historical_data","caution":"Trade and quote clocks and matching conventions required"},
 "absorption":{"inputs":["aggressor_side","trade_size","trade_timestamp","bid_levels","ask_levels","book_timestamp"],"status":"requires_new_historical_data","caution":"OHLCV divergence alone cannot prove absorption"}
}

def audit(catalog,raw=None):
    if not isinstance(catalog,dict) or catalog.get("schema_version")!=1 or catalog.get("symbol")!="BTCUSD" or catalog.get("resolution")!="1m":
        raise ValueError("Unexpected verified dataset catalog")
    if catalog.get("status") not in ("complete","gap_safe_partial") or not isinstance(catalog.get("segments"),list) or not catalog["segments"]:
        raise ValueError("Missing verified coverage")
    total=sum(int(s["rows"]) for s in catalog["segments"])
    if total!=catalog.get("verified_minutes") or total<=0 or len(catalog["segments"])!=catalog.get("continuous_segments"):
        raise ValueError("Verified segment accounting mismatch")
    if not 0<=catalog.get("coverage_pct",-1)<=100:
        raise ValueError("Invalid coverage")
    measurements={name:dict(spec) for name,spec in MEASURES.items()}
    return {"schema_version":1,"phase":"5_step_3","scope":"catalog_and_schema_only",
       "source_catalog_sha256":hashlib.sha256(raw).hexdigest() if raw else None,
       "symbol":"BTCUSD","resolution":"1m","verified_minutes":total,
       "continuous_segments":len(catalog["segments"]),"coverage_pct":catalog["coverage_pct"],
       "gap_safe_partial":catalog["status"]=="gap_safe_partial",
       "available_source_fields":sorted(SUPPORTED_FIELDS),
       "measurements":measurements,
       "data_requirements_for_next_stage":{
         "trade_tape":["UTC timestamp and precision","price","size","exchange aggressor-side flag or validated signing rule","trade ID for deduplication"],
         "order_book":["UTC timestamp and precision","instrument identifier","bid/ask levels and sizes","snapshot plus update sequencing","gap/reconnect detection"],
         "execution":["contract specifications","taker/maker schedule","funding history","market impact estimation","latency and timestamp alignment"]},
       "validation_evaluated":False,"holdout_evaluated":False,"promotion_authorized":False,"live_trading_enabled":False,
       "decision":"MEASURE_AVAILABILITY_ONLY_NO_ORDER_FLOW_INFERRED",
       "limitations":["Catalog-only audit; no order-book or historical trade data loaded",
           "Do not treat high/low range as bid-ask spread",
           "Do not infer aggressor volume, absorption or depth from OHLCV",
           "No hypothesis, trading signal, backtest or profitability claim"]}

def evaluate(path,output):
    raw=Path(path).read_bytes()
    r=audit(json.loads(raw),raw)
    target=Path(output)
    target.mkdir(parents=True,exist_ok=True)
    (target/"microstructure_feasibility.json").write_text(json.dumps(r,indent=2,allow_nan=False)+chr(10))
    return r

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    r=evaluate(a.catalog,a.output)
    print(json.dumps({"decision":r["decision"],"verified_minutes":r["verified_minutes"],
      "available_proxies":sum(x["status"]=="available_proxy" for x in r["measurements"].values()),
      "requires_new_historical_data":sum(x["status"]=="requires_new_historical_data" for x in r["measurements"].values()),
      "validation_evaluated":False,"holdout_evaluated":False},indent=2))
if __name__=="__main__":main()
