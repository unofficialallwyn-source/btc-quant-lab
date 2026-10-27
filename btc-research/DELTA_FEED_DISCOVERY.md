# Delta India feed discovery and fixed-conversion policy

Official Delta India documentation says platform USD/INR conversion **is fixed at 85 INR per USD**, rather than the floating interbank rate: https://guides.delta.exchange/delta-exchange-india-user-guide/account-setup/usd-inr-rate and https://www.delta.exchange/support/solutions?articleId=80001200076.

**Historically applicable date range must be verified before the `delta_india_fixed_85` manifest policy is enabled.** The research input loader supports this with `fx_policy: "delta_india_fixed_85"`, `fx_policy_reference` pointing to the official documentation, and `fx_policy_effective_period_verified: true`. It produces exactly the observed mark timestamps with constant 85; this is contract settlement policy, not guessed market FX. Otherwise the previous strict observed `fx_1m.csv` requirement remains.

The official Delta history API documents `MARK:BTCUSD` and `FUNDING:BTCUSD` support, up to 2000 candles/page: https://docs.delta.exchange/. A sampled public MCP query returned historic mark candles but empty funding-history results. An empty response is evidence of missing data, **not evidence of zero funding**.

New manual GitHub workflow `BTC Delta external-feed discovery` runs all tests and a short **training-period-only** probe (default 2025-10-20 through 2025-10-21, exclusive) using a public read-only endpoint. It writes raw mark/funding candles and independent SHA-256 hashes, mark 1m CSV, observed/missing counts and a block explaining that funding OHLC cannot be equated to an actual settlement rate without verified reconciliation.

Never use the holdout period for research source discovery, strategy tuning or fee selection. Never fabricate historical funding settlements. A probe with all mark minutes but missing funding still leaves the Delta-integrated backtest blocked. For complete historical Phase 2 Step 3 validation, the remaining necessary work is a verifiable historical funding settlement source, whole-period mark coverage, and proven historical validity of the Delta fixed-85 INR conversion.

No live trading, no authenticated trading access, and no unconditional scheduled collectors.
