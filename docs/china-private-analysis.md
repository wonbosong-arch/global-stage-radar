# Mainland ETF private analysis

Reuse of #193 charts and #194 metadata, based on latest integration. No data files are added, deleted or activated. Default execution only lists 12 identity records.

For personal local use, place the existing #193 `research/china_dashboard_snapshot` files OUTSIDE the checkout and set `CHINA_PRIVATE_SNAPSHOT_DIR` to that directory. Run Streamlit bound to `127.0.0.1`; do not publish or share the private instance or commit those inputs. The loader verifies the existing manifest and official reconciliation, limits previews to 60 reconciled sessions, and blocks 512400. Environment configuration is a private input selector, not a rights grant.

List selection by ETF name, shared daily/weekly chart controls, price/volume, 150-bar window and 9+3 pagination reuse #193. Only the available 60 daily bars are shown; missing history is never filled with unverified data. Watchlist activation is intentionally disabled for research candidates.

All 12 Stage decisions remain withheld. `china_stage.stage_readiness` now reports independent prerequisites:

| Prerequisite | Minimum evidence |
| --- | --- |
| MA30 | 30 complete weekly bars |
| Four-week MA slope | 34 complete weekly bars (MA30 now and four weeks earlier) |
| Comparable previous bar | 35 complete weekly bars (previous bar also has a four-week slope) |
| Adjusted history | Reviewed adjustment method and corporate-action coverage across the entire calculation interval, independently reconciled prices |
| Previous Stage | A valid previous Stage decision using the same verified inputs and classification policy |

The first partial week and the trailing incomplete week do not count. Actual XSHG sessions must cover the supplied daily interval without missing sessions, duplicate dates, non-session dates, future dates, mixed symbols, nonfinite numbers or invalid OHLC/volume. Calendar failures block validation. Prerequisite flags are diagnostics, never Stage decisions. MA, slope, 26-week absolute return and new-entry outputs remain null, and operational eligibility remains false even with 35 or more structurally valid weeks. There is no configuration flag that can declare adjustment verification or activate Stage 1–4.

The existing longer file has 8,905 rows across 30 symbols from 2025-07-30 through 2026-10-27, but independent exchange reconciliation covers only 60 sessions. KIS MODP=1 alone does not verify adjustment quality; the older rows are not connected to analysis. No additional verified adjusted history was obtained in this change. A trusted Stage 1–4 classification path remains pending that evidence and the benchmark/classification policy review. No artificial Stage 2 promotion is permitted.

The private loader requires integrity entries for every consumed CSV; an omitted manifest entry cannot bypass hashing. Hashes establish byte consistency, not source authenticity or adjustment verification. The unresolved 512400 discrepancy remains explicitly blocked even if local match flags are rewritten. Removing that block requires a separately reviewed reconciliation fix.

Tests: `CHINA_PRIVATE_SNAPSHOT_DIR=/outside/snapshot python -m pytest tests/test_china_private_snapshot.py tests/test_china_stage_guard.py`. The first module skips when private inputs are absent, and no confidential fixtures are published. Browser: the same environment plus `python browser_checks/check_china_private.py --browser /usr/bin/chromium`.
