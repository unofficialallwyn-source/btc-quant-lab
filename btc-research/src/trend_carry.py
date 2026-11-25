"""Phase 6 — slow, volatility-targeted trend (+ optional funding carry) forecasts.

Design source: Robert Carver, *Systematic Trading* (quant-resources), chapters on
the EWMAC trend rule, forecast scaling/capping at +/-20, volatility targeting and
position buffering, and the "speed limit" on turnover. All constants below are
fixed *a priori* from that text (not fitted to BTC data) so there is nothing to
optimise on the training partition.

Every value at row i uses only bars whose close time is <= the close of bar i.
Positions derived from row i are executed by the backtester at bar i+1's open.
"""
from dataclasses import dataclass, asdict, field
import hashlib
import json
import math

import numpy as np
import pandas as pd

HOURS_PER_YEAR = 24 * 365
CONTRACT_BTC = 0.001  # Delta India BTCUSD perpetual contract value (BTC per lot)

# Carver's published forecast scalars for EWMAC (daily-data spans, vol-normalised)
EWMAC_SCALARS = {(4, 16): 7.5, (8, 32): 5.3, (16, 64): 3.75, (32, 128): 2.65, (64, 256): 1.87}
CARRY_SCALAR = 30.0
FORECAST_CAP = 20.0
AVG_ABS_FORECAST = 10.0


@dataclass(frozen=True)
class TrendCarrySpec:
    name: str = "ewmac_8_16_32_voltarget"
    ewmac_days: tuple = ((8, 32), (16, 64), (32, 128))
    carry_weight: float = 0.0          # 0 => pure trend; carry needs funding data
    fdm: float = 1.1                   # forecast diversification multiplier (correlated rules)
    vol_target: float = 0.20           # annualised % of capital
    vol_short_days: int = 36
    vol_long_days: int = 365
    vol_long_weight: float = 0.3
    vol_floor: float = 0.25            # never assume BTC annual vol below 25%
    buffer_fraction: float = 0.10      # Carver position inertia, 10% of average position
    max_leverage: float = 2.0
    carry_smooth_days: int = 30
    long_only: bool = False
    contract_btc: float = CONTRACT_BTC

    def validate(self):
        if not self.ewmac_days:
            raise ValueError("At least one EWMAC speed required")
        for pair in self.ewmac_days:
            if tuple(pair) not in EWMAC_SCALARS:
                raise ValueError(f"No published scalar for EWMAC {pair}")
        if not 0 <= self.carry_weight < 1:
            raise ValueError("carry_weight must be in [0,1)")
        if not 0 < self.vol_target <= 0.5:
            raise ValueError("vol_target must be in (0, 0.5]")
        if not 0 < self.max_leverage <= 5:
            raise ValueError("max_leverage must be in (0, 5]")
        if not 0 <= self.buffer_fraction < 1 or self.fdm < 1:
            raise ValueError("Invalid buffer or FDM")
        if self.contract_btc <= 0:
            raise ValueError("Invalid contract size")

    def to_dict(self):
        d = asdict(self)
        d["ewmac_days"] = [list(p) for p in self.ewmac_days]
        return d

    def sha256(self):
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()


def check_hourly(frame):
    req = {"time", "open", "high", "low", "close"}
    if not req.issubset(frame.columns):
        raise ValueError("Missing hourly OHLC columns")
    f = frame.sort_values("time").reset_index(drop=True)
    if f.time.duplicated().any() or (f.time % 3600 != 0).any():
        raise ValueError("Hourly timestamps must be unique and hour aligned")
    if f[list(req)].isna().any().any() or (f[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Invalid OHLC values")
    return f


def annual_vol(close, spec):
    """Causal blended EWMA volatility of hourly log returns, annualised, floored."""
    r = np.log(close).diff()
    short = r.ewm(span=spec.vol_short_days * 24, min_periods=7 * 24).std()
    long = r.ewm(span=spec.vol_long_days * 24, min_periods=7 * 24).std()
    blended = (1 - spec.vol_long_weight) * short + spec.vol_long_weight * long.fillna(short)
    return (blended * math.sqrt(HOURS_PER_YEAR)).clip(lower=spec.vol_floor)


def ewmac_forecast(close, fast_days, slow_days, ann_vol):
    fast = close.ewm(span=fast_days * 24, min_periods=slow_days * 24).mean()
    slow = close.ewm(span=slow_days * 24, min_periods=slow_days * 24).mean()
    daily_price_vol = close * ann_vol / math.sqrt(365)
    raw = (fast - slow) / daily_price_vol
    return (raw * EWMAC_SCALARS[(fast_days, slow_days)]).clip(-FORECAST_CAP, FORECAST_CAP)


def funding_on_hours(times, funding):
    """As-of align funding settlements (time, rate) to hourly bar close times."""
    out = pd.Series(np.nan, index=times.index)
    if funding is None or len(funding) == 0:
        return out
    fs = funding.sort_values("time")
    known = fs.time.to_numpy(dtype="int64")
    at = times.to_numpy(dtype="int64") + 3600
    idx = np.searchsorted(known, at, side="right") - 1
    ok = idx >= 0
    out.iloc[np.where(ok)[0]] = fs.rate.to_numpy(dtype=float)[idx[ok]]
    return out


def carry_forecast(funding, times, ann_vol, spec, interval_hours=8):
    """Positive funding (longs pay) => negative carry forecast."""
    if funding is None or len(funding) == 0:
        return pd.Series(np.nan, index=times.index)
    fs = funding.sort_values("time").reset_index(drop=True)
    per_year = HOURS_PER_YEAR / interval_hours
    smooth = fs.rate.ewm(span=max(2, int(spec.carry_smooth_days * 24 / interval_hours)), min_periods=3).mean()
    smoothed = pd.DataFrame({"time": fs.time, "rate": smooth})
    aligned = funding_on_hours(times, smoothed)
    return (-aligned * per_year / ann_vol * CARRY_SCALAR).clip(-FORECAST_CAP, FORECAST_CAP)


def forecasts(frame, spec, funding=None):
    """Return DataFrame with per-rule forecasts, combined forecast, ann_vol."""
    spec.validate()
    f = check_hourly(frame)
    vol = annual_vol(f.close, spec)
    out = pd.DataFrame({"time": f.time, "close": f.close, "ann_vol": vol})
    trend_cols = []
    for fast, slow in spec.ewmac_days:
        col = f"ewmac_{fast}_{slow}"
        out[col] = ewmac_forecast(f.close, fast, slow, vol)
        trend_cols.append(col)
    trend = out[trend_cols].mean(axis=1, skipna=False)
    if spec.carry_weight > 0:
        out["carry"] = carry_forecast(funding, f.time, vol, spec)
        combined = (1 - spec.carry_weight) * trend + spec.carry_weight * out["carry"]
    else:
        combined = trend
    combined = (combined * spec.fdm).clip(-FORECAST_CAP, FORECAST_CAP)
    if spec.long_only:
        combined = combined.clip(lower=0)
    out["forecast"] = combined
    return out


def ideal_contracts(forecast, price, ann_vol, equity_usd, spec):
    """Carver position sizing, in (fractional) contracts; NaN forecast => 0."""
    if not np.isfinite(forecast) or not np.isfinite(ann_vol) or equity_usd <= 0:
        return 0.0
    notional = equity_usd * spec.vol_target / ann_vol * forecast / AVG_ABS_FORECAST
    cap = equity_usd * spec.max_leverage
    notional = max(-cap, min(cap, notional))
    return notional / (price * spec.contract_btc)


def buffered_target(current, ideal, price, ann_vol, equity_usd, spec):
    """Integer target contracts after Carver buffering; returns current if inside buffer."""
    avg_pos = equity_usd * spec.vol_target / ann_vol / (price * spec.contract_btc) if ann_vol > 0 else 0
    # at least one lot wide, otherwise integer rounding churns 1<->2 lots every bar
    width = max(spec.buffer_fraction * abs(avg_pos), 1.0)
    lo, hi = ideal - width, ideal + width
    if lo <= current <= hi:
        return int(current)
    edge = hi if current > hi else lo
    # round toward the ideal so we never end up outside the buffer by rounding
    return int(math.floor(edge)) if current > hi else int(math.ceil(edge))
