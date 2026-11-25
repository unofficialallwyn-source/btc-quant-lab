"""Phase 6 execution agent: reconcile the account to the strategy's target position.

One decision per completed UTC hour, using exactly the research code path
(`trend_carry.forecasts` -> `ideal_contracts` -> `buffered_target`).

Modes
  paper   : no keys, simulated fills, state in a JSON file (default)
  testnet : real orders on Delta India testnet (demo) keys
  live    : real money; refused unless DELTA_LIVE_CONFIRM=I_ACCEPT_REAL_MONEY_RISK

Signals always come from PRODUCTION public candles (testnet prices are not a
market). Hard guards: kill-switch file, stale-data refusal, max contracts, max
order size, leverage cap, daily-loss lock (reduce-only), idempotent per bar,
every decision journaled as JSON lines.
"""
import argparse
from dataclasses import dataclass, asdict
import json
import math
import os
from pathlib import Path
import time

import numpy as np
import pandas as pd

from ..trend_carry import TrendCarrySpec, forecasts, ideal_contracts, buffered_target
from ..phase6_research import PRIMARY
from .delta_rest import DeltaRest, DeltaError

LIVE_CONFIRM = "I_ACCEPT_REAL_MONEY_RISK"


@dataclass
class TraderConfig:
    mode: str = "paper"
    symbol: str = "BTCUSD"
    capital_usd: float = 1000.0
    max_contracts: int = 50
    max_order_contracts: int = 20
    max_leverage: float = 2.0
    daily_loss_limit: float = 0.05
    stale_after_seconds: int = 2 * 3600
    history_hours: int = 24 * 300
    execution: str = "market"          # market | maker_first
    maker_wait_seconds: int = 60
    paper_fee: float = 0.0005 * 1.18
    paper_slippage: float = 0.00025
    inr_per_usd: float = 85.0
    flatten_on_kill: bool = True
    state_dir: str = "state"

    def validate(self):
        if self.mode not in ("paper", "testnet", "live"):
            raise ValueError("mode must be paper, testnet or live")
        if self.mode == "live" and os.environ.get("DELTA_LIVE_CONFIRM") != LIVE_CONFIRM:
            raise PermissionError(f"Live trading refused: set DELTA_LIVE_CONFIRM={LIVE_CONFIRM}")
        if self.capital_usd <= 0 or self.max_contracts < 1 or self.max_order_contracts < 1:
            raise ValueError("Invalid capital or contract limits")
        if self.execution not in ("market", "maker_first"):
            raise ValueError("Invalid execution style")


def fetch_hourly(rest, symbol, start, end):
    rows = {}
    for lo in range(start, end, 3600 * 1900):
        hi = min(lo + 3600 * 1900, end)
        for c in rest.candles(symbol, "1h", lo, hi) or []:
            t = int(c["time"])
            if lo <= t < hi:
                rows[t] = {k: float(c[k]) for k in ("open", "high", "low", "close")} | {"time": t}
    return pd.DataFrame([rows[t] for t in sorted(rows)])


class Trader:
    def __init__(self, cfg, data_rest, trade_rest=None, spec=PRIMARY, clock=time.time, sleep=time.sleep):
        cfg.validate()
        if cfg.mode != "paper" and trade_rest is None:
            raise ValueError("trade_rest required for testnet/live")
        self.cfg, self.data, self.ex, self.spec = cfg, data_rest, trade_rest, spec
        self.clock, self.sleep = clock, sleep
        self.dir = Path(cfg.state_dir); self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / f"{cfg.mode}_state.json"
        self.journal_path = self.dir / f"{cfg.mode}_journal.jsonl"
        self.kill_path = self.dir / "KILL"
        self.product_id = None

    # ---- persistence ------------------------------------------------------
    def load_state(self):
        if self.state_path.exists():
            return json.loads(self.state_path.read_text())
        return {"position": 0, "equity": self.cfg.capital_usd, "last_price": None, "last_bar": None,
                "day": None, "day_start_equity": None}

    def save_state(self, s):
        tmp = self.state_path.with_suffix(".tmp"); tmp.write_text(json.dumps(s, indent=2)); tmp.replace(self.state_path)

    def journal(self, event, **kw):
        rec = {"ts": int(self.clock()), "mode": self.cfg.mode, "event": event, **kw}
        with self.journal_path.open("a") as fh:
            fh.write(json.dumps(rec, default=float) + "\n")
        return rec

    # ---- account ----------------------------------------------------------
    def pid(self):
        if self.product_id is None:
            self.product_id = int((self.ex or self.data).product(self.cfg.symbol)["id"])
        return self.product_id

    def exchange_position(self):
        p = self.ex.position(self.pid()) or {}
        return int(p.get("size") or 0)

    def exchange_equity_usd(self):
        bal = self.ex.wallet() or []
        by = {b.get("asset_symbol"): b for b in bal}
        if "USD" in by:
            return float(by["USD"].get("balance") or 0)
        if "INR" in by:
            return float(by["INR"].get("balance") or 0) / self.cfg.inr_per_usd
        raise DeltaError("No USD/INR wallet balance found")

    # ---- decision ---------------------------------------------------------
    def step(self):
        cfg, now = self.cfg, int(self.clock())
        s = self.load_state()
        if self.kill_path.exists():
            if cfg.flatten_on_kill:
                pos = s["position"] if cfg.mode == "paper" else self.exchange_position()
                if pos:
                    self.execute(-pos, s, price=s.get("last_price"), reason="kill_switch")
                    self.save_state(s)
            return self.journal("KILLED", note="kill switch file present; no new risk")
        end = now // 3600 * 3600
        frame = fetch_hourly(self.data, cfg.symbol, end - cfg.history_hours * 3600, end)
        if frame.empty:
            return self.journal("NO_DATA")
        frame = frame[frame.time + 3600 <= now].reset_index(drop=True)
        last_close_time = int(frame.time.iloc[-1]) + 3600
        if now - last_close_time > cfg.stale_after_seconds:
            return self.journal("STALE_DATA", last_close_time=last_close_time)
        bar = int(frame.time.iloc[-1])
        if s.get("last_bar") == bar:
            return self.journal("ALREADY_PROCESSED", bar=bar)
        fc = forecasts(frame, self.spec)
        forecast, vol, price = float(fc.forecast.iloc[-1]), float(fc.ann_vol.iloc[-1]), float(fc.close.iloc[-1])
        # mark paper book
        if cfg.mode == "paper":
            if s["last_price"] is not None and s["position"]:
                s["equity"] += s["position"] * self.spec.contract_btc * (price - s["last_price"])
            equity, pos = s["equity"], int(s["position"])
        else:
            equity = min(cfg.capital_usd, self.exchange_equity_usd())
            pos = self.exchange_position()
        s["last_price"] = price
        day = time.strftime("%Y-%m-%d", time.gmtime(now))
        if s.get("day") != day:
            s["day"], s["day_start_equity"] = day, equity
        locked = equity < s["day_start_equity"] * (1 - cfg.daily_loss_limit)
        if not np.isfinite(forecast):
            s["last_bar"] = bar; self.save_state(s)
            return self.journal("WARMUP", bar=bar)
        ideal = ideal_contracts(forecast, price, vol, equity, self.spec)
        target = buffered_target(pos, ideal, price, vol, equity, self.spec)
        lev_cap = int(cfg.max_leverage * equity / (price * self.spec.contract_btc))
        target = max(-min(cfg.max_contracts, lev_cap), min(min(cfg.max_contracts, lev_cap), target))
        if locked:  # reduce-only: never increase or flip exposure
            target = 0 if (target * pos <= 0) else (target if abs(target) < abs(pos) else pos)
        delta = target - pos
        delta = int(math.copysign(min(abs(delta), cfg.max_order_contracts), delta)) if delta else 0
        rec = dict(bar=bar, price=price, forecast=forecast, ann_vol=vol, equity_usd=equity,
                   ideal=ideal, target=target, position=pos, order=delta, daily_lock=locked)
        if delta:
            rec["fills"] = self.execute(delta, s, price=price, reason="rebalance")
        s["last_bar"] = bar
        self.save_state(s)
        return self.journal("DECISION", **rec)

    # ---- execution --------------------------------------------------------
    def execute(self, delta, s, price, reason):
        pos = int(s["position"]) if self.cfg.mode == "paper" else self.exchange_position()
        legs = []
        if pos and delta and (pos + delta) * pos < 0:   # crossing zero: close, then open
            legs = [(-pos, True), (pos + delta, False)]
        else:
            legs = [(delta, bool(pos) and abs(pos + delta) < abs(pos))]
        fills = []
        for qty, reduce_only in legs:
            if not qty:
                continue
            if self.cfg.mode == "paper":
                cost = abs(qty) * self.spec.contract_btc * price * (self.cfg.paper_fee + self.cfg.paper_slippage)
                s["equity"] -= cost; s["position"] = int(s["position"]) + qty
                fills.append({"qty": qty, "price": price, "cost_usd": cost, "reduce_only": reduce_only})
            else:
                fills.append(self._exchange_order(qty, reduce_only, reason))
        if self.cfg.mode != "paper":
            s["position"] = self.exchange_position()
        return fills

    def _exchange_order(self, qty, reduce_only, reason):
        side = "buy" if qty > 0 else "sell"
        size = abs(int(qty))
        cid = f"p6{int(self.clock())}{side[0]}{size}"
        if self.cfg.execution == "maker_first":
            q = (self.ex.ticker(self.cfg.symbol) or {}).get("quotes") or {}
            px = q.get("best_bid") if side == "buy" else q.get("best_ask")
            if px:
                o = self.ex.place_order(self.pid(), side, size, "limit_order", limit_price=px, post_only=True,
                                        reduce_only=reduce_only, client_order_id=cid + "m")
                self.sleep(self.cfg.maker_wait_seconds)
                unfilled = size
                try:
                    c = self.ex.cancel_order(self.pid(), o["id"])
                    unfilled = int(c.get("unfilled_size", 0))
                except DeltaError:  # already filled / closed
                    unfilled = 0
                filled = size - unfilled
                if unfilled <= 0:
                    return {"qty": qty, "maker_filled": filled, "reduce_only": reduce_only, "reason": reason}
                m = self.ex.place_order(self.pid(), side, unfilled, "market_order", reduce_only=reduce_only,
                                        client_order_id=cid + "t")
                return {"qty": qty, "maker_filled": filled, "taker_order": m.get("id"), "reduce_only": reduce_only}
        m = self.ex.place_order(self.pid(), side, size, "market_order", reduce_only=reduce_only, client_order_id=cid)
        return {"qty": qty, "order_id": m.get("id"), "avg_fill_price": m.get("average_fill_price"),
                "reduce_only": reduce_only, "reason": reason}


def main(argv=None):
    p = argparse.ArgumentParser(description="Phase 6 BTCUSD perp trader (paper by default)")
    p.add_argument("--mode", choices=["paper", "testnet", "live"], default="paper")
    p.add_argument("--capital-usd", type=float, default=1000.0)
    p.add_argument("--max-contracts", type=int, default=50)
    p.add_argument("--max-order-contracts", type=int, default=20)
    p.add_argument("--execution", choices=["market", "maker_first"], default="market")
    p.add_argument("--state-dir", default="state")
    p.add_argument("--exchange-leverage", type=int, default=None,
                   help="optionally set Delta order leverage once at start (e.g. 5 = ~20%% adverse move to liquidation)")
    p.add_argument("--loop", action="store_true", help="run every hour (+45s) until killed")
    a = p.parse_args(argv)
    cfg = TraderConfig(mode=a.mode, capital_usd=a.capital_usd, max_contracts=a.max_contracts,
                       max_order_contracts=a.max_order_contracts, execution=a.execution, state_dir=a.state_dir)
    data = DeltaRest("prod")
    trade = None
    if a.mode != "paper":
        trade = DeltaRest("prod" if a.mode == "live" else "testnet",
                          os.environ.get("DELTA_API_KEY"), os.environ.get("DELTA_API_SECRET"))
    t = Trader(cfg, data, trade)
    if trade is not None and a.exchange_leverage:
        t.journal("SET_LEVERAGE", result=trade.set_leverage(t.pid(), a.exchange_leverage))
    while True:
        try:
            print(json.dumps(t.step(), default=float), flush=True)
        except Exception as exc:  # never crash-loop into duplicate orders; journal and wait
            print(json.dumps(t.journal("ERROR", error=str(exc)[:500])), flush=True)
        if not a.loop:
            break
        now = time.time()
        time.sleep(3600 - now % 3600 + 45)


if __name__ == "__main__":
    main()
