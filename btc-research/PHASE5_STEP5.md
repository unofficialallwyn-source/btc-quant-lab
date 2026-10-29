# Phase 5 Step 5 — Read-only public trade / L2 snapshot pilot

## Research objective
Collect ONE recent-trade REST response and ONE current L2 REST snapshot for Delta Exchange India BTCUSD (public, unauthenticated, read-only). Preserve raw responses and SHA-256 digests, inspect aggressor fields, quote shape, and issue a fail-closed decision. No trading keys, authenticated data, orders, backtest, or holdout access.

## Data source
- https://docs.delta.exchange/ — GET /v2/trades/{symbol}, recent public trades; `side` identifies aggressor according to REST docs. Example records do not specify a unique trade ID, so unique trade IDs are **not assumed**.
- https://docs.delta.exchange/ — GET /v2/l2orderbook/{symbol}, current book with `buy`, `sell`, `last_updated_at`.
- The newer public WebSocket trades channel documents `r` buyer role, not REST `side`. `ob_updates` supports initial snapshot and increments, but this pilot does not certify reconstruction, sequence continuity or feed gap recovery.

## Actual quant-resources references carried into the decision
- `extracted-text/madhavan-microstructure.txt`, Ananth Madhavan: execution costs, price discovery and information in transactions.
- `extracted-text/Market microstructure and market liquidity.txt`, Muranaga and Shimizu: volume and liquidity indicators need not agree.
- `extracted-text/Algorithmic Trading From Beginner to Advanced.txt`, especially Chapters 15–16: walk-forward stability and stress tests required *after* data certification.
- `extracted-text/ALGORITHMIC TRADING2.txt`, Ernest Chan: research, execution and backtest assumptions.

## Important interpretation
A completed two-request REST pilot **does not** certify:
- historical archive depth/retention or an ability to backtest years of order flow;
- full trade tape completeness, deduplication, unique trade IDs, or exact-time quote-trade alignment;
- a synchronized streaming order book, dropped-update detection, sequence continuity or reconnect recovery;
- execution performance, alpha, or profitability.

A failed endpoint or schema triggers a nonzero workflow exit and keeps a report artifact. Successful snapshots still retain `NOT_READY_HISTORICAL_TAPE_AND_DEPTH_UNVERIFIED` as the research decision.

## Follow-on research gate
If REST snapshots succeed, propose a separate bounded WebSocket continuity experiment and/or exchange/vendor historical archive verification. Do not promote any strategy until reliable historical evidence, train/validation splits and realistic costs are available.

## Run
`python -m src.phase5_readonly_pilot --output data/research/phase5-readonly-pilot`
