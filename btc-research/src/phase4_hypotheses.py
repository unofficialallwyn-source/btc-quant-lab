"""Phase 4: three frozen causal BTC strategy hypotheses, not tuned or backtested.

Input is a verified contiguous 1m OHLCV segment. Signals describe the close
of the latest fully complete HTF candle and can only be executed at the next
minute open by the existing simulator. Each family produces {-1,0,1}.
"""
from dataclasses import asdict, dataclass
import numpy as np
import pandas as pd

from .multi_timeframe import aggregate, SECONDS
from .strategies import _available, rsi
from .phase4_regimes import RegimeConfig, classify


NAMES=("hv_range_continuation","exhaustion_reversal","trend_transition")


@dataclass(frozen=True)
class Hypothesis:
    name:str
    signal_tf:str="5m"
    context_tf:str="1h"
    breakout_lookback:int=12
    volume_window:int=20
    volume_multiple:float=1.5
    rsi_period:int=14
    rsi_low:float=25.
    rsi_high:float=75.
    transition_threshold:float=1.0
    minimum_cost_move_ratio:float=2.0
    fee_rate:float=.0005
    slippage_rate:float=.00025

    def validate(self):
        if self.name not in NAMES:raise ValueError("Unknown hypothesis")
        if self.signal_tf!="5m" or self.context_tf!="1h":
            raise ValueError("Phase 4 hypotheses freeze 5m signal / 1h context")
        if self.breakout_lookback<3 or self.volume_window<3 or self.rsi_period<2:
            raise ValueError("Invalid window")
        if self.volume_multiple<=0 or not 0<self.rsi_low<self.rsi_high<100:
            raise ValueError("Invalid volume or RSI")
        if self.transition_threshold<=0 or self.minimum_cost_move_ratio<0:
            raise ValueError("Invalid thresholds")
        if not 0<=self.fee_rate<1 or not 0<=self.slippage_rate<.1:
            raise ValueError("Invalid cost assumptions")


def signals(frame,spec):
    spec.validate()
    if frame.empty:return []
    signal=aggregate(frame,spec.signal_tf)
    context=classify(frame,RegimeConfig(timeframe=spec.context_tf))
    if signal.empty or context.empty:return [0]*len(frame)
    s=signal.copy()
    high=s.high.shift(1).rolling(spec.breakout_lookback,min_periods=spec.breakout_lookback).max()
    low=s.low.shift(1).rolling(spec.breakout_lookback,min_periods=spec.breakout_lookback).min()
    volume_avg=s.volume.shift(1).rolling(spec.volume_window,min_periods=spec.volume_window).mean()
    vol_ok=(s.volume>=volume_avg*spec.volume_multiple)
    prev=s.close.shift(1)
    tr=pd.concat([s.high-s.low,(s.high-prev).abs(),(s.low-prev).abs()],axis=1).max(axis=1)
    atr=tr.rolling(14,min_periods=14).mean()
    roundtrip_cost=2*(spec.fee_rate+spec.slippage_rate)
    cost_ok=(atr/s.close>=roundtrip_cost*spec.minimum_cost_move_ratio)
    osc=rsi(s.close,spec.rsi_period)
    # Observed directional event, evaluated after the 5m candle closes.
    breakout_up=(s.close>high)&(s.close>s.open)
    breakout_down=(s.close<low)&(s.close<s.open)
    # Exhaustion needs a prior 5m oscillator extreme and a newly completed
    # reversal candle. The price confirmation is deliberately explicit.
    exhaust_up=(osc.shift(1)<spec.rsi_low)&(s.close>s.open)&(s.close>prev)
    exhaust_down=(osc.shift(1)>spec.rsi_high)&(s.close<s.open)&(s.close<prev)
    # Map existing context states using numeric completed-bar as-of joins.
    context=context.copy()
    context["hv_range"]=(context.regime=="high_volatility_range").astype(float)
    context["range"]=(context.regime=="range").astype(float)
    context["trend_score_numeric"]=context.trend_score.astype(float)
    context["prior_score"]=context.trend_score.shift(1)
    context["transition_up"]=((context.trend_score>=spec.transition_threshold)&
        (context.prior_score<spec.transition_threshold)).astype(float)
    context["transition_down"]=((context.trend_score<=-spec.transition_threshold)&
        (context.prior_score>-spec.transition_threshold)).astype(float)
    t=frame.time
    s["breakout_up"]=breakout_up.astype(float)
    s["breakout_down"]=breakout_down.astype(float)
    s["exhaust_up"]=exhaust_up.astype(float)
    s["exhaust_down"]=exhaust_down.astype(float)
    s["vol_ok"]=vol_ok.astype(float)
    s["cost_ok"]=cost_ok.astype(float)
    def ss(col):return _available(s,t,SECONDS[spec.signal_tf],col)==1
    def cc(col):return _available(context,t,SECONDS[spec.context_tf],col)==1
    common=ss("vol_ok")&ss("cost_ok")
    out=np.zeros(len(frame),dtype=int)
    if spec.name=="hv_range_continuation":
        allow=common&cc("hv_range")
        out[allow&ss("breakout_up")]=1
        out[allow&ss("breakout_down")]=-1
    elif spec.name=="exhaustion_reversal":
        allow=common&cc("range")
        out[allow&ss("exhaust_up")]=1
        out[allow&ss("exhaust_down")]=-1
    else:
        allow=common
        out[allow&cc("transition_up")&ss("breakout_up")]=1
        out[allow&cc("transition_down")&ss("breakout_down")]=-1
    return out.tolist()


def research_specs():
    """Locked research protocol for Step 4, no measured performance."""
    return {
      "schema_version":1,"phase":"4_step_3","training_only":True,
      "validation_evaluated":False,"holdout_evaluated":False,
      "signal_timeframe":"5m","context_timeframe":"1h",
      "execution":"earliest next 1m open after completed 5m candle",
      "no_trade":"missing warmup/context, absence of the condition, weak volume, insufficient ATR vs modeled round-trip costs, data gaps",
      "risk_policy_for_future_testing":{
        "entry_mode":"transition","atr_stop_multiple":2.0,"reward_multiple":2.0,
        "max_hold_minutes":60,"cooldown_minutes":15,"risk_fraction":.005,
        "max_exposure":1.0,"fee_rate":.0005,"slippage_rate":.00025,
        "funding_guard_minutes":10},
      "hypotheses":{
        "hv_range_continuation":{
          "spec":asdict(Hypothesis("hv_range_continuation")),
          "entry":"completed high-volatility ranging 1h regime; 5m channel breakout in candle direction; >=1.5x prior volume, ATR-to-cost gate",
          "exit":"frozen risk-policy ATR stop/target, 60m time limit or funding-window flat",
          "prediction":"short-term directional continuation, not yet tested"},
        "exhaustion_reversal":{
          "spec":asdict(Hypothesis("exhaustion_reversal")),
          "entry":"completed ordinary ranging 1h regime; preceding 5m RSI beyond 25/75, current opposite-body candle confirms reversal, volume and cost gate",
          "exit":"frozen risk-policy ATR stop/target, 60m time limit or funding-window flat",
          "prediction":"short-term price reversal after extension, not yet tested"},
        "trend_transition":{
          "spec":asdict(Hypothesis("trend_transition")),
          "entry":"first completed 1h trend-score crossing +/-1.0 from weaker state; 5m breakout agrees, volume and cost gate",
          "exit":"frozen risk-policy ATR stop/target, 60m time limit or funding-window flat",
          "prediction":"continuation near directional regime change, not yet tested"}}}
