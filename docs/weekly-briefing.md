# Weekly briefing design connection

Accepted source: the existing Global Stage Radar Work prototype, minimal analysis
and market exploration, refined on 2026-11-13. Reuses native Streamlit widgets,
screening results, bookmarks and existing chart routes; no new price pipeline.

## Accepted behavior

- Dashboard: chart-free weekly counts, entries/exits, market and country-filtered
  sector 26-week absolute returns/rank movement, strength change, weekly watchlist.
- Desktop left navigation; narrow screens retain the accessible native menu.
- Charts remain in Stage 2 / markets and commodities / sectors / stocks / favorites.
  Market → sector → stock/research actions reuse the existing routes.
- Shared row/ticker selection and stars stay unchanged. Existing comparison
  controls are retained; no asset-selection checkbox is introduced.
- List/3×3, nine-chart paging, filters, selection, scroll, weekly/log defaults,
  about 150 visible bars, moving averages, volume and right whitespace remain.
- The active menu is remembered outside widget ownership across full reruns.

## Comparison contract

- The displayed current analysis universe is held fixed for comparison. This is
  not a reconstruction of historical universe additions/removals or all stocks.
- Existing guarded Stage labels and prior Stage labels are reused, never
  reclassified here. Stage 2A is separate from Stage 2. Holds are not exits.
- Require the same completed Friday and its immediately preceding weekly bar.
  No adjacent-row assumption across missing weeks. Sunday crypto stays in its
  separate existing analysis calendar and is excluded from this briefing.
- Counts: current minus previous equals entries minus exits when every member
  has a valid comparison. Otherwise totals explicitly read **비교 불가**; individual
  verified transitions can still be inspected, with their coverage shown.
- Rank changes use the same filtered group both weeks, tied minimum ranks.
  Missing dates/returns withhold group rank movement. Current ranks exclude
  rows outside the named reference week and show coverage.
- Strength is the change in 26-week absolute return, in percentage points.
  Watchlist weekly return uses completed weekly closes. Missing/ambiguous price
  identities never fall back to old bookmark returns or sample values.
- Existing synthetic demo is explicitly labeled. Missing real values are never
  filled from that demo or from the prototype.
- US research summary is opt-in and uses the existing cached saved-data path.
  Research is separate from operating counts and confirmed/buy signals. Prior
  research Stage history is unavailable; entry/exit comparisons remain unknown.

## Verification boundary

Pure weekly tests and AppTest cover missing history, calendar gaps, holds,
identity ambiguity, count conservation, ties, country filtering, chart-free
rendering, stars, routes and independent analysis settings. The existing browser
workflow also checks the briefing and 800/390px overflow before its full table,
chart, pagination, scroll, reload and market-sector-stock sequence.

Exact-head CI is the merge gate. Real CSVs, providers, activation, main, access
policy, secrets, deployment settings and paid services are outside this change.
Hosted deployment is unverified until separately observed.
