"""Phase 6 research runner: slow vol-targeted trend/carry on hourly BTCUSD perp data.

The variant family and the PRIMARY candidate are declared here, before any
result is seen. The runner evaluates one chronological partition at a time:
training (default) -> validation (only for the frozen primary) -> holdout
(requires --confirm-frozen-spec with the primary's SHA-256; run once).
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .trend_carry import TrendCarrySpec, HOURS_PER_YEAR
from .perp_backtest import CostModel, run
from .overfitting import deflated_sharpe, pbo_cscv, speed_limit

PRIMARY = TrendCarrySpec()
PRIOR_TRIALS_IN_REPO = 22  # Phase 3 grid (16) + Phase 3 strategies (3) + Phase 4 hypotheses (3)

GATE = {"min_annual_sharpe": 0.3, "max_drawdown_pct": 35.0, "max_pbo": 0.5,
        "min_deflated_sharpe": 0.80, "speed_limit_cost_sr": 0.13}


def family(has_funding):
    fam = {
        "ewmac_8_32": replace(PRIMARY, name="ewmac_8_32", ewmac_days=((8, 32),)),
        "ewmac_16_64": replace(PRIMARY, name="ewmac_16_64", ewmac_days=((16, 64),)),
        "ewmac_32_128": replace(PRIMARY, name="ewmac_32_128", ewmac_days=((32, 128),)),
        PRIMARY.name: PRIMARY,
        "primary_long_only": replace(PRIMARY, name="primary_long_only", long_only=True),
    }
    if has_funding:
        fam["primary_plus_carry"] = replace(PRIMARY, name="primary_plus_carry", carry_weight=0.25)
    return fam


def partition(frame, which):
    t0, t1 = int(frame.time.iloc[0]), int(frame.time.iloc[-1]) + 3600
    a = t0 + int((t1 - t0) * 0.6) // 3600 * 3600
    b = t0 + int((t1 - t0) * 0.8) // 3600 * 3600
    bounds = {"training": (t0, a), "validation": (a, b), "holdout": (b, t1)}[which]
    return frame[(frame.time >= bounds[0]) & (frame.time < bounds[1])].reset_index(drop=True), bounds


def load(data_dir):
    d = Path(data_dir)
    px = pd.read_csv(d / "btcusd_1h.csv")
    fund = pd.read_csv(d / "funding.csv") if (d / "funding.csv").exists() else None
    return px.sort_values("time").reset_index(drop=True), fund


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--partition", choices=["training", "validation", "holdout"], default="training")
    p.add_argument("--confirm-frozen-spec", default=None)
    p.add_argument("--equity-usd", type=float, default=10000.0)
    p.add_argument("--assume-funding-rate", type=float, default=None,
                   help="per-settlement rate used when no observed funding (e.g. 0.0001)")
    p.add_argument("--taker-fee", type=float, default=0.0005)
    p.add_argument("--slippage", type=float, default=0.00025)
    a = p.parse_args(argv)

    if a.partition == "holdout" and a.confirm_frozen_spec != PRIMARY.sha256():
        raise SystemExit("Holdout is sealed: pass --confirm-frozen-spec <PRIMARY sha256> to run it once")
    px, fund = load(a.data_dir)
    cost = CostModel(taker_fee=a.taker_fee, slippage=a.slippage, assumed_funding_rate=a.assume_funding_rate)
    fam = family(fund is not None) if a.partition == "training" else {PRIMARY.name: PRIMARY}
    part, bounds = partition(px, a.partition)
    results, hourly = {}, {}
    for name, spec in fam.items():
        # warm-up: evaluate only inside the partition; forecasts need slow-span history,
        # so prior (earlier, already-seen) bars are used for indicator warm-up only.
        warm = max(s for _, s in spec.ewmac_days) * 24 * 2
        start = max(int(px.time.iloc[0]), bounds[0] - warm * 3600)
        window = px[(px.time >= start) & (px.time < bounds[1])].reset_index(drop=True)
        summary, curve, ledger = run(window, spec, cost, fund, a.equity_usd)
        inside = curve[curve.time >= bounds[0]].reset_index(drop=True)
        # restate metrics on the partition only (warm-up P&L excluded by re-basing)
        eq = inside.equity.to_numpy()
        rets = np.diff(eq) / eq[:-1] if len(eq) > 1 else np.array([0.0])
        hourly[name] = rets
        ann_sr = rets.mean() / rets.std(ddof=1) * np.sqrt(HOURS_PER_YEAR) if rets.std(ddof=1) > 0 else 0.0
        peak = np.maximum.accumulate(eq)
        summary.update({"partition_return_pct": round((eq[-1] / eq[0] - 1) * 100, 4) if len(eq) else 0.0,
                        "partition_annual_sharpe": round(float(ann_sr), 4),
                        "partition_max_drawdown_pct": round(float(((peak - eq) / peak).max() * 100), 4),
                        "spec": spec.to_dict(), "spec_sha256": spec.sha256()})
        sl = speed_limit(summary["turnover_round_trips_per_year"],
                         summary["standardised_cost_sr_per_round_trip"], GATE["speed_limit_cost_sr"])
        summary["speed_limit"] = sl
        results[name] = summary
        out = Path(a.output) / a.partition / name
        out.mkdir(parents=True, exist_ok=True)
        curve.to_csv(out / "equity.csv", index=False)
        ledger.to_csv(out / "fills.csv", index=False)

    primary = results[PRIMARY.name]
    report = {"partition": a.partition, "bounds_utc": bounds, "primary": PRIMARY.name,
              "primary_spec_sha256": PRIMARY.sha256(), "gate": GATE, "results": results,
              "funding": "observed" if fund is not None else (
                  f"assumed {a.assume_funding_rate}" if a.assume_funding_rate is not None else "NOT MODELLED"),
              "live_trading_enabled": False}
    if a.partition == "training":
        n = min(len(v) for v in hourly.values())
        matrix = np.column_stack([v[-n:] for v in hourly.values()])
        trial_srs = [float(np.mean(c) / np.std(c, ddof=1)) if np.std(c, ddof=1) > 0 else 0.0 for c in matrix.T]
        trial_srs += [0.0] * PRIOR_TRIALS_IN_REPO  # failed prior trials, assumed ~zero skill
        dsr = deflated_sharpe(hourly[PRIMARY.name], trial_srs)
        pbo = pbo_cscv(matrix, 10)
        report.update({"deflated_sharpe": dsr, "pbo": pbo})
        checks = {
            "sharpe": primary["partition_annual_sharpe"] >= GATE["min_annual_sharpe"],
            "drawdown": primary["partition_max_drawdown_pct"] <= GATE["max_drawdown_pct"],
            "speed_limit": primary["speed_limit"]["passes"],
            "pbo": pbo["pbo"] <= GATE["max_pbo"],
            "deflated_sharpe": dsr["deflated_sharpe"] >= GATE["min_deflated_sharpe"],
            "no_margin_breach": not primary["margin_breach"],
        }
        report["checks"] = checks
        report["decision"] = ("TRAINING_GATE_PASSED_MANUAL_VALIDATION_REVIEW" if all(checks.values())
                              else "REJECTED_TRAINING_GATE")
    else:
        report["decision"] = f"{a.partition.upper()}_EVALUATED_REVIEW_REQUIRED"
    path = Path(a.output) / a.partition / "phase6_report.json"
    path.write_text(json.dumps(report, indent=2, default=float) + "\n")
    print(json.dumps({k: report[k] for k in report if k != "results"}, indent=2, default=float))
    print(json.dumps({k: {m: v[m] for m in ("partition_return_pct", "partition_annual_sharpe",
                     "partition_max_drawdown_pct", "turnover_round_trips_per_year", "fees_usd",
                     "funding_usd")} for k, v in results.items()}, indent=2))
    return report


if __name__ == "__main__":
    main()
