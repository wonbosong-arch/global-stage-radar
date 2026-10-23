# Global Stage Analysis — expansion roadmap

## Objective

Build a reliable global weekly Stage Analysis screener for individual stocks, broad-market ETFs, sector ETFs, and commodity ETFs/proxies and commodity spot/futures series. Do not label a market or asset class "supported" until its source, rights, coverage, and price-quality checks pass.

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
- [x] Add a structural test for the default global ETF-proxy universe and its benchmark references.

### Phase 2 — provider interface and source approval
Each provider adapter must declare:
- markets, exchanges, asset classes, supported history depth, adjustment behavior, update cadence, rate limits, and known gaps;
- authentication method and secret names (never log or commit credentials);
- whether personal use, hosted display, caching, derived metrics, and CSV export are permitted by current terms;
- normalized OHLCV output and provider/source metadata.

No provider is selected merely because it is free or easy to query. Before implementation, confirm the intended deployment model and applicable exchange-level rights. The current KIS adapter remains US-only and a small-watchlist pilot until verified.

### Phase 3 — market and asset coverage, in order
1. Use KIS for US-listed stocks and ETFs, plus Korean KRX-listed stocks/ETFs where the live endpoint verifies.
2. Use US-listed ETF proxies for global market exposures (Canada, Europe, Japan, Korea, Taiwan, Hong Kong, India, China, Brazil, Australia, Mexico) when direct KIS series are unavailable.
3. Use US-listed sector ETFs and liquid commodity ETFs/proxies where direct sector indexes or commodity spot/futures series are unavailable.
4. Expand the Korean stock universe and validate market/sector benchmarks through KIS.
5. Add direct foreign-exchange-listed instruments or commodity spot/futures only if KIS supports them and the history/terms are verified; ETF proxies remain explicitly labeled as proxies.
6. Additional regions only after symbols, exchange calendars, currency, and sector taxonomy are mapped. Commodity ETFs and spot/futures series must remain separate asset types.

Coverage is driven by provider capabilities, not by UI labels. A market is not supported just because users can type a ticker.

### Phase 4 — durable universe and reference data

**Current implementation:** KIS market-cap candidate discovery is wired into the UI for US (NAS/NYS/AMS) and KRX rankings, with raw response fields and CSV export. Requests now use the official documented parameter names, apply bounded retries, and follow KIS continuation headers for up to ten pages by default (capped at ten). Automated tests cover parameter names, rate-limit retries, continuation, and fail-fast handling of deterministic parameter errors. Live continuation behavior and the returned fields are still unverified. This remains candidate discovery only: market-cap units/currency, stock-vs-ETF filtering, and sector/benchmark mapping must be verified before candidates enter the default screening universe. Do not insert stale or guessed market-cap values.
Maintain, with provenance and an as-of date where relevant:
- canonical instrument ID and symbol history;
- country, exchange, currency, exchange timezone, asset class and instrument type;
- market cap in native currency and USD equivalent, valuation timestamp and FX source;
- sector/industry taxonomy and mapping source;
- market and sector benchmark assignments;
- active/delisted status and corporate-action policy.

Keep symbols, instruments, and providers separate: tickers can change, be reused, or differ by exchange.

### Phase 5 — scale and daily operations
- [x] Add per-symbol error reporting so one failed symbol does not discard all successful results.
- [x] Add bounded retries/backoff for transient KIS errors and request pacing.
- [x] Cache fetched prices in the active Streamlit session.
- [ ] Fetch incrementally from the last successful date instead of downloading the full history each run.
- [ ] Add persistent cache by provider/instrument/date range and record provider status.
- [ ] Use batch endpoints where authorized; rate-limit requests and avoid concurrent bursts.
- [x] Add on-screen counts for universe size, symbols with price data, and symbols eligible for weekly Stage calculations; show failed-symbol details.
- [ ] Add data freshness, missing-bar, and adjustment-quality indicators.
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


### Market-cap candidate normalization (2026-10-22)
- [x] Add a review export that conditionally normalizes US KIS `tomv` only when it agrees with `last × shar`, and KRX `stck_avls` only when its unit is consistent with price × listed shares (100-million-KRW units).
- [x] Preserve Korean ticker codes as strings, including leading zeros.
- [x] Block US market-cap screening when `tomv` cannot be reconciled with current price × listed shares; cover both accepted and rejected cases with unit tests.
- [x] Flag likely funds/ETFs from names as a conservative review hint; this is not definitive instrument classification.
- [x] Keep ordinary-stock status unverified and prevent candidate rows from auto-entering Stage Analysis.
- [x] Allow optional USD/KRW input for KRX USD-cap conversion; leave USD cap blank when no rate is supplied.
- [x] Apply the USD market-cap threshold only to stock-like candidates; ETF/fund-like rows remain visible for proxy review but have no pass/fail threshold result.
- [x] Expand name heuristics to flag exchange-traded funds and likely preferred/debt/warrant instruments separately from ordinary-stock candidates.
- [x] Export a separate manual-review template for stock-like candidates above the threshold, leaving market, sector, and benchmark fields blank until verified.
- [x] Use the official KIS US symbol master to classify stock/ETP/index/warrant types when downloadable; retain name heuristics only as a fallback, and still require manual ordinary-common-equity review.
- [x] Retain ADRs as separate stock candidates instead of excluding them; record KIS depositary-receipt metadata when available. ADR market-cap screening remains pending until depositary-ratio-aware market-cap data is available.
- [x] Keep ADRs with unverified market cap in a pending manual-review export, and suggest an issuer-country/region ETF benchmark from KIS depositary metadata when a supported proxy exists; retain required Stage fields blank until approved.
- [ ] Replace remaining name heuristics with an authoritative security master / instrument-type source for KRX and unmatched US candidates.
- [ ] Verify the ranking endpoint's maximum rows and coverage: discovery now follows continuation for up to ten pages per exchange, but the uploaded template has 195 rows, so it must not be described as the complete set of all stocks above the selected USD threshold.
- [ ] Source and record a timestamped FX rate automatically before using KRX USD-cap thresholds.
- [ ] Map verified stocks to market and sector benchmarks, then create a separately approved Stage universe.


### First-pass sector and benchmark suggestions (2026-10-22)
- [x] Add review-only ticker-based first-pass suggestions to the stock-candidate export for market, sector, asset type, market benchmark, and sector benchmark.
- [x] Keep the actual required Stage fields (market, sector, asset_type, market_benchmark, sector_benchmark) blank until the user verifies the suggested values.
- [x] Use SPY as the broad-market-relative benchmark suggestion for US-listed candidates regardless of NAS/NYS/AMS listing venue; listing venue alone does not determine index membership.
- [x] Suggest sector ETFs for mapped sectors (for example, XLK for Information Technology and SOXX for Semiconductors) while keeping suggestions explicitly unverified.
- [ ] Review all proposed sector mappings against an authoritative sector taxonomy and confirm each instrument is ordinary common equity before approving.
- [ ] Add automated tests for mapping coverage and benchmark references; do not treat a successful GitHub commit as proof the Streamlit deployment or KIS live calls work.
