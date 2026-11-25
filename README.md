# BTC Quant Lab

BTCUSD quantitative research with reproducible historical data, simulation-only backtesting, and strict out-of-sample evaluation. **No validated profitable strategy is provided.** Phase 6 adds a cost-feasible, volatility-targeted trend/carry research track and a paper → testnet → live execution path that stays gated: see [`btc-research/PHASE6_TREND_CARRY.md`](btc-research/PHASE6_TREND_CARRY.md).

## Repository

- `btc-research/src/ingest.py`: historical candle fetch interface, OHLCV audit, timestamp checks, and minute-to-five-minute resampling.
- `btc-research/src/research.py`: initial Donchian breakout benchmark and chronological training/validation/holdout runs.
- `btc-research/src/trend_carry.py`, `perp_backtest.py`, `overfitting.py`, `phase6_research.py`, `delta_hourly_data.py`: Phase 6 research (EWMAC + vol targeting, hourly perp ledger with funding, Deflated Sharpe / PBO / speed limit, public Delta data).
- `btc-research/src/live/`: signed Delta India REST client and the guarded trader (paper default).
- `.claude/agents/`, `.mcp.json`: Claude Code monitoring/review agents and the Delta Exchange MCP server config (testnet, read-only key recommended).
- `btc-research/tests/`: regression tests.
- `btc-research/requirements.txt`: Python dependencies.

## Run locally

```bash
cd btc-research
python -m pip install -r requirements.txt
pytest -q
python -m src.research --input data/btc_1m.parquet --output results
```

The input is a locally available Parquet dataset with `time,open,high,low,close,volume` columns, with candle-open timestamps in UTC Unix seconds. **The research command does not download candles.** Download and continuity validation remain outstanding.

## Data management

Use partitioned Parquet in private versioned object storage; commit ingestion code, manifests, checksums, and small reports, not massive raw candle files or exchange credentials. Reconstruct 5M/15M/1H/4H candles only from data available as of each backtest decision. Verify sampled reconstructed bars against native exchange bars.

## Research standards

1. Validate completeness and provenance of historical BTCUSD 1-minute candles.
2. Make ingestion restartable and capture exact UTC ranges and dataset hashes.
3. Use a $1,000 simulated portfolio with realistic fees, slippage, stop handling, and exposure limits.
4. Select parameters on training/validation only; preserve an untouched chronological holdout.
5. Report win rate, profit factor, drawdown, market regimes, and every fill assumption.

This repository contains BTC research exclusively. The previous CompTrail/PayLens Next.js application was removed in a dedicated cleanup PR and remains accessible in Git history.
