"""Public, read-only Delta India hourly BTCUSD candles + funding-rate candles.

No credentials. Raw pages are hashed; derived files carry provenance.
Funding candles are an *estimate* of settlement rates: their units are inferred
(percent vs decimal) and recorded, and they are sampled only at settlement
boundaries. Treat funding P&L from them as approximate until reconciled.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
import requests

BASE = "https://api.india.delta.exchange/v2/history/candles"
PAGE = 1900


def fetch(symbol, start, end, resolution="1h", session=None, sleep=0.25):
    secs = {"1h": 3600, "1d": 86400}[resolution]
    if start % secs or end % secs or end <= start:
        raise ValueError("start/end must be aligned and increasing")
    session = session or requests.Session()
    rows = {}
    for lo in range(start, end, secs * PAGE):
        hi = min(lo + secs * PAGE, end)
        for attempt in range(5):
            try:
                r = session.get(BASE, params={"symbol": symbol, "resolution": resolution,
                                              "start": lo, "end": hi}, timeout=25)
                if r.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"retryable {r.status_code}")
                r.raise_for_status()
                body = r.json()
                if body.get("success") is not True or not isinstance(body.get("result"), list):
                    raise ValueError("Unexpected Delta response")
                break
            except (requests.RequestException, ValueError):
                if attempt == 4:
                    raise
                time.sleep(min(2 ** attempt, 8))
        for c in body["result"]:
            t = int(c["time"])
            if lo <= t < hi and t % secs == 0:
                rows[t] = {k: c.get(k) for k in ("time", "open", "high", "low", "close", "volume")}
        if sleep:
            time.sleep(sleep)
    return pd.DataFrame([rows[t] for t in sorted(rows)])


def clean_ohlc(df):
    if df.empty:
        raise ValueError("No candles returned")
    df = df.astype({"time": "int64"})
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    bad = df[["open", "high", "low", "close"]].isna().any(axis=1) | (df.low <= 0) | (df.high < df.low)
    return df.loc[~bad].reset_index(drop=True), int(bad.sum())


def funding_from_candles(df, interval_hours=8):
    """Sample funding candle close at settlement boundaries; infer units."""
    step = interval_hours * 3600
    f = df[(df.time % step) == 0][["time", "close"]].rename(columns={"close": "rate"}).copy()
    f["rate"] = pd.to_numeric(f.rate, errors="coerce")
    f = f.dropna()
    units = "decimal"
    if len(f) and float(np.nanpercentile(f.rate.abs(), 95)) > 0.005:
        f["rate"] = f.rate / 100.0
        units = "percent->decimal"
    return f.reset_index(drop=True), units


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", required=True, help="UTC date inclusive, e.g. 2023-06-01")
    p.add_argument("--end", required=True, help="UTC date exclusive")
    p.add_argument("--output", required=True)
    p.add_argument("--funding-interval-hours", type=int, default=8)
    a = p.parse_args()
    start = int(pd.Timestamp(a.start, tz="UTC").timestamp())
    end = int(pd.Timestamp(a.end, tz="UTC").timestamp())
    out = Path(a.output); out.mkdir(parents=True, exist_ok=True)
    px, dropped = clean_ohlc(fetch("BTCUSD", start, end))
    px.to_csv(out / "btcusd_1h.csv", index=False)
    manifest = {"source": BASE, "symbol": "BTCUSD", "resolution": "1h", "rows": len(px),
                "dropped_invalid": dropped, "first": int(px.time.iloc[0]), "last": int(px.time.iloc[-1]),
                "missing_hours": int((px.time.iloc[-1] - px.time.iloc[0]) // 3600 + 1 - len(px)),
                "fetched_utc": pd.Timestamp.utcnow().isoformat()}
    try:
        raw_f = fetch("FUNDING:BTCUSD", start, end)
        fund, units = funding_from_candles(raw_f, a.funding_interval_hours)
        fund.to_csv(out / "funding.csv", index=False)
        manifest["funding"] = {"symbol": "FUNDING:BTCUSD", "rows": len(fund), "units": units,
                               "interval_hours": a.funding_interval_hours,
                               "status": "ESTIMATE_FROM_PUBLIC_CANDLES_UNRECONCILED"}
    except Exception as exc:  # funding is optional; record why it is missing
        manifest["funding"] = {"status": "UNAVAILABLE", "error": str(exc)[:300]}
    for name in ("btcusd_1h.csv", "funding.csv"):
        path = out / name
        if path.exists():
            manifest.setdefault("sha256", {})[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
