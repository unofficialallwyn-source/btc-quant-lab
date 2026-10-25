import pandas as pd
import pytest
from src.historical import validate, collect

def candles(start,end):
    return pd.DataFrame([dict(time=t,open=10.,high=11.,low=9.,close=10.,volume=2.) for t in range(start,end,60)])

def test_complete_and_gap():
    assert validate(candles(0,300),0,300)['rows']==5
    with pytest.raises(ValueError,match='Missing'):
        validate(candles(0,300).drop(index=2).reset_index(drop=True),0,300)

def test_resume(tmp_path):
    calls=[]
    def fetcher(symbol,resolution,start,end):
        calls.append(start)
        return {'result':candles(start,end+60).iloc[::-1].to_dict('records')}
    one=collect(fetcher,0,600,tmp_path,window_minutes=5)
    two=collect(fetcher,0,600,tmp_path,window_minutes=5)
    assert one==two and len(calls)==2
