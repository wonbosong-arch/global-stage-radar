# MVP Scope Freeze — Global Stage Radar

Decision date: 2026-10-28

## Objective

Finish a usable screening dashboard quickly. The dashboard finds and organizes candidates; the user makes all final investment decisions in their HTS. This is not an order-entry, trade-alert, or automated-investment system.

## P0 — required for first usable release

1. Focus individual-stock candidate coverage on US and South Korea.
2. Keep US-listed foreign-country market ETFs (for example EWJ, EWY, EWC, EWT, INDA, MCHI, EWZ and EWA), global market ETFs, and existing commodity ETF proxies in the first release. These ETF proxy views are a core part of global market-strength screening and do not receive market-cap filters. Other-country direct stock coverage and broad local-sector expansion are deferred. Existing US-listed country-specific sector proxies may remain where already available, but new broad local-sector data collection is not a release blocker.
3. Keep the Stage screening core: completed weekly bars, 30-week moving average and slope, and relative strength. Keep volume as supporting context, not a hard eligibility rule.
4. Keep candidate and analysis lists, list-to-chart navigation, list/3x3 view switching, 3x3 pagination, daily/weekly candles, volume, candle hover details, and stable view state across reruns/navigation.
5. Keep daily close refresh and visible freshness/error/coverage status. Sunday refresh is not required.
6. Keep conservative candidate gates: unresolved identity, provider support, market cap, ADR/depositary ratio, or benchmark mapping remains pending; do not auto-activate uncertain candidates.
7. Preserve existing accepted behavior and regression tests. Verify the current integration branch and relevant CI after each targeted change.

## Deferred until after the first usable release

- Direct individual-stock universes for countries beyond the US and South Korea.
- Broad expansion of country-specific sector classifications and local-sector datasets.
- FX-adjusted sector relative strength. Use the existing market/sector benchmark return approach where available; mark missing mappings rather than blocking the entire release.
- Exhaustive ADR inventory expansion and unconfirmed depositary-ratio resolution.
- Advanced scoring, extra indicators, real-time prices, notifications, automated trade decisions, and HTS order integration.
- Exhaustive manual verification of every pending candidate. Work only on a prioritized, reviewable queue; unresolved rows remain explicitly pending.

## Release acceptance checklist

- [ ] User can navigate market/commodity -> sector -> stock without losing the selected view unexpectedly.
- [ ] List and 3x3 modes both work; 3x3 pagination stays in the selected mode and shows more than nine instruments across pages.
- [ ] Daily and weekly charts show price and volume; candle hover includes price-change information; vertical-axis drag is disabled if already supported by the chart library.
- [ ] Stage screening uses completed weekly bars and the 30-week trend; missing data/benchmarks are surfaced as pending, not silently treated as passes.
- [ ] US/Korea core price refresh and candidate intake show success/partial failure explicitly.
- [ ] Relevant automated tests pass on the exact current PR head.
- [ ] Hosted app is checked separately before claiming deployment success.

## Implementation rule

Prefer small targeted fixes against the latest data-validation-mvp integration branch. Do not replace whole UI functions with stale versions. Do not merge into main; it is maintained separately. This scope freeze prioritizes the usable US/Korea MVP and does not imply that deferred markets or unresolved data sources are complete.
