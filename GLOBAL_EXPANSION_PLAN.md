# Global Stage Analysis — expansion roadmap

## Objective

Build a reliable global weekly Stage Analysis screener for individual stocks, broad-market ETFs, sector ETFs, and commodity ETFs/proxies and commodity spot/futures series. Do not label a market or asset class "supported" until its source, rights, coverage, and price-quality checks pass.

## Current baseline (2026-10-24)

- Streamlit UI supports synthetic demo, CSV upload, and a scheduled KIS US/KRX daily-price snapshot for the current approved watchlist.
- The committed daily-price snapshot has 56 symbols with 300 daily bars each (16,800 rows); the latest observed bar date was 2026-10-23, with no refresh errors in the recorded status file. This verifies the stored snapshot, not every future live run.
- The current active universe has 56 assets: 20 stocks, 14 market ETFs, 14 sector ETFs, and 8 commodity ETF proxies. Stock coverage is still a limited pilot, not a comprehensive global stock universe.
- Market-cap threshold is entered in USD billions ($B); the underlying CSV field remains USD dollars. ETF/commodity proxies are exempt from stock market-cap filtering.
- Shared OHLCV validation is applied across data modes; automated GitHub Actions tests pass for the latest main commit.
- Stage labels remain heuristic screening labels; they have not been shown to be profitable.
- The hosted Streamlit URL could not be independently verified in this review, and a hosted URL does not itself grant data-display or redistribution rights.

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

No provider is selected merely because it is free or easy to query. Before implementation, confirm the intended deployment model and applicable exchange-level rights. KIS US and KRX adapters are integrated for the current watchlist; broader market coverage, data-rights approval, and point-in-time reference-data quality remain unverified. **Adjustment-flag configuration is now verified in code and covered by tests:** the US adapter sends `MODP=1` and the KRX adapter sends `FID_ORG_ADJ_PRC=0`; KIS's official sample code describes the domestic `inquire-daily-itemchartprice` flag as `0=adjusted price, 1=original price`, and the official overseas sample exposes `MODP` as the adjustment-mode parameter. This verifies the requested mode, not that every returned historical series is correctly adjusted, nor that dividend-adjusted total-return history is provided. A controlled corporate-action comparison remains open. The weekly-bar builder conservatively excludes a week when the latest observation is before Thursday; this avoids treating a stale partial week as complete, but may also omit a valid week when Friday is an exchange holiday. Exchange-calendar-aware completion remains an open item.

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

**Latest main-branch unit tests pass and the committed 56-symbol snapshot has been structurally validated, but future live KIS runs, rights for hosted display, comprehensive stock coverage, authoritative sector/benchmark mapping, and the current Streamlit deployment remain separate verification tasks.** Do not represent the full global universe as complete until those gates pass.


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


### Security-master source investigation (2026-10-24)
- [x] Confirm from the official KIS Developers portal that KIS publishes a security-master file for instruments available for trading/price lookup and says it is updated daily (portal's stated update times range from 06:00 through 18:55). Source: https://apiportal.koreainvestment.com/apiservice-summary
- [ ] Retrieve and inspect the actual domestic master-file download and schema; portal HTML confirms the resource exists, but the downloadable domestic file format/fields have not yet been verified in this repository review.
- [ ] Implement a KRX master parser only after its actual format and stock/ETF/preferred-share classifications are verified; unknown or unmatched types must remain pending, not auto-approved.
- [x] Add a regression test comparing the dashboard's embedded candidate normalizer against the canonical `kis_universe.py` normalizer on US stock, unknown type, ADR, ETF, and KRX cases.
- [ ] Confirm the regression-test run result and continue testing.


### KRX master-file parser (2026-10-24)
- [x] Confirm the public KIS KOSPI/KOSDAQ master-file URLs from the official KIS sample repository.
- [x] Add an isolated parser in `krx_master.py` for the fixed-width master records, preserving symbol, ISIN, Korean name, market, group code, preferred-share flag, and SPAC flag.
- [x] Add offline parser tests for both market schemas, ZIP input, ETP/preferred-share classification, duplicate symbols, and malformed records.
- [x] Add a dedicated GitHub Actions workflow for Python compilation and unit tests.
- [x] Cross-check the official sample parser's suffix widths; KOSPI uses 228 bytes and KOSDAQ 222 bytes, each with one trailing padding byte beyond the named field widths.
- [x] Confirm parser/unit tests pass in GitHub Actions after correcting the byte-width boundary.
- [x] Download both live KIS masters in GitHub Actions; KOSPI 2,583 rows and KOSDAQ 1,825 rows parsed with no duplicate short codes, and representative common stocks/ETFs matched expected group codes. [ ] Verify preferred-share/SPAC flag semantics and classifications from raw field values.
- [ ] Only after that verification, connect the parser to candidate review exports. It is not currently wired into the active Stage universe and does not automatically approve any symbols.


### Bounded KRX master download helper (2026-10-24)
- [x] Add an explicit KIS KOSPI/KOSDAQ master download helper using the official ZIP URLs, request timeout, response status checks, ZIP signature validation, and a maximum payload size.
- [x] Add offline tests using a fake HTTP session for successful parsing, invalid market, non-ZIP response, and oversized payload.
- [ ] Confirm the unit-test workflow result after these commits.
- [ ] Execute a live download and compare a small set of known instruments against the downloaded official files before wiring this helper into candidate review.
- The helper returns rows with `manual_review_required`; it does not modify the active Stage universe.


### Live KRX master audit workflow (2026-10-24)
- [x] Add a non-mutating audit script that downloads both official KIS KOSPI/KOSDAQ master files with bounded payload size and timeout.
- [x] Check known Korean stock, preferred-share and ETF symbols are present, verify no duplicate tickers, summarize group-code classifications, and require every row to remain manual-review-only.
- [x] Add a GitHub Actions workflow triggered by changes to the audit/parser and by manual dispatch; it does not need KIS credentials and never updates the active Stage universe.
- [x] Review the first live workflow output for record counts, duplicate symbols, and known-stock/ETF group codes. [ ] Review raw preferred-share/SPAC flag values before treating those classifications as verified.
- The live download is attempted by GitHub Actions because this review environment cannot directly retrieve the KIS ZIP endpoint. Workflow result: https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40056989033

### Market-cap metadata regression checks (2026-10-24)
- [x] Add automated checks that active stock rows carry a positive USD market-cap value, a market-cap as-of date, and a source label.
- [x] Verify active ETF and commodity-proxy rows leave stock market-cap fields blank, so stock-only cap screening does not inadvertently filter them.
- [x] Verify Korean ticker strings preserve leading zeroes.
- [x] Confirm GitHub Actions succeeded for the new checks: https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40061557693
- [ ] Independently reconcile each stored market-cap value to its original source and valuation date. Presence of a value/date/source label is a metadata check, not proof that the value is current or correctly converted to USD.

### KRX USD market-cap provenance safeguard (2026-10-24)
- [x] Clear the unverified USD market-cap values and as-of dates for Samsung Electronics (005930) and SK Hynix (000660); retain their source note with an explicit USD-FX-verification caveat.
- [x] Update the stock screen so missing/unverified stock market caps remain visible with a warning instead of being silently removed by the minimum-cap filter. Such rows are not considered to have passed the cap threshold.
- [x] Add regression coverage requiring US stock cap metadata while requiring KRX USD caps/as-of dates to remain blank until conversion is verified.
- [ ] Confirm GitHub Actions after these changes.
- [ ] Populate KRX USD market caps only after verifying the native KRX unit, price × shares consistency, and a dated KRW/USD exchange rate.

### US market-cap source traceability (2026-10-24)
- [x] Compare active US stock market-cap values and the as-of date against the FinHacker daily ranking, which reports data updated 2026-10-22 4:00 PM ET.
- [x] Add an explicit `market_cap_source_url` field for active US stocks so the source is directly traceable from the universe CSV.
- [x] Add regression checks for source URL presence on US stock rows and blank source URLs for KRX rows while their USD cap remains unverified.
- [x] Treat this as source/value-date reconciliation, not independent recalculation of shares outstanding or primary-source audit.
- [x] Add source URL coverage regression and correct all 18 US-stock rows to include the source URL; GitHub Actions passed for commit `05f736336339ddfc270b8e01375e3b24c2ccd0eb`.
- [x] Add a regression test for ADRs whose issuer-country metadata is unavailable; they remain a US-listed-market fallback suggestion only, with explicit verification wording.
- [ ] Continue expanding the stock universe only after instrument type, listing/ADR status, sector, benchmarks, and market-cap provenance have been reviewed.

### Weekly-bar integrity and benchmark date alignment (2026-10-24)
- [x] Add a regression test that a Thursday-only latest week is excluded on Saturday when no exchange calendar proves Friday was a holiday.
- [x] Add a regression test that a missing midweek session does not cause fabricated OHLCV values; aggregation uses only available daily bars.
- [x] Fix the test fixture to provide sufficient history for the 35-week minimum and confirm GitHub Actions passed: https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40063781509
- [x] Confirm relative-strength calculations require exact weekly-label alignment; mismatched benchmark week labels produce missing RS rather than comparing different endpoints.
- [ ] Add exchange-calendar-aware completion before allowing a Thursday-ending week to count as complete. Do not infer a holiday from the price feed alone.
- [x] Add a shared, unit-tested freshness guard that withholds Stage labels when the asset, market benchmark, or (for stocks) sector benchmark has stale daily data. Regression tests cover stale asset, stale market benchmark, stale sector benchmark, and market proxies not requiring a sector benchmark. GitHub Actions: https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40064034859
- [ ] Add exchange-calendar-aware freshness rules. The current ten-calendar-day stale-data guard is conservative but is not an exchange-session calendar and does not prove that each market's latest close is synchronized.
- The missing-session aggregation test is a data-integrity guard, not a claim that incomplete daily history is complete. Where the feed misses a session, the resulting weekly bar may still be incomplete and should be treated cautiously.

### Corporate-action adjustment validation (2026-10-24)
- [x] Reconfirm the overseas adapter requests `MODP="1"` and the domestic adapter requests `FID_ORG_ADJ_PRC="0"`; parameter-level regression tests passed in workflow https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40063564260.
- [ ] Validate an actual historical split against an independent dated reference for at least one US-listed symbol and one KRX symbol, including pre-split OHLC continuity and split date handling.
- [ ] Compare returned KIS historical bars before and after the event using authenticated live API output; current repository tests use mocked responses and cannot establish live-series correctness.
- [ ] Verify whether the requested series adjusts for splits only or also dividends. Do not describe it as a total-return series without explicit provider documentation and data checks.
- Until those checks are completed, treat adjustment-mode flags as verified request configuration only, not proof that the complete historical series is correctly adjusted.
