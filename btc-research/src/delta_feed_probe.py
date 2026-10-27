"""Read-only Delta India market feed probe; no invented observations.

The candle endpoint advertises historical MARK and FUNDING data. This tool
records actual API results and coverage for short windows, without interpreting
funding OHLC as an 8-hour settled payment.
"""
import argparse
import csv
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

from .delta_public_history import fetch_candles


def probe(start,end,output,*,fetch=fetch_candles):
    if end<=start or start%3600 or end%3600 or end-start>7*86400:
        raise ValueError("Probe window must be aligned hours and <=7 days")
    folder=Path(output)
    folder.mkdir(parents=True,exist_ok=True)
    summary={"utc_start":datetime.fromtimestamp(start,timezone.utc).isoformat(),
             "utc_end_exclusive":datetime.fromtimestamp(end,timezone.utc).isoformat(),
             "symbol":"BTCUSD","exchange":"Delta Exchange India",
             "holdout_evaluated":False,"probes":{}}
    for symbol,resolution,step,label in (
        ("MARK:BTCUSD","1m",60,"mark"),
        ("FUNDING:BTCUSD","1h",3600,"funding")):
        raw=fetch(symbol,start,end,resolution)
        times=[int(x["time"]) for x in raw]
        if len(times)!=len(set(times)) or any(t<start or t>=end or t%step for t in times):
            raise ValueError("Delta returned duplicate or invalid timestamps")
        path=folder/f"raw_{label}.json"
        path.write_text(json.dumps(raw,separators=(",",":"))+"\n")
        expected=set(range(start,end,step))
        observed=set(times)
        summary["probes"][label]={"resolution":resolution,
            "received":len(raw),"expected":len(expected),
            "missing":len(expected-observed),"coverage_pct":round(100*len(observed)/len(expected),4),
            "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
        if label=="mark":
            with (folder/"mark_1m.csv").open("w",newline="") as stream:
                writer=csv.writer(stream)
                writer.writerow(["time","mark_usd"])
                for candle in sorted(raw,key=lambda x:int(x["time"])):
                    # The observed candle *close* is a minute-level sampled mark,
                    # NOT an intraminute liquidation path.
                    price=float(candle["close"])
                    if price<=0:raise ValueError("Invalid mark price")
                    writer.writerow([int(candle["time"]),format(price,".12g")])
    summary["funding_settlements_verified"]=False
    summary["blocked_reason"]="Funding OHLC is not a verified settlement event rate; requires reconciliation"
    (folder/"feed_probe_report.json").write_text(json.dumps(summary,indent=2)+"\n")
    return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",type=int,required=True)
    p.add_argument("--end",type=int,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    print(json.dumps(probe(a.start,a.end,a.output),indent=2))


if __name__=="__main__":
    main()
