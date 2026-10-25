"""Read-only cloud coverage audit and resumable 7-day BTC backfill windows."""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .blob_auth import client_from_url, storage_url
from .delta_client import fetch_candles
from .historical import collect
from .upload_azure import upload

PREFIX = "historical/BTCUSD/1m"
DAY = 86400

def epoch(date):
    return int(datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())

def plan(start, end, days=7):
    if end <= start or (end-start) % DAY or days < 1 or days > 7:
        raise ValueError("UTC dates must span whole days; chunk length 1..7 days")
    return [(lo, min(end,lo+days*DAY)) for lo in range(start,end,days*DAY)]

def inventory(client, prefix=PREFIX, verify_bytes=True):
    """Only credit data whose complete manifest and referenced blobs are valid."""
    records=[]
    manifest_prefix=f"{prefix}/manifests/"
    for item in client.list_blobs(name_starts_with=manifest_prefix):
        name=item.name
        try:
            data=json.loads(client.get_blob_client(name).download_blob().readall())
            if not data: raise ValueError("Empty manifest")
            for i,part in enumerate(data):
                lo,hi=int(part["start"]),int(part["end_exclusive"])
                if lo >= hi or (hi-lo)//60 != int(part["rows"]):
                    raise ValueError("Malformed interval")
                if i and int(data[i-1]["end_exclusive"]) != lo:
                    raise ValueError("Noncontiguous manifest")
                filename=part["filename"]
                if Path(filename).name != filename: raise ValueError("Unsafe filename")
                blob=client.get_blob_client(f"{prefix}/{filename}")
                if verify_bytes:
                    actual=hashlib.sha256(blob.download_blob().readall()).hexdigest()
                    if actual != part["sha256"]: raise ValueError("SHA mismatch")
                else:
                    blob.get_blob_properties()
            records.append(dict(start=int(data[0]["start"]),end=int(data[-1]["end_exclusive"]),name=name,rows=sum(int(p["rows"]) for p in data)))
        except Exception as exc:
            raise RuntimeError(f"Cloud manifest verification failed: {name}: {exc}") from exc
    return sorted(records,key=lambda x:x["start"])

def classify(windows, stored):
    """Fully covered windows are skipped; partial overlaps block execution."""
    selected=[]
    for lo,hi in windows:
        overlaps=[x for x in stored if x["start"]<hi and x["end"]>lo]
        pos=lo
        for x in sorted(overlaps,key=lambda y:y["start"]):
            if x["start"] > pos:
                break
            pos=max(pos,x["end"])
        if pos >= hi:
            selected.append(("skip",lo,hi))
        elif overlaps:
            selected.append(("overlap",lo,hi))
        else:
            selected.append(("fetch",lo,hi))
    return selected

def execute(start,end,url,workspace,days=7,dry_run=False,verify_bytes=True):
    client=client_from_url(url)
    stored=inventory(client,verify_bytes=verify_bytes)
    windows=classify(plan(start,end,days),stored)
    if any(state=="overlap" for state,_,_ in windows):
        raise ValueError("Partial overlap with existing Azure data: choose aligned nonoverlapping dates or use 1-day chunks")
    for state,lo,hi in windows:
        print(f"{state.upper()} UTC [{lo},{hi})",flush=True)
    if dry_run: return windows
    root=Path(workspace)
    for state,lo,hi in windows:
        if state=="skip": continue
        path=root/f"{lo}_{hi}"
        collect(fetch_candles,lo,hi,path,window_minutes=1800)
        uploaded=upload(path,url)
        print(f"COMPLETE [{lo},{hi}) uploaded {len(uploaded)} blobs",flush=True)
    return windows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",required=True)
    p.add_argument("--end",required=True)
    p.add_argument("--days",type=int,default=7)
    p.add_argument("--workspace",default="data/backfill")
    p.add_argument("--dry-run",action="store_true")
    a=p.parse_args()
    start,end=epoch(a.start),epoch(a.end)
    if end-start>28*DAY: p.error("Maximum 28 days per workflow run; split into more runs")
    url=storage_url()
    result=execute(start,end,url,a.workspace,days=a.days,dry_run=a.dry_run)
    print(json.dumps({"windows":len(result),"skipped":sum(x[0]=="skip" for x in result),"fetched":sum(x[0]=="fetch" for x in result)},indent=2))

if __name__=="__main__": main()
