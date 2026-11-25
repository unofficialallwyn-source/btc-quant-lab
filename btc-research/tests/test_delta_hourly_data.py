import pandas as pd

from src import delta_hourly_data as d


class Resp:
    def __init__(self, body, code=200):
        self.body, self.status_code = body, code

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


class Session:
    def __init__(self):
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append(params)
        lo, hi = params["start"], params["end"]
        # newest-first, like the exchange, plus an out-of-window candle that must be ignored
        res = [{"time": t, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 3}
               for t in range(hi - 3600, lo - 3600, -3600)] + [{"time": hi, "open": 9, "high": 9, "low": 9, "close": 9}]
        return Resp({"success": True, "result": res})


def test_fetch_paginates_sorted_and_bounded():
    s = Session()
    start = 1_700_000_000 // 3600 * 3600
    df = d.fetch("BTCUSD", start, start + 3600 * 4000, session=s, sleep=0)
    assert len(s.calls) == 3 and len(df) == 4000
    assert df.time.is_monotonic_increasing and df.time.iloc[0] == start


def test_funding_units_inferred_and_sampled():
    t = 28800 * 100
    raw = pd.DataFrame({"time": [t, t + 3600, t + 28800], "close": [0.01, 0.02, -0.01]})
    f, units = d.funding_from_candles(raw)
    assert list(f.time) == [t, t + 28800]
    assert units == "percent->decimal" and f.rate.iloc[0] == 0.0001
