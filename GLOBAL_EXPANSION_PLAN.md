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

## Current relative-strength policy (2026-10-25)

- Individual stocks use only the country/market representative benchmark for 26-week relative strength; sector RS is disabled for now and must not gate Stage labels or candidate preview.
- US stocks use SPY as a tradable proxy for the S&P 500; Korean stocks use KODEX 200 (069500). Selected non-US issuers use market ETFs as explicit local-market proxies where available (for example, EWT for Taiwan and MCHI for China).
- Broad-market ETFs are evaluated on their own 30-week trend rather than relative to the US market; the market ETF itself is the representative series. Sector and commodity ETFs remain separately classified instruments.
- These are implementation choices, not claims that the proxy perfectly represents a local index or that provider support/data rights have been verified. See `README.md` for the current screening rule.

## Implementation phases

### Phase 1 — reliable normalized data contract
- [x] Normalize daily bars to `date, symbol, open, high, low, close, volume`.
- [x] Reject missing/non-numeric OHLCV, invalid prices, negative volume, inconsistent highs/lows, and conflicting duplicate symbol/date rows.
- [x] Deduplicate identical symbol/date rows.
- [x] Exclude the current incomplete weekly bar, including on Friday.
- [x] Validate universe symbols, asset types, exchange codes, names, and non-negative market cap.
- [x] Extend automated tests to holiday weeks and missing sessions; corporate-action adjustment behavior, timezone boundaries, and additional provider error cases remain separate validation items.
- [x] Add a structural test for the default global ETF-proxy universe and its benchmark references.

### Phase 2 — provider interface and source approval
Each provider adapter must declare:
- markets, exchanges, asset classes, supported history depth, adjustment behavior, update cadence, rate limits, and known gaps;
- authentication method and secret names (never log or commit credentials);
- whether personal use, hosted display, caching, derived metrics, and CSV export are permitted by current terms;
- normalized OHLCV output and provider/source metadata.

No provider is selected merely because it is free or easy to query. Before implementation, confirm the intended deployment model and applicable exchange-level rights. KIS US and KRX adapters are integrated for the current watchlist; broader market coverage, data-rights approval, and point-in-time reference-data quality remain unverified. **Adjustment-flag configuration is now verified in code and covered by tests:** the US adapter sends `MODP=1` and the KRX adapter sends `FID_ORG_ADJ_PRC=0`; KIS's official sample code describes the domestic `inquire-daily-itemchartprice` flag as `0=adjusted price, 1=original price`, and the official overseas sample exposes `MODP` as the adjustment-mode parameter. This verifies the requested mode, not that every returned historical series is correctly adjusted, nor that dividend-adjusted total-return history is provided. A controlled corporate-action comparison remains open. The weekly-bar builder uses `exchange_calendars` for supported US (XNYS) and Korean (XKRX) instruments when determining whether the week's final expected session has occurred. It can accept a Thursday-ending week when the exchange calendar confirms Friday was a holiday. If calendar lookup fails, it fails closed and excludes the week; without a recognized calendar, the conservative fallback remains. Automated holiday-week regression tests pass. This is a weekly-bar completion check, not proof that the source feed contains every expected session.

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

### Incremental refresh implementation contract

Before switching the scheduled refresh from full-history downloads to incremental requests, keep these safeguards explicit:

1. Read the last successful date per symbol from the stored normalized snapshot; do not use the newest date across the entire universe as a shared cursor.
2. Request an overlap window (at least several recent sessions) to capture late corrections and corporate-action restatements, then merge on `symbol,date`.
3. Validate the merged history before replacing the snapshot; reject conflicting duplicates and invalid OHLCV rather than silently selecting a row.
4. If a symbol request fails, preserve that symbol's previous history and record the failure; if a successful response is empty, do not interpret it as a delisting without a separate identity/status check.
5. Retain enough history for 30-week averages and 26-week relative strength; incremental updates must not truncate the rolling lookback.
6. Write the data file and status metadata atomically, and include per-symbol requested start date, received rows, first/latest date, and whether prior history was preserved.
7. Keep a full-refresh/rebuild path for recovery and compare incremental output with a rebuild before enabling it as the only scheduled mode.

This is an implementation contract, not a claim that incremental refresh is already implemented. Until these conditions are met, the scheduled full-history snapshot remains the safer behavior.

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
- [x] Confirm the regression-test run result and continue testing.


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
- [x] Confirm the unit-test workflow result after these commits.
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
- [x] Add exchange-calendar-aware completion before allowing a Thursday-ending week to count as complete. US instruments map to XNYS and Korean instruments to XKRX; if calendar lookup fails, the week is excluded. Regression workflow passed: https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40065574523.
- [x] Add regression tests proving missing/future-dated market benchmark data and missing sector benchmark data fail freshness checks; GitHub Actions passed: https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40064490564.
- [x] Add a shared, unit-tested freshness guard that withholds Stage labels when the asset, market benchmark, or (for stocks) sector benchmark has stale daily data. Regression tests cover stale asset, stale market benchmark, stale sector benchmark, and market proxies not requiring a sector benchmark. GitHub Actions: https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40064034859
- [ ] Add exchange-calendar-aware freshness rules. The current ten-calendar-day stale-data guard is conservative but is not an exchange-session calendar and does not prove that each market's latest close is synchronized.
- The missing-session aggregation test is a data-integrity guard, not a claim that incomplete daily history is complete. Where the feed misses a session, the resulting weekly bar may still be incomplete and should be treated cautiously.

### Live split-adjustment sanity audit (2026-10-24)
- [x] Add a read-only audit script that requests historical bars from the authenticated live KIS API for NVIDIA's 2024-06-10 10-for-1 split and Samsung Electronics' 2018-05-04 50-for-1 split.
- [x] Add offline tests for continuity, split-scale discontinuity, and missing event-side observations; GitHub Actions passed: https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40066170705.
- [x] Add a manual-only GitHub Actions workflow so the live historical requests do not run on every code push.
- [ ] Run the manual workflow and inspect the returned event dates, closes, and ratios. This connection can inspect workflow runs but cannot dispatch a manual run; the one-time manual launch is still required.
- The ratio check is a continuity sanity check, not an independent-source price reconciliation, and does not validate dividend-adjusted total-return history.

### Corporate-action adjustment validation (2026-10-24)
- [x] Reconfirm the overseas adapter requests `MODP="1"` and the domestic adapter requests `FID_ORG_ADJ_PRC="0"`; parameter-level regression tests passed in workflow https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40063564260.
- [ ] Validate an actual historical split against an independent dated reference for at least one US-listed symbol and one KRX symbol, including pre-split OHLC continuity and split date handling.
- [ ] Compare returned KIS historical bars before and after the event using authenticated live API output; current repository tests use mocked responses and cannot establish live-series correctness.
- [ ] Verify whether the requested series adjusts for splits only or also dividends. Do not describe it as a total-return series without explicit provider documentation and data checks.
- Until those checks are completed, treat adjustment-mode flags as verified request configuration only, not proof that the complete historical series is correctly adjusted.


### Screener usability improvements (2026-10-24)
- [x] Add an in-section Stage filter so users can isolate Stage 2 candidates, Stage 2A watch candidates, and other classifications without changing the underlying calculation.
- [x] Add case-insensitive symbol/name search within each market/sector section.
- [x] Add sort controls for market-relative strength, sector-relative strength, and 30-week moving-average slope; expose market-cap sorting only in the stock section so ETF screens are not sorted by blank cap values.
- These controls only change the visible list/chart ordering and selection set; they do not change Stage labels or the underlying screening rules.
- UI code changes are committed. The deployed page has not been visually inspected as part of this pass.


### Screening workflow and reviewability (2026-10-24)
- [x] Add a per-section CSV export that reflects the current country/market, group/sector, Stage, and text-search filters and the selected sort order.
- [x] Add a stock market-cap review-status field to the visible stock table and full-screen CSV: unknown USD cap is marked as pending; missing source metadata is called out; source presence is not represented as independent verification.
- [x] Keep the market-cap review field compatible with demo and user-uploaded universes that do not include the newer source-URL column.
- [x] Treat both symbol and name search as literal case-insensitive text rather than regular expressions.
- [ ] The code changes have been committed; visual inspection of the deployed app is intentionally excluded from this development pass.

- [x] Recompute stock/cap review masks after the market-cap screen filter, preventing boolean-index misalignment when a universe contains below-threshold stocks.

## 2026-10-24 — Cross-market Stage overview
- Added a top-level `시장 레이더 요약` before the market/commodity, sector, and stock tabs.
- Displays total analyzed assets, Stage 2 candidates, Stage 2A watch candidates, and data/benchmark-held assets.
- Adds a cross-tab pivot table of Stage counts by asset area, including totals and explicit zero-count Stage columns for consistent reading.
- The summary is derived from the already-filtered `screen` dataset; it does not alter Stage classification or include assets excluded by the selected market-cap threshold.
- Validation policy: live data and deployed UI checks remain excluded by request; GitHub Actions syntax/unit-test runs are used where available.

## 2026-10-24 — Stage 2 candidate quick comparison
- Added an expandable cross-area shortlist for `Stage 2 후보` and `Stage 2A 관찰 후보` above the asset tabs.
- Added candidate type, asset area, symbol/name search, and sorting by market-relative strength, sector-relative strength, 30-week MA slope, or 26-week return.
- Shows up to 25 candidates and offers a CSV export of the filtered/sorted shortlist.
- Explicitly labels sorting as a comparison aid, not a buy signal or performance forecast; the existing Stage classifier remains unchanged.
- Automatic syntax/unit-test workflows were queued after the app change; live data and deployed UI validation remain excluded by request.


## 2026-10-24 — Candidate exports and session watchlist

- Fixed the candidate comparison count so the UI reports the full filtered candidate total separately from the maximum 25 rows shown in the comparison table.
- The candidate CSV export now includes every candidate matching the current filters and sort, rather than only the visible top 25 rows.
- Added a selectable candidate watchlist with its own table and CSV export. The selected list is held in the current Streamlit session only; it is not presented as durable storage across app sessions.
- Stage classification and ranking logic are unchanged. Sorting remains a comparison aid, not a buy signal or performance prediction.


## 2026-10-24 — Data quality status panel

- Added a compact status row for asset-data staleness, stale benchmarks, missing benchmarks, and stock market-cap review pending counts.
- Added an expandable per-asset data status table with latest daily date, completed weekly date, benchmark symbols, staleness flags, missing-benchmark flag, and market-cap review status.
- The panel explicitly distinguishes basic data guards from full validation of prices, security classifications, and market capitalization. It does not change Stage classification or suppress review rows.


## 2026-10-24 — Refresh history and per-symbol dates

- Expanded the scheduled-snapshot status display to include the last recorded KST refresh time, requested symbol count, error count, and symbols whose previous history was preserved after a failed refresh.
- Added an expandable refresh-history detail section with recorded symbol errors and a per-symbol latest daily-bar date table, including a CSV export.
- The UI explains that refresh execution time is not the same as each exchange's latest trading date; holidays and time zones can legitimately produce different dates.
- This exposes the status file generated by `refresh_daily_prices.py`; it does not independently verify that the source returned every expected trading session.

- Follow-up: the per-symbol date table now calculates each symbol's calendar-day gap against the latest date present in the snapshot, and shows the largest gap. This is a diagnostic only; calendar-day gaps include exchange holidays and are not a substitute for expected-session completeness checks.


## 2026-10-24 — Separate Stage holds from data-review issues

- The data-status summary now counts assets whose Stage classification is explicitly withheld because of stale asset data or missing/stale required benchmarks.
- The detail table shows the current Stage label and an explicit Stage-classification status alongside data-quality and market-cap review items.
- Data issues are listed cumulatively rather than using a first-match-only label, so an asset can show multiple relevant review reasons at once. A market-cap review flag is informational and is not itself a Stage-data guard.


## 2026-10-24 — Analysis eligibility and freshness in asset lists

- Added an explicit `Stage 분류 표시` / `판정 보류` status and calendar-day lag from the latest daily bar present in the loaded screen data to each asset row.
- Included these fields in the asset-area tables and their CSV exports, and in the detailed data-status view, so users can distinguish a displayed Stage classification from a withheld result without opening a separate diagnostic panel.
- Calendar-day lag is only a quick cross-symbol diagnostic; market holidays and different exchange schedules can create legitimate gaps. Assets without sufficient weekly history remain separately counted in the collection-status summary and do not receive a Stage row.


## 2026-10-24 — Parallel implementation lanes

The codebase is split into parallelizable work lanes to reduce serial turnaround while limiting merge conflicts:

- **Stage engine:** `stage_engine.py` and focused engine tests. Keep classification changes isolated from UI presentation.
- **Data refresh and quality:** provider/refresh modules and their tests. Publish a stable per-symbol coverage/status contract for the dashboard.
- **Universe coverage:** universe CSV, symbol mapping, exchange metadata, and their tests. Coordinate symbol support with data-provider constraints before treating a listing as covered.
- **Operations and documentation:** workflow files and documentation. Avoid duplicating schedules or creating overlapping jobs that write the same snapshot.
- **UI integration:** `app.py` remains a single-owner integration surface because its sections and session-state behavior are tightly coupled.

Branches should start from the same current main revision, modify non-overlapping files where possible, and merge through small pull requests. Integrate engine/data/universe changes before the final UI integration. CI completion does not imply live KIS or hosted UI validation; those remain separate checks.


## Candidate queue checkpoint — 2026-10-24

The review-only file `data/stock_universe_candidates.csv` now contains 31 additional stock candidates across major US-listed sectors. It is separate from `data/monitoring_universe.csv`; candidates are not analyzed by the dashboard until explicitly promoted after review.

Offline guard tests cover:
- no duplicate symbols in the candidate queue;
- no overlap with active monitoring symbols;
- candidate provider and market-cap statuses remain unverified/pending;
- ADRs remain identity/proxy-review candidates;
- market benchmarks and any populated sector benchmarks must exist in the active universe;
- candidates without a sector proxy remain pending.

These checks validate metadata consistency only. They do **not** establish KIS price endpoint support, recent OHLCV coverage, current market capitalization, security-master identity, or ADR depositary ratios. Those checks are still required before any candidate is activated. Do not treat the queue as confirmed coverage.


The offline candidate coverage report also counts unique symbol/date bars (so duplicate rows cannot inflate history depth), flags whether a candidate has at least 150 daily bars as a basic 30-week/26-week-analysis history screen, and records each candidate/benchmark's calendar-day lag against the newest date in the saved snapshot. These are diagnostic flags, not trading-day freshness guarantees or proof of provider support; all candidates remain pending review.


The candidate coverage report also emits explicit blocker codes for missing provider confirmation, listing identity, market-cap review, insufficient price history, absent benchmark coverage, and potentially stale dates. A report row with zero metadata/snapshot blockers is still not sufficient for activation: live KIS/provider support and identity/cap checks must be separately confirmed.


ADR and foreign-incorporation review blockers are explicit in the offline candidate report: ADR candidates remain blocked until depositary-ratio metadata is verified, issuer-country proxy review is resolved, and listing identity/provider/capitalization gates are separately cleared. US-listed companies incorporated outside the US also remain pending when issuer-country treatment needs review. These blockers are conservative workflow flags, not legal or security-master verification.


The offline candidate audit compares populated sector proxies against the dashboard's curated sector-to-ETF mapping (for example, Information Technology → XLK and Semiconductors → SOXX). A mismatch is a review blocker; the report does not silently rewrite the candidate's chosen proxy. ADRs with a missing sector proxy remain blocked until an appropriate sector comparison is deliberately assigned.


The dashboard candidate report now exposes the candidate's declared listing exchange, country, currency, instrument type, listing-identity status, ADR depositary-ratio status, market-cap review status, and provider-support status alongside coverage dates. These values are candidate metadata and remain explicitly unverified until their corresponding review gates are cleared.


The dashboard presents Korean-readable explanations for candidate review blocker codes while retaining the raw codes in a separate column for debugging and export. A row with no snapshot/metadata blockers is still not an activation approval because provider support and listing/capitalization checks can only be cleared by their corresponding evidence.


Candidate queue schema checks require every pending row to carry market, exchange, country, currency, instrument type, identity, capitalization, and provider-review statuses; they also prevent duplicate symbols and references to non-active benchmark symbols. Schema completeness does not mean the metadata itself has been independently verified.


Pending candidates have a separate, isolated price-history refresh workflow scheduled for 08:05 KST Monday-Saturday (after the active-universe 08:00 KST refresh), with manual dispatch retained. It writes to `data/candidate_daily_prices.csv` and a separate status file, preserves prior candidate history on per-symbol errors, and merges review-only prices with the active snapshot only for the coverage report. The scheduled active-universe refresh does not request candidate symbols, and the candidate workflow never edits `monitoring_universe.csv` or `daily_prices.csv`.


The dashboard's pending-candidate coverage panel also reads `candidate_daily_prices_status.json` and displays the latest attempt timestamp, number of requested candidates, number with price history, error count, and per-symbol error details. A failed or empty retrieval is therefore visible without activating candidates or replacing the active universe.


After the isolated candidate fetch returned price history for a symbol, the coverage report records `provider_observed_data_returned=true` and no longer labels that specific symbol's provider access as wholly unobserved. This is only evidence that a response was returned for the requested symbol; it does not verify listing identity, instrument type, ADR ratio, market capitalization, or eligibility for activation. All candidates remain `keep_pending_review`.


### Candidate evidence provenance fields (2026-10-24)
- [x] Add explicit columns for identity evidence URL, identity review date, market-cap source URL, market-cap as-of date, and ADR depositary-ratio status to the pending candidate queue.
- [x] Expose the evidence provenance fields in the generated coverage report.
- ADR depositary ratio is explicitly `not_verified`; non-ADR candidates are `not_applicable`. Empty evidence URLs/dates mean review has not been documented, not that the fields have passed.
- No pending candidate was activated and no market-cap value or identity source was invented.


### Candidate next-action prioritization (2026-10-24)
- [x] Generate a suggested next review action and a conservative priority bucket from existing blocker codes.
- Identity / ADR / issuer-country issues take precedence; then sector benchmark mapping, market-cap evidence, data coverage, and freshness.
- These are process priorities only. They do not validate a candidate or authorize activation.


### Candidate evidence-field completeness (2026-10-24)
- [x] Report missing provenance fields separately from blocker-based review priorities.
- Evidence completeness checks whether identity URL/review date and market-cap source/as-of fields are populated; ADR candidates also require verified depositary-ratio status.
- This is a completeness check only. Populated URLs/dates are not proof that the source is authoritative or that the values are correct. Candidate activation remains separately gated.

- BABA's pending candidate row now proposes XLY as its Consumer Discretionary sector proxy, consistent with the curated sector map and active benchmark universe. This removes only the missing-proxy metadata gap; ADR issuer-country treatment, depositary ratio, listing identity, provider support, and market-cap evidence remain unverified. BABA remains `pending_review` and must not be activated from this mapping alone.

### Candidate issuer-source coverage checkpoint (2026-10-24)
- All 31 pending candidate rows now have an issuer investor-relations URL recorded as a starting point for review.
- 16 rows retain a dated identity-source record from earlier review work. The remaining 15 rows have the URL recorded but intentionally leave `identity_reviewed_at` blank because the page was not independently reviewed in this pass.
- Every candidate remains `pending_review`; identity status, KIS support, and market-cap evidence are not promoted by the presence of a URL. ETN and LIN retain explicit US-listing / Irish issuer-country review requirements.
- Normalized review-note fields to avoid unescaped commas corrupting the CSV column alignment. BABA's row was repaired so its ADR ratio, evidence URL/date, blank market-cap fields, and `verified` ratio status occupy their intended columns.
- The coverage report has not been regenerated after these latest candidate metadata edits; rely on the next scheduled workflow/report run for an updated report. No tests, live KIS checks, or hosted UI validation were run in this pass, consistent with the request to skip validation.

### Candidate market-cap source discovery (2026-10-24)
- [x] Record a dated secondary market-cap discovery reference URL and as-of date (2026-10-23) for all 31 pending stock candidates.
- The reference is a discovery starting point, not an independently reconciled per-symbol market-cap value. Candidate `market_cap_status` remains `not_verified`; no market-cap number was inserted and no candidate was activated.
- Next gate: capture per-symbol market-cap value and source page, reconcile against price × shares outstanding where available, and keep ADR/company-wide capitalization treatment explicit. ETN/LIN issuer-country review remains open.
- The generated candidate coverage report has not been refreshed after these metadata edits. Live KIS support, source values, and hosted UI remain unverified; no validation run was requested for this pass.

### Per-candidate market-cap reference pages (2026-10-24)
- [x] Replaced the single generic market-cap discovery link with a ticker-specific Stock Analysis market-cap page for each of the 31 pending candidates; the reference date is 2026-10-23.
- The page URLs are recorded as secondary research references, not proof that the market-cap values were individually captured, reconciled, or approved. `market_cap_status` remains `not_verified`, no numeric cap values were added, and all candidates remain pending.
- Example pages opened for format/data-date confirmation: ORCL and PLTR pages report a market cap dated 2026-10-23; TSM's page uses the same ticker-specific format. ADR/company-wide share-count treatment still needs separate review.
- Candidate coverage report remains stale after these metadata changes. No local tests, live KIS requests, or hosted UI validation were run in this pass.

### Listing metadata correction (2026-10-24)
- [x] Corrected LIN's exchange field from `NYS` to `NAS` based on Linde's official investor page, which states that Linde plc is listed on Nasdaq under ticker LIN.
- LIN remains `issuer_country_review_required`: Irish plc domicile and the dashboard's issuer-country/market-benchmark convention still need a deliberate rule. Market-cap status and KIS support remain unverified; no activation.
- Eaton's official investor-relations page confirms ETN is listed on NYSE, but the issuer-country classification policy remains unresolved.

### Parallel work checkpoint: market-cap values + issuer/listing metadata (2026-10-24)
- [x] Added a new optional `market_cap_usd_b_secondary` field and populated the dated secondary-source figures available from the Stock Analysis US-company list for PLTR, CVX, COST, CSCO, KO, ORCL, PG, BAC, HD, CAT, and NFLX; TSM uses its ticker-specific page. Values are in USD billions, source date 2026-10-23.
- These are **source-reported reference values only**. `market_cap_status` remains `not_verified` because per-share-class treatment and shares-outstanding reconciliation have not been completed. Remaining candidates are blank, not zero.
- [x] Listing-metadata stream separately corrected LIN to Nasdaq based on Linde's official stock page; ETN/LIN issuer-country policy remains open.
- Next parallel tracks: (1) capture remaining candidate values and cross-check price × shares, (2) complete identity/issuer-country/sector-benchmark review, (3) allow the scheduled candidate collection/report workflows to refresh the stale report. No candidate activated; no validation/test/live KIS run.

- [x] Second market-cap capture batch added secondary-source USD billions for CRM, ADBE, IBM, NOW, TMUS, MCD, TJX and SBUX, also dated 2026-10-23. There are now 20 of 31 candidate rows with a source-reported numeric reference; 11 remain blank pending capture.
- All captured numbers remain provisional secondary-source fields; do not treat them as a validated eligibility threshold or display as verified market cap. `market_cap_status` remains `not_verified`.

- [x] Third market-cap capture batch recorded values for AMGN, COP, DE, ETN, LIN, WELL, CEG, AEP, BABA, ANET and DIS from dated secondary market-cap references, using the October 23, 2026 close where the source showed that date. Candidate table now has numeric reference values for all 31 rows.
- Values are reference-only, USD billions; all candidates retain `market_cap_status=not_verified`. BABA's value is the ADS/ticker-level source value and needs ADR/share-count convention review before use as company-wide cap. No candidate activation or automated thresholding.

### Progress estimate and remaining-work outlook (2026-10-24)
- Implementation progress estimate for the dashboard overall: approximately 80–85%. Core Stage engine, daily/weekly charts, candidate-review queue, scheduled workflows and conservative activation gates are present in the repository.
- Operational readiness estimate: approximately 65–70%, lower than implementation progress because live KIS support, hosted UI behavior, scheduled workflow logs, market-cap reconciliation, and several identity/country classifications remain unconfirmed.
- Candidate expansion subtask: 31/31 secondary-source market-cap reference numbers are recorded; 0/31 are marked verified. The coverage-report generator now carries the numeric reference, source URL, and as-of date through to its output, explicitly separate from verified status.
- Remaining estimated active work: 3–5 hours for source reconciliation and identity/benchmark policy decisions; 1–2 hours for integrating and reviewing report/UI presentation; operational workflow observation is calendar-dependent and may require waiting until the next scheduled run. This is a planning estimate, not elapsed-time measurement or a promise of completion.
- User-requested exclusions remain: no test suite, live KIS validation, or hosted UI visual check in this pass.


### Candidate coverage gate hardening (2026-10-24)
- [x] Updated `candidate_coverage_audit.py` so any candidate whose `provider_status` is not explicitly `verified` or `supported` retains the `provider_support_unverified` blocker even when saved candidate price rows exist.
- The report still records `provider_observed_data_returned=true` when the saved snapshot contains rows. This is intentionally separate from provider certification: historical rows do not by themselves prove current live KIS support or exact instrument identity.
- Removed duplicate dictionary entries for market-cap source URL and as-of date in the report row builder; output fields remain present once.
- Commit: `1474ebec23d9c24c01aacfb2e6fb0bfa742928e2`.
- Per user instruction, no tests, live KIS requests, workflow dispatch, or hosted UI validation were run. The scheduled workflow may regenerate the report later; no refreshed report is claimed here.

## Pending-candidate activation policy

- [x] Add a separate, conservative activation-gate checklist covering instrument identity, live provider support, usable price history, stock-only market-cap provenance, benchmark mapping, and explicit final review.
- [ ] Regenerate the candidate coverage report after metadata changes; report generation has not been performed as part of this documentation change.
- [ ] Dispatch the candidate-price workflow manually only when live workflow execution is in scope; a scheduled workflow definition is not evidence of a successful run.

See [CANDIDATE_ACTIVATION_GATE.md](CANDIDATE_ACTIVATION_GATE.md). All queued candidates remain pending until the documented gates are explicitly reviewed. Automated report output is triage, not approval.

### Candidate refresh failure-state hardening (2026-10-24)
- [x] The candidate audit report distinguishes a fresh per-symbol fetch from retained history, a symbol-specific failure, an unconfirmed outcome, and a run-level failure before per-symbol results are reliable.
- [x] The workflow fallback status includes empty fresh-symbol results, an explicit run-level failure marker, and KST/UTC timestamps.
- [x] The workflow now overwrites a stale prior status artifact when the current refresh step fails, preventing a previous success from being mistaken for the latest attempt.
- [x] Documented refresh_attempt_run_level_failed and refresh_run_failed in the activation-gate guide.
- These changes were committed to main (audit: 86b5d7b602497dfc3803188ba16f53ecd81f5704; workflow: 7c35e4f8fe4908b9ec32c8066d879605b780ee45; guide: 1708cb431a594da199588cbb7e7599c5291ec4de). No tests were run. The report CSV has not been regenerated in this pass, and no manual workflow dispatch or live KIS validation is claimed.

### Candidate refresh visibility and atomic snapshot writes (2026-10-24)
- [x] Dashboard candidate-coverage panel now separates symbols newly returned in the latest attempt from symbols present in the saved snapshot. It raises a distinct warning for the run-level failure marker and a softer warning for per-symbol errors.
- [x] Candidate price CSV and status JSON are written to temporary sibling files and atomically replaced, reducing the risk that an interrupted write leaves a partially written artifact.
- App commit: be4b13a2d9faf98f1b18604e4736f454943461b2; refresh script commit: d7bd418585ea9c74db806c55fd3f2adee8a41056.
- No tests, live KIS requests, report regeneration, workflow dispatch, or hosted UI validation were run. This records code changes only; actual scheduled/manual workflow success remains unconfirmed. Candidates remain pending review.

### Latest candidate refresh and CI results (2026-10-24 20:53 KST)
- [x] Confirmed GitHub Actions run 40091478917 (Manual pending-candidate price review v5) completed successfully. All 8 workflow steps passed, including isolated candidate refresh, failure-state handling, coverage report generation, and committing the review snapshot/diagnostics.
- [x] Latest committed status JSON records 31/31 candidates with fresh data, 300 daily rows each, 2025-08-15 through 2026-10-23, zero symbol errors, and no symbols preserved from an older snapshot.
- [x] Latest coverage report records `fresh_data_returned` for all 31 candidates. All 31 remain `keep_pending_review`; identity review, market-cap verification, and KIS/provider support are still blockers. Price-history availability is not treated as proof of KIS support or instrument eligibility.
- [x] Confirmed CI runs for commit 38cc92d7 completed successfully: Python tests and unit tests/syntax validation both passed.
- Workflow run: https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40091478917
- Python tests: https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40091562148
- Unit tests and syntax validation: https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40091562100

### Candidate identity review queue refinement (2026-10-24)
- [x] Candidate audit actions now distinguish standard US listing-identity review, ADR issuer-country/market-proxy and ADS market-cap convention review (TSM/BABA), and foreign-domiciled issuer-country treatment (ETN/LIN). This changes the recommended manual review task only; it does not mark identity as verified or activate a candidate.
- [x] Regenerated report commit: 173239a07e82fa22e37782312e6d8e3d009c3534. Current report has 31 rows: 27 standard identity reviews, 2 ADR-specific reviews, 2 issuer-country classification reviews. All remain P1 identity review, `blocked_pending_manual_review`, and `keep_pending_review`; market cap remains unverified and provider support remains unchecked.
- [x] Follow-up test correction retains the expected listing-identity wording in specialized actions. CI on commit 5aef549d passed Python tests and unit tests/syntax validation.
- The pending-candidate refresh workflow is queued behind the daily snapshot workflow through a shared concurrency group, intentionally serializing API access to avoid KIS rate-limit pressure. The previously successful candidate snapshot remains 31/31 fresh symbols with zero recorded errors; the next queued run has not yet completed.

### Candidate refresh rerun and workflow commit-conflict prevention (2026-10-24 21:03 KST)
- [x] Candidate refresh run 40091840939 completed successfully after the identity-action update: all 9 workflow steps passed. Latest status artifact records 31/31 fresh symbols, 300 rows each, 2025-08-15 through 2026-10-23, zero errors, and zero symbols carried forward from the previous snapshot. [Run details](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40091840939)
- [x] Python test workflow on commit 6558e1c1 passed; Python tests and unit/syntax checks on commit 5aef549d also passed.
- [x] Diagnosed the prior daily snapshot workflow failure: its data fetch and offline report generation succeeded, but its commit/rebase conflicted on `data/stock_candidate_coverage_report.csv` with a concurrent report writer.
- [x] Changed the daily snapshot workflow to commit only active daily price/status files; the dedicated candidate-report workflow owns report commits. Also put the candidate-report workflow into the same concurrency group as the daily and candidate refresh workflows to serialize writers. These changes address the observed conflict path; their subsequent scheduled execution is not yet confirmed.
- All candidates remain pending manual review; successful price fetching does not certify KIS symbol support, identity, or market-cap values.


## Candidate pipeline run record (2026-10-24 21:12 KST)

- [x] Confirmed GitHub Actions candidate-price refresh run [40092660946](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40092660946) completed successfully after the workflow-trigger cleanup.
- [x] Its committed status snapshot records 31 requested symbols, 31 symbols with fresh data, 300 bars per symbol, 2025-08-15 through 2026-10-23, zero symbol errors, and no rows preserved from an older candidate snapshot.
- [x] Confirmed candidate coverage report run [40092990019](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40092990019) completed successfully; the report now includes the latest-attempt KIS-response observation field.
- [x] Python tests passed on the workflow-trigger cleanup commit [138a8674](https://github.com/wonbosong-arch/global-stage-radar/commit/138a867456e86bc8561f55b8ae049f4cda974b72); Python tests also passed on the preceding report-trigger cleanup commit [abc89d93](https://github.com/wonbosong-arch/global-stage-radar/commit/abc89d930c7361adff43a935abad1f21dcea92cc).
- [ ] All 31 candidates remain pending review. The successful KIS fetch is evidence of a response during that run only; it does not establish verified listing identity, official market capitalization, durable provider support, or permission to redistribute the data.
- [ ] Remaining candidate blockers: 27 standard listing/issuer identity reviews, 2 ADR/ADS share-class reviews (TSM, BABA), 2 issuer-country classification reviews (ETN, LIN), and market-cap evidence/provider review for all 31.
- Note: the latest active-universe daily snapshot run [40092427595](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40092427595) completed successfully on commit 68d763d1, before the latest workflow-only changes. This confirms that specific run, not the hosted Streamlit UI or every future scheduled run.

## Candidate refresh commit fix confirmation (2026-10-24 21:51 KST)

- [x] Candidate-price workflow run [40095465556](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/40095465556) completed successfully after correcting the competing report-file handling. The commit step succeeded; the report workflow owns the shared coverage report file.
- [x] The committed candidate status snapshot now records 31 requested symbols, 31 fresh-data symbols, 300 bars per symbol, 2025-08-15 through 2026-10-23, zero failed symbols, zero errors, and zero symbols preserved from the previous snapshot.
- [x] The candidate coverage report was regenerated from the refreshed snapshot. This confirms that run only; it does not verify official listing identity, market capitalization, provider support, or hosted dashboard UI.
- [x] Identity evidence coverage explicitly distinguishes a review date from verified identity and flags ADR/ADS ratio gaps.
- [x] The automated market-cap triage report is published at [candidate_market_cap_reconciliation.csv](https://github.com/wonbosong-arch/global-stage-radar/blob/main/data/candidate_market_cap_reconciliation.csv). It uses dated share counts only where the source fact is explicitly captured; unsupported ANET, CSCO, and CVX share-count entries were removed rather than treated as official evidence.
- [ ] Remaining: market-cap evidence and KIS/provider mapping for all candidates; identity remains pending, and no candidates were activated.

## Official share-count triage expansion (2026-10-24 21:59 KST)

- [x] Added dated issuer-filing share counts for CAT, PG, HD, BAC, NFLX, AMGN, and SBUX to the market-cap triage code and retained source URLs/effective dates.
- [x] The report workflow completed successfully after the AMGN/SBUX addition; the 31-row report now has 11 candidates with dated share-count evidence, 18 without captured share counts, and 2 ADR/ADS cases routed separately.
- [x] Current triage outcomes: 7 arithmetic-consistent but still unverified; 3 date/share-count investigations; 1 material mismatch (CRM); 2 ADR share-class reviews; 18 official share counts not captured.
- [x] Tests cover the new CAT, PG, AMGN, and SBUX share-count entries; the relevant Python test run completed successfully.
- [ ] These are not market-cap verification decisions. All 31 candidates remain pending, and provider mapping/KIS support is still unresolved.
