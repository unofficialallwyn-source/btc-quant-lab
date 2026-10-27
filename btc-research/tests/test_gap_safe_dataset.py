"""Gap-safe exported research data never crosses unverified UTC intervals."""
import hashlib
import io
import json
from types import SimpleNamespace

import pandas as pd
import pytest

from src.cloud_backfill import DAY, PREFIX
from src.gap_safe_dataset import build


def client_with_days(days):
    blobs={}
    manifests=[]
    for day in days:
        frame=pd.DataFrame({
            "time":[day+i*60 for i in range(1440)],
            "open":[100.]*1440,"high":[101.]*1440,"low":[99.]*1440,
            "close":[100.]*1440,"volume":[1.]*1440,
        })
        raw=io.BytesIO()
        frame.to_parquet(raw,index=False)
        payload=raw.getvalue()
        filename=f"BTCUSD_1m_{day}_{day+DAY}.parquet"
        name=f"{PREFIX}/manifests/BTCUSD_1m_{day}_{day+DAY}.json"
        blobs[f"{PREFIX}/{filename}"]=payload
        blobs[name]=json.dumps([{
            "start":day,"end_exclusive":day+DAY,"rows":1440,
            "filename":filename,"sha256":hashlib.sha256(payload).hexdigest(),
        }]).encode()
        manifests.append(name)
    class Client:
        def list_blobs(self,name_starts_with):
            return [SimpleNamespace(name=n) for n in manifests
                    if n.startswith(name_starts_with)]
        def get_blob_client(self,name):
            return SimpleNamespace(download_blob=lambda:
                SimpleNamespace(readall=lambda:blobs[name]))
    return Client(), blobs


def test_gap_safe_export_keeps_gap_and_checksums(tmp_path):
    start=DAY*20000
    client,_=client_with_days([start,start+2*DAY])
    result=build(client,start,start+3*DAY,tmp_path/"research")
    assert result["status"]=="gap_safe_partial"
    assert result["verified_minutes"]==2880
    assert result["target_minutes"]==4320
    assert result["continuous_segments"]==2
    assert len(result["missing_intervals_utc"])==1
    for part in result["segments"]:
        p=tmp_path/"research"/part["filename"]
        frame=pd.read_parquet(p)
        assert len(frame)==1440
        assert hashlib.sha256(p.read_bytes()).hexdigest()==part["sha256"]
    assert json.loads((tmp_path/"research"/"dataset_catalog.json").read_text())["verified_minutes"]==2880


def test_contiguous_days_produce_one_segment(tmp_path):
    start=DAY*20000
    client,_=client_with_days([start,start+DAY])
    result=build(client,start,start+2*DAY,tmp_path/"complete")
    assert result["status"]=="complete"
    assert result["continuous_segments"]==1
    assert result["segments"][0]["rows"]==2880


def test_reject_partition_tamper(tmp_path):
    start=DAY*20000
    client,blobs=client_with_days([start])
    path=next(p for p in blobs if p.endswith(".parquet"))
    blobs[path]=b"tampered"
    with pytest.raises(RuntimeError,match="SHA mismatch"):
        build(client,start,start+DAY,tmp_path/"bad")


def test_reject_missing_all_data(tmp_path):
    client,_=client_with_days([])
    with pytest.raises(ValueError,match="No verified"):
        build(client,DAY,2*DAY,tmp_path/"none")
