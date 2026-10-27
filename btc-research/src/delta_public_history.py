"""Download verifiable raw Delta public historical mark/funding candles.

REST market-data endpoint max 2000 candles. Raw downloads are evidence only:
funding *candles* are not silently reinterpreted as settlement events.
FX is never fabricated. Validation requires reviewed, timestamped CSV inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import requests


BASE="https://api.india.delta.exchange/v2/history/candles"


def fetch_candles(symbol,start,end,resolution="1m",session=None):
    if symbol not in ("MARK:BTCUSD","FUNDING:BTCUSD"):
        raise ValueError("Only public BTCUSD mark/funding data")
    secs={"1m":60,"1h":3600,"8h":28800}
    if resolution not in secs:raise ValueError("Unsupported resolution")
    if not 0<=start<end or start%secs[resolution] or end%secs[resolution]:
        raise ValueError("Timestamps must align to requested resolution")
    session=session or requests.Session()
    step=secs[resolution]*1900
    gathered={}
    for lo in range(start,end,step):
        hi=min(lo+step,end)
        params={"symbol":symbol,"resolution":resolution,"start":lo,"end":hi}
        error=None
        for attempt in range(5):
            try:
                response=session.get(BASE,params=params,timeout=25)
                if response.status_code in (429,500,502,503,504):
                    raise requests.HTTPError(f"Retryable HTTP {response.status_code}")
                response.raise_for_status()
                body=response.json()
                if body.get("success") is not True or not isinstance(body.get("result"),list):
                    raise ValueError("Unexpected Delta historical endpoint response")
                error=None
                break
            except (requests.RequestException,ValueError) as exc:
                error=exc
                if attempt<4:time.sleep(min(2**attempt,8))
        if error is not None:raise RuntimeError(f"Historical request failed: {lo}..{hi}") from error
        for candle in body["result"]:
            t=int(candle["time"])
            if lo<=t<hi and t%secs[resolution]==0:
                if t in gathered and gathered[t]!=candle:
                    raise ValueError("Conflicting duplicate Delta candle")
                gathered[t]=candle
    return [gathered[t] for t in sorted(gathered)]


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",type=int,required=True)
    p.add_argument("--end",type=int,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    target=Path(a.output);target.mkdir(parents=True,exist_ok=True)
    inventory={}
    for symbol,res in (("MARK:BTCUSD","1m"),("FUNDING:BTCUSD","1h")):
        data=fetch_candles(symbol,a.start,a.end,res)
        filename="raw_"+symbol.split(":")[0].lower()+".json"
        path=target/filename
        path.write_text(json.dumps(data,separators=(",",":"))+"\n")
        inventory[symbol]={"resolution":res,"rows":len(data),
             "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
             "file":filename}
    (target/"raw_inventory.json").write_text(json.dumps(inventory,indent=2)+"\n")
    print(json.dumps(inventory,indent=2))


if __name__=="__main__":
    main()
