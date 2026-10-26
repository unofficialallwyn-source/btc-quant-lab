"""One-click bounded orchestration of verified, gap-aware 28-day batches.

No cron, no orders, no gap interpolation. Each batch uses existing validated
Azure ingestion and writes its own report before the next batch starts.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .blob_auth import storage_url
from .cloud_backfill import DAY, epoch
from .gap_aware import collect_days

MAX_BATCHES = 40
MAX_RUNTIME_MINUTES = 270


def orchestrate(start, end, url, workspace, *, max_batches=32,
                days_per_batch=28, max_runtime_minutes=240, execute=False,
                report="data/automated-backfill-summary.json"):
    if start >= end or start % DAY or end % DAY:
        raise ValueError("Expected UTC day-aligned start/end")
    if not 1 <= max_batches <= MAX_BATCHES:
        raise ValueError("max_batches must be 1..40")
    if not 1 <= days_per_batch <= 28:
        raise ValueError("days_per_batch must be 1..28")
    if not 1 <= max_runtime_minutes <= MAX_RUNTIME_MINUTES:
        raise ValueError("max_runtime_minutes must be 1..270")
    workspace = Path(workspace)
    summary_path = Path(report)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    began = time.monotonic()
    batches = []
    result = {
        "start": datetime.fromtimestamp(start,timezone.utc).strftime("%Y-%m-%d"),
        "end_exclusive": datetime.fromtimestamp(end,timezone.utc).strftime("%Y-%m-%d"),
        "execute": execute, "max_batches": max_batches,
        "days_per_batch": days_per_batch,
        "max_runtime_minutes": max_runtime_minutes,
        "batches": batches, "status": "not_started",
        "all_eligible_days_attempted": False,
        "fully_complete": False,
        "verified_minutes": None,
        "expected_minutes": (end-start)//60,
        "source_gap_days_count": None, "error": None,
    }
    def save():
        summary_path.write_text(json.dumps(result,indent=2)+"\n")
        print("AUTOMATED BACKFILL CHECKPOINT " + json.dumps({
            "batches":len(batches),"status":result["status"],
            "verified_minutes":result["verified_minutes"],
            "source_gap_days_count":result["source_gap_days_count"]}),flush=True)

    save()
    try:
        for i in range(max_batches):
            if time.monotonic()-began >= max_runtime_minutes*60:
                result["status"]="runtime_budget_reached"
                break
            batch_report=workspace/f"batch-{i+1:02d}.json"
            output=collect_days(start,end,url,workspace/f"batch-{i+1:02d}",
                                max_days=days_per_batch,download=execute,
                                retry_gaps=False,report=batch_report)
            states=[e["state"] for e in output["attempts"]]
            batches.append({
                "batch":i+1,
                "attempted_days":len(states),
                "verified_days":states.count("verified"),
                "source_gap_days":states.count("source_gap_recorded"),
                "verified_minutes_cumulative":output["verified_minutes"],
                "report":str(batch_report),
            })
            result["verified_minutes"]=output["verified_minutes"]
            result["source_gap_days_count"]=len(output["source_gap_days"])
            result["fully_complete"]=output["fully_complete"]
            result["status"]="running"
            if output["fully_complete"]:
                result["status"]="fully_complete"
            elif not output["attempts"]:
                result["status"]="all_eligible_days_attempted"
                result["all_eligible_days_attempted"]=True
            elif not execute:
                result["status"]="dry_run"
            save()
            if result["status"]!="running":
                break
        else:
            result["status"]="batch_limit_reached"
    except Exception as exc:
        result["status"]="failed"
        result["error"]=f"{type(exc).__name__}: {exc}"
        save()
        raise
    save()
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",default="2024-02-03")
    p.add_argument("--end",help="Exclusive UTC date; default current UTC midnight")
    p.add_argument("--max-batches",type=int,default=32)
    p.add_argument("--days-per-batch",type=int,default=28)
    p.add_argument("--max-runtime-minutes",type=int,default=240)
    p.add_argument("--execute",action="store_true")
    args=p.parse_args()
    cutoff=args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    orchestrate(epoch(args.start),epoch(cutoff),storage_url(),"data/automated-backfill",
                max_batches=args.max_batches,
                days_per_batch=args.days_per_batch,
                max_runtime_minutes=args.max_runtime_minutes,
                execute=args.execute)


if __name__=="__main__":
    main()
