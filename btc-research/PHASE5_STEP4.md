# Phase 5 Step 4 — Trade and order-book data feasibility

## Decision
**Historical depth and trade-tape archives are NOT VERIFIED.** Do not infer availability of years of historical order flow from public *recent-trade* endpoints or live WebSocket streams. No new trading strategy, signal, out-of-sample analysis, or profitability claim is authorized.

## Source review
**Exchange docs:** https://docs.delta.exchange/ describes Delta India `GET /v2/trades/{symbol}` public trades, `GET /v2/l2orderbook/{symbol}` live L2 snapshot, public `trades` channel and `ob_l2` / `ob_updates` streams. See https://www.delta.exchange/blog/guide-to-api-trading-with-delta-india for the historical OHLCV `/v2/history/candles` endpoint. Interface documentation is not proof of years of historical trade or depth coverage. Exact exchange symbol, UTC timestamp precision, aggressor metadata, pagination/lookback and snapshot sequencing must be verified against read-only real data.

**Private quant-resources files actually reviewed:**
1. `extracted-text/madhavan-microstructure.txt` — Ananth Madhavan, *Market Microstructure: A Survey* (introduction and abstract): price discovery, market structure, transparency and trading-cost mechanisms. This motivates separate measurement of trades and executable quotes.
2. `extracted-text/Market microstructure and market liquidity.txt` — Muranaga & Shimizu, *Market Microstructure and Market Liquidity* (abstract and introduction): liquidity indicators can disagree; traded volume cannot stand in for executable depth.
3. `extracted-text/Algorithmic Trading From Beginner to Advanced.txt` (contents and beginning): Chapters 15–16 emphasize walk-forward and stress tests; these will matter after data certification.
4. `extracted-text/ALGORITHMIC TRADING2.txt` — Ernest P. Chan, *Algorithmic Trading: Winning Strategies and Their Rationale* (opening and contents): research and execution context, not evidence of this BTC strategy's profitability.

## Implementation
`src.phase5_trade_book_feasibility` builds a deterministic, documented capability registry and validates normalized *candidate* trade and book schemas. It uses **no live requests**, credentials, trading API or historical validation/holdout data. Its report states that no historical archive has been verified.

## Required next gates
1. Confirm actual public REST recent-trade lookback and whether trades contain reliable exchange aggressor side and unique trade IDs.
2. Confirm depth snapshot/update sequencing, clock precision, reconnect recovery and how feed gaps will be detected.
3. Verify historical archive supply, licensing, retention, rate limits and storage budget with the exchange or authorized vendor.
4. Run a small training-only read-only acquisition pilot with audit trail and raw response hashes.
5. Gate all order-flow feature/strategy research on certified tape and book data.

Run: `python -m src.phase5_trade_book_feasibility --output data/research/phase5-trade-book`.
