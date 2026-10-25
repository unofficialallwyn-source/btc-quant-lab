"""Public, read-only Delta India market-data adapter."""
import time
import requests

API_URL = 'https://api.india.delta.exchange/v2/history/candles'

def fetch_candles(*, symbol, resolution, start, end, session=None, retries=4):
    if symbol != 'BTCUSD' or resolution != '1m':
        raise ValueError('BTCUSD 1m only for this research pipeline')
    if end < start or (end-start)//60 + 1 > 1800:
        raise ValueError('Request must contain 1..1800 candles')
    client = session or requests.Session()
    for attempt in range(retries):
        try:
            r = client.get(API_URL, params={'symbol':symbol,'resolution':resolution,'start':start,'end':end},headers={'Accept':'application/json'},timeout=25)
            r.raise_for_status()
            body=r.json()
            if not isinstance(body,dict) or not isinstance(body.get('result'),list):
                raise ValueError('Unexpected Delta response')
            return body
        except (requests.RequestException,ValueError):
            if attempt == retries-1: raise
            time.sleep(min(2**attempt,8))
