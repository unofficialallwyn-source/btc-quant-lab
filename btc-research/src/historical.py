"""Resumable BTCUSD 1-minute OHLCV ingestion into audited Parquet partitions."""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

FIELDS = ['time', 'open', 'high', 'low', 'close', 'volume']

def gap_diagnostics(frame, start, end):
    expected = set(range(start, end, 60))
    actual = set(int(x) for x in frame.time) if 'time' in frame.columns else set()
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    def utc(t):
        return datetime.fromtimestamp(t, timezone.utc).isoformat()
    return {'expected': (end-start)//60, 'received': len(frame),
            'missing_count': len(missing),
            'first_missing_utc': utc(missing[0]) if missing else None,
            'missing_samples_utc': [utc(t) for t in missing[:8]],
            'unexpected_count': len(extra)}


def validate(frame, start, end):
    """Validate complete, half-open UTC interval [start,end) at 1m resolution."""
    if end <= start or start % 60 or end % 60:
        raise ValueError('Unaligned or invalid UTC interval')
    if list(frame.columns) != FIELDS or frame.empty:
        raise ValueError('Invalid columns or empty candles')
    if frame.isna().any().any():
        raise ValueError('Null candle values')
    times = frame.time.astype('int64')
    if times.duplicated().any() or not times.is_monotonic_increasing:
        raise ValueError('Duplicate or unsorted candles')
    if times.iloc[0] != start or times.iloc[-1] != end - 60 or (times.diff().dropna() != 60).any() or len(frame) != (end-start)//60:
        raise ValueError('Missing candles: ' + json.dumps(gap_diagnostics(frame,start,end),sort_keys=True))
    for key in FIELDS[1:]:
        if not pd.api.types.is_numeric_dtype(frame[key]):
            raise ValueError('Non-numeric OHLCV')
    if ((frame.low<=0)|(frame.high<frame.low)|(frame.open<frame.low)|(frame.open>frame.high)|(frame.close<frame.low)|(frame.close>frame.high)|(frame.volume<0)).any():
        raise ValueError('Invalid OHLCV range or volume')
    return {'rows':len(frame),'start':start,'end_exclusive':end,'gaps':0,'duplicates':0}

def collect(fetcher, start, end, directory, symbol='BTCUSD', window_minutes=3600, incomplete_retries=3):
    """Call supplied Delta-compatible fetcher in bounded windows; validate before saving."""
    if not 1 <= window_minutes <= 3600: raise ValueError('window_minutes must be 1..3600')
    if not 1 <= incomplete_retries <= 5: raise ValueError('incomplete_retries must be 1..5')
    if start % 60 or end % 60 or end <= start: raise ValueError('Invalid range')
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for lo in range(start,end,window_minutes*60):
        hi=min(end,lo+window_minutes*60)
        file=directory/f'{symbol}_1m_{lo}_{hi}.parquet'
        if file.exists():
            df=pd.read_parquet(file)
        else:
            for attempt in range(incomplete_retries):
                result=fetcher(symbol=symbol,resolution='1m',start=lo,end=hi-60)
                df=pd.DataFrame(result.get('result',[]))
                if df.empty:
                    detail={'expected':(hi-lo)//60,'received':0,
                            'first_missing_utc':datetime.fromtimestamp(lo,timezone.utc).isoformat()}
                    error=ValueError('Missing candles: ' + json.dumps(detail,sort_keys=True))
                else:
                    df=df[FIELDS].sort_values('time').reset_index(drop=True)
                    try:
                        info=validate(df,lo,hi)
                        break
                    except ValueError as exc:
                        if 'Missing candles' not in str(exc): raise
                        error=exc
                if attempt==incomplete_retries-1: raise error
                time.sleep(min(2**attempt,4))
        info=validate(df,lo,hi)
        if not file.exists():
            temp=file.with_suffix('.pending.parquet')
            df.to_parquet(temp,index=False)
            temp.replace(file)
        manifest.append({'symbol':symbol,'resolution':'1m',**info,'filename':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    (directory/f'{symbol}_1m_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest
