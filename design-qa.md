# Desktop weekly briefing visual verification

Scope: the accepted minimal + market-exploration dashboard, inside the existing
Streamlit app. Analysis screens are regression constraints, not a redesign scope.

## Evidence and normalization

- Source visual truth: user attachment `image(20261113-011117).png` from the
  referenced design conversation. Original 1920×1040; remove only the 87px browser
  chrome, yielding 1920×953 at 1:1 density. No content scaling or reconstruction.
- Actual hosting: `global-stage-radar-kmb524zemj5vawb3ipampm.streamlit.app`.
  Manage app showed `wonbosong-arch/global-stage-radar/data-validation-mvp/app.py`.
  The PR260 weekly route and styles were present; this was not a missing feature
  deployment. The user's 05:58 image was scrolled down, so a fresh top capture was
  required. Its embedded app was measured at 1920×953 with main scrollTop=0.
- Local implementation: unchanged saved repository data in an isolated replay
  that rejects provider requests. Measured viewport 1920×953, main scrollTop=0,
  operating values 6/18/0; incomplete aggregate change explicitly unavailable.
- Local evidence directory outside Git: `../weekly-visual-evidence-20261113/`.
  Source: `approved-content-1920x953.png`; implementation:
  `implementation-final-top.jpg`; hosting: `hosted-before-top.jpg`.
- Full-view comparisons: `approved-vs-implementation.png` and
  `hosted-before-vs-local-after.png` (each 3840×997, including 44px labels).
  Focused comparison: `detail-kpis-tables.png`. Both source and implementation
  were opened together; separate screenshots alone were not the acceptance gate.

## Findings, fixes and comparison history

1. **P1, baseline: wrong shell and density.** A 300px sidebar mixed navigation
   and settings. Status/upload/management sections preceded the dashboard; KPI
   cards were roughly 190px tall, and rows appeared as individual large buttons.
   Fix: briefing-only white 65px header, 184px light-blue navigation, collapsed
   native settings, 94px KPIs and 42px table rows; retain all native callbacks.
2. **P1/P2, iteration 1: header overlap and leading blank space.** Fixed status
   inherited full width and zero-height bridge/style wrappers still added gaps.
   Fix: explicit header bounds; remove only briefing-root wrapper gaps. Preserve
   the existing sticky-header path for analysis views.
3. **P2, iterations 2–3: table header/footnote collisions and collapsed empty
   panel.** Streamlit's negative Markdown bottom margin no longer matched the
   compact paragraph margins. Fix that margin, prevent flex shrinking, reserve
   the empty state, and align table cells using native columns.
4. **P2, iterations 3–4: typography/assets and small controls.** Reuse the source
   logo, official Phosphor paths and the source Noto Sans KR Latin/Korean subsets
   at 400/600/700 weights. Local assets only, with licenses. Compact accessible
   native search, country selector, event tabs and analysis links remain usable.
5. **P2, final iteration: event footnote and watch action alignment.** Use a
   200px scrolling event list, concise coverage notes and a watch action in its
   heading. Strength headings and positive/negative values use semantic colors.
6. **Behavior correction during verification:** the new settings expander has
   a stable native state key, so error/success/full rerun states stay open; its
   scroll region does not sit beneath the fixed navigation. Reload starts closed.
   Demo/CSV/operating source badges explicitly follow the selected data source.

## Required fidelity surfaces

- **Fonts:** source Noto Sans KR restored; 21px dashboard title, 16px panel titles,
  27px KPI values, 12–13px row names, 9–10px secondary labels. Longer real English
  names truncate inside their cells and retain full accessible labels/tooltips.
- **Spacing:** main left edge 212px, KPI top 131px, upper panels top 240px and
  height 316px, lower panels top 571px and height 306px. All five panels fit the
  first viewport. Native table headings do not overlap their first row.
- **Colors/tokens:** white surfaces, #f6f9fd canvas, #f4f8fd sidebar, blue selection,
  #e3eaf4 borders, 8px cards, green/red financial changes. No dark/default sidebar.
- **Image quality:** original local logo; official library vector paths; matching
  icon sizes and palettes. No screenshot-as-UI or generated replacement artwork.
- **Copy/content:** source examples are deliberately replaced by actual values.
  Empty watchlist is genuine. Missing comparisons remain unavailable; neutral is
  not relabeled Stage 1. Operating stocks and opt-in US research remain separate.

## Validation and limits

- Added runtime checks for first-viewport panel bounds, sidebar width, hidden
  collapsed settings and non-overlapping table header/first row.
- Full dashboard browser sequence passed: rapid roundtrips, row/star/keyboard,
  sorting/filtering, list/grid/pagination, chart defaults, reload and selection/
  scroll preservation, 1440/800/390px overflow checks. Measured scroll deltas 0px.
- Settings upload/approval/recovery/chart-preservation browser sequence passed.
- Added AppTest coverage for native settings state, source labels and global
  search using the existing asset route. No engine/provider/data changes.
- Local Windows full suite: 667 passed, 30 failed, 7 skipped, 449 subtests.
  All 26 distinct failure IDs match the recorded exact-base Windows run; no
  additional failure IDs. Final-head Linux CI remains the merge gate.
- No browser page errors in the local real-data inspection.
- Hosting captured above is the pre-patch baseline. Integration/CI alone does
  not prove hosted reflection; check it separately after merge.

## Residual P3 / intentional differences

- Native searchable combobox retains a dropdown affordance instead of the
  prototype's decorative search icon/keyboard hint. Existing menu wording stays.
- Some icon weights, tiny text antialiasing and upper grid widths differ by a
  few pixels. These do not alter hierarchy or above-the-fold content.
- Research details continue below the briefing, in their existing separate
  opt-in panel. No mock watchlist or fabricated comparison fills empty space.
- Other menus retain the accepted existing analysis layout. Decide extension
  separately after this one-screen review; no frontend/runtime replacement.

## Resumed verification, 2026-11-16

- Rebased onto f89398f; intervening integration changes were saved-data updates,
  with no overlap in the affected UI code. The patch itself changes no CSV.
- Current replay at 1920×953 / scrollTop=0 shows 9 markets, 22 sectors, 0 stocks
  at completed week 2026-11-13. Earlier 6/18/0 evidence remains dated 2026-11-13;
  those values are not hardcoded into the interface.
- A long watchlist is now bounded to a 201px native scrolling container; eight
  bookmarks remain available and their callbacks use the existing stock route.
  This prevents rows from spilling beyond the 306px watch card.
- The opt-in local research replay returned a guarded ValueError with the newer
  saved inputs. No current research count is inferred from the earlier 1,411
  observation. This patch preserves the existing unavailable state and does not
  alter research calculations or fall back to prototype numbers.

final result: passed
