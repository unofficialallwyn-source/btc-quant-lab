"""Deterministic reporting for the simulation-only chronological BTC baseline.

Never reads or evaluates holdout files unless the evaluation metadata explicitly
marks holdout evaluated. No funding inputs, no claim of exchange-realistic P&L.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _metrics(trades, curve, initial):
    required_trades={"entry_time","exit_time","side","gross_pnl","fees","net_pnl"}
    required_equity={"time","equity"}
    if not required_trades.issubset(trades.columns) or not required_equity.issubset(curve.columns):
        raise ValueError("Ledger or equity schema missing required fields")
    if curve.empty:
        raise ValueError("Cannot report an empty equity curve")
    if curve.time.duplicated().any() or not curve.time.is_monotonic_increasing:
        raise ValueError("Equity observations must be increasing and unique")
    for col in ("equity",):
        if not np.isfinite(curve[col].to_numpy(dtype=float)).all():
            raise ValueError("Non-finite equity")
    if (curve.equity<=0).any():
        raise ValueError("Nonpositive equity: metrics cannot use log returns")
    if len(trades):
        if (trades.exit_time<trades.entry_time).any():
            raise ValueError("Exit before entry")
        if not np.isfinite(trades[["gross_pnl","fees","net_pnl"]].to_numpy(dtype=float)).all():
            raise ValueError("Non-finite trade outcomes")
        if not np.allclose(trades.gross_pnl-trades.fees,trades.net_pnl,atol=1e-6,rtol=1e-6):
            raise ValueError("Trade ledger P&L does not reconcile")
    vals=curve.equity.astype(float)
    peaks=vals.cummax().clip(lower=float(initial))
    drawdown=(vals/peaks)-1
    returns=vals.pct_change().dropna()
    # Use realized trade P&L for expectancy and profit factor.
    pnl=trades.net_pnl.astype(float)
    positives=pnl[pnl>0]
    negatives=pnl[pnl<0]
    if len(negatives):
        profit_factor=float(positives.sum()/-negatives.sum())
    elif len(positives):
        profit_factor=None  # mathematically infinite; avoid fake large number
    else:
        profit_factor=None
    dd=float(drawdown.min()*100)
    if dd<0:
        trough=int(drawdown.idxmin())
        peak=int(vals.iloc[:trough+1].idxmax())
        recovery=next((i for i in range(trough+1,len(vals))
                       if vals.iloc[i]>=peaks.iloc[trough]),None)
        drawdown_window={
            "peak_time_utc":pd.to_datetime(int(curve.time.iloc[peak]),unit="s",utc=True).isoformat(),
            "trough_time_utc":pd.to_datetime(int(curve.time.iloc[trough]),unit="s",utc=True).isoformat(),
            "recovered_time_utc":None if recovery is None else
                pd.to_datetime(int(curve.time.iloc[recovery]),unit="s",utc=True).isoformat()}
    else:
        drawdown_window=None
    return {
        "starting_equity":float(initial),
        "ending_equity":float(vals.iloc[-1]),
        "total_return_pct":float((vals.iloc[-1]/initial-1)*100),
        "max_drawdown_pct":-dd,
        "max_drawdown_window":drawdown_window,
        "trades":len(trades),
        "win_rate_pct":float((pnl>0).mean()*100) if len(pnl) else None,
        "profit_factor":profit_factor,
        "expectancy_per_trade":float(pnl.mean()) if len(pnl) else None,
        "median_trade_pnl":float(pnl.median()) if len(pnl) else None,
        "gross_profit":float(positives.sum()),
        "gross_loss":float(negatives.sum()),
        "total_fees":float(trades.fees.sum()),
        "total_gross_pnl":float(trades.gross_pnl.sum()),
        "net_realized_pnl":float(pnl.sum()),
        "mean_trade_duration_minutes":float(((trades.exit_time-trades.entry_time)/60).mean()) if len(trades) else None,
        "max_consecutive_losses":_max_loss_streak(pnl),
        "minute_return_std":float(returns.std(ddof=1)) if len(returns)>1 else None,
        "sharpe_annualized_1m":float(returns.mean()/returns.std(ddof=1)*np.sqrt(525600))
            if len(returns)>1 and returns.std(ddof=1)>0 else None,
        "sharpe_caveat":"annualized 1m mark-to-market Sharpe assumes uniform observations; data gaps and flat resets make it descriptive only"
    }


def _max_loss_streak(pnl):
    best=streak=0
    for x in pnl:
        streak=streak+1 if x<0 else 0
        best=max(best,streak)
    return best


def build_report(folder, *, output=None):
    root=Path(folder)
    evaluation=json.loads((root/"evaluation.json").read_text())
    if evaluation.get("holdout_evaluated") is not False:
        raise ValueError("Research reporting requires locked holdout")
    if evaluation.get("results",{}).get("holdout",{}).get("status")!="locked":
        raise ValueError("Holdout status must be locked")
    config=evaluation["config"]
    initial=float(config["initial_equity"])
    report={"schema_version":1,
        "currency":"USD equivalent (not Delta India INR settlement)",
        "model":"simulation-only baseline, not exchange-accurate",
        "funding_handling":"not modeled; returns must NOT be described as funding-free exchange results",
        "holdout_evaluated":False,
        "signal_timeframe":evaluation.get("signal_timeframe"),
        "execution_timeframe":evaluation.get("execution_timeframe"),
        "fee_rate":float(config["fee_rate"]),
        "slippage_rate":float(config["slippage_rate"]),
        "partitions":{},"input_sha256":{}}
    for name in ("training","validation"):
        state=evaluation["results"].get(name,{})
        if state.get("status")!="evaluated":
            raise ValueError(f"{name} is not evaluated")
        trades_path=root/f"{name}_trades.csv"
        equity_path=root/f"{name}_equity.csv"
        # Empty trade CSV from pandas has no columns; preserve schema by
        # reporting zero trades rather than misinterpreting missing history.
        try:
            trades=pd.read_csv(trades_path)
        except pd.errors.EmptyDataError:
            trades=pd.DataFrame(columns=["entry_time","exit_time","side","gross_pnl","fees","net_pnl"])
        curve=pd.read_csv(equity_path)
        calc=_metrics(trades,curve,initial)
        if abs(calc["ending_equity"]-float(state["ending_equity"]))>1e-4:
            raise ValueError(f"{name} equity does not match simulator metrics")
        if len(trades)!=int(state["trades"]):
            raise ValueError(f"{name} trade count mismatch")
        if abs(calc["total_return_pct"]-float(state["return_pct"]))>1e-3:
            raise ValueError(f"{name} return does not match simulator metrics")
        report["partitions"][name]=calc
        report["input_sha256"][name]={"trades":_sha(trades_path),"equity":_sha(equity_path)}
    report["input_sha256"]["evaluation"]=_sha(root/"evaluation.json")
    destination=Path(output or root/"performance_report.json")
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input-dir",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    print(json.dumps(build_report(args.input_dir,output=args.output),indent=2,allow_nan=False))


if __name__=="__main__":
    main()
