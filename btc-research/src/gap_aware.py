"""Source-gap-aware BTC backfill: verified full-day shards, explicit exclusions.

A gap record is a retryable observation, NOT evidence that data never existed.
Cloud manifests remain the only source of verified candle coverage.
"""
import argparse
import json
from datetime import datetime, timezone

from .blob_auth import client_from_url, storage_url
from .cloud_backfill import DAY, PREFIX, epoch, inventory, execute
from .coverage_plan import coverage, iso

GAP_PREFIX = PREFIX + "/source_gaps/"
MAX_DAYS = 28


def gap_records(client):
    found = {}
    for entry in client.list_blobs(name_starts_with=GAP_PREFIX):
        data = json.loads(client.get_blob_client(entry.name).download_blob().readall())
        day = int(data["day_start"])
        if entry.name != f"{GAP_PREFIX}{day}.json" or day % DAY:
            raise ValueError("Unexpected gap registry entry")
        found[day] = data
    return found


def next_day(stored, blocked, start, end):
    verified, _ = coverage(stored, start, end)
    for day in range(start, end, DAY):
        if day in blocked:
            continue
        if not any(lo <= day and day + DAY <= hi for lo, hi in verified):
            return day
    return None


def collect_days(start, end, url, workspace, max_days=4, download=False,
                 retry_gaps=False, report="data/gap-aware-progress.json"):
    from pathlib import Path
    if start >= end or start % DAY or end % DAY or not 1 <= max_days <= MAX_DAYS:
        raise ValueError("Invalid UTC dates or max_days (1..28)")
    client = client_from_url(url)
    attempts, fatal = [], None
    try:
        for _ in range(max_days):
            stored = inventory(client)
            gaps = gap_records(client)
            blocked = set() if retry_gaps else set(gaps)
            day = next_day(stored, blocked, start, end)
            if day is None:
                break
            attempt = {"start":iso(day),"end_exclusive":iso(day+DAY),
                       "state":"planned"}
            attempts.append(attempt)
            if not download:
                break
            try:
                # A partial source day is never represented as an ordinary valid partition.
                execute(day, day+DAY, url, Path(workspace)/str(day), days=1)
                attempt["state"] = "uploaded_pending_audit"
                # Remove older gap record only after a successful re-read audit.
                inventory(client)
                if day in gaps:
                    client.delete_blob(f"{GAP_PREFIX}{day}.json")
            except ValueError as exc:
                if "Missing candles" not in str(exc) and "No data in" not in str(exc):
                    raise
                record = {
                    "day_start":day,"date_utc":iso(day),
                    "state":"source_unavailable_on_last_check",
                    "source":"Delta Exchange India BTCUSD 1m",
                    "last_checked_utc":datetime.now(timezone.utc).isoformat(),
                    "diagnostic":str(exc),
                    "retryable":True,
                }
                client.upload_blob(name=f"{GAP_PREFIX}{day}.json",
                                   data=json.dumps(record,indent=2).encode(),
                                   overwrite=True)
                attempt["state"]="source_gap_recorded"
                attempt["diagnostic"]=str(exc)
            # All other failures propagate and are never marked as source gaps.
    except Exception as exc:
        fatal=f"{type(exc).__name__}: {exc}"
    # Report even on partial Azure / API failure. Do not mask errors.
    audit_error=None
    try:
        stored=inventory(client)
        gaps=gap_records(client)
        verified,missing=coverage(stored,start,end)
    except Exception as exc:
        audit_error=f"{type(exc).__name__}: {exc}"
        verified,missing,gaps=[],[(start,end)],{}
    unresolved=[{"date":iso(day),"diagnostic":gaps[day].get("diagnostic")}
                for day in sorted(gaps) if start <= day < end]
    result={
        "start":iso(start),"end_exclusive":iso(end),
        "verified_minutes":sum((hi-lo)//60 for lo,hi in verified),
        "expected_minutes":(end-start)//60,
        "missing_intervals":[[iso(lo),iso(hi)] for lo,hi in missing],
        "source_gap_days":unresolved,
        "fully_complete":not missing and not fatal and not audit_error,
        "attempts":attempts,"dry_run":not download,
        "error":fatal,"audit_error":audit_error,
    }
    path=Path(report)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2),flush=True)
    if fatal or audit_error:
        raise RuntimeError(f"Gap-aware collection stopped; report: {path}: {fatal or audit_error}")
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",default="2024-02-03")
    p.add_argument("--end",help="Exclusive UTC cutoff; defaults to today UTC")
    p.add_argument("--max-days",type=int,default=4)
    p.add_argument("--execute",action="store_true")
    p.add_argument("--retry-gaps",action="store_true")
    args=p.parse_args()
    end=args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    collect_days(epoch(args.start),epoch(end),storage_url(),"data/gap-aware",
                 max_days=args.max_days,download=args.execute,
                 retry_gaps=args.retry_gaps)


if __name__=="__main__":
    main()
