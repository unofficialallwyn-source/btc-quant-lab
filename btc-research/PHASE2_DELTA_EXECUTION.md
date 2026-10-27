# Phase 2 Step 3 — Delta Exchange India BTCUSD contract accounting (first increment)

Sources checked 2026-10-27:
- Official BTCUSD contract page: https://www.delta.exchange/en/contracts
- Exchange India fees page: https://www.delta.exchange/fees
- Exchange API documentation: https://docs.delta.exchange/

Published BTCUSD spec includes: perpetual future, 0.001 BTC per lot, $0.5 tick size, maker 0.02%, taker 0.05%, 0.5% base initial margin, 0.25% base maintenance margin, 8-hour funding interval, INR margin/effective settlement, and increased margin above $100,000 of notional. Fee page lists 18% GST. These values are **current reference defaults**, NOT proof of rates on every historical candle.

Implementation:
- `delta_contract.py` gives deterministic tick and integer-lot rounding, BTC price-difference linear P&L, fee+GST calculations, explicit INR/USD conversion, base-tier initial/maintenance margin, signed funding-payment arithmetic and **diagnostic** maintenance breach.
- `delta_accounting.py` can re-account existing simulated trades only when caller explicitly provides timestamp-aligned INR/USD conversion rates and a **certified list of funding events per trade**. Missing FX/funding event declarations raise rather than defaulting to zero. Fills from the previous simulator are not exchange-grade.
- Hard fail for margin schedules above USD 100,000 notional instead of silently applying inaccurate base rates.
- In contracts of size 0.001 BTC, previous simulated sizes under one lot cannot be traded. The adapter explicitly flags such sizes.
- No live orders, no secrets, no write API, and no change to baseline outputs or locked holdout.

**Important limitations before declaring Step 3 finished:**
1. Actual historical per-timestamp funding events, INR/USD conversion sources and fair/mark-price series have not been ingested. These cannot be inferred from ordinary OHLCV.
2. Liquidation is NOT simulated. Maintenance breach diagnostics alone cannot determine the true liquidation fill, penalties, insurance fund or ADL.
3. Exchange rounding, conversion/settlement, fee tier, historical changes, GST application and funding are parameterized, not independently reconciled against actual account statements.
4. The first-step reconciliation adapter does NOT replace the live run's execution/fill/position engine and must not be used to claim realistic returns.
5. No sample trade ledger is supplied to the automated workflow because doing so would require inventing funding/FX history.

Recommended validation: review and merge PR, run Python unit tests in GitHub Actions, inspect exact public contract settings. Then obtain historical funding, FX, mark-price and margin rules before integrating an exchange-grade backtest with real price series. The untouched holdout must stay locked.
