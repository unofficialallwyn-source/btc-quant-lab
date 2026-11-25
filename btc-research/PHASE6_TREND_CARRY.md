# Phase 6 — Cost-feasible, volatility-targeted trend (+ funding carry) and an execution path

## Why Phases 3–5 could not work: the turnover "speed limit"
Robert Carver, *Systematic Trading* (`quant-resources/extracted-text/《Systematic_Trading》－Robert_Carver_2015.txt`, "Setting a speed limit", ~lines 6844–6900): a realistic per-instrument Sharpe ratio is about 0.4, and you shouldn't spend more than a third of it on costs. That puts annual costs at no more than **0.13 SR**. Cost in SR = turnover (round trips per year) × standardised cost per round trip.

These are the Delta India BTCUSD perp costs at the repo's assumptions:

| item | value |
|---|---|
| taker fee × (1 + 18% GST) + slippage, per side | 0.05% × 1.18 + 0.025% = **0.084%** |
| round trip | 0.168% |
| BTC annual volatility (typical) | ~55% |
| standardised cost | 0.168% / 55% ≈ **0.0031 SR per round trip** |
| speed limit | 0.13 / 0.0031 ≈ **42 round trips / year** |

Phase 3's training runs made 1,884–3,550 trades over ~1.6 years. That's roughly 1,100–2,200 round trips a year, or **3.5–6.5 SR of cost every year**. No realistic signal can pay that, which is why every variant lost 92–99%. Phase 4's frozen hypotheses were also 5m/60-minute-hold systems. The problem is the holding period, not the specific entry rule.

## Strategy (pre-registered, nothing fitted)
`src/trend_carry.py` uses only constants published in Carver's book:
- **EWMAC trend** at speeds 8/32, 16/64 and 32/128 days, computed on hourly closes (spans × 24). Each speed is normalised by daily price volatility, multiplied by Carver's published forecast scalar (5.3 / 3.75 / 2.65) and capped at ±20. The speeds are equally weighted, with FDM 1.1.
- **Optional funding carry** (`carry_weight` 0.25 in one variant): when longs pay funding the forecast goes negative. It uses a smoothed 30-day annualised funding rate divided by volatility, with scalar 30.
- **Volatility targeting**: 20% annualised. The volatility estimate blends 36-day and 365-day EWMA of hourly returns, floored at 25%. Leverage is capped at 2×.
- **Position buffering**: no trade inside ±10% of the average position, with a minimum width of 1 lot. This stops integer-lot churn, a bug caught in testing.
- Execution happens at the next hourly open, in integer 0.001 BTC lots.

The variant family is declared in `phase6_research.py` before any result exists: three single speeds, the PRIMARY (combined), long-only, and +carry. The PRIMARY spec SHA-256 is printed in every report.

## Backtester and controls
- `src/perp_backtest.py`: hourly linear-perp ledger. It charges taker fee × (1+GST), slippage, and funding cash flows at 8-hourly settlements. Funding is either observed, or an assumed rate you supply explicitly; it's never silently zero, and the report says which applied. P&L is in USD and also reported in INR at a fixed 85. Data gaps split segments and positions are flattened. A maintenance-margin breach is flagged.
- `src/overfitting.py` covers three checks. The **Deflated Sharpe Ratio** (AFML §14.7.3) counts this family plus the 22 earlier failed trials in the repo. **PBO via CSCV** follows Bailey et al., *The Probability of Backtest Overfitting*. The **speed-limit** check is from Carver.
- Training gate (fail-closed): annual Sharpe ≥ 0.3, max drawdown ≤ 35%, speed limit passes, PBO ≤ 0.5, Deflated Sharpe ≥ 0.80, no margin breach. Validation needs a human decision. The holdout refuses to run without `--confirm-frozen-spec <PRIMARY sha256>`.

## Data
`src/delta_hourly_data.py` downloads **public** Delta India `BTCUSD` 1h candles and `FUNDING:BTCUSD` candles. No keys or Azure access are needed. Funding units (percent vs decimal) are inferred and recorded, and the manifest labels funding as `ESTIMATE_FROM_PUBLIC_CANDLES_UNRECONCILED`.

**Limitation:** Delta India history covers only a few years. That's short for statistical evidence about slow trend rules: Carver's tables need decades to tell apart Sharpe ratios of a few tenths. A stronger study would run the same code on longer BTC hourly history from another venue (any CSV with `time,open,high,low,close`), and use Delta data to calibrate costs and funding.

## Run
Workflow **BTC Phase 6 vol-targeted trend research (public Delta data)**, `training` partition. Locally:
```bash
python -m src.delta_hourly_data --start 2023-01-01 --end 2026-11-25 --output data/phase6
python -m src.phase6_research --data-dir data/phase6 --output data/backtest/phase6
```

## Execution path (only after the gate passes and a human reviews)
`src/live/trader.py` runs the same functions as the research code, once per completed UTC hour:
`paper` (default, no keys) → `testnet` (Delta demo keys, `https://cdn-ind.testnet.deltaex.org`) → `live` (refused unless `DELTA_LIVE_CONFIRM=I_ACCEPT_REAL_MONEY_RISK`).
Guards: kill-switch file `state/KILL` (flattens with reduce-only orders, then stops), stale-data refusal, idempotent per bar, max contracts, max order size, leverage cap, daily-loss lock (reduce-only), order POSTs never auto-retried, every decision journaled to `state/<mode>_journal.jsonl`. Optional `--execution maker_first` posts a post-only limit at the top of book and falls back to market after 60 s, since maker fees are 0.02% vs 0.05% taker.
Deployment: `deploy/btc-trader.service` (systemd, secrets in `/etc/btc-trader.env`).

## Claude Code agents and Delta MCP
- `.mcp.json` registers the official `delta-exchange-mcp` server (via `uvx`), defaulting to `india_testnet`. Keys are **not** in the repo; put them in `~/.delta-exchange-mcp/config.env`, which is what the MCP project recommends.
- Give the MCP a **Read Data** key. The server has no confirmation step and no size caps, so the key's permissions are the only gate. `.claude/settings.json` additionally denies `close_all_positions`.
- `.claude/agents/`: `trade-monitor` (reconciles journal against exchange and can engage the kill switch; never trades), `risk-officer` (pre-merge and pre-live checklist), `quant-researcher` (pre-registered, training-only hypotheses from quant-resources).
- Orders are placed by the deterministic trader, not by an LLM. The agents observe, review and can only stop trading.

No profitability is claimed. The real-data result is whatever the training gate reports.
