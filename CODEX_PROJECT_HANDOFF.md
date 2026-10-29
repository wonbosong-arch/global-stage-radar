# Global Stage Analysis — Codex project handoff (2026-10-28)

This document provides project context. Check the current code, CI, data files, and GitHub run status before assuming any item remains unresolved. Follow `AGENTS.md` for mandatory branching, PR and regression-test rules.

## Mission and scope
- Screening dashboard for early Stan Weinstein Stage 2 (30-week moving average, relative strength, trend structure). It is not an automated trading or buy/sell system; the user makes final investment decisions in HTS.
- Prioritize US and Korean markets. US-listed international country ETFs can represent other markets. Individual stocks matter; ETFs are primarily market/sector indicators and must not be subject to stock market-cap filters.
- Commodity prices and related companies; Bitcoin and Ethereum were also requested. Do not broaden international sector mappings at the expense of core stability.
- Daily data collection and weekly analysis; correctness and completeness are more important than intraday frequency. No real-time scanner is currently requested.
- Display market capitalization in USD billions when applicable.

## Operational details
- Repository: `wonbosong-arch/global-stage-radar`.
- Integration branch: `data-validation-mvp`. `main` belongs to another developer; NEVER edit or merge into main.
- Streamlit: https://global-stage-radar-kmb524zemj5vawb3ipampm.streamlit.app/
- Scheduled collection: 07:00 KST Monday–Saturday (UTC cron `0 22 * * 0-5`); no Sunday collection. Candidate price refresh is at 07:05 KST (`5 22 * * 0-5`). Confirm actual workflow definitions before changing schedules.
- KIS uses the live trading API. Credentials are in Actions/Streamlit secrets, not source control. Never print or expose secrets. Rate limit `EGW00201` has occurred: keep calls serialized/throttled.
- Candidate data is review-only until explicitly activated. Do not silently add provisional symbols to the active universe.

## Accepted dashboard behavior
- Main sections: countries and commodities, sectors, stocks; Stage 2 candidate quick comparison and analysis area.
- Countries/commodities default to a heatmap of absolute 26-week returns (name, return, Stage), with clickable tiles switching the existing chart. Preserve list and 3×3 views, responsive stacking, country drill-down, selected symbol and daily/weekly period across area/mode round trips.
- Sectors and Stage 2 quick comparison must retain a compact clickable list beside a larger chart, prioritizing name, absolute 26-week return, Stage and new-entry status.
- List view and 3×3 chart-grid view must both exist in relevant areas. Grid paging must preserve grid mode and selection; do not jump back to fixed-chart list.
- Click an item name to switch its chart; no checkbox-only selection. Country-to-sector drill-down must coexist with direct chart access.
- Avoid unexpected page/scroll navigation when changing asset or sector selections.
- Daily and weekly candlestick charts with price and volume visible together, wheel zoom, shared hover crosshair extending through volume, percent change in candle information. Hover information should appear near the cursor without obscuring candles; vertical axis dragging is disabled. Default chart viewport around 150 bars.
- Absolute 26-week returns replaced the earlier market-relative 26-week return display.
- Volume is a soft confirmation input, not a strict Stage 2 eligibility requirement.
- Stage 2 newly entered candidates should be visually marked compared with the previous completed weekly bar; missing previous-week data must not be mislabeled as a new entrant.

## List UI verification (2026-10-29)

- Country/commodity heatmap landed in PR #169, targeting `data-validation-mvp`. Sector and Stage 2 compact split panes retain the existing chart builders, filters and Stage calculations. The main modes are fixed-chart list and 3×3; the country heatmap remains available. The mistakenly added table mode was removed at user direction; review/status tables and CSV downloads remain.
- Regression coverage includes real AppTest selection/period/table/grid/area round trips and actual Chromium layouts at 1440, 800 and 390px. Browser checks preserve the country→sector route, independent candidate selection and zero main-scroll movement on paging/selection. Run the current CI before merging subsequent changes.
- These local/CI browser checks do not verify the hosted Streamlit deployment or its configured source branch.

## Known work and investigations
- Stage 2 new-entrant labeling and guards were committed in `app.py`; Python tests passed in workflow run `40649895643` at commit `520555bb5675107e12f97b1081bc3f8a9ba79d88`. Actual hosted UI was not verified.
- Candidate price refresh run `40645163243` ended cancelled at the 30-minute job limit. PR #157 adds a 15-minute soft budget between symbols, saves partial results, explicitly records deferred candidates and prioritizes them next run. PR #158 distinguishes `deferred_time_budget` from provider request failures in the coverage report. Run `40667647827` completed successfully at 19:09 KST: 436 of 676 candidates fetched, 240 deferred, zero actual provider errors. Snapshot: 129,527 rows / 436 symbols, no invalid dates, future dates or symbol/date duplicates in the audit. This is partial collection, not full coverage. Follow-up run `40669994232` is processing the deferred tail and newly added review candidates; inspect its actual outcome.
- Provisional Korean sector benchmark ETF refresh had succeeded for 12 symbols with 502 daily bars each, but identity/mapping is not final approval.
- KIS US ranking schema discrepancy: the official sample omits `CURR_GB`, but stored live results at `0c8c9ce` used `CURR_GB="0"` and returned USD rows on NAS/NYS/AMS without market errors. After removal, results at `928bc43` failed on all three with `OPSQ2001`. PR #160 restores the empirically accepted selector and documents evidence in `KIS_SETUP.md`. Live discovery run `40669299966` succeeded with no market errors after the repair. NAS/NYS/AMS each returned 100 unique rows, then repeated page 1; all three explicitly report stalled pagination. Discovery also added a bounded 250-candidate secondary review batch (926 total candidates), all still pending. Repeated page 1 remains a separate limitation; preserve the stall guard and do not claim exhaustive ranking coverage or approve market-cap units from request success.
- China ETF work was provisional/review-only, with 30 symbols collected, 4 provisional Stage 2 signals in an earlier report, and some RS coverage gaps. Do not auto-activate.

## Continuation verification (2026-10-28)

- PRs #155–#161 were merged only into `data-validation-mvp`; `main` was not edited or merged.
- #155 prevents false Stage 2 new-entry labels when the preceding weekly row is missing. #156 filters incomplete/future/invalid candidate daily bars, including retained history.
- Actual Streamlit AppTest exposed a pagination exception that older source assertions missed. #159 moves all four grid paging handlers into callbacks. Its regression exercises both independent grids, reruns, analysis-area round trips, list selection, daily-chart selection and return to grid mode, with network calls rejected.
- Latest full local suite for the follow-up deferred-status UI fix: 349 pytest tests and 74 subtests passed; 273 unittest tests passed. All PR CI checks passed before merging. Check the current integration SHA and subsequent CI/data commits before relying on these counts.
- #161 separates deferred work from provider errors in dashboard metrics and shows an explicit Korean continuation warning; the raw status error list still includes budget deferrals for history preservation and diagnostics.
- Local AppTest verifies server-side widget behavior. Hosted browser rendering, scroll position, hover/crosshair appearance and deployment remain unverified. Existing pandas/Streamlit deprecation warnings remain.

## Working relationship
- User is not a programmer. Minimize manual GitHub/terminal actions and unnecessary confirmation loops.
- User inspects the dashboard and reports changes as they notice them. Independently continue useful prioritized engineering work when no UI request is pending.
- Treat every accepted feature as a regression constraint. Never overwrite newer UI changes with older snapshots. Follow `AGENTS.md`: focused feature branches and PRs targeting `data-validation-mvp`, with tests and diff review.
- Keep explanations in Korean, concise and outcome-oriented. Clearly distinguish: code edited, tests passed, data refreshed, PR merged, and deployed screen actually verified.
- Avoid making ungrounded progress or time claims.

## Recommended next actions
1. Inspect current branch, AGENTS.md, latest workflow runs and open PRs; reconcile this handoff with actual repository state.
2. Inspect bounded candidate refresh outcomes and deferred queues; retained historical rows are not fresh-provider success. Do not expose KIS credentials.
3. Verify the restored KIS US currency selector in live results, then investigate repeated ranking pages using verified continuation evidence. Missing ranking rows remain unknown, not failed size screens.
4. Keep the actual Streamlit pagination regression and weekly-entry guards. Check hosted list/grid navigation, scroll and hover separately; AppTest does not validate browser rendering.
5. Report concise priorities and proceed with focused PRs, preserving accepted functionality.

## Cursor chart interaction contract (2026-10-29)

- Candle information is selected by X/date throughout price/volume panels, including empty space. A cursor-following overlay replaces native hover labels, with a viewport clamp and a dotted line through both panels.
- Existing native Plotly charts share a browser component (`chart_interactions.py`/`.js`), including fixed-list, grid and pending-review charts. Streamlit components v2 requires Streamlit >=1.51; Plotly JS is bundled locally, without a CDN.
- Price defaults to Linear; Log uses the same axis for candles/MA, ignores nonpositive prices for bounds, and falls back to Linear when the visible range has no positive prices. Price/volume bounds independently follow visible bars; vertical dragging remains locked.
- Browser regressions verify empty-space hover, boundaries, shared line, scale switches, equal-ratio log distances and visible-range fitting. Hosted deployment still requires separate verification.

## Analysis shell redesign

- Default entry is Stage 2 candidates. Sticky title/four horizontal tabs replace the simultaneous comparison/analysis sections; each tab owns its mode, selection and period state. Mobile tabs scroll horizontally.
- Collection diagnostics, complete warnings, development details and review tables live in a collapsed Data Management panel; the compact status line remains above analysis. Collector logic and schedules are unchanged.
