import hashlib
import hmac
import json

import numpy as np
import pytest

from src.live.delta_rest import DeltaRest, signature
from src.live import trader as tr


def test_signature_matches_documented_prehash():
    sig = signature("secret", "POST", "1700000000", "/v2/orders", "", '{"size":1}')
    expect = hmac.new(b"secret", b'POST1700000000/v2/orders{"size":1}', hashlib.sha256).hexdigest()
    assert sig == expect
    q = signature("s", "GET", "1", "/v2/positions", "product_id=27")
    assert q == hmac.new(b"s", b"GET1/v2/positions?product_id=27", hashlib.sha256).hexdigest()


class FakeResp:
    status_code = 200
    def __init__(self, body): self.body = body
    def json(self): return self.body


class RecordingSession:
    def __init__(self): self.calls = []
    def request(self, method, url, data=None, headers=None, timeout=None):
        self.calls.append((method, url, data, headers))
        return FakeResp({"success": True, "result": {"id": 1}})


def test_private_request_headers_and_no_retry_flag():
    s = RecordingSession()
    c = DeltaRest("testnet", "k", "sec", session=s, clock=lambda: 1700000000)
    c.place_order(27, "buy", 3, reduce_only=True, client_order_id="abc")
    method, url, data, headers = s.calls[0]
    assert url == "https://cdn-ind.testnet.deltaex.org/v2/orders" and method == "POST"
    assert headers["api-key"] == "k" and headers["timestamp"] == "1700000000"
    assert headers["signature"] == signature("sec", "POST", "1700000000", "/v2/orders", "", data)
    assert json.loads(data) == {"product_id": 27, "side": "buy", "size": 3, "order_type": "market_order",
                                "reduce_only": True, "client_order_id": "abc"}


class FakeData:
    """Deterministic uptrend hourly candles ending at the clock's current hour."""
    def __init__(self, clock, drift=0.0004):
        self.clock, self.drift = clock, drift
    def candles(self, symbol, resolution, start, end):
        out = []
        for t in range(start, end, 3600):
            k = (t - (self.clock() - 3600 * 24 * 400)) / 3600
            c = 30000 * np.exp(self.drift * k + 0.01 * np.sin(k / 7))
            out.append({"time": t, "open": c, "high": c * 1.001, "low": c * 0.999, "close": c})
        return out
    def product(self, symbol): return {"id": 27}


def make(tmp_path, now, **kw):
    clock = lambda: now[0]
    cfg = tr.TraderConfig(state_dir=str(tmp_path), **kw)
    return tr.Trader(cfg, FakeData(clock), clock=clock)


def test_paper_trader_goes_long_in_uptrend_idempotent_and_kill(tmp_path):
    now = [1_720_000_000 // 3600 * 3600 + 120]
    t = make(tmp_path, now, capital_usd=10000)
    r = t.step()
    assert r["event"] == "DECISION" and r["forecast"] > 0 and r["target"] > 0
    assert t.step()["event"] == "ALREADY_PROCESSED"
    now[0] += 3600
    assert t.step()["event"] == "DECISION"
    (tmp_path / "KILL").write_text("stop")
    assert t.step()["event"] == "KILLED"
    assert t.load_state()["position"] == 0


def test_stale_data_refused(tmp_path):
    now = [1_720_000_000 // 3600 * 3600 + 120]
    t = make(tmp_path, now)
    t.data.candles = lambda *a: FakeData(lambda: 0).candles(a[0], a[1], a[2], a[3] - 4 * 3600)
    assert t.step()["event"] == "STALE_DATA"


def test_live_requires_confirmation(monkeypatch, tmp_path):
    monkeypatch.delenv("DELTA_LIVE_CONFIRM", raising=False)
    with pytest.raises(PermissionError):
        tr.TraderConfig(mode="live", state_dir=str(tmp_path)).validate()


def test_order_size_and_contract_caps(tmp_path):
    now = [1_720_000_000 // 3600 * 3600 + 120]
    t = make(tmp_path, now, capital_usd=1_000_000, max_contracts=7, max_order_contracts=3)
    r = t.step()
    assert r["target"] == 7 and r["order"] == 3
