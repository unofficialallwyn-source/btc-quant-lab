"""Build one auditable BTCUSD 1m research dataset from verified Azure manifests."""
import argparse
import io
import json
from pathlib import Path

import pandas as pd

from .blob_auth import client_from_url, storage_url
from .cloud_backfill import PREFIX, inventory, epoch
from .coverage_plan import coverage, iso

COLUMNS = ("time", "open", "high", "low", "close", "volume")


def assemble(client, start, end, destination):
    if end <= start or start % 86400 or end % 86400:
        raise ValueError("Use UTC day-aligned dates")
    # This inventory verifies every blob SHA256 before treating its manifest as valid.
    manifests = inventory(client)
    verified, missing = coverage(manifests, start, end)
    if missing:
        raise ValueError("Unverified or missing coverage: " + str([(iso(a), iso(b)) for a,b in missing]))
    frames = []
    # Read exact manifests; reuse their checksummed partitions, never glob unverified files.
    for item in manifests:
        if item["start"] >= end or item["end"] <= start:
            continue
        manifest = json.loads(client.get_blob_client(item["name"]).download_blob().readall())
        for part in manifest:
            lo, hi = int(part["start"]), int(part["end_exclusive"])
            if lo >= end or hi <= start:
                continue
            blob = client.get_blob_client(f'{PREFIX}/{part["filename"]}')
            import hashlib
            data = blob.download_blob().readall()
            if hashlib.sha256(data).hexdigest() != part["sha256"]:
                raise ValueError("Partition hash changed while assembling research dataset")
            frame = pd.read_parquet(io.BytesIO(data))
            if list(frame.columns) != list(COLUMNS):
                raise ValueError("Unexpected candle columns")
            frames.append(frame[(frame.time >= start) & (frame.time < end)])
    if not frames:
        raise ValueError("No matching manifest-backed candles")
    candles = pd.concat(frames, ignore_index=True).sort_values("time").reset_index(drop=True)
    # Adjacent manifests may have identical data, but conflicting duplicates are never trusted.
    duplicate = candles[candles.duplicated("time", keep=False)]
    if not duplicate.empty:
        for _, rows in duplicate.groupby("time"):
            if not (rows[list(COLUMNS)].nunique(dropna=False) == 1).all():
                raise ValueError("Conflicting duplicate BTC candles")
        candles = candles.drop_duplicates("time").reset_index(drop=True)
    from .historical import validate
    validate(candles, start, end)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(".pending.parquet")
    candles.to_parquet(tmp, index=False)
    tmp.replace(destination)
    summary = {"symbol": "BTCUSD", "resolution": "1m", "start": iso(start),
               "end_exclusive": iso(end), "candles": len(candles),
               "verified_manifests": len(manifests), "status": "complete"}
    destination.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", default="data/research/BTCUSD_1m_verified.parquet")
    args = parser.parse_args()
    print(json.dumps(assemble(client_from_url(storage_url()), epoch(args.start), epoch(args.end), args.output), indent=2))


if __name__ == "__main__":
    main()
