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
