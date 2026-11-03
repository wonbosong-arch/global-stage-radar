# Mainland ETF private analysis

Reuse of #193 charts and #194 metadata, based on latest integration. No data files are added, deleted or activated. Default execution only lists 12 identity records.

For personal local use, place the existing #193 `research/china_dashboard_snapshot` files OUTSIDE the checkout and set `CHINA_PRIVATE_SNAPSHOT_DIR` to that directory. Run Streamlit bound to `127.0.0.1`; do not publish or share the private instance or commit those inputs. The loader verifies the existing manifest and official reconciliation, limits previews to 60 reconciled sessions, and blocks 512400. Environment configuration is a private input selector, not a rights grant.

List selection by ETF name, shared daily/weekly chart controls, price/volume, 150-bar window and 9+3 pagination reuse #193. Only the available 60 daily bars are shown; missing history is never filled with unverified data. Watchlist activation is intentionally disabled for research candidates.

All 12 Stage decisions remain withheld: 60 sessions cannot support 30 completed weeks plus four-week MA slope and prior-stage comparison; adjustment evidence is absent. `china_stage.stage_readiness` reuses the existing completed-week engine but suppresses MA/return/new-entry output. It is readiness integration, not a completed trusted Stage 1–4 classification path. Longer independently reconciled adjusted history and an appropriate verified benchmark are the next priority; no switch automatically promotes research candidates.

Tests: `CHINA_PRIVATE_SNAPSHOT_DIR=/outside/snapshot python -m pytest tests/test_china_private_snapshot.py tests/test_china_stage_guard.py`. The first module skips when private inputs are absent, and no confidential fixtures are published. Browser: the same environment plus `python browser_checks/check_china_private.py --browser /usr/bin/chromium`.
