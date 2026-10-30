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
