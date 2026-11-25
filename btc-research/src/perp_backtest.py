"""Hourly position-based backtester for the Delta India BTCUSD linear perpetual.

Timeline for hourly bar i (UTC open time t_i):
  1. at t_i the funding settlement (if any) is charged on the position carried in;
  2. the order computed from bar i-1's CLOSE is filled at bar i's OPEN +/- slippage,
     paying taker fee * (1 + GST);
  3. the position is marked at bar i's close; a new target is computed from it.

Contracts are integers of 0.001 BTC. P&L is USD (linear), reported also in INR at
a fixed conversion (Delta India settles USD contracts in INR at a fixed rate).
Data gaps split the series into segments; positions are flattened (with costs) at
each segment end, so nothing is held across unobserved time.
This is a research model: no queue/maker fills, no liquidation engine (a
maintenance-margin breach is flagged and fails the run), no fee tiers.
"""
from dataclasses import dataclass, asdict
import math

import numpy as np
import pandas as pd

from .trend_carry import HOURS_PER_YEAR, forecasts, ideal_contracts, buffered_target


@dataclass(frozen=True)
class CostModel:
    taker_fee: float = 0.0005
    gst: float = 0.18
    slippage: float = 0.00025
    maintenance_margin: float = 0.005
    inr_per_usd: float = 85.0
    assumed_funding_rate: float = None   # per settlement; None => only use observed data
    funding_interval_hours: int = 8

    @property
    def per_side(self):
        return self.taker_fee * (1 + self.gst) + self.slippage


def split_segments(frame):
    f = frame.sort_values("time").reset_index(drop=True)
    breaks = np.where(f.time.diff().fillna(3600).to_numpy() != 3600)[0]
    edges = [0, *breaks.tolist(), len(f)]
    return [f.iloc[a:b].reset_index(drop=True) for a, b in zip(edges[:-1], edges[1:]) if b > a]


def _funding_lookup(funding, cost):
    if funding is None or len(funding) == 0:
        return {}
    step = cost.funding_interval_hours * 3600
    fs = funding[(funding.time % step) == 0]
    return dict(zip(fs.time.astype("int64"), fs.rate.astype(float)))


def run(frame, spec, cost=None, funding=None, initial_equity_usd=1000.0):
    cost = cost or CostModel()
    fund = _funding_lookup(funding, cost)
    step = cost.funding_interval_hours * 3600
    equity = float(initial_equity_usd)
    rows, fills = [], []
    totals = dict(gross=0.0, fees=0.0, slippage=0.0, funding=0.0, funding_assumed_events=0,
                  funding_observed_events=0, margin_breach=False)
    for seg_id, seg in enumerate(split_segments(frame), 1):
        fc = forecasts(seg, spec, funding)
        pos = 0
        pending = None
        n = len(seg)
        for i in range(n):
            t = int(seg.time[i]); o = float(seg.open[i]); c = float(seg.close[i])
            prev_close = float(seg.close[i - 1]) if i else o
            if t % step == 0 and pos != 0:
                rate = fund.get(t)
                if rate is None and cost.assumed_funding_rate is not None:
                    rate = cost.assumed_funding_rate; totals["funding_assumed_events"] += 1
                elif rate is not None:
                    totals["funding_observed_events"] += 1
                if rate is not None:
                    pay = -pos * spec.contract_btc * o * rate
                    equity += pay; totals["funding"] += pay
            # mark carried position from prev close to this open
            if pos:
                g = pos * spec.contract_btc * (o - prev_close)
                equity += g; totals["gross"] += g
            if pending is not None and pending != pos:
                equity -= trade(pending - pos, o, t, "rebalance", pos, spec, cost, totals, fills, seg_id)
                pos = pending
            pending = None
            if pos:
                g = pos * spec.contract_btc * (c - o)
                equity += g; totals["gross"] += g
            notional = abs(pos) * spec.contract_btc * c
            if notional and equity < notional * cost.maintenance_margin:
                totals["margin_breach"] = True
            if i == n - 1:
                if pos:
                    equity -= trade(-pos, c, t + 3600, "segment_end", pos, spec, cost, totals, fills, seg_id)
                    pos = 0
            else:
                fcast = float(fc.forecast.iloc[i]); vol = float(fc.ann_vol.iloc[i])
                if equity > 0 and np.isfinite(fcast):
                    ideal = ideal_contracts(fcast, c, vol, equity, spec)
                    pending = buffered_target(pos, ideal, c, vol, equity, spec)
            rows.append({"segment": seg_id, "time": t, "close": c, "position": pos,
                         "equity": equity, "forecast": float(fc.forecast.iloc[i])})
    curve = pd.DataFrame(rows)
    ledger = pd.DataFrame(fills)
    return summarize(curve, ledger, totals, initial_equity_usd, spec, cost), curve, ledger


def trade(delta, price, t, reason, pos, spec, cost, totals, fills, seg_id):
    """Record a taker fill; returns its cost (fee + slippage) in USD."""
    side = 1 if delta > 0 else -1
    qty_btc = abs(delta) * spec.contract_btc
    fee = qty_btc * price * cost.taker_fee * (1 + cost.gst)
    slip = qty_btc * price * cost.slippage
    totals["fees"] += fee; totals["slippage"] += slip
    fills.append({"segment": seg_id, "time": t, "side": side, "contracts": abs(delta),
                  "price": price, "fee": fee, "slippage": slip, "position_before": pos,
                  "position_after": pos + delta, "reason": reason})
    return fee + slip


def summarize(curve, ledger, totals, initial, spec, cost):
    if curve.empty:
        return {"bars": 0}
    eq = curve.equity.to_numpy()
    rets = pd.Series(eq).pct_change().fillna(eq[0] / initial - 1).to_numpy()
    years = len(curve) / HOURS_PER_YEAR
    mean, std = rets.mean(), rets.std(ddof=1)
    ann_ret = mean * HOURS_PER_YEAR
    ann_vol = std * math.sqrt(HOURS_PER_YEAR) if std > 0 else 0.0
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
    peak = np.maximum.accumulate(np.concatenate([[initial], eq]))[1:]
    dd = ((peak - eq) / peak).max()
    traded = float(ledger.contracts.sum()) if not ledger.empty else 0.0
    avg_abs_pos = float(curve.position.abs().mean())
    turnover = (traded / (2 * avg_abs_pos) / years) if avg_abs_pos > 0 and years > 0 else 0.0
    btc_vol = float(np.log(curve.close).diff().std() * math.sqrt(HOURS_PER_YEAR))
    std_cost = 2 * cost.per_side / btc_vol if btc_vol > 0 else float("nan")
    costs = totals["fees"] + totals["slippage"]
    return {
        "bars": len(curve), "years": round(years, 4),
        "initial_equity_usd": initial, "ending_equity_usd": round(float(eq[-1]), 4),
        "ending_equity_inr": round(float(eq[-1]) * cost.inr_per_usd, 2),
        "total_return_pct": round((eq[-1] / initial - 1) * 100, 4),
        "annual_return_pct": round(ann_ret * 100, 4), "annual_vol_pct": round(ann_vol * 100, 4),
        "sharpe": round(sharpe, 4), "max_drawdown_pct": round(float(dd) * 100, 4),
        "skew": round(float(pd.Series(rets).skew()), 4),
        "gross_pnl_usd": round(totals["gross"], 4), "fees_usd": round(totals["fees"], 4),
        "slippage_usd": round(totals["slippage"], 4), "funding_usd": round(totals["funding"], 4),
        "funding_observed_events": totals["funding_observed_events"],
        "funding_assumed_events": totals["funding_assumed_events"],
        "cost_share_of_gross": round(costs / totals["gross"], 4) if totals["gross"] > 0 else None,
        "fills": int(len(ledger)), "contracts_traded": traded,
        "avg_abs_position_contracts": round(avg_abs_pos, 4),
        "turnover_round_trips_per_year": round(turnover, 3),
        "btc_annual_vol_pct": round(btc_vol * 100, 3),
        "standardised_cost_sr_per_round_trip": round(std_cost, 6),
        "annual_cost_sr": round(turnover * std_cost, 4),
        "margin_breach": totals["margin_breach"],
        "model": "hourly linear perp, taker fee+GST, slippage, funding cash flows, integer 0.001 BTC lots",
    }
