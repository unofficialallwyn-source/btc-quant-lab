"""Assemble immutable, verified, gap-safe BTCUSD research segments from Azure.

Never fill missing candles. Segment boundaries require fresh strategy/indicator
state; the exported catalog is an input to a future backtesting engine.
"""
import argparse
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .blob_auth import client_from_url, storage_url
from .cloud_backfill import DAY, PREFIX, epoch, inventory
from .coverage_plan import coverage, iso
from .historical import FIELDS, validate
from .research_segments import segments


def build(client, start, end, destination):
    if start >= end or start % DAY or end % DAY:
        raise ValueError("Start and end must be aligned UTC days")
    dest = Path(destination)
    # Verify every manifest and referenced blob before relying on cloud coverage.
    manifests = inventory(client)
    selected = [m for m in manifests if m["start"] < end and m["end"] > start]
    if not selected:
        raise ValueError("No verified BTCUSD manifests in requested interval")
    frames = []
    source_manifest_names = []
    for entry in selected:
        name = entry["name"]
        parts = json.loads(client.get_blob_client(name).download_blob().readall())
        source_manifest_names.append(name)
        for part in parts:
            lo, hi = int(part["start"]), int(part["end_exclusive"])
            if hi <= start or lo >= end:
                continue
            blob = client.get_blob_client(f'{PREFIX}/{part["filename"]}')
            payload = blob.download_blob().readall()
            if hashlib.sha256(payload).hexdigest() != part["sha256"]:
                raise ValueError(f"Partition checksum changed: {part['filename']}")
            frame = pd.read_parquet(io.BytesIO(payload))
            validate(frame, lo, hi)
            frames.append(frame[(frame.time >= start) & (frame.time < end)])
    candles = pd.concat(frames, ignore_index=True).sort_values("time").reset_index(drop=True)
    if candles.empty:
        raise ValueError("No BTCUSD candles in selected range")
    duplicates = candles[candles.duplicated("time", keep=False)]
    if not duplicates.empty:
        for _, same_time in duplicates.groupby("time"):
            if not (same_time[FIELDS].nunique(dropna=False) == 1).all():
                raise ValueError("Conflicting overlapping verified BTCUSD candles")
        candles = candles.drop_duplicates("time").reset_index(drop=True)
    pieces = segments(candles)
    # Validate each continuous interval separately; never validate across gaps.
    for piece in pieces:
        validate(piece, int(piece.time.iloc[0]), int(piece.time.iloc[-1]) + 60)
    verified, missing = coverage(selected, start, end)
    expected = (end-start)//60
    if len(candles) != sum((hi-lo)//60 for lo,hi in verified):
        raise ValueError("Manifest-backed candle count disagrees with verified coverage")
    if sum(len(p) for p in pieces) != len(candles):
        raise ValueError("Segment counts do not add up")

    dest.mkdir(parents=True, exist_ok=True)
    segment_meta = []
    for idx, piece in enumerate(pieces, 1):
        lo,hi = int(piece.time.iloc[0]), int(piece.time.iloc[-1])+60
        filename = f"BTCUSD_1m_segment_{idx:03d}_{lo}_{hi}.parquet"
        target=dest/filename
        pending=dest/(filename+".pending")
        piece.to_parquet(pending,index=False)
        digest=hashlib.sha256(pending.read_bytes()).hexdigest()
        pending.replace(target)
        segment_meta.append({"segment_id":idx,"filename":filename,
            "start_utc":datetime.fromtimestamp(lo,timezone.utc).isoformat(),
            "end_exclusive_utc":datetime.fromtimestamp(hi,timezone.utc).isoformat(),
            "rows":len(piece),"sha256":digest})
    summary={
        "schema_version":1,"symbol":"BTCUSD","resolution":"1m",
        "start_utc":iso(start),"end_exclusive_utc":iso(end),
        "target_minutes":expected,"verified_minutes":len(candles),
        "coverage_pct":round(len(candles)/expected*100,4),
        "continuous_segments":len(pieces),
        "source_manifests":sorted(source_manifest_names),
        "missing_intervals_utc":[{"start":iso(lo),"end_exclusive":iso(hi)}
                                  for lo,hi in missing],
        "segments":segment_meta,
        "status":"complete" if not missing else "gap_safe_partial",
        "policy":"No missing bars synthesized; reset indicators and positions at segment boundaries",
    }
    report=dest/"dataset_catalog.json"
    pending=dest/"dataset_catalog.json.pending"
    pending.write_text(json.dumps(summary,indent=2)+"\n")
    pending.replace(report)
    return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",required=True)
    p.add_argument("--end",required=True)
    p.add_argument("--output-dir",default="data/research/gap-safe")
    args=p.parse_args()
    result=build(client_from_url(storage_url()),epoch(args.start),epoch(args.end),args.output_dir)
    print(json.dumps({k:v for k,v in result.items() if k not in ("segments","source_manifests")},indent=2))


if __name__=="__main__":
    main()
