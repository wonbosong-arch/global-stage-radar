# Market Data Provider Validation Checklist

Status: **in progress**. No provider is approved for live public display.

## Why the license gate comes first

The intended app is hosted online and may display derived screening tables, charts, and CSV exports. API access is not equivalent to permission to display or redistribute its data.

- **Yahoo Finance**: Yahoo Help explicitly says not to redistribute information displayed or provided by Yahoo Finance. This blocks using it as the default source for a public-facing dashboard unless a separate right is confirmed. Source: [Yahoo Finance data providers and exchanges](https://help.yahoo.com/kb/finance/article-exchanges-data-delays-sln2310.html).
- **Twelve Data**: its individual plans are described as personal/internal/non-commercial; its support page says those plans do not permit redistribution or commercial display to third parties. Business plans may allow commercial display subject to exchange licenses, and redistribution requires a separate agreement. Sources: [usage policy](https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage), [pricing](https://twelvedata.com/pricing).
- **Financial Modeling Prep (FMP)**: its current pricing page says displaying or redistributing sourced data requires a specific Data Display and Licensing Agreement. Source: [FMP pricing and licensing](https://site.financialmodelingprep.com/developer/docs/pricing?planType=commercial).
- **Alpha Vantage**: its official support page states the free service covers most datasets at 25 requests/day, with unlimited requests for verified open-source or educational projects. That quota alone does not grant public display rights; terms must be checked for the specific use. Source: [Alpha Vantage support](https://www.alphavantage.co/support/).

These sources make the practical result clear: none of the above is automatically approved for a public production dashboard on the basis of a free API key. A private personal-use prototype may have different permissions, but those must also be confirmed against the current terms and the intended use.

## Gate 1 — rights and intended use
- Confirm terms allow the exact purpose, audience, hosted dashboard, derived metrics, storage/cache, and CSV export.
- Confirm whether public or private access changes the license requirements.
- Confirm attribution requirements and exchange-level licensing.
- Never commit API keys to GitHub. Use hosting secrets only after a provider is approved.

## Gate 2 — data requirements
- Daily adjusted OHLCV, preferably 5+ years of history.
- Document splits, dividends, delistings, symbol changes, timezone and market holidays.
- Market capitalization with currency, as-of date, and clear definition (latest vs historical).
- Country/market and sector classification with provenance.
- Market and sector benchmarks for relative-strength comparisons.
- Commodity spot/futures series kept distinct from commodity ETFs and related companies.
- Record request limits, history depth, endpoints available on free tiers, and rate limits.

## Candidate provider assessment

| Provider | What looks useful | Blocking question / current posture |
|---|---|---|
| Yahoo Finance / yfinance | Broad ticker coverage and convenient historical series | Redistribution is prohibited in Yahoo's help text; do not use for public live display without explicit rights. Unofficial access adds reliability risk. |
| Alpha Vantage | Official API; free access to selected datasets | 25 requests/day is too low for broad daily screening unless eligible for its open-source/educational exception; verify terms and market-cap/sector coverage. |
| Twelve Data | Structured API, multiple markets, market and commodity endpoints | Individual free plan is not a public-display license; paid business/display terms and exchange licenses may be needed. |
| FMP | Stocks, company profiles, market cap and fundamentals | Public display/redistribution requires a specific agreement; free quota does not solve licensing. |
| Stooq | Potential exploratory historical data | Coverage, corporate-action adjustment, service stability, and redistribution permissions remain unverified; not approved yet. |
| Coinbase Exchange public candles | Implemented for BTC-USD and ETH-USD daily OHLCV; separate from KIS and scheduled after UTC daily close | Technical fetch is working, but current API terms, hosted display, retention, and redistribution rights still need review; not approved for public production. |
| Official exchange/vendor feeds | Best route to clear source and data-quality documentation | Likely requires licensing and/or payment; evaluate only after a small universe and usage model are agreed. |
| FRED | Selected macroeconomic series | Not a replacement for global daily equity OHLCV, market cap, or traded commodity series. |

## Data validation protocol

1. Start with 20 US stocks, two broad-market ETFs, two sector ETFs, and two commodity series.
2. Compare at least 20 randomly selected dates per symbol with a trusted/authorized reference.
3. Check adjusted vs unadjusted closes, splits/dividends, missing days, duplicate rows, timezone handling, and weekly aggregation around holidays.
4. Check market-cap currency and timestamp, sector mappings, delisted symbols, and ticker changes.
5. Verify the license covers the exact deployment and whether derived values, screenshots, exports, and downloads are permitted.
6. Only then add automated daily refresh and broaden to Korea, Japan, and other markets.

## Decision rule

Until a source passes both the **data-quality gate** and the **rights gate**, keep the app in synthetic-demo or user-supplied-CSV mode. This is safer than quietly wiring a convenient but unauthorized feed into a public website.
