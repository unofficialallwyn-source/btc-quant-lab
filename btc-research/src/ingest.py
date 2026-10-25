import pandas as pd
COLUMNS = ['time','open','high','low','close','volume']

def fetch_candles(fetcher, symbol, start, end, resolution='1m', batch_size=3600):
    step={'1m':60,'5m':300,'15m':900}[resolution]
    rows=[]
    for t in range(start,end,batch_size*step):
        boundary=min(end,t+batch_size*step)
        result=fetcher(symbol=symbol,resolution=resolution,start=t,end=boundary-step)
        rows.extend(result.get('result',[]))
    if not rows: raise ValueError('No candles returned')
    return pd.DataFrame(rows,columns=COLUMNS).sort_values('time').drop_duplicates('time').reset_index(drop=True)

def audit(frame,interval=60):
    if frame.empty: raise ValueError('Empty data')
    d=frame.sort_values('time')
    gaps=d.time.diff().dropna()
    invalid=(d.low>d.high)|(d.open<d.low)|(d.open>d.high)|(d.close<d.low)|(d.close>d.high)|(d.volume<0)
    return dict(rows=len(d),duplicates=int(frame.time.duplicated().sum()),missing_intervals=int(((gaps/interval).clip(lower=1)-1).sum()),bad_ohlcv=int(invalid.sum()),misaligned=int((d.time%interval!=0).sum()))

def resample(frame,minutes):
    x=frame.copy()
    x.index=pd.to_datetime(x.time,unit='s',utc=True)
    g=x.resample(f'{minutes}min',label='left',closed='left')
    y=g.agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
    return y.loc[g.close.count()==minutes].dropna().reset_index()
