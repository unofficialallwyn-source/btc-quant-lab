# Phase 5 Step 3 — Market Microstructure Research and Data Feasibility

## Research sources already read from private quant-resources extracted text

1. **Ananth Madhavan — Market Microstructure: A Survey** (`extracted-text/madhavan-microstructure.txt`). The model discussion distinguishes observed transactions from efficient prices and discusses signed order flow and the bid-ask spread (around extracted lines 172–188). We should avoid assuming minute candle range is spread or candle direction identifies the aggressor.
2. **Paolo Vitale — A Guided Tour of the Market Microstructure Approach to Exchange Rate Determination** (`extracted-text/A Guided Tour of the Market Microstructure Approach to Exchange Rate Determination.txt`). The introduction examines the relationship between order flow and exchange-rate changes and time-series estimates. Foreign exchange findings are not automatically transferable to Delta India BTCUSD.
3. **Muranaga and Shimizu — Market Microstructure and Market Liquidity** (`extracted-text/Market microstructure and market liquidity.txt`). Their abstract emphasizes that liquidity indicators can behave inconsistently in simulated markets; do not label volume as directly executable liquidity.
4. **Algorithmic Trading From Beginner to Advanced** (`extracted-text/Algorithmic Trading From Beginner to Advanced.txt`), especially section 3.4, emphasizes commission, slippage and sizing realism; Chapters 15–16 concern stability and stress testing. This supplements the execution-feasibility framing.
5. **Ernest P. Chan — Algorithmic Trading: Winning Strategies and Their Rationale** (`extracted-text/ALGORITHMIC TRADING2.txt`), warns about ignoring transaction costs and in-sample selection in example backtests. The book references Chan's separate earlier *Quantitative Trading*. These are not proof of BTC strategy profitability.

Source URLs are private GitHub paths under https://github.com/unofficialallwyn-source/quant-resources/tree/main/extracted-text .

## What Step 3 implements

The audit consumes only the verified `dataset_catalog.json` archived with Phase 5 Step 1, without downloading candle or future validation/holdout price data. The underlying ingestion schema is **time, open, high, low, close, volume**. The audit classifies:

- **OHLCV proxies available:** bar returns, bar range, total bar volume, bar-sampled realized volatility. These are **not** aggressor-volume, bid-ask, or executable-depth observations.
- **Not available without new source data:** signed trade-volume delta, trade-count imbalance, best-bid/ask spread, order-book depth imbalance, trade-to-quote impact, and absorption.

The report records verified minute count, coverage and gap count provenance, missing source fields, and next-stage data contract for a trade tape, synchronized order book and realistic execution assumptions. No market microstructure metric is fabricated.

## Data feasibility gates before implementing actual order-flow research

1. Verify exchange historical market-trade availability, whether aggressor side is supplied, and instrument/feed semantics.
2. Verify best-bid/ask snapshots and incremental depth history, sequencing, outages and quote/trade clock synchronization.
3. Determine feasible historical retention, licensing, fees, rate limits, source continuity and storage budget.
4. Choose training-only time windows and gap-safe quality control, keeping validation and holdout untouched.
5. Only after quality certification, predeclare separately testable order-flow hypotheses. Never treat promising exploratory charts as qualified trading signals.

## Run

After review, dispatch `BTC Phase 5 microstructure data feasibility` on main with default `source_run_id=40802892631`. Archive `microstructure_feasibility.json`.

This is a **feasibility audit**, not a market profitability backtest. The source papers and books improve methodology, not guaranteed returns.
