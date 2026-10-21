# Global Stage Analysis — expansion roadmap

## Objective

Build a reliable global weekly Stage Analysis screener for individual stocks, broad-market ETFs, sector ETFs, and commodity proxies/series. Do not label a market or asset class "supported" until its source, rights, coverage, and price-quality checks pass.

## Current baseline (2026-10-21)

- Streamlit UI supports synthetic demo, CSV upload, and small-watchlist KIS US/Korea daily-price pilots. The Korea adapter is not yet live-API verified.
- Market-cap threshold is entered in USD billions ($B); the underlying CSV field remains USD dollars.
- Shared OHLCV validation is applied across data modes.
- Universe metadata validation and unit tests are separated from the UI.
- Stage labels remain heuristic screening labels; they have not been shown to be profitable.
- A hosted URL does not itself grant data-display or redistribution rights.

## Implementation phases

### Phase 1 — reliable normalized data contract
- [x] Normalize daily bars to `date, symbol, open, high, low, close, volume`.
- [x] Reject missing/non-numeric OHLCV, invalid prices, negative volume, inconsistent highs/lows, and conflicting duplicate symbol/date rows.
- [x] Deduplicate identical symbol/date rows.
- [x] Exclude the current incomplete weekly bar, including on Friday.
- [x] Validate universe symbols, asset types, exchange codes, names, and non-negative market cap.
- [ ] Extend automated tests to holiday weeks, split/dividend adjustments, missing sessions, timezone boundaries, and provider error cases.

### Phase 2 — provider interface and source approval
Each provider adapter must declare:
- markets, exchanges, asset classes, supported history depth, adjustment behavior, update cadence, rate limits, and known gaps;
- authentication method and secret names (never log or commit credentials);
- whether personal use, hosted display, caching, derived metrics, and CSV export are permitted by current terms;
- normalized OHLCV output and provider/source metadata.

No provider is selected merely because it is free or easy to query. Before implementation, confirm the intended deployment model and applicable exchange-level rights. The current KIS adapter remains US-only and a small-watchlist pilot until verified.

### Phase 3 — market and asset coverage, in order
1. US individual stocks and broad-market ETFs.
2. US sector ETFs and liquid commodity ETFs/proxies.
3. Broaden and live-validate Korean stocks and market/sector benchmarks (a KRX adapter now exists).
4. Japan and other major developed markets.
5. Commodity futures/spot series only when a suitable licensed series is available; do not silently substitute an ETF for a futures/spot series.
6. Additional regions only after symbols, exchange calendars, currency, and sector taxonomy are mapped.

Coverage is driven by provider capabilities, not by UI labels. A market is not supported just because users can type a ticker.

### Phase 4 — durable universe and reference data
Maintain, with provenance and an as-of date where relevant:
- canonical instrument ID and symbol history;
- country, exchange, currency, exchange timezone, asset class and instrument type;
- market cap in native currency and USD equivalent, valuation timestamp and FX source;
- sector/industry taxonomy and mapping source;
- market and sector benchmark assignments;
- active/delisted status and corporate-action policy.

Keep symbols, instruments, and providers separate: tickers can change, be reused, or differ by exchange.

### Phase 5 — scale and daily operations
- Fetch incrementally from the last successful date instead of downloading the full history each run.
- Cache by provider/instrument/date range; store request timestamps and provider status.
- Add per-symbol error reporting and retries with bounded backoff.
- Use batch endpoints where authorized; rate-limit requests and avoid concurrent bursts.
- Add data freshness, coverage, missing-bar, and adjustment-quality indicators.
- Keep credentials in Streamlit secrets or a dedicated secret manager; never in CSVs or Git.

### Phase 6 — strategy validation and release
- Compare daily/weekly bars with an authorized reference across random dates and corporate actions.
- Test holiday weeks and partial-week behavior for each exchange timezone.
- Backtest Stage rules with transaction costs, delisted names, point-in-time universe membership, and survivorship-bias controls before presenting performance claims.
- Keep the app in demo/CSV mode until live provider rights and production quality are confirmed.
- Verify Streamlit deployment after every relevant commit; a GitHub commit does not prove the hosted app has restarted successfully.

## Target instrument schema

Required today: `symbol, name, market, sector, asset_type, market_cap_usd, market_benchmark, sector_benchmark`.

Optional metadata may be added without breaking older CSVs:
- `country`, `currency`, `exchange_timezone`, `provider`
- `market_cap_asof`, `sector_source`, `instrument_type`, `active`

The canonical price-bar schema is `date, symbol, open, high, low, close, volume`. Keep raw provider payloads out of the screen engine; normalize them in adapters before analysis.

## Current release gate

**Code tests pass for the baseline validation changes, but live KIS behavior, rights for hosted display, broad-market coverage, and latest Streamlit deployment remain separate verification tasks.** Do not represent the full global universe as complete until those gates pass.
