# Mainland ETF private analysis

## Current KIS path — supersedes the historical gates below

The user adopted [the global provider trust policy](provider-trust-policy.md) on
2026-11-03. Independent SSE matching and KIS adjustment reconstruction are no
longer required. `china_kis_stage.py` uses the full private KIS MODP=1 history.
The old reconciled loader remains available only for old manifest diagnostics;
its 60-session/512400 limits do not apply to the new KIS path.

Place `china_candidate_prices.csv` outside every Git checkout. Check that the
original collector used SHS/MODP=1 and record symbols with successful KIS responses.
Run `python china_kis_stage.py --root /private/path --prepare-source-commit SHA
--observed-symbols 512800 512880 ...` (all observed symbols as separate arguments).
This writes `kis_stage_manifest.json`, binding price bytes to explicit provenance,
and a private `china_kis_stage_report.csv`. A hash is integrity, not independent
source authentication. Do not claim support for symbols without response evidence.
Later replay: `python china_kis_stage.py --root /private/path --as-of 2026-11-03`.
No provider/network calls occur. Changed price bytes require provenance refresh.

Set `CHINA_PRIVATE_SNAPSHOT_DIR` to that folder and run Streamlit bound to
`127.0.0.1`. In saved-data mode, use 국가 및 원자재 → 업종 보기 or select the
market from 업종. The shared list and 3×3 charts use the saved KIS history. The
mainland scope shows all 30 registered ETFs and computes Stage only for symbols
listed in the private provenance manifest with valid current data.

- CSI 300 (510300) is the mainland CNY benchmark. Run
  `python hong_kong_etf_research.py --mainland-benchmark-only --private-report-dir /private/path`
  from a KIS-authenticated environment to verify and save its history.
- The Hong Kong-listed Chinese company scope uses 2828 and focuses on HK-listed
  underlying shares. The wider HK-listed ETF scope uses 2800 and includes funds
  with other underlying markets. EWH is the Hong Kong domestic market proxy.
- The existing `hong_kong_etf_stage.json` is read from the root. Existing reports
  show current Stage results. On the next private refresh,
  `python hong_kong_etf_research.py --private-report-dir /private/path` also
  saves the adjusted bars needed by charts and same-currency relative strength.
- If available, use private `china_market_fx.csv` with `date,currency,usd_per_unit`.
  Supply CNY and HKD closing FX quotes for the ETF trading dates used in returns.
  The country table leaves a USD return blank when a needed quote is absent.
  Stage still uses the current local-price rules.

Price inputs remain private. Legacy reconciled snapshots can still be inspected
with `china_dashboard.load_research`.

The retained KIS snapshot has last daily date 2026-10-27. Replay as of 2026-11-03
produced 63 completed weeks and Stage labels for all 12; Stage2 candidates 512800
and 512010, new entries zero. 512400 passed basic quality checks and classified
as 하락 추세 관찰. No numeric price/indicator values or original payloads are
published. Results are dated snapshots; after the existing ten-day freshness
limit the labels are withheld until fresh private KIS input is supplied.

Code is not operational activation: a reviewed merge, approved deployment,
configured private input on a non-public/local instance and fresh data are needed
to see these results in the running dashboard. Public hosted access additionally
requires separate data-display permission. Nothing changes active universes,
workflows, schedules, collection, or public price data.

Private browser check: `python browser_checks/check_china_kis_private.py --browser
/path/to/chromium --output-dir /private/artifacts`. It expects the retained dated
snapshot's two Stage2 candidates; screenshots/logs must stay outside Git. It is
not part of default CI and does not require confidential fixtures in CI.

## Historical legacy diagnostics (superseded policy, not current readiness rules)

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
