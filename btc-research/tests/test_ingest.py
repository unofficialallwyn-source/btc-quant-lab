import pandas as pd
from src.ingest import audit,resample,fetch_candles

def test_resample():
    rows=[dict(time=i*60,open=10+i,high=11+i,low=9+i,close=10.5+i,volume=2) for i in range(10)]
    d=pd.DataFrame(rows)
    assert audit(d)['missing_intervals']==0
    b=resample(d,5)
    assert len(b)==2 and b.iloc[0].volume==10 and b.iloc[0].close==14.5

def test_gap():
    d=pd.DataFrame([dict(time=t,open=1,high=2,low=1,close=1,volume=1) for t in [0,120]])
    assert audit(d)['missing_intervals']==1

def test_fetch():
    def f(symbol,resolution,start,end):
        return {'result':[dict(time=t,open=1,high=1,low=1,close=1,volume=1) for t in range(start,end+1,60)]}
    assert len(fetch_candles(f,'BTCUSD',0,600,batch_size=3))==10
