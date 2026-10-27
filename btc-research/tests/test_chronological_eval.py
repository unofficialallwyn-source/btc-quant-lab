import hashlib
import json
from datetime import datetime, timezone

import pandas as pd
import pytest

from src.chronological_eval import boundaries, evaluate


DAY=86400


def write_dataset(root, start, dates):
    root.mkdir()
    parts=[]
    for i,day in enumerate(dates):
        frame=pd.DataFrame({"time":[day+j*60 for j in range(1440)],
            "open":[100.]*1440,"high":[101.]*1440,"low":[99.]*1440,
            "close":[100.]*1440,"volume":[1.]*1440})
        name=f"segment_{i}.parquet"
        path=root/name
        frame.to_parquet(path,index=False)
        utc=lambda x:datetime.fromtimestamp(x,timezone.utc).isoformat()
        parts.append({"filename":name,"rows":1440,
            "start_utc":utc(day),"end_exclusive_utc":utc(day+DAY),
            "sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    (root/"dataset_catalog.json").write_text(json.dumps({
        "symbol":"BTCUSD","resolution":"1m",
        "start_utc":datetime.fromtimestamp(start,timezone.utc).strftime("%Y-%m-%d"),
        "end_exclusive_utc":datetime.fromtimestamp(start+10*DAY,timezone.utc).strftime("%Y-%m-%d"),
        "segments":parts}))


def test_boundaries_use_calendar_not_available_candles():
    start=20000*DAY
    b=boundaries(start,start+10*DAY)
    assert b["training"]==(start,start+6*DAY)
    assert b["validation"]==(start+6*DAY,start+8*DAY)
    assert b["holdout"]==(start+8*DAY,start+10*DAY)


def test_holdout_locked_and_gap_safe(tmp_path):
    start=20000*DAY
    folder=tmp_path/"data"
    write_dataset(folder,start,[start,start+2*DAY,start+6*DAY,start+9*DAY])
    r=evaluate(folder,tmp_path/"out")
    assert not r["holdout_evaluated"]
    assert r["results"]["holdout"]["status"]=="locked"
    assert r["results"]["training"]["verified_candles"]==2880
    assert r["results"]["training"]["segments"]==2
    assert r["results"]["validation"]["verified_candles"]==1440
    assert not (tmp_path/"out"/"holdout_trades.csv").exists()
    r2=evaluate(folder,tmp_path/"final",include_holdout=True)
    assert r2["results"]["holdout"]["verified_candles"]==1440


def test_reject_corrupted_segment(tmp_path):
    start=20000*DAY
    folder=tmp_path/"data"
    write_dataset(folder,start,[start])
    (folder/"segment_0.parquet").write_bytes(b"tampered")
    with pytest.raises(ValueError,match="SHA256"):
        evaluate(folder,tmp_path/"out")


def test_invalid_split_fails():
    with pytest.raises(ValueError):
        boundaries(0,10*DAY,.9,.2)
