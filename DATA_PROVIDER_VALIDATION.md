# Market Data Provider Validation Checklist

Status: **in progress**. No provider is approved for live public display yet.

## Gate 1 — rights and intended use
- Confirm terms allow the intended personal research and hosted dashboard use.
- Confirm whether a public, unauthenticated Streamlit app can display the data.
- Confirm caching, storage, derived metrics, attribution and redistribution conditions.
- Do not commit API keys to GitHub. Use deployment secrets if a provider is later approved.

## Gate 2 — data requirements
- Daily adjusted OHLCV, preferably 5+ years of history.
- Clear treatment of splits, dividends, delistings, symbol changes and timezone/market holidays.
- Market capitalization with currency and as-of date.
- Country/market and sector classification with provenance.
- Benchmarks for both market-relative and sector-relative strength.
- Commodity spot/futures series as distinct instruments from commodity-related companies and ETFs.
- Document request limits, concurrent limits, rate limits and history limits.

## Initial provider posture
- **Yahoo Finance / yfinance**: broad coverage and useful for a private prototype, but unofficial access and usage/display rights need review. Not approved for public production by default.
- **Alpha Vantage**: free request limits are restrictive for broad universe screening; confirm the current official limits and licensing before use.
- **Financial Modeling Prep**: free quotas may be enough for a small test, but confirm endpoint availability, history, and public display rights.
- **Stooq**: potentially useful for exploratory history; coverage, adjustments, API stability and redistribution permissions require verification.
- **Official exchange/vendor feeds**: preferable for production reliability, but often require a paid license.
- **FRED**: useful for selected macroeconomic series, not a substitute for global daily equity OHLCV or weekly commodity trading data.

## Acceptance test before production
1. Select 20 representative US stocks, two broad-market ETFs, two sector ETFs, and two commodity series.
2. Compare at least 20 random dates per symbol against an authoritative source.
3. Verify corporate-action adjustments and weekly resampling around holidays.
4. Confirm market cap currency/as-of date and sector mappings.
5. Verify provider terms permit the exact deployment and display model.
6. Only then add automated daily refresh and broader markets.
