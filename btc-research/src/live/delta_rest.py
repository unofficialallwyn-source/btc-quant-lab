"""Minimal signed REST client for Delta Exchange India (prod / testnet).

Signature (docs.delta.exchange): hex HMAC-SHA256(secret,
    method + timestamp + path + ('?' + query if query) + body), headers
api-key, timestamp (unix seconds), signature, User-Agent. Signatures expire
after ~5 s, so one is generated per request.

Mutating requests (orders, leverage) are NEVER retried automatically: a timeout
may still have executed on the exchange. Reconcile by reading state instead.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import requests

BASE_URLS = {
    "prod": "https://api.india.delta.exchange",
    "testnet": "https://cdn-ind.testnet.deltaex.org",
}


class DeltaError(RuntimeError):
    pass


def signature(secret, method, timestamp, path, query="", body=""):
    q = f"?{query}" if query else ""
    msg = f"{method}{timestamp}{path}{q}{body}"
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()


class DeltaRest:
    def __init__(self, env="testnet", api_key=None, api_secret=None, session=None, clock=time.time):
        if env not in BASE_URLS:
            raise ValueError("env must be prod or testnet")
        self.env, self.base = env, BASE_URLS[env]
        self.key, self.secret = api_key, api_secret
        self.session = session or requests.Session()
        self.clock = clock

    # ---- transport -------------------------------------------------------
    def _request(self, method, path, params=None, body=None, auth=False, retries=3):
        query = urlencode(params or {})
        payload = json.dumps(body, separators=(",", ":")) if body is not None else ""
        mutating = method in ("POST", "PUT", "DELETE")
        attempts = 1 if mutating else retries
        for attempt in range(attempts):
            headers = {"Accept": "application/json", "User-Agent": "btc-quant-lab/phase6"}
            if payload:
                headers["Content-Type"] = "application/json"
            if auth:
                if not (self.key and self.secret):
                    raise DeltaError("API key/secret required for private endpoint")
                ts = str(int(self.clock()))
                headers.update({"api-key": self.key, "timestamp": ts,
                                "signature": signature(self.secret, method, ts, path, query, payload)})
            url = self.base + path + (f"?{query}" if query else "")
            try:
                r = self.session.request(method, url, data=payload or None, headers=headers, timeout=20)
            except requests.RequestException as exc:
                if attempt == attempts - 1:
                    raise DeltaError(f"{method} {path} transport error: {exc}") from exc
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 429 and not mutating and attempt < attempts - 1:
                time.sleep(2 ** attempt)
                continue
            try:
                data = r.json()
            except ValueError:
                raise DeltaError(f"{method} {path}: HTTP {r.status_code} non-JSON response")
            if r.status_code >= 400 or data.get("success") is False:
                raise DeltaError(f"{method} {path}: HTTP {r.status_code} {data.get('error')}")
            return data.get("result")
        raise DeltaError(f"{method} {path}: retries exhausted")

    # ---- public ----------------------------------------------------------
    def product(self, symbol="BTCUSD"):
        return self._request("GET", f"/v2/products/{symbol}")

    def ticker(self, symbol="BTCUSD"):
        return self._request("GET", f"/v2/tickers/{symbol}")

    def candles(self, symbol, resolution, start, end):
        return self._request("GET", "/v2/history/candles",
                             {"symbol": symbol, "resolution": resolution, "start": start, "end": end})

    # ---- private ---------------------------------------------------------
    def position(self, product_id):
        return self._request("GET", "/v2/positions", {"product_id": product_id}, auth=True)

    def wallet(self):
        return self._request("GET", "/v2/wallet/balances", auth=True)

    def open_orders(self, product_id):
        return self._request("GET", "/v2/orders", {"product_ids": product_id, "states": "open"}, auth=True)

    def set_leverage(self, product_id, leverage):
        return self._request("POST", f"/v2/products/{product_id}/orders/leverage",
                             body={"leverage": str(leverage)}, auth=True)

    def place_order(self, product_id, side, size, order_type="market_order", limit_price=None,
                    reduce_only=False, post_only=False, client_order_id=None, time_in_force=None):
        if side not in ("buy", "sell") or int(size) <= 0:
            raise ValueError("Invalid side/size")
        body = {"product_id": int(product_id), "side": side, "size": int(size), "order_type": order_type,
                "reduce_only": bool(reduce_only)}
        if order_type == "limit_order":
            body["limit_price"] = str(limit_price)
            body["post_only"] = bool(post_only)
            if time_in_force:
                body["time_in_force"] = time_in_force
        if client_order_id:
            body["client_order_id"] = client_order_id[:32]
        return self._request("POST", "/v2/orders", body=body, auth=True)

    def cancel_order(self, product_id, order_id):
        return self._request("DELETE", "/v2/orders", body={"id": int(order_id), "product_id": int(product_id)},
                             auth=True)

    def cancel_all(self, product_id):
        return self._request("DELETE", "/v2/orders/all", body={"product_id": int(product_id)}, auth=True)
