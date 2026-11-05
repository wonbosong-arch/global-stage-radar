# China sector ETF continuation audit — 2026-10-29

Scope: `data-validation-mvp` baseline and the draft PR #181. Review-only; no live API, no ETF activation, no re-collection. All statements about historical data below refer to repository records, **not** a fresh provider validation.

## Reconciled current state

| Registry / stage | Count | Meaning |
| --- | ---: | --- |
| Mainland SHS ETFs in `data/monitoring_universe.csv` | 30 | All `active=false`, each mapped to MCHI |
| Mainland SHS ETFs individually documented in `data/country_sector_proxy_candidates.csv` | 19 | Research records; not activation |
| Mainland SHS ETFs not individually documented in that review CSV | 11 | Metadata gap; **not** proof of missing price data |
| US-listed China proxies active in monitoring universe | 3 | KWEB, CQQQ, CHIQ |
| Isolated China SHS price observations in coverage matrix | 30 | Historical record through 2026-10-27; verify source artifacts before operational use |
| Provisional trend labels in coverage matrix | 4 / 21 / 5 | Trend / downtrend / neutral-or-confirmation-needed, not approved Stage 2 signals |

The coverage matrix records weekly SMA30, four-week slope, and absolute 26-week returns for the 30-symbol provisional report. Market-relative RS was unavailable because MCHI was absent **from that report input**. Do not infer that MCHI is unavailable to the application generally.

## Eleven research records not yet mirrored into the review CSV

`515120, 515070, 515210, 516150, 516160, 516970, 515880, 512290, 515170, 515650, 515790`

Their names and sector labels already exist in `data/monitoring_universe.csv`. **Do not automatically promote those labels to verified official names** or generate fabricated issuer URLs. A review registry row needs a specific source and explicit pending status. Until official evidence is available, keep the gap visible.

## Evidence intake order for the 11 remaining records

Do not treat the existing English instrument names as independently verified. Review the following groups against issuer and exchange product pages, capturing exact fund title, manager, index provider, tracked index, currency, initial listing date, source URL, source date, and any symbol reuse before adding review rows.

| Order | Symbols | Reason |
| --- | --- | --- |
| 1 | 515120, 515070, 515210 | Innovative drugs, AI, steel; avoid treating narrow thematic indexes as broad sectors |
| 2 | 516150, 516160, 516970, 515880 | Rare earths, new energy, construction engineering, communications equipment; verify constituent/index distinctions |
| 3 | 512290, 515170, 515650, 515790 | Biomedicine, food/beverage, consumer 50, photovoltaics; validate benchmark overlap and index identities |

Each approved *research metadata* addition must retain `active=false` in the monitoring universe and `provider_price_history_confirmed_activation_pending` in the candidate review CSV; a confirmed ticker name does **not** grant data rights or approve dashboard activation. Do not infer data availability from the number of registry rows.

## Primary-source review completed for three overlapping proxies

- **512480:** SSE 2025 fund product summary confirms Guolianan Fund as manager, CSI All Share Semiconductor Products and Equipment Index, CNY, listing 2019-06-12. Existing monitoring-universe label `CPIC SEMICON ETF` was incorrect and is corrected in PR #181. Source: https://www.sse.com.cn/disclosure/fund/announcement/c/new/2025-04-09/512480_20250409_VFF0.pdf
- **512700:** SSE 2026 fund product summary confirms China Southern CSI Banks ETF, CSI Banks Index, CNY, listing 2017-07-26. Source: https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-06-25/512700_20260625_3O6H.pdf
- **512170:** SSE 2026 fund product summary confirms Hwabao CSI Healthcare ETF, CSI Healthcare Index, CNY, listing 2019-06-17. Monitoring name standardized. Source: https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-03-25/512170_20260325_KUIL.pdf

These three research records are still inactive; price-history quality, rights, broker access and broad-sector duplication remain separate gates.

## Additional official review sources

- **512580:** GF Fund's SSE-published 2026 Q1 report identifies code 512580, the CSI Environmental Protection Industry Index and manager GF Fund. Fund effective 2017-01-25, but the **initial exchange listing date has not been independently confirmed**. The underlying index includes clean-technology and environmental businesses and should not be mislabeled a narrow waste-management sector. Source: https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-04-22/512580_20260422_51YZ.pdf
- **512660:** Guotai Fund's SSE-published November 2025 product summary identifies code 512660, manager Guotai Fund, CSI National Defense Industry Index, SSE listing 2016-08-08 and CNY denomination. The universe and review registry now use one name. Source: https://www.sse.com.cn/disclosure/fund/announcement/c/new/2025-11-26/512660_20251126_6NDH.pdf

Both remain research-only and inactive, subject to price-series, rights and broker validation.

## New primary-source research: alcohol, 5G and coal

- **512690:** Penghua CSI Alcohol ETF; manager Penghua Fund; CSI Alcohol Index; SSE listed 2019-05-06; CNY. Source: https://www.sse.com.cn/disclosure/fund/announcement/c/new/2025-11-26/512690_20251126_URJV.pdf
- **515050:** ChinaAMC CSI 5G Communication Theme ETF; manager ChinaAMC; CSI 5G Communication Theme Index; SSE listed 2019-10-16; CNY. Source: https://www.sse.com.cn/disclosure/fund/announcement/c/new/2023-05-31/515050_20230531_E5FZ.pdf . **Critical corporate action:** ChinaAMC's SSE-published announcement confirms a **1:3 ETF share split** on 2026-05-12 (ex-split 2026-05-13). Official result: https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-05-13/515050_20260513_P4D1.pdf . Raw pre/post-split close prices could produce a false 30-week MA break or Stage 2 classification. Validate whether the already collected KIS OHLCV is split-adjusted before any signal evaluation or activation. Do **not** blindly multiply/divide the snapshot without inspecting provider adjustment policy and the actual event window.
- **515220:** Guotai CSI Coal ETF; manager Guotai Fund; CSI Coal Index; SSE listed 2020-03-02; CNY. Source: https://www.sse.com.cn/disclosure/fund/announcement/c/new/2024-06-13/515220_20240613_N6QC.pdf

All three are **research-only and inactive**; theme scope, rights, broker availability and source OHLCV remain separate review gates.

## Adjusted-price request versus observed adjustment (2026-10-30 KST)

`KIS_SETUP.md` states that the application **requests the KIS daily-price API's adjusted-price option**, while explicitly requiring independent corporate-action validation. This is useful implementation context but **does not establish** that 515050's isolated SHS history is adjusted correctly: exchange routes and historical split handling may differ, and the original price rows remain unavailable in the inspected GitHub price placeholders.

For 515050, verify the actual request parameters of the isolated SHS collection path, capture the returned adjustment metadata if provided, and compare the May 2026 split-window bars with issuer/SSE evidence. Until then keep `split_adjustment_unverified` and inactive status. Do not silently infer data quality from a configured adjusted-price request.

## Actual application snapshot read path verified (2026-10-30 KST)

Inspected the feature-branch `app.py` snapshot-loading block. When no manual KIS fetch is requested and there is no existing session price cache, the app reads `data/daily_prices.csv`, optionally concatenates `data/crypto_daily_prices.csv` and candidate prices, applies `filter_incomplete_daily_bars`, then caches the result in `st.session_state["kis_prices"]`. This supports **read-from-snapshot on ordinary visits**; it does not prove the collector uses atomic writes or that data collection and app deployment are isolated.

The committed `data/daily_prices_status.json` records `updated_at_kst=2026-10-29T08:35:20.613331+09:00`, `requested_symbols=92`, and `symbols_with_data=92`. It is a status record and **not proof** of the scheduler's start time or that all current 07:00 runs are on schedule. `515050` is absent from that 92-symbol core requested list, so this status record cannot validate its isolated China price snapshot.

Follow-up: trace the actual scheduled collector script and workflow configuration; verify staged write, validation, atomic publish, cache invalidation and timestamp propagation before claiming safe nonblocking collection.

## Non-blocking collection/development execution contract

The 07:00 KST KIS collection is an independent scheduled job; development, tests and review can proceed while it runs **only when writes and deployments are isolated**. This is a workflow policy, not a claim that a particular scheduler or artifact upload has been verified.

- **Collector owns** its temporary OHLCV output and collection report. Write to unique run-scoped paths and publish a validated snapshot atomically only after collection and integrity checks finish. Never let review/feature branches overwrite the published snapshot.
- **Developer owns** code, tests, and research metadata on a feature branch; never edit `main` or `data-validation-mvp` directly. Keep the 30 mainland ETF research entries inactive until independent approval.
- **Dashboard reads** the last complete published snapshot. During collection, show its capture timestamp and retain the previous valid dataset; do not display a partially written file.
- **Verification** checks collection success, source coverage, missing symbols, date ranges, OHLCV validity, stale data, and corporate actions (including 515050). A CI pass for application code is **not** evidence that a price collection completed.
- **Coordination**: review and test code while collection runs; after the collector publishes, run the data-quality gate. Do not re-trigger all KIS requests merely because development finished.
- **Scheduler**: intended KIS collection 07:00 KST Monday-Saturday, Sunday skipped. The exact deployed workflow schedule and its timezone conversion still require configuration verification. The separate BTC/ETH job is documented as 09:15 KST Tuesday-Saturday.

## Repository price-source check (2026-10-30 KST)

Inspected `app.py` and the GitHub feature-branch versions of `data/daily_prices.csv` and `data/candidate_daily_prices.csv`. The app reads those paths, but **both GitHub file contents are empty** on this branch; neither can provide the 515050 split-window bars. This does not establish whether deployed Streamlit runtime files, caches, historical GitHub Actions outputs or local operator snapshots contain data. Do not use the empty GitHub placeholders as proof that provider collection failed.

The user reconfirmed the intended KIS refresh as **07:00 KST Monday-Saturday (Sunday skipped)**. README's stale **08:00 KST** text was corrected in commit `52b26e5`; the actual scheduler YAML/workflow configuration still needs independent verification. Do not silently change the operational schedule.

Next evidence source: locate the actual data-collection workflow and its run/artifact retention, and inspect deployed runtime storage only through authorized access. Current classification: `515050_source_snapshot_not_yet_located`, `515050_split_adjustment_unverified`.

## Existing-source artifact availability check (2026-10-30 KST)

GitHub Actions runs for commit `bd4000428d27169513381a540e752931797a5eb4` were inspected: **Unit tests and syntax validation** run `40961217660` and **Python tests** run `40961217628` both passed, but **neither published a downloadable workflow artifact**. These two CI runs cannot supply the isolated 30-symbol OHLCV snapshot. This is **not evidence** that an earlier price-data workflow, external cache, or local operator snapshot does not exist.

The repository's `data/sector_coverage_matrix.csv` is a textual coverage summary rather than a 515050 bar-by-bar source. Therefore `515050` remains `source_snapshot_not_yet_located` and `split_adjustment_unverified`. Do not treat the absence of artifacts on these two test runs as a repository-wide artifact search. Next, inspect the historical data-collection workflow run IDs and its artifact retention, then any existing cache/storage reference, before requesting provider prices.

## 515050 split-adjustment verification protocol — no new provider requests

**Known event:** 1:3 split on 2026-05-12, ex-split 2026-05-13, per SSE-hosted ChinaAMC notice. **Not yet established:** whether the historical KIS bars are adjusted or where the original isolated 30-symbol snapshot artifact is stored. The coverage matrix records a summary, not OHLCV rows; no adjustment conclusion can be drawn from it.

1. Locate the original *existing* snapshot or saved workflow artifact by exact source filename, run ID and capture date. If inaccessible, mark `source_snapshot_unavailable` rather than inferring adjustment from a summary or requerying all 30.
2. For 515050 only, inspect trading dates around 2026-05-12/13 and the 20 sessions on either side. Check duplicates, missing dates, OHLC ordering, nonnegative volumes and price/volume scaling. Cross-check official pre/post-split NAV and published split ratio before labeling adjusted vs unadjusted.
3. Compare pre-event and post-event close/volume and total-return or adjusted-price fields **without assuming** a ratio near 3 proves a data error: market movement and other corporate actions can affect observations.
4. If unadjusted, correct through the provider's documented adjustment policy or a separately audited transform with test fixtures; do not silently patch historical prices. Verify Stage 2 weekly bars, SMA30, 4-week slope and absolute 26-week returns on both sides of the event.
5. Keep 515050 inactive until the evidence, adjustment method and regression tests are recorded. Do not initiate a new API call without a specific missing field and explicit rate-limit-aware plan.

## Evidence quality tiers (do not conflate)

Some of the 19 review rows cite **general exchange eligibility or margin-trading pages**, not a ticker-specific primary fund notice. An official-domain URL alone is insufficient to verify the issuer, index or legal name. Treat evidence as three tiers:

- **Ticker-specific official listing notice, fund summary or report:** sufficient for the precise facts stated in that document; still not sufficient for price adjustment, data rights or broker tradability.
- **General exchange eligibility/margin list:** contextual market evidence only; does **not** establish a ticker's exact fund identity or index.
- **Unverified existing monitoring label:** research candidate only; never silently upgrade to verified status.

Existing generic exchange-page references in the review CSV include 512800, 512760, 512720, 512880, 512980, 512200, 512400 and 515030. Prioritize replacing those with symbol-specific issuer/SSE disclosures after the remaining 11 records are handled. The automated exchange-domain URL guard is deliberately a **format/domain guard**, not a claim of instrument-level primary-source verification.

## Specific issues

- **512600:** review registry previously attributed the ETF to ChinaAMC, while monitoring universe attributed it to Harvest. PR #181 corrects the review attribution and adds a referenced HKEX notice. Recheck exact legal fund name/index before approval.
- **512620:** SSE primary listing notice verifies Tianhong CSI Agriculture Theme ETF, listing date 2025-11-21; SSE product summary confirms CSI Agriculture Theme Index and CNY denomination. The 224 observed bars through 2026-10-27 match 224 expected SSE trading sessions (243 weekdays minus 19 official closure weekdays). Actual source dates, OHLCV, adjustments, broker availability and data rights remain unverified. Candidate is still inactive.
- **MCHI:** check whether the existing benchmark price series can be joined by dates and currency with mainland CNY ETFs. MCHI is US-listed and USD-denominated; raw price-ratio RS across currencies must not be silently treated as a currency-neutral sector ranking. Do not change the user's 26-week **absolute return** quick-compare metric to relative RS.
- **Sector overlap:** 512800/512700 (banks), 512010/512170 (healthcare), 512760/512480 (semiconductors) are overlapping themes but not necessarily interchangeable indexes. Keep separate identities and avoid double-counting as independent broad sectors.
- **Source rights:** successful KIS observations do not establish redistribution rights, adjustment quality, or broker tradability. All 30 SHS ETFs remain inactive.

## Next actions (no repeated collection)

1. Obtain primary issuer/SSE evidence for the 11 remaining research records, and reconcile names/index methodologies with the monitoring universe.
2. Find the *existing* 30-symbol report and price-snapshot artifacts, inspect bar counts, date gaps, duplicates, OHLCV validity and split/distribution adjustment treatment. Run new provider calls **only if a specific missing data question remains**.
3. Join existing MCHI history if present; record whether dates, trading calendars, FX basis and price adjustments make a comparative RS meaningful. Preserve 26-week absolute return in the quick-compare UI.
4. Add tests for every resolved discrepancy and for nonactivation; run targeted and full CI at the exact PR head.
5. Confirm KIS/HTS availability, data rights, and index scope individually before any activation decision. Do not auto-activate.

## Work boundary

This report is a **continuation** of already collected China data. No changes to US/Korea/Japan sector work, KIS schedules, Stage classification, dashboard UI, or `main`. PR #181 stays draft until checks are complete.

## Codex final handoff (only after this work bundle is ready)

Recommended: **latest Codex reasoning model available, High effort**; use Extra High for complex regression failures. Begin with `AGENTS.md`, `CODEX_PROJECT_HANDOFF.md`, this audit and PR #181. Do not restart discovery or re-collect all 30. Run the existing targeted tests and full CI, check source evidence and remaining review gaps, and merge only to `data-validation-mvp` after passing validation. Report separately: commits, tests, merged PR, actual data refresh, and hosted deployment.
