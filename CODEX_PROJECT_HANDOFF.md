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
- List view and 3×3 chart-grid view must both exist in relevant areas. Grid paging must preserve grid mode and selection; do not jump back to fixed-chart list.
- Click an item name to switch its chart; no checkbox-only selection. Country-to-sector drill-down must coexist with direct chart access.
- Avoid unexpected page/scroll navigation when changing asset or sector selections.
- Daily and weekly candlestick charts with price and volume visible together, wheel zoom, shared hover crosshair extending through volume, percent change in candle information. Hover information should appear near the cursor without obscuring candles; vertical axis dragging is disabled. Default chart viewport around 150 bars.
- Absolute 26-week returns replaced the earlier market-relative 26-week return display.
- Volume is a soft confirmation input, not a strict Stage 2 eligibility requirement.
- Stage 2 newly entered candidates should be visually marked compared with the previous completed weekly bar; missing previous-week data must not be mislabeled as a new entrant.

## Known work and investigations
- Stage 2 new-entrant labeling and guards were committed in `app.py`; Python tests passed in workflow run `40649895643` at commit `520555bb5675107e12f97b1081bc3f8a9ba79d88`. Actual hosted UI was not verified.
- Candidate price refresh run `40645163243` was rerun. At last inspection on 2026-10-28 07:38Z it was still in progress, at step 'Fetch pending candidate history into isolated snapshot' (job `122690254903`). Do not confuse an older fallback `candidate_daily_prices_status.json` (676 requested, 0 fresh, refresh_failed_before_status_write) with the rerun outcome. Poll actual run and inspect resulting status and logs.
- Provisional Korean sector benchmark ETF refresh had succeeded for 12 symbols with 502 daily bars each, but identity/mapping is not final approval.
- KIS US market-cap ranking requests for NAS/NYS/AMS failed with `ERROR INPUT FIELD NOT FOUND [CURR_GB] (OPSQ2001)` despite request keys `AUTH, EXCD, KEYB, VOL_RANG`. Current `kis_universe.py` request matches the official KIS Python sample (`/uapi/overseas-stock/v1/ranking/market-cap`, TR `HHDFS76350100`). Do not claim this issue fixed or blindly add fields; determine cause from evidence and safely validate.
- China ETF work was provisional/review-only, with 30 symbols collected, 4 provisional Stage 2 signals in an earlier report, and some RS coverage gaps. Do not auto-activate.

## Working relationship
- User is not a programmer. Minimize manual GitHub/terminal actions and unnecessary confirmation loops.
- User inspects the dashboard and reports changes as they notice them. Independently continue useful prioritized engineering work when no UI request is pending.
- Treat every accepted feature as a regression constraint. Never overwrite newer UI changes with older snapshots. Follow `AGENTS.md`: focused feature branches and PRs targeting `data-validation-mvp`, with tests and diff review.
- Keep explanations in Korean, concise and outcome-oriented. Clearly distinguish: code edited, tests passed, data refreshed, PR merged, and deployed screen actually verified.
- Avoid making ungrounded progress or time claims.

## Recommended next actions
1. Inspect current branch, AGENTS.md, latest workflow runs and open PRs; reconcile this handoff with actual repository state.
2. Check candidate refresh rerun completion and diagnostics, without exposing KIS credentials.
3. Investigate and resolve the KIS US market-cap error using verified request/response evidence.
4. Verify Stage 2 new-entry flags and ensure regression coverage for list/grid navigation and hover behavior.
5. Report concise priorities and proceed with focused PRs, preserving accepted functionality.
