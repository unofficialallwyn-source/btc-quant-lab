"""Bounded restartable full-history collector; no trading or data fabrication."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .blob_auth import client_from_url, storage_url
from .cloud_backfill import DAY, epoch, inventory, execute
from .coverage_plan import coverage, next_window, iso


def collect_history(start, end, url, workspace, max_windows=4, execute_download=False,
                    report="data/full-history-progress.json"):
    if not 1 <= max_windows <= 12:
        raise ValueError("max_windows must be 1..12")
    if start >= end or start % DAY or end % DAY:
        raise ValueError("Use valid UTC day-aligned dates")
    events=[]
    failure=None
    stored=[]
    try:
        for index in range(max_windows):
            stored=inventory(client_from_url(url))
            target=next_window(stored,start,end)
            if target is None:
                break
            lo,hi=target
            event={"window":[iso(lo),iso(hi)],"state":"planned"}
            events.append(event)
            print(f"WINDOW {index+1}/{max_windows}: {iso(lo)} to {iso(hi)}",flush=True)
            if not execute_download:
                break
            event["state"]="in_progress"
            execute(lo,hi,url,Path(workspace)/str(index),days=7,dry_run=False)
            event["state"]="uploaded_pending_audit"
    except Exception as exc:
        failure=f"{type(exc).__name__}: {exc}"
        if events:
            events[-1]["state"]="failed"
            events[-1]["error"]=failure
        print(f"COLLECTION FAILURE: {failure}",flush=True)
    # Always attempt to audit the cloud, including after a partly successful upload.
    audit_error=None
    try:
        stored=inventory(client_from_url(url))
    except Exception as exc:
        audit_error=f"{type(exc).__name__}: {exc}"
        print(f"CLOUD AUDIT FAILURE: {audit_error}",flush=True)
    if audit_error is None:
        verified,missing=coverage(stored,start,end)
        target=next_window(stored,start,end)
    else:
        verified,missing,target=[],[(start,end)],None
    result={
        "start":iso(start),"end_exclusive":iso(end),
        "covered_minutes":sum((hi-lo)//60 for lo,hi in verified),
        "expected_minutes":(end-start)//60,
        "missing_intervals":[[iso(lo),iso(hi)] for lo,hi in missing],
        "next_window":None if target is None else [iso(x) for x in target],
        "complete":not missing and failure is None and audit_error is None,
        "dry_run":not execute_download,"executed_windows":events,
        "error":failure,"audit_error":audit_error,
        "status":"failed" if failure or audit_error else "complete" if not missing else "partial",
    }
    destination=Path(report)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2),flush=True)
    if failure or audit_error:
        raise RuntimeError(f"Historical collection failed; progress report saved to {destination}: {failure or audit_error}")
    if execute_download and any(e["state"]=="uploaded_pending_audit" for e in events):
        print("Completed cloud read-back SHA256 verification.",flush=True)
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--start",default="2024-02-03")
    parser.add_argument("--end",help="Exclusive UTC date; default today UTC midnight")
    parser.add_argument("--workspace",default="data/backfill")
    parser.add_argument("--max-windows",type=int,default=4)
    parser.add_argument("--execute",action="store_true")
    args=parser.parse_args()
    cutoff=args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    collect_history(epoch(args.start),epoch(cutoff),storage_url(),args.workspace,
                    max_windows=args.max_windows,execute_download=args.execute)


if __name__=="__main__":
    main()
