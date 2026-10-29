# China sector ETF continuation audit — 2026-10-29

Scope: `data-validation-mvp` baseline and the draft PR #181. Review-only; no live API, no ETF activation, no re-collection. All statements about historical data below refer to repository records, **not** a fresh provider validation.

## Reconciled current state

| Registry / stage | Count | Meaning |
| --- | ---: | --- |
| Mainland SHS ETFs in `data/monitoring_universe.csv` | 30 | All `active=false`, each mapped to MCHI |
| Mainland SHS ETFs individually documented in `data/country_sector_proxy_candidates.csv` | 11 | Research records; not activation |
| Mainland SHS ETFs not individually documented in that review CSV | 19 | Metadata gap; **not** proof of missing price data |
| US-listed China proxies active in monitoring universe | 3 | KWEB, CQQQ, CHIQ |
| Isolated China SHS price observations in coverage matrix | 30 | Historical record through 2026-10-27; verify source artifacts before operational use |
| Provisional trend labels in coverage matrix | 4 / 21 / 5 | Trend / downtrend / neutral-or-confirmation-needed, not approved Stage 2 signals |

The coverage matrix records weekly SMA30, four-week slope, and absolute 26-week returns for the 30-symbol provisional report. Market-relative RS was unavailable because MCHI was absent **from that report input**. Do not infer that MCHI is unavailable to the application generally.

## Twenty research records not yet mirrored into the review CSV

`512580, 512660, 512690, 515050, 515220, 515120, 512480, 512700, 512170, 515070, 515210, 516150, 516160, 516970, 515880, 512290, 515170, 515650, 515790`

Their names and sector labels already exist in `data/monitoring_universe.csv`. **Do not automatically promote those labels to verified official names** or generate fabricated issuer URLs. A review registry row needs a specific source and explicit pending status. Until official evidence is available, keep the gap visible.

## Specific issues

- **512600:** review registry previously attributed the ETF to ChinaAMC, while monitoring universe attributed it to Harvest. PR #181 corrects the review attribution and adds a referenced HKEX notice. Recheck exact legal fund name/index before approval.
- **512620:** SSE primary listing notice verifies Tianhong CSI Agriculture Theme ETF, listing date 2025-11-21; SSE product summary confirms CSI Agriculture Theme Index and CNY denomination. The 224 observed bars through 2026-10-27 match 224 expected SSE trading sessions (243 weekdays minus 19 official closure weekdays). Actual source dates, OHLCV, adjustments, broker availability and data rights remain unverified. Candidate is still inactive.
- **MCHI:** check whether the existing benchmark price series can be joined by dates and currency with mainland CNY ETFs. MCHI is US-listed and USD-denominated; raw price-ratio RS across currencies must not be silently treated as a currency-neutral sector ranking. Do not change the user's 26-week **absolute return** quick-compare metric to relative RS.
- **Sector overlap:** 512800/512700 (banks), 512010/512170 (healthcare), 512760/512480 (semiconductors) are overlapping themes but not necessarily interchangeable indexes. Keep separate identities and avoid double-counting as independent broad sectors.
- **Source rights:** successful KIS observations do not establish redistribution rights, adjustment quality, or broker tradability. All 30 SHS ETFs remain inactive.

## Next actions (no repeated collection)

1. Obtain primary issuer/SSE evidence for the 20 research records, excluding already verified 512620, and reconcile names/index methodologies with the monitoring universe.
2. Find the *existing* 30-symbol report and price-snapshot artifacts, inspect bar counts, date gaps, duplicates, OHLCV validity and split/distribution adjustment treatment. Run new provider calls **only if a specific missing data question remains**.
3. Join existing MCHI history if present; record whether dates, trading calendars, FX basis and price adjustments make a comparative RS meaningful. Preserve 26-week absolute return in the quick-compare UI.
4. Add tests for every resolved discrepancy and for nonactivation; run targeted and full CI at the exact PR head.
5. Confirm KIS/HTS availability, data rights, and index scope individually before any activation decision. Do not auto-activate.

## Work boundary

This report is a **continuation** of already collected China data. No changes to US/Korea/Japan sector work, KIS schedules, Stage classification, dashboard UI, or `main`. PR #181 stays draft until checks are complete.

## Codex final handoff (only after this work bundle is ready)

Recommended: **latest Codex reasoning model available, High effort**; use Extra High for complex regression failures. Begin with `AGENTS.md`, `CODEX_PROJECT_HANDOFF.md`, this audit and PR #181. Do not restart discovery or re-collect all 30. Run the existing targeted tests and full CI, check source evidence and remaining review gaps, and merge only to `data-validation-mvp` after passing validation. Report separately: commits, tests, merged PR, actual data refresh, and hosted deployment.
