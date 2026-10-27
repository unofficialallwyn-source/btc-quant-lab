"""Re-account simulated trade fills under Delta India BTCUSD contract units.

Diagnostic comparison only: imported fills are from the old baseline engine,
not a new exchange-execution engine. Mandatory per-timestamp FX; funding events
must be explicitly supplied for any position spanning a funding settlement.
"""
import csv
import json
from pathlib import Path

from .delta_contract import (D, quantize_lots, pnl_inr, fee_inr,
                             notional_usd, required_margin_inr)


def reaccount_ledger(trades, fx_by_time, funding_by_time, *, opening_cash_inr):
    cash=D(opening_cash_inr)
    if cash<=0:raise ValueError("Initial INR cash must be positive")
    result=[]
    for record in trades:
        entry_time=int(record["entry_time"]);exit_time=int(record["exit_time"])
        if exit_time<entry_time:raise ValueError("Backwards trade")
        if entry_time not in fx_by_time or exit_time not in fx_by_time:
            raise ValueError("FX observations required at BOTH fill timestamps")
        side=int(record["side"])
        qty=D(record["quantity"])
        lots=quantize_lots(qty)
        if not lots:
            result.append({"entry_time":entry_time,"exit_time":exit_time,
                           "status":"untradeable_subminimum_lot","lots":0})
            continue
        entry=D(record["entry"]);exit_=D(record["exit"])
        fx_entry=D(fx_by_time[entry_time]);fx_exit=D(fx_by_time[exit_time])
        initial=required_margin_inr(lots,entry,fx_entry)
        entry_fee=fee_inr(lots,entry,fx_entry)
        if initial+entry_fee>cash:
            result.append({"entry_time":entry_time,"exit_time":exit_time,
                           "status":"insufficient_initial_margin","lots":lots})
            continue
        # Funding is deliberately NOT silently assumed to be zero. A caller
        # must supply an ordered list of (timestamp, rate, mark USD, INR/USD)
        # events for this trade, or certify it had no scheduled events.
        if entry_time not in funding_by_time:
            raise ValueError("Explicit funding event coverage required per trade")
        funding_events=funding_by_time[entry_time]
        if funding_events is None:
            raise ValueError("Missing funding events")
        previous=entry_time
        funding_total=D(0)
        for event in funding_events:
            t=int(event["time"])
            if not entry_time<t<=exit_time or t<=previous:
                raise ValueError("Funding events outside position / unordered")
            previous=t
            from .delta_contract import funding_inr
            funding_total+=funding_inr(side,lots,event["mark_usd"],
                                       event["inr_per_usd"],event["rate"])
        exit_fee=fee_inr(lots,exit_,fx_exit)
        price_pnl=pnl_inr(side,lots,entry,exit_,fx_exit)
        net=price_pnl-entry_fee-exit_fee-funding_total
        cash+=net
        result.append({"entry_time":entry_time,"exit_time":exit_time,"status":"accounted",
            "lots":lots,"price_pnl_inr":str(price_pnl),
            "entry_fee_gst_inr":str(entry_fee),"exit_fee_gst_inr":str(exit_fee),
            "funding_payment_inr":str(funding_total),
            "net_pnl_inr":str(net),"cash_after_inr":str(cash),
            "maintenance_liquidation_modeled":False})
    return {"opening_cash_inr":str(D(opening_cash_inr)),
            "ending_cash_inr":str(cash),
            "currency":"INR","liquidation_modeled":False,
            "fills_source":"previous baseline; NOT executable Delta matching-engine fills",
            "trades":result}
