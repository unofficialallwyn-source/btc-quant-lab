"""Simulation-only Delta India BTCUSD event engine with strict external market inputs.

Prices USD, cash/margin/fees/PnL INR. Requires aligned contemporaneous 1m
mark prices and FX; funding must have an observed settlement event at every
8-hour UTC boundary while a position is held. No invented funding, FX or mark.
Liquidation breach halts the simulation: actual exchange liquidation pricing
cannot be reconstructed from minute candles.
"""
from dataclasses import dataclass
from decimal import Decimal
import pandas as pd

from .delta_contract import (D, CONTRACT, quantize_lots, fee_inr, pnl_inr,
    required_margin_inr, funding_inr)


@dataclass(frozen=True)
class DeltaSimConfig:
    initial_inr: str = "85000"
    risk_fraction: str = "0.005"
    max_exposure_multiple: str = "1"
    stop_fraction: str = "0.01"
    reward_multiple: str = "2"
    slippage_fraction: str = "0.00025"

    def validate(self):
        if not D(self.initial_inr)>0 or not D(0)<D(self.risk_fraction)<=1:
            raise ValueError("Invalid initial INR or risk")
        if not D(0)<D(self.max_exposure_multiple)<=1:
            raise ValueError("Research leverage is restricted to 1x notional")
        if not D(0)<D(self.stop_fraction)<1 or not D(self.reward_multiple)>0:
            raise ValueError("Invalid stop/target")
        if not D(0)<=D(self.slippage_fraction)<D("0.1"):
            raise ValueError("Invalid slippage")


def _validate_segment(frame,mark,fx):
    if frame.empty: return
    ts=frame.time.astype("int64")
    if ts.duplicated().any() or (ts%60!=0).any() or (ts.diff().iloc[1:]!=60).any():
        raise ValueError("Non-continuous price segment")
    for name,series in (("mark",mark),("FX",fx)):
        if not isinstance(series,pd.Series) or series.index.has_duplicates:
            raise ValueError(f"{name} requires unique timestamps")
        if not set(ts).issubset(series.index):
            raise ValueError(f"Missing {name} timestamp(s); fail closed")
        values=series.reindex(ts).astype(float)
        if values.isna().any() or (values<=0).any():
            raise ValueError(f"Invalid {name} values")
    for c in ("open","high","low","close","volume"):
        if c not in frame or frame[c].isna().any():
            raise ValueError("Missing OHLCV")
    if ((frame.low<=0)|(frame.high<frame.low)|(frame.open<frame.low)|
            (frame.open>frame.high)|(frame.close<frame.low)|
            (frame.close>frame.high)|(frame.volume<0)).any():
        raise ValueError("Invalid candles")


def run_delta(segments,signal_fn,mark_by_time,fx_by_time,funding_by_time,
              config=None):
    """One portfolio across segments. Positions always flat at boundaries.

    The run refuses to return a PnL number following an unmodelled liquidation.
    Funding marks must be actual observed events, not interpolated OHLC prices.
    """
    cfg=config or DeltaSimConfig()
    cfg.validate()
    CONTRACT.check()
    cash=D(cfg.initial_inr)
    initial=cash
    equity_curve=[]
    trades=[]
    funding_paid=D(0)
    fees_paid=D(0)
    for segment_id,original in enumerate(segments,1):
        frame=original.sort_values("time").reset_index(drop=True)
        if frame.empty:continue
        _validate_segment(frame,mark_by_time,fx_by_time)
        signals=list(signal_fn(frame.copy()))
        if len(signals)!=len(frame) or any(v not in (-1,0,1) for v in signals):
            raise ValueError("Signal vector must be -1, 0 or +1")
        pos=None
        last_exit_index=-1
        for i,bar in enumerate(frame.itertuples(index=False)):
            t=int(bar.time)
            mark=D(mark_by_time.loc[t])
            fx=D(fx_by_time.loc[t])
            if pos is None and i>0 and i-1>last_exit_index and signals[i-1] and cash>0:
                side=int(signals[i-1])
                entry=D(bar.open)*(D(1)+D(side)*D(cfg.slippage_fraction))
                stop_distance=entry*D(cfg.stop_fraction)
                risk_lots=cash*D(cfg.risk_fraction)/(stop_distance*fx*CONTRACT.lot_btc)
                exposure_lots=cash*D(cfg.max_exposure_multiple)/(entry*fx*CONTRACT.lot_btc)
                lots=quantize_lots(min(risk_lots,exposure_lots)*CONTRACT.lot_btc)
                if lots:
                    entry_fee=fee_inr(lots,entry,fx)
                    margin=required_margin_inr(lots,entry,fx)
                    if margin+entry_fee<=cash:
                        cash-=entry_fee
                        fees_paid+=entry_fee
                        pos=dict(side=side,lots=lots,entry=entry,
                            stop=entry-D(side)*stop_distance,
                            target=entry+D(side)*stop_distance*D(cfg.reward_multiple),
                            entry_time=t,entry_fee=entry_fee,funding=D(0))
            if pos is not None:
                # Check maintenance against an observed mark before settlement.
                state_equity=cash+pnl_inr(pos["side"],pos["lots"],pos["entry"],mark,fx)
                maint=required_margin_inr(pos["lots"],mark,fx,maintenance=True)
                if state_equity<=maint:
                    raise ValueError(f"UNMODELLED_LIQUIDATION segment={segment_id} utc={t}; run invalid")
                # Funding happens at 00:00/08:00/16:00 UTC if held through boundary.
                if t>pos["entry_time"] and t%CONTRACT.funding_interval_seconds==0:
                    if t not in funding_by_time:
                        raise ValueError(f"Missing verified funding settlement at {t}")
                    event=funding_by_time[t]
                    # Public mark candles alone are insufficient: event needs its own
                    # observed funding rate; bar's contemporaneous mark is used.
                    payment=funding_inr(pos["side"],pos["lots"],mark,fx,event)
                    cash-=payment
                    funding_paid+=payment
                    pos["funding"]+=payment
                    if cash+pnl_inr(pos["side"],pos["lots"],pos["entry"],mark,fx)<=maint:
                        raise ValueError(f"UNMODELLED_LIQUIDATION_AFTER_FUNDING utc={t}")
                side=pos["side"]
                exit_price=None
                reason=None
                if (side==1 and D(bar.open)<=pos["stop"]) or (side==-1 and D(bar.open)>=pos["stop"]):
                    exit_price=D(bar.open);reason="stop_gap"
                elif (side==1 and D(bar.open)>=pos["target"]) or (side==-1 and D(bar.open)<=pos["target"]):
                    exit_price=D(bar.open);reason="target_gap"
                elif (side==1 and D(bar.low)<=pos["stop"]) or (side==-1 and D(bar.high)>=pos["stop"]):
                    exit_price=pos["stop"];reason="stop"
                elif (side==1 and D(bar.high)>=pos["target"]) or (side==-1 and D(bar.low)<=pos["target"]):
                    exit_price=pos["target"];reason="target"
                elif i==len(frame)-1:
                    exit_price=D(bar.close);reason="segment_end"
                if exit_price is not None:
                    fill=exit_price*(D(1)-D(side)*D(cfg.slippage_fraction))
                    exit_fee=fee_inr(pos["lots"],fill,fx)
                    price_pnl=pnl_inr(side,pos["lots"],pos["entry"],fill,fx)
                    cash+=price_pnl-exit_fee
                    fees_paid+=exit_fee
                    trades.append(dict(segment_id=segment_id,entry_time=pos["entry_time"],
                        exit_time=t,side=side,lots=pos["lots"],entry_usd=float(pos["entry"]),
                        exit_usd=float(fill),price_pnl_inr=float(price_pnl),
                        fee_inr=float(pos["entry_fee"]+exit_fee),
                        funding_inr=float(pos["funding"]),
                        net_pnl_inr=float(price_pnl-pos["entry_fee"]-exit_fee-pos["funding"]),
                        reason=reason,cash_after_inr=float(cash)))
                    pos=None
                    last_exit_index=i
            unrealized=D(0) if pos is None else pnl_inr(pos["side"],pos["lots"],pos["entry"],mark,fx)
            equity_curve.append(dict(time=t,segment_id=segment_id,equity_inr=float(cash+unrealized)))
    curve=pd.DataFrame(equity_curve)
    ledger=pd.DataFrame(trades)
    if curve.empty:
        drawdown=0.
    else:
        peaks=curve.equity_inr.cummax().clip(lower=float(initial))
        drawdown=float(((peaks-curve.equity_inr)/peaks).max()*100)
    return (dict(currency="INR",initial_equity_inr=float(initial),
        ending_equity_inr=float(cash),return_pct=float((cash/initial-1)*100),
        max_drawdown_pct=drawdown,trade_count=len(ledger),total_fee_inr=float(fees_paid),
        net_funding_paid_inr=float(funding_paid),segments=len(segments),
        liquidation_status="no maintenance threshold breach observed at minute marks",
        execution_model="taker, next-minute open, adverse slippage, stop-first, 1m mark"),
        ledger,curve)
