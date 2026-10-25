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
    for index in range(max_windows):
        # Each cycle reads live inventory and SHA256-verifies every manifest's partitions.
        # A successful upload is not credited until the *next* inventory verifies it.
        stored=inventory(client_from_url(url))
        target=next_window(stored,start,end)
        if target is None:
            break
        lo,hi=target
        events.append({"window":[iso(lo),iso(hi)],"state":"planned"})
        print(f"WINDOW {index+1}/{max_windows}: {iso(lo)} to {iso(hi)}",flush=True)
        if not execute_download:
            break
        execute(lo,hi,url,Path(workspace)/str(index),days=7,dry_run=False)
        events[-1]["state"]="uploaded_pending_audit"
    stored=inventory(client_from_url(url))
    verified,missing=coverage(stored,start,end)
    result={
        "start":iso(start),"end_exclusive":iso(end),
        "covered_minutes":sum((hi-lo)//60 for lo,hi in verified),
        "expected_minutes":(end-start)//60,
        "missing_intervals":[[iso(lo),iso(hi)] for lo,hi in missing],
        "next_window":None if not missing else [iso(x) for x in next_window(stored,start,end)],
        "complete":not bool(missing),"dry_run":not execute_download,
        "executed_windows":events,
    }
    destination=Path(report)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2),flush=True)
    if execute_download and any(e["state"]=="uploaded_pending_audit" for e in events):
        # Full readback verification above must have succeeded before considering the run successful.
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
