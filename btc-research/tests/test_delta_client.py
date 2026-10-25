from src.delta_client import fetch_candles
from src.backfill import utc_epoch
import pytest

class MockResponse:
    def raise_for_status(self): pass
    def json(self): return {'result':[{'time':0,'open':1,'high':1,'low':1,'close':1,'volume':1}]}
class MockSession:
    def get(self,url,params,headers,timeout):
        assert params == {'symbol':'BTCUSD','resolution':'1m','start':0,'end':60}
        assert url.startswith('https://api.india.delta.exchange/')
        return MockResponse()

def test_public_delta_client():
    assert fetch_candles(symbol='BTCUSD',resolution='1m',start=0,end=60,session=MockSession())['result'][0]['time']==0

def test_request_size():
    with pytest.raises(ValueError):
        fetch_candles(symbol='BTCUSD',resolution='1m',start=0,end=120000,session=MockSession())

def test_utc():
    assert utc_epoch('2025-07-01')==1751328000
