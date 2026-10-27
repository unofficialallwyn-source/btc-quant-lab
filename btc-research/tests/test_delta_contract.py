"""Validate published BTCUSD lot, fee, FX and margin arithmetic."""
from decimal import Decimal
import pytest
from src.delta_contract import (CONTRACT,round_price,quantize_lots,notional_usd,
 fee_inr,pnl_inr,required_margin_inr,funding_inr,margin_state)


def test_lot_and_tick():
    assert quantize_lots("0.004999")==4
    assert notional_usd(4,"100000")==Decimal("400.000")
    assert round_price("100000.26")==Decimal("100000.5")
    with pytest.raises(ValueError):
        quantize_lots(-.01)


def test_fees_gst_and_liquidity():
    # 1 lot at $100,000 = $100. At INR 85/USD, taker .05% + 18% GST
    assert fee_inr(1,100000,85)==Decimal("5.0150000000")
    assert fee_inr(1,100000,85,liquidity="maker")==Decimal("2.0060000000")
    with pytest.raises(ValueError,match="INR"):
        fee_inr(1,100000,0)


def test_long_short_usd_move_converts_to_inr():
    assert pnl_inr(1,2,100000,101000,85)==Decimal("170.000")
    assert pnl_inr(-1,2,100000,101000,85)==Decimal("-170.000")


def test_margin_maintenance_and_diagnostic_no_fake_liquidation():
    assert required_margin_inr(1,100000,85)==Decimal("42.5000000")
    assert required_margin_inr(1,100000,85,maintenance=True)==Decimal("21.2500000")
    s=margin_state(20,1,1,100000,100000,85)
    assert s["maintenance_breached"] is True
    assert s["liquidation_price_known"] is False
    with pytest.raises(ValueError,match="tiered"):
        required_margin_inr(2000,100000,85)


def test_funding_direction_and_bounds():
    assert funding_inr(1,1,100000,85,"0.001")==Decimal("8.5000000")
    assert funding_inr(-1,1,100000,85,"0.001")==Decimal("-8.5000000")
    with pytest.raises(ValueError,match="cap"):
        funding_inr(1,1,100000,85,"0.02")


def test_invalid_side_rejected():
    with pytest.raises(ValueError):
        pnl_inr(0,1,100000,100100,85)
