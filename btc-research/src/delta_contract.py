"""Delta Exchange India BTCUSD perpetual *research* accounting primitives.

Based on public specs, as of 2026-10-27. These rules are parameterized and
do NOT assert historical fee tiers, exact mark prices or historical funding.
All account balances are INR; USD prices require an explicit INR/USD rate.
No API orders and no liquidation-price prediction.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP


def D(value):
    return Decimal(str(value))


@dataclass(frozen=True)
class BTCUSDContract:
    lot_btc: Decimal = D("0.001")
    tick_usd: Decimal = D("0.5")
    maker_fee: Decimal = D("0.0002")
    taker_fee: Decimal = D("0.0005")
    gst_fraction: Decimal = D("0.18")
    initial_margin_rate: Decimal = D("0.005")
    maintenance_margin_rate: Decimal = D("0.0025")
    funding_interval_seconds: int = 28800
    max_leverage: Decimal = D("200")

    def check(self):
        if self.lot_btc<=0 or self.tick_usd<=0 or self.funding_interval_seconds<=0:
            raise ValueError("Invalid BTCUSD contract")
        if not (D(0)<=self.maker_fee<D(1) and D(0)<=self.taker_fee<D(1)
                and D(0)<=self.gst_fraction<D(1)
                and D(0)<self.maintenance_margin_rate<=self.initial_margin_rate<D(1)):
            raise ValueError("Invalid fee or margin schedule")


CONTRACT=BTCUSDContract()


def round_price(usd_price, contract=CONTRACT):
    price=D(usd_price)
    if price<=0:raise ValueError("Invalid USD price")
    return (price/contract.tick_usd).quantize(D(1),rounding=ROUND_HALF_UP)*contract.tick_usd


def quantize_lots(quantity_btc, contract=CONTRACT):
    """Nonnegative BTC quantity rounded DOWN to a tradable whole lot."""
    qty=D(quantity_btc)
    if qty<0:raise ValueError("Negative quantity")
    return int((qty/contract.lot_btc).to_integral_value(rounding=ROUND_FLOOR))


def notional_usd(lots, price_usd, contract=CONTRACT):
    if not isinstance(lots,int) or lots<0:raise ValueError("Lots must be nonnegative integers")
    price=D(price_usd)
    if price<=0:raise ValueError("Invalid USD price")
    return D(lots)*contract.lot_btc*price


def fee_inr(lots, price_usd, inr_per_usd, *, liquidity="taker", contract=CONTRACT):
    """Fee includes GST; INR conversion rate is supplied, never inferred."""
    contract.check()
    if liquidity not in ("maker","taker"):raise ValueError("Invalid liquidity type")
    fx=D(inr_per_usd)
    if fx<=0:raise ValueError("Valid INR per USD rate required")
    rate=contract.maker_fee if liquidity=="maker" else contract.taker_fee
    return notional_usd(lots,price_usd,contract)*fx*rate*(D(1)+contract.gst_fraction)


def pnl_inr(side, lots, entry_usd, exit_usd, inr_per_usd, contract=CONTRACT):
    """Simplified linear price-difference PnL at an explicit FX conversion."""
    if side not in (-1,1):raise ValueError("Side must be +1 or -1")
    if D(inr_per_usd)<=0:raise ValueError("Valid FX rate required")
    if D(entry_usd)<=0 or D(exit_usd)<=0:raise ValueError("Invalid price")
    notional_usd(lots,entry_usd,contract)
    return D(side)*D(lots)*contract.lot_btc*(D(exit_usd)-D(entry_usd))*D(inr_per_usd)


def required_margin_inr(lots,mark_usd,fx,*,maintenance=False,contract=CONTRACT):
    """Base-tier margin only. Larger notional tiers must be modeled separately."""
    n=notional_usd(lots,mark_usd,contract)
    if n>D("100000"):
        raise ValueError("Above $100,000: tiered margin scaling not implemented")
    if D(fx)<=0:raise ValueError("Valid FX rate required")
    rate=contract.maintenance_margin_rate if maintenance else contract.initial_margin_rate
    return n*D(fx)*rate


def funding_inr(side,lots,mark_usd,fx,funding_rate,contract=CONTRACT):
    """Signed payment: positive = debit, negative = credit.

    Positive funding rate means long pays short. Caller must supply the actual
    funding rate and settlement event; OHLCV alone cannot provide this.
    """
    if side not in (-1,1):raise ValueError("Invalid side")
    rate=D(funding_rate)
    if not D("-0.01")<=rate<=D("0.01"):
        raise ValueError("Funding rate exceeds configured absolute 1% cap")
    return D(side)*notional_usd(lots,mark_usd,contract)*D(fx)*rate


def margin_state(cash_inr,side,lots,entry_usd,mark_usd,fx,contract=CONTRACT):
    """Diagnostic only: threshold breach, NOT an executable liquidation fill."""
    equity=D(cash_inr)+pnl_inr(side,lots,entry_usd,mark_usd,fx,contract)
    maintenance=required_margin_inr(lots,mark_usd,fx,maintenance=True,contract=contract)
    return {"equity_inr":equity,"maintenance_inr":maintenance,
            "maintenance_breached":equity<=maintenance,
            "liquidation_price_known":False}
