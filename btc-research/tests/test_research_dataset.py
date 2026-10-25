"""Dataset validation against manifest-backed fake Azure blobs."""
import io
import json
import hashlib
from types import SimpleNamespace
import pandas as pd
import pytest
from src.research_dataset import assemble
from src.cloud_backfill import DAY, PREFIX

def test_assemble_verified_one_day(monkeypatch,tmp_path):
    start=DAY*20000
    rows=1440
    frame=pd.DataFrame({"time":[start+i*60 for i in range(rows)],
        "open":[100.]*rows,"high":[101.]*rows,"low":[99.]*rows,
        "close":[100.]*rows,"volume":[1.]*rows})
    buf=io.BytesIO()
    frame.to_parquet(buf,index=False)
    data=buf.getvalue()
    filename=f"BTCUSD_1m_{start}_{start+DAY}.parquet"
    manifest=[dict(start=start,end_exclusive=start+DAY,rows=rows,filename=filename,
                   sha256=hashlib.sha256(data).hexdigest())]
    manifest_name=f"{PREFIX}/manifests/test.json"
    blobs={manifest_name:json.dumps(manifest).encode(),f"{PREFIX}/{filename}":data}
    class Client:
        def list_blobs(self,name_starts_with):
            return [SimpleNamespace(name=manifest_name)]
        def get_blob_client(self,name):
            payload=blobs[name]
            return SimpleNamespace(download_blob=lambda:SimpleNamespace(readall=lambda:payload))
    # inventory integrity and report must both work against the supplied client
    path=tmp_path/"BTCUSD_1m_verified.parquet"
    result=assemble(Client(),start,start+DAY,path)
    assert result["candles"]==1440
    assert len(pd.read_parquet(path))==1440
    assert json.loads(path.with_suffix(".json").read_text())["status"]=="complete"

def test_reject_unverified_gap(tmp_path):
    class Empty:
        def list_blobs(self,name_starts_with):
            return []
    with pytest.raises(ValueError,match="missing coverage"):
        assemble(Empty(),DAY,2*DAY,tmp_path/"missing.parquet")
