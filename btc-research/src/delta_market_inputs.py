"""Strict auditable CSV observations required for Delta historical simulation.

Expected CSV files in input dir:
 mark_1m.csv: time,mark_usd (every simulated 1m bar)
 fx_1m.csv: time,inr_per_usd (every simulated 1m bar; independently sourced)
 funding_8h.csv: time,rate (settlement timestamps 00,08,16 UTC)
 source_manifest.json: source, recorded_utc, mark_source, fx_source,
                       funding_source, methodology (no synthetic or inferred)
"""
import json
from pathlib import Path
import pandas as pd


FILES={"mark":"mark_1m.csv","fx":"fx_1m.csv","funding":"funding_8h.csv"}
SCHEMA={"mark":"mark_usd","fx":"inr_per_usd","funding":"rate"}


def _csv(path,value_name,*,interval):
    frame=pd.read_csv(path)
    if list(frame.columns)!=["time",value_name]:
        raise ValueError(f"Incorrect schema for {path.name}")
    if frame.empty:
        raise ValueError(f"Empty observations: {path.name}")
    try:
        time=pd.to_numeric(frame.time,errors="raise")
        value=pd.to_numeric(frame[value_name],errors="raise")
    except Exception as exc:
        raise ValueError(f"Non-numeric observations: {path.name}") from exc
    if (time%interval!=0).any() or time.duplicated().any() or not time.is_monotonic_increasing:
        raise ValueError(f"Duplicate, unordered or misaligned timestamps: {path.name}")
    if not value.notna().all() or not __import__("numpy").isfinite(value).all():
        raise ValueError(f"Non-finite observations: {path.name}")
    if value_name!="rate" and (value<=0).any():
        raise ValueError(f"Nonpositive market inputs: {path.name}")
    if value_name=="rate" and (value.abs()>0.01).any():
        raise ValueError(f"Funding rate outside exchange cap: {path.name}")
    return pd.Series(value.to_numpy(dtype=float),index=time.to_numpy(dtype="int64"))


def load_inputs(folder):
    folder=Path(folder)
    manifest=json.loads((folder/"source_manifest.json").read_text())
    for name in ("mark_source","funding_source","methodology","recorded_utc"):
        if not str(manifest.get(name,"")).strip():
            raise ValueError(f"Missing historical-input provenance: {name}")
    if manifest.get("fx_policy")!="delta_india_fixed_85" and not str(manifest.get("fx_source","")).strip():
        raise ValueError("Missing historical-input provenance: fx_source")
    if manifest.get("synthetic",False):
        raise ValueError("Synthetic provenance forbidden for real historical validation")
    if manifest.get("methodology") in ("assumed_constant","inferred_from_traded_candles"):
        raise ValueError("Assumed FX/mark/funding inputs forbidden")
    mark=_csv(folder/FILES["mark"],SCHEMA["mark"],interval=60)
    if manifest.get("fx_policy")=="delta_india_fixed_85":
        if not manifest.get("fx_policy_reference") or not manifest.get("fx_policy_effective_period_verified"):
            raise ValueError("Fixed INR/USD policy requires an official source and historical period verification")
        # This is a policy conversion, not an observed spot-market FX series.
        fx=pd.Series(85.0,index=mark.index,dtype=float)
    else:
        fx=_csv(folder/FILES["fx"],SCHEMA["fx"],interval=60)
    funding=_csv(folder/FILES["funding"],SCHEMA["funding"],interval=28800)
    return manifest,mark,fx,funding.to_dict()


def coverage_report(segments,mark,fx,funding):
    expected=set()
    settlements=set()
    for s in segments:
        timestamps=list(s.time.astype("int64"))
        expected.update(timestamps)
        settlements.update(t for t in timestamps if t%28800==0)
    def missing(series):
        return sorted(expected.difference(series.index))
    # Conservative: require all possible settlement timestamps, even when no
    # strategy position is held. Data readiness independent of strategy.
    funding_missing=sorted(settlements.difference(funding))
    return {"required_1m_candles":len(expected),
        "missing_mark_minutes":len(missing(mark)),
        "missing_fx_minutes":len(missing(fx)),
        "missing_funding_settlements":len(funding_missing),
        "first_missing_mark":missing(mark)[:5],
        "first_missing_fx":missing(fx)[:5],
        "first_missing_funding":funding_missing[:5],
        "complete":not(missing(mark) or missing(fx) or funding_missing)}
