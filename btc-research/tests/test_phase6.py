import numpy as np
import pandas as pd
import pytest

from src.trend_carry import TrendCarrySpec, forecasts, ideal_contracts, buffered_target
from src import perp_backtest as pb
from src.overfitting import deflated_sharpe, pbo_cscv, probabilistic_sharpe, speed_limit
from src.phase6_research import PRIMARY, main as research_main


def hourly(n=24 * 400, seed=0, drift=0.0, start=1_700_000_000 // 3600 * 3600):
    rng = np.random.default_rng(seed)
    close = 50000 * np.exp(np.cumsum(rng.normal(drift, 0.006, n)))
    op = np.r_[close[0], close[:-1]]
    return pd.DataFrame({"time": start + np.arange(n) * 3600, "open": op,
                         "high": np.maximum(op, close) * 1.001, "low": np.minimum(op, close) * 0.999,
                         "close": close, "volume": 1.0})


def test_forecasts_are_causal():
    df = hourly()
    spec = TrendCarrySpec()
    full = forecasts(df, spec)
    cut = 24 * 300
    tampered = df.copy()
    tampered.loc[cut + 1:, ["open", "high", "low", "close"]] *= 3.0
    part = forecasts(tampered, spec)
    pd.testing.assert_series_equal(full.forecast.iloc[:cut + 1], part.forecast.iloc[:cut + 1])


def test_forecast_capped_and_warmup_flat():
    fc = forecasts(hourly(drift=0.002), TrendCarrySpec())
    assert fc.forecast.abs().max() <= 20 + 1e-9
    assert fc.forecast.iloc[:24 * 100].isna().all()


def test_position_sizing_and_buffer():
    spec = TrendCarrySpec()
    ideal = ideal_contracts(10, 100000, 0.5, 10000, spec)  # 10k*0.2/0.5 = 4000 USD = 40 lots
    assert ideal == pytest.approx(40)
    assert ideal_contracts(20, 100000, 0.10, 10000, spec) == pytest.approx(200)  # 2x leverage cap
    assert buffered_target(39, 40, 100000, 0.5, 10000, spec) == 39            # inside buffer
    assert buffered_target(0, 40, 100000, 0.5, 10000, spec) == 36             # trade to edge
    assert buffered_target(1, 1.6, 100000, 0.5, 300, spec) == 1                # >=1 lot buffer, no churn


def test_random_walk_has_no_edge_and_costs_reconcile():
    summary, curve, ledger = pb.run(hourly(n=24 * 500, seed=3), PRIMARY)
    recon = summary["gross_pnl_usd"] - summary["fees_usd"] - summary["slippage_usd"] + summary["funding_usd"]
    assert summary["ending_equity_usd"] - 1000 == pytest.approx(recon, abs=1e-2)
    assert curve.position.iloc[-1] == 0
    assert summary["turnover_round_trips_per_year"] < 40


def test_funding_sign_longs_pay():
    df = hourly(n=24 * 300, drift=0.0002)
    fund = pd.DataFrame({"time": df.time[df.time % 28800 == 0], "rate": 0.001})
    base, _, _ = pb.run(df, PRIMARY)
    paid, _, _ = pb.run(df, PRIMARY, funding=fund)
    assert paid["funding_usd"] < 0 and paid["funding_observed_events"] > 0
    assert paid["ending_equity_usd"] < base["ending_equity_usd"]


def test_gap_splits_segments_and_flattens():
    df = hourly(n=24 * 300)
    df = df.drop(index=range(24 * 200, 24 * 200 + 5)).reset_index(drop=True)
    _, curve, ledger = pb.run(df, PRIMARY)
    assert curve.segment.nunique() == 2


def test_psr_dsr_and_pbo():
    rng = np.random.default_rng(0)
    good = rng.normal(0.001, 0.01, 5000)
    assert probabilistic_sharpe(good) > 0.99
    noise = rng.normal(0, 0.01, (4000, 8))
    d = deflated_sharpe(noise[:, 0], [noise[:, j].mean() / noise[:, j].std() for j in range(8)] + [0] * 20)
    assert d["deflated_sharpe"] < 0.9
    res = pbo_cscv(noise, 8)
    assert 0 <= res["pbo"] <= 1 and res["combinations"] == 70
    skill = noise.copy(); skill[:, 3] += 0.002
    assert pbo_cscv(skill, 8)["pbo"] < 0.05


def test_speed_limit():
    assert speed_limit(1000, 0.003)["passes"] is False
    assert speed_limit(12, 0.003)["passes"] is True


def test_runner_rejects_random_walk_and_seals_holdout(tmp_path):
    df = hourly(n=24 * 700, seed=5)
    df.to_csv(tmp_path / "btcusd_1h.csv", index=False)
    report = research_main(["--data-dir", str(tmp_path), "--output", str(tmp_path / "out")])
    assert report["decision"] in ("REJECTED_TRAINING_GATE", "TRAINING_GATE_PASSED_MANUAL_VALIDATION_REVIEW")
    assert report["live_trading_enabled"] is False
    with pytest.raises(SystemExit):
        research_main(["--data-dir", str(tmp_path), "--output", str(tmp_path / "o2"), "--partition", "holdout"])
