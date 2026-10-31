# China mainland ETF identity audit — research only

Date: 2026-10-30
Base: data-validation-mvp

## Scope and safeguards

- Continue the existing mainland-China 30-candidate research without fetching new KIS bars.
- Do not modify active ETF universe, scheduled collection, Stage logic, price snapshots, or the deployed dashboard.
- PR #181 separately corrects SSE 512600's issuer attribution; do not duplicate its edits.

## Findings from current repository metadata

1. The coverage matrix records 30 mainland Shanghai ETF candidates as research-only, with price observations already collected. It explicitly flags 512620's identity and shorter history for further review.
2. The current country_sector_proxy_candidates.csv contains a China row for 512600 with a provisional ChinaAMC attribution; PR #181 proposes correcting it to Harvest using an official HKEX notice. Treat the pending PR as the owner of this correction.
3. The current country_sector_proxy_candidates.csv does **not** contain a 512620 row. Do not interpret absence as delisting or invent a candidate mapping.
4. The existing coverage matrix treats 512760 as a specialist semiconductor exposure and 515030 as a new-energy-vehicle theme, not broad information-technology or energy-sector benchmarks.

## Required independent evidence before activation

For each candidate, record symbol, exchange, exact fund name (Chinese and English if officially available), issuer, tracked index, effective listing status, source URL and document date, quote history length, benchmark suitability, Korean broker tradability and data-use rights. Unverified attributes must be marked unknown, not inferred from a similar symbol.

## Immediate next actions

- Locate 512620 in existing research snapshots and verify its official SSE/issuer record before creating or changing a production candidate row.
- Complete the remaining 29 identity checks while PR #181 handles 512600.
- Keep all unapproved mainland candidates inactive; only validated mappings may proceed to an implementation PR.

This document records repository-grounded review status, **not** a completed independent verification of official external records.

## Official-source verification completed: SSE 512620

- Symbol: **512620**, Shanghai Stock Exchange, CNY ETF.
- Chinese legal name: **天弘中证农业主题交易型开放式指数证券投资基金**.
- English working translation: **Tianhong CSI Agriculture Theme ETF** (translation, not asserted as official English registered name).
- Fund manager: **天弘基金管理有限公司** (Tianhong Fund Management).
- Tracked index: **中证农业主题指数** (CSI Agriculture Theme Index).
- Fund effective date: **2025-11-12**; SSE listing/trading and subscriptions/redemptions began **2025-11-21**.
- Primary SSE listing announcement (2025-11-21): https://etf.sse.com.cn/disclosure/ssenotice/c/c_20251121_10799250.shtml
- SSE official fund information: https://www.sse.com.cn/assortment/fund/list/etfinfo/basic/index.shtml?FUNDID=512620
- SSE fund product summary (2026-06-26): https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-06-26/512620_20260626_JDV7.pdf
- Repository monitoring_universe.csv already has an **inactive** 512620 row (TH CSI Agriculture ETF, SHS). The country_sector_proxy_candidates.csv has no 512620 row; this is a review-metadata coverage gap, **not** a missing active instrument.
- **Important history-quality discrepancy:** SSE confirms November 2025 listing; the coverage matrix claims 224 daily price bars in an isolated KIS observation through October 2026. Validate first/last dates and uniqueness against the official listing date before treating 224 as usable historical bars. Do not infer pre-listing price validity.
- Korean broker tradability, rights, liquidity thresholds and suitability for 30-week Stage analysis are **not verified**. Keep inactive.

### Evidence status

Official issuer/index/listing identity: **verified from SSE**. Quote-history integrity and investability: **pending**.

## Price-history source audit — 2026-10-30

- `data/monitoring_universe.csv` contains inactive 512620 with provider KIS, exchange SHS, CNY currency, and MCHI benchmark.
- `data/sector_coverage_matrix.csv` reports 224 observed daily bars for 512620, but contains no row-level OHLC dates.
- The attempted repository paths `data/china_mainland_etf_price_observations.csv`, `data/china_sector_etf_stage_report.csv`, `data/china_sector_etf_price_snapshot.csv` were not found on `data-validation-mvp`. Their absence does not establish that no snapshot exists elsewhere.
- Do not label the 224 bars verified until the underlying isolated KIS snapshot or report is located and checked for earliest date >= 2025-11-21, latest date <= observation date, unique trading dates, OHLC consistency, and sufficient completed weekly bars for 30-week MA.
- No live KIS API calls were made and no data was promoted.

## Scheduled snapshot versus isolated China batch — 2026-10-30

- `data/daily_prices_status.json` reports 92 requested symbols and 92 with data as of 2026-10-29. **512620 is not in that requested-symbol list.** This is the regular collection status, not evidence that the isolated 30-symbol China candidate batch passed validation.
- The coverage matrix's 224-bar observation for 512620 is a separate research statement. It cannot be verified from the regular status JSON.
- Avoid running a redundant full KIS collection. Locate the isolated SHS batch artifact and verify raw date rows; if unavailable, mark `history_status` unknown rather than claiming verified 224 usable bars.

## Actions artifact check — 2026-10-30

- Inspected artifacts for GitHub Actions run `41020551569` (dashboard verification on `data-validation-mvp`, SHA `1ff9308531180c998d6213c57121276eef08aa68`).
- One unexpired artifact exists: `hosted-dashboard-results` (artifact ID `12960954644`). Its name and workflow context identify dashboard testing, **not** the isolated mainland SHS price-observation batch. No claim was made that it contains raw 512620 prices.
- Attempted likely workflow and report paths were not found. The China batch's actual workflow/run ID and raw snapshot path remain unknown.
- Next verification requires identifying the original batch-producing commit/run or artifact before inspecting OHLC row dates; avoid rerunning KIS simply to fill this provenance gap.

## Prior China index comparison recovered — 2026-10-30

- Commit `db22c47b622de1ffe722695ab79400c3a753fcfc` (#152) introduced `data/china_etf_index_distinction_review.csv` and `tests/test_china_etf_index_distinction_review.py`.
- The current CSV already covers six symbols: `512700, 512800, 512010, 512170, 512480, 512760`. It compares underlying indices, 30-week moving-average distance, 13/26-week returns, MCHI-relative returns, volume and daily-return correlation. Preserve and reuse these findings; do not restart those six index comparisons.
- This CSV is an **aggregate analytical report**, not underlying daily OHLCV bars. Its existence does not resolve 512620's first/last observed trading date or the original 30-symbol snapshot location.
- Subsequent work should focus on the other 24 candidate identities and the isolated raw price snapshot provenance; avoid duplicate research already present in #152.

## RAW SNAPSHOT FOUND AND CHECKED — 2026-10-30

- Original raw daily OHLCV: `data/china_candidate_prices.csv` on `data-validation-mvp`; collection status: `data/china_candidate_prices_status.json`; producer workflow: `.github/workflows/china_candidate_prices.yml` (runs `refresh_china_candidate_prices.py`). Prior statements that raw source could not be found are superseded.
- The CSV contains **8,905 rows for 30 distinct symbols**. For 512620: **224 rows**, from **2025-11-21** through **2026-10-27**, **224 unique dates**, **zero pre-listing rows**, **zero OHLC bound violations**, and nondecreasing dates.
- Basic 512620 date/structure checks **pass**. This is not adjusted-price validation, completeness versus exchange trading calendar, investability, broker availability, or data-use-rights approval. Remain inactive.
- Existing `data/china_candidate_official_identity_review.csv` and `data/china_etf_index_distinction_review.csv` should be reused; earlier documentation underestimated existing verification coverage.

## SSE candidate identity inventory — 2026-10-30

- `research/china_mainland_12_sse_identity_evidence.csv` records the 12 symbols not covered by the existing 17-row official-identity review and the separately verified 512620 record. It stores exchange-listed English names, issuer attributions, listing dates, and exposure labels with a shared SSE eligible-ETF-list URL.
- Inventory coverage: 17 existing review rows + 12 additional identity rows + 1 separate 512620 identity row = 30 distinct candidate symbols. This is **identity-documentation coverage**, not 30 approvals for sector benchmarking or live activation.
- The 12-row inventory does **not** verify detailed underlying-index methodology, adjusted-price quality, Korea broker tradability, data rights, or liquidity. These remain pending; all 12 are `inactive_research_only`.
- The 512620 basic raw price-history date/OHLC structure check passed for 224 observations; the earlier pending-history language above is superseded by the later raw snapshot audit. Its updated status is `raw_224_bars_structure_pass`, not full history-quality approval.
- Classification caution: 515030 new-energy vehicles, 515050 5G communications, 515120 branded pharmaceuticals, and 515220 coal are specialist exposures; do not automatically promote them to broad-sector proxies.

## Provisional exposure taxonomy (not benchmark approval)

- Broad-sector candidate: 512200 (real estate); still requires official index-methodology review.
- Industry/subsector: 512400 (non-ferrous metals), 512580 (environmental protection), 512660 (defense), 512690 (alcoholic drinks), 512720 (computers), 512880 (brokerage), 512980 (media), 515120 (branded pharmaceuticals), 515220 (coal).
- Specialist themes: 515030 (new-energy vehicles), 515050 (5G communications).
- These are name-based provisional classifications, not validated underlying-index classifications. No candidates are approved or activated. Avoid combining specialist themes with broad sectors in the same sector-strength ranking without a clear separate label.

## Existing six-symbol index comparison: proxy de-duplication

The existing `data/china_etf_index_distinction_review.csv` (2026-10-27 snapshot) is the source for the following provisional rules; do not rerun this comparison or mistake these observations for current executable quotes.

- **Banks:** 512700 and 512800 both report CSI Banks Index (399986). Their daily-return correlation is 0.9828. The reported 60-day average volumes are 72,251,425 and 1,237,170,554, respectively (approximately 17.1x higher for 512800). Prefer evaluating 512800 first for a *single* bank-sector proxy, subject to index, liquidity and tradability verification; do not count both as independent sector signals.
- **Healthcare:** 512010 reports CSI 300 Health Care Index (000913), while 512170 reports CSI Medical Service Index (399989). They are not interchangeable broad healthcare proxies. Keep distinct industry scopes pending official index methodology and constituent review.
- **Semiconductors:** 512480 reports CSI All Share Semiconductors & Semiconductor Equipment Index (H30184); 512760 reports CES China Semiconductor Chips Index (990001). Reported return correlation is 0.9950. Different indices do not imply independent market-strength signals; use a clear specialist/subsector label and avoid double counting.
- All six remain inactive. Existing review still flags adjusted-price integrity, official index methodology, broker tradability and data-use rights. Do not change active monitoring or Stage calculations based solely on these preliminary comparisons.

## CSV integrity incident and guardrails — 2026-10-30

- The existing 17-row `data/china_candidate_official_identity_review.csv` had four issuer names containing unquoted commas: 516150, 516160, 516970, 515650. Python `csv.DictReader` consequently shifted columns and returned an incorrect activation status, despite earlier tests passing.
- Fixed by quoting those issuer fields in commit `334123d`. Tests now check the existing 17-row inventory's `activation_status`, absence of extra CSV fields, source URL, and identity-status prefix; see `tests/test_china_mainland_identity_inventory.py`.
- The prior failing run for commit `c1300d5` showed four failures among 323 tests. CI success on the later fix must be checked separately; do not infer it from the earlier passing commit.

## CI verification and promotion decision — 2026-10-31

- Commit `cd97b315c0af0b85698aa98060ef69f084a5ef6e` completed both PR-triggered workflows successfully: Python tests (run `41046916689`) and Unit tests and syntax validation (run `41046916685`). This verifies the research-branch test suite, **not** mainland ETF investability or production readiness.
- Confirmed the current research branch still has 17 pre-existing official-identity rows, 12 supplemental identity rows, and six already-completed index comparisons. Together with the separate 512620 identity row, the inventory totals 30 research symbols.
- **Promotion decision:** retain Draft and do not activate mainland SSE ETFs. Outstanding gates are index methodology and benchmark breadth, adjusted OHLCV and exchange-calendar checks, Korean brokerage tradability, and market-data usage rights. Existing KWEB/CQQQ/CHIQ production proxies remain unchanged.

## Index methodology verification queue — 2026-10-31

Prioritize independent primary-source methodology and fund prospectus checks in this order (not an activation ranking):

1. **512800 / 512700 (banks):** independently confirm both benchmark codes and constituent-selection methodology from CSI and fund filings; keep only one representative signal if materially identical. Observed liquidity alone is insufficient for selection.
2. **512010 / 512170 (healthcare):** confirm CSI 300 Health Care versus CSI Medical Service constituent universes; treat as different industry exposures unless source documents establish broader representativeness.
3. **512480 / 512760 (semiconductors):** verify CSI semiconductor/equipment versus CES chip-index construction and overlap; 0.995 historical return correlation is not proof of identical indices.
4. **512200 (real estate):** verify benchmark breadth before treating the only name-based broad-sector candidate among the 12 supplementary identities as a sector proxy.
5. **515030 / 515050 (NEV / 5G):** specialist themes, not broad sector substitutes; do not promote merely because trend metrics are strong.

For each review record source document URL, publication date, official index name/code, selection universe, weighting/rebalancing, constituent concentration, and any unresolved fields as unknown. No live KIS re-fetch is needed for methodology review.

## Official-source evidence status and remaining blockers — 2026-10-31

- Bank ETF issuer benchmark disclosures are recorded in `research/china_bank_etf_issuer_verification.csv`; 512800 is only the **research** representative, and 512700 is held as a duplicate benchmark.
- Healthcare 512010 and 512170 are tracked separately because their recorded indices cover different healthcare universes; issuer profile verification is not equivalent to validating official index methodology.
- Semiconductor 512480 and 512760 have SSE-hosted issuer report references in `research/china_semiconductor_index_evidence_queue.csv`. Distinct benchmark names and high return correlation must not be mistaken for constituent-overlap measurement.
- `research/china_etf_promotion_gates.csv` is the explicit no-activation decision ledger. All six reviewed ETF symbols remain inactive until broker access, adjusted prices and data rights are independently established.
- Regression tests now check CSV column integrity in the four source-evidence files and promotion gate consistency. This does not independently validate that each external URL remains reachable or that every document assertion is correct; verify documents directly before production promotion.
