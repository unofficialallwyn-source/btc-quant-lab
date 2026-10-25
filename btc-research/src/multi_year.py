"""Bounded multi-year BTC backfill from first missing UTC interval."""
import argparse
import json
import os
from pathlib import Path
from .blob_auth import client_from_url, storage_url
from .cloud_backfill import DAY, epoch, inventory, execute
from .coverage_plan import coverage, next_window, iso

def run(start,end,url,workspace,dry_run=True,report_path="data/coverage.json"):
    if start>=end or start%DAY or end%DAY:
        raise ValueError("Start/end must be aligned UTC dates")
    stored=inventory(client_from_url(url))
    verified,missing=coverage(stored,start,end)
    target=next_window(stored,start,end)
    report={
        "start":iso(start),
        "end_exclusive":iso(end),
        "verified_intervals":[[iso(a),iso(b)] for a,b in verified],
        "missing_intervals":[[iso(a),iso(b)] for a,b in missing],
        "covered_minutes":sum((b-a)//60 for a,b in verified),
        "expected_minutes":(end-start)//60,
        "next_window":None if target is None else [iso(target[0]),iso(target[1])],
        "dry_run":dry_run
    }
    path=Path(report_path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2),flush=True)
    if target and not dry_run:
        execute(target[0],target[1],url,workspace,days=7)
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",default="2024-03-01")
    p.add_argument("--end",required=True)
    p.add_argument("--workspace",default="data/backfill")
    p.add_argument("--execute",action="store_true")
    a=p.parse_args()
    url=storage_url()
    run(epoch(a.start),epoch(a.end),url,a.workspace,dry_run=not a.execute)

if __name__=="__main__":
    main()
