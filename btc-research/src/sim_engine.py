"""Conservative, simulation-only BTC backtesting on continuous verified candles.

Signals are evaluated at candle close; fills happen on NEXT candle open.
Stop/target collision is resolved against the position (stop first).
Each segment starts FLAT; there is no simulated trading across data gaps.
"""
from dataclasses import dataclass, asdict
import json
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class Config:
    initial_equity: float = 1000.0
    fee_rate: float = 0.0005
    slippage_rate: float = 0.00025
    risk_fraction: float = 0.005
    max_notional_multiple: float = 1.0
    stop_pct: float = 0.01
    reward_multiple: float = 2.0

    def validate(self):
        if self.initial_equity <= 0 or not 0 <= self.fee_rate < 1 or not 0 <= self.slippage_rate < 1:
            raise ValueError("Invalid equity, fees or slippage")
        if not 0 < self.risk_fraction <= 1 or not 0 < self.max_notional_multiple <= 1:
            raise ValueError("Phase 2 baseline is capped at 1x exposure")
        if not 0 < self.stop_pct < 1 or self.reward_multiple <= 0:
            raise ValueError("Invalid stop or reward multiple")


def run(segments, signal_fn, config=None):
    """Return equity/trades/summary. signal_fn(frame) -> {-1,0,1} per candle.

    No borrowed capital, margin, funding or liquidation model in this baseline.
    The short side is a simplified simulated linear short P&L convention,
    NOT a validated Delta BTCUSD perpetual-contract model.
    """
    cfg=config or Config()
    cfg.validate()
    balance=float(cfg.initial_equity)
    trades, curve=[], []
    for segment_id, raw in enumerate(segments,1):
        frame=raw.sort_values("time").reset_index(drop=True)
        if frame.empty:
            continue
        required={"time","open","high","low","close","volume"}
        if not required.issubset(frame.columns):
            raise ValueError("Missing OHLCV columns")
        if frame.time.duplicated().any() or (frame.time % 60 != 0).any() or (frame.time.diff().iloc[1:] != 60).any():
            raise ValueError("Segment contains missing or invalid timestamps")
        if frame[list(required)].isna().any().any() or (frame.low <= 0).any() or (frame.high < frame.low).any() or (frame.open < frame.low).any() or (frame.open > frame.high).any() or (frame.close < frame.low).any() or (frame.close > frame.high).any() or (frame.volume < 0).any():
            raise ValueError("Invalid OHLCV candle")
        signals=list(signal_fn(frame.copy()))
        if len(signals)!=len(frame) or any(s not in (-1,0,1) for s in signals):
            raise ValueError("Signal must be -1, 0 or 1 for every candle")
        position=None
        last_exit_index=-1
        for i, bar in frame.iterrows():
            # Entry uses *previous closed bar's* signal.
            if position is None and i>0 and i-1>last_exit_index and signals[i-1]!=0 and balance>0:
                side=int(signals[i-1])
                entry=float(bar.open)*(1+side*cfg.slippage_rate)
                distance=entry*cfg.stop_pct
                qty=min(balance*cfg.risk_fraction/distance,
                        balance*cfg.max_notional_multiple/entry)
                entry_fee=qty*entry*cfg.fee_rate
                if qty>0 and entry_fee<balance:
                    balance-=entry_fee
                    position={"side":side,"entry":entry,"qty":qty,
                              "stop":entry-side*distance,
                              "target":entry+side*distance*cfg.reward_multiple,
                              "entry_time":int(bar.time),"entry_fee":entry_fee}
            if position:
                side=position["side"]
                stop=position["stop"]; target=position["target"]
                price=None; reason=None
                # Open gaps are filled at the adverse open; no favorable stop improvement.
                if (side==1 and bar.open<=stop) or (side==-1 and bar.open>=stop):
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
                    exit_fee=fill*position["qty"]*cfg.fee_rate
                    gross=side*(fill-position["entry"])*position["qty"]
                    balance+=gross-exit_fee
                    trades.append({"segment_id":segment_id,
                        "entry_time":position["entry_time"],"exit_time":int(bar.time),
                        "side":side,"entry":position["entry"],"exit":fill,
                        "quantity":position["qty"],"gross_pnl":gross,
                        "fees":position["entry_fee"]+exit_fee,
                        "net_pnl":gross-position["entry_fee"]-exit_fee,
                        "exit_reason":reason})
                    position=None
                    last_exit_index=i
            unrealized=0.0 if position is None else (
                position["side"]*(float(bar.close)-position["entry"])*position["qty"])
            curve.append({"segment_id":segment_id,"time":int(bar.time),
                          "equity":balance+unrealized})
    equity=pd.DataFrame(curve)
    ledger=pd.DataFrame(trades)
    if not equity.empty:
        peak=equity.equity.cummax().clip(lower=cfg.initial_equity)
        max_dd=float(((peak-equity.equity)/peak).max()*100)
    else:
        max_dd=0.0
    pnl=ledger.net_pnl if not ledger.empty else pd.Series(dtype=float)
    wins=pnl[pnl>0]; losses=pnl[pnl<0]
    summary={"initial_equity":cfg.initial_equity,"ending_equity":round(balance,6),
       "return_pct":round((balance/cfg.initial_equity-1)*100,4),
       "max_drawdown_pct":round(max_dd,4),"trades":len(ledger),
       "win_rate_pct":round(100*len(wins)/len(ledger),4) if len(ledger) else None,
       "profit_factor":round(float(wins.sum()/-losses.sum()),4) if len(losses) else None,
       "segments":len(segments),
       "model":"linear spot-equivalent PnL, fees + adverse slippage, no funding/liquidation",
       "gap_policy":"flat at each segment boundary"}
    return summary,ledger,equity


def breakout_signal(frame,lookback=20):
    """Causal baseline: previous channel thresholds at bar close."""
    high=frame.high.shift(1).rolling(lookback).max()
    low=frame.low.shift(1).rolling(lookback).min()
    return [1 if c>h else -1 if c<l else 0
            for c,h,l in zip(frame.close,high,low)]


def run_catalog(folder,output,config=None,signal_fn=breakout_signal):
    folder=Path(folder)
    catalog=json.loads((folder/"dataset_catalog.json").read_text())
    if catalog.get("symbol")!="BTCUSD" or catalog.get("resolution")!="1m":
        raise ValueError("Unexpected catalog")
    pieces=[]
    import hashlib
    for item in catalog["segments"]:
        path=folder/Path(item["filename"]).name
        if path.name!=item["filename"] or hashlib.sha256(path.read_bytes()).hexdigest()!=item["sha256"]:
            raise ValueError("Research segment checksum mismatch")
        frame=pd.read_parquet(path)
        if len(frame)!=item["rows"]:
            raise ValueError("Segment count mismatch")
        start=int(pd.Timestamp(item["start_utc"]).timestamp())
        end=int(pd.Timestamp(item["end_exclusive_utc"]).timestamp())
        if frame.empty or int(frame.time.iloc[0])!=start or int(frame.time.iloc[-1])+60!=end:
            raise ValueError("Segment bounds mismatch")
        pieces.append(frame)
    summary,trades,curve=run(pieces,signal_fn,config)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    trades.to_csv(output/"trades.csv",index=False)
    curve.to_csv(output/"equity.csv",index=False)
    (output/"metrics.json").write_text(json.dumps(summary,indent=2)+"\n")
    return summary
