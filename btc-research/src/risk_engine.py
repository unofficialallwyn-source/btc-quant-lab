"""Phase 3 risk-controlled simulation: fail-safe, 1m execution, no funding modeled.

Policies enforced at 1m open/close: max duration, daily entry drawdown,
cooldown, and UTC settlement-boundary entry embargo/mandatory flat.
ATR stop sized using prior complete signal-timeframe bar, not future bars.
"""
from dataclasses import dataclass,asdict
import math
import pandas as pd
from .multi_timeframe import aggregate,SECONDS


@dataclass(frozen=True)
class RiskPolicy:
    max_hold_minutes:int=60
    cooldown_minutes:int=15
    daily_loss_limit_fraction:float=.02
    funding_guard_minutes:int=10
    atr_period:int=14
    atr_stop_multiple:float=2.
    reward_multiple:float=2.
    fee_rate:float=.0005
    slippage_rate:float=.00025
    risk_fraction:float=.005
    max_exposure:float=1.
    initial_equity:float=1000.

    def validate(self):
        if self.max_hold_minutes<1 or self.cooldown_minutes<0 or not 0<self.daily_loss_limit_fraction<1:
            raise ValueError("Invalid holding/cooldown/daily loss")
        if self.funding_guard_minutes<0 or self.funding_guard_minutes>=240:
            raise ValueError("Invalid UTC funding guard")
        if self.atr_period<2 or self.atr_stop_multiple<=0 or self.reward_multiple<=0:
            raise ValueError("Invalid ATR parameters")
        if not 0<=self.fee_rate<1 or not 0<=self.slippage_rate<.1:
            raise ValueError("Invalid costs")
        if not 0<self.risk_fraction<=1 or not 0<self.max_exposure<=1 or self.initial_equity<=0:
            raise ValueError("Risk capped at 1x and positive equity")


def completed_atr(frame,timeframe,period):
    bars=aggregate(frame,timeframe)
    out=pd.Series(float("nan"),index=frame.index)
    if bars.empty:return out
    prev=bars.close.shift(1)
    tr=pd.concat([bars.high-bars.low,(bars.high-prev).abs(),(bars.low-prev).abs()],axis=1).max(axis=1)
    atr=tr.rolling(period,min_periods=period).mean()
    close_time=(bars.time+SECONDS[timeframe]).to_numpy(dtype="int64")
    idx=close_time.searchsorted((frame.time+60).to_numpy(dtype="int64"),side="right")-1
    valid=idx>=0
    out.iloc[valid]=atr.to_numpy()[idx[valid]]
    return out


def _near_funding(t,guard):
    # Exchange funding cadence is assumed 00:00/08:00/16:00 UTC.
    # A time-window restriction, NOT historical proof of funding payments.
    interval=28800
    return min(t%interval,interval-t%interval)<=guard*60


def run_risk(segments,signal_fn,policy=None,signal_tf="5m"):
    cfg=policy or RiskPolicy()
    cfg.validate()
    if signal_tf not in SECONDS:raise ValueError("Unsupported signal timeframe")
    cash=float(cfg.initial_equity);trades=[];curve=[];closed_at=None;segment_diagnostics=[]
    for seg_id,raw in enumerate(segments,1):
        frame=raw.sort_values("time").reset_index(drop=True)
        if frame.empty:continue
        if (frame.time.diff().iloc[1:]!=60).any() or (frame.time%60!=0).any() or frame.time.duplicated().any():
            raise ValueError("Gap or invalid minute timestamps")
        signals=list(signal_fn(frame.copy()))
        if len(signals)!=len(frame) or any(s not in (-1,0,1) for s in signals):
            raise ValueError("Invalid signal vector")
        atr=completed_atr(frame,signal_tf,cfg.atr_period)
        pos=None;last_exit=-1; counters={"signals":0,"entries":0,"blocked_cooldown":0,"blocked_funding":0,"blocked_daily_loss":0,"blocked_atr":0,"blocked_balance":0}
        current_day=None;day_start=cash;day_locked=False
        for i,bar in enumerate(frame.itertuples(index=False)):
            t=int(bar.time);day=t//86400
            if day!=current_day:
                current_day=day;day_start=cash if pos is None else cash+pos["side"]*(float(bar.open)-pos["entry"])*pos["qty"]
                day_locked=False
            # Realized and mark-to-market loss limit prohibits new entries.
            mark_equity=cash if pos is None else cash+pos["side"]*(float(bar.open)-pos["entry"])*pos["qty"]
            if mark_equity<=day_start*(1-cfg.daily_loss_limit_fraction):day_locked=True
            if pos is None and i>0 and i-1>last_exit and signals[i-1]:
                counters["signals"]+=1
                if day_locked:
                    counters["blocked_daily_loss"]+=1
                elif closed_at is not None and t-closed_at<cfg.cooldown_minutes*60:
                    counters["blocked_cooldown"]+=1
                elif _near_funding(t,cfg.funding_guard_minutes):
                    counters["blocked_funding"]+=1
                else:
                    distance=float(atr.iloc[i-1])*cfg.atr_stop_multiple
                    side=int(signals[i-1]);entry=float(bar.open)*(1+side*cfg.slippage_rate)
                    if math.isfinite(distance) and 0<distance<entry:
                        qty=min(cash*cfg.risk_fraction/distance,cash*cfg.max_exposure/entry)
                        fee=qty*entry*cfg.fee_rate
                        if qty>0 and fee<cash:
                            counters["entries"]+=1
                            cash-=fee
                            pos=dict(side=side,entry=entry,qty=qty,entry_time=t,
                                stop=entry-side*distance,target=entry+side*distance*cfg.reward_multiple,
                                fee=fee)
                        else:
                            counters["blocked_balance"]+=1
                    else:
                        counters["blocked_atr"]+=1
            if pos is not None:
                side=pos["side"];stop=pos["stop"];target=pos["target"]
                price=None;reason=None
                # At a funding guard boundary, use bar open if exposed.
                if _near_funding(t,cfg.funding_guard_minutes):
                    price=float(bar.open);reason="funding_guard"
                elif t-pos["entry_time"]>=cfg.max_hold_minutes*60:
                    price=float(bar.open);reason="time_limit"
                elif (side==1 and bar.open<=stop) or (side==-1 and bar.open>=stop):
                    price=float(bar.open);reason="stop_gap"
                elif (side==1 and bar.open>=target) or (side==-1 and bar.open<=target):
                    price=float(bar.open);reason="target_gap"
                elif (side==1 and bar.low<=stop) or (side==-1 and bar.high>=stop):
                    price=stop;reason="stop"
                elif (side==1 and bar.high>=target) or (side==-1 and bar.low<=target):
                    price=target;reason="target"
                elif i==len(frame)-1:
                    price=float(bar.close);reason="segment_end"
                if price is not None:
                    fill=price*(1-side*cfg.slippage_rate)
                    gross=side*(fill-pos["entry"])*pos["qty"]
                    exit_fee=fill*pos["qty"]*cfg.fee_rate
                    cash+=gross-exit_fee
                    trades.append(dict(segment_id=seg_id,entry_time=pos["entry_time"],
                        exit_time=t,side=side,entry=pos["entry"],exit=fill,quantity=pos["qty"],
                        gross_pnl=gross,fees=pos["fee"]+exit_fee,
                        net_pnl=gross-pos["fee"]-exit_fee,exit_reason=reason))
                    pos=None;last_exit=i;closed_at=t
            eq=cash if pos is None else cash+pos["side"]*(float(bar.close)-pos["entry"])*pos["qty"]
            if eq<=day_start*(1-cfg.daily_loss_limit_fraction):day_locked=True
            curve.append(dict(time=t,segment_id=seg_id,equity=eq))
        # Segment end must always close all positions, before a data gap.
        if pos is not None:raise AssertionError("Position carried beyond gap")
        segment_diagnostics.append({"segment_id":seg_id,**counters})
    ledger=pd.DataFrame(trades,columns=["segment_id","entry_time","exit_time","side","entry","exit",
        "quantity","gross_pnl","fees","net_pnl","exit_reason"])
    equity=pd.DataFrame(curve,columns=["time","segment_id","equity"])
    peak=equity.equity.cummax().clip(lower=cfg.initial_equity) if not equity.empty else pd.Series(dtype=float)
    dd=((peak-equity.equity)/peak).max()*100 if not equity.empty else 0.
    pnl=ledger.net_pnl
    wins=pnl[pnl>0];losses=pnl[pnl<0]
    return dict(initial_equity=cfg.initial_equity,ending_equity=round(cash,6),
        return_pct=round((cash/cfg.initial_equity-1)*100,4),
        max_drawdown_pct=round(float(dd),4),trades=len(ledger),
        win_rate_pct=round(100*len(wins)/len(ledger),4) if len(ledger) else None,
        profit_factor=round(float(wins.sum()/-losses.sum()),4) if len(losses) else None,
        fee_total=float(ledger.fees.sum()),segments=len(segments),
        exit_reasons={str(k):int(v) for k,v in ledger.exit_reason.value_counts().items()},
        average_hold_minutes=float(((ledger.exit_time-ledger.entry_time)/60).mean()) if len(ledger) else None,
        entry_decisions={key:sum(int(d[key]) for d in segment_diagnostics) for key in ("signals","entries","blocked_cooldown","blocked_funding","blocked_daily_loss","blocked_atr","blocked_balance")},
        funding_modeled=False,model="linear research only; funding excluded"),ledger,equity
