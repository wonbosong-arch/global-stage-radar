# Shared analysis presentation

The accepted weekly briefing is the visual reference for all six top-level areas:
dashboard, Stage 2 candidates, markets/commodities, sectors, stocks and favorites.
The existing analysis layouts and native widget callbacks remain in place.

## Changes

- Reuse the 65px white brand/search header, 184px blue-tinted navigation, local
  fonts/icons, 28px desktop content inset, white cards and compact blue table
  selection across the analysis areas. Keep chart/list/grid geometries intact.
- Keep the native sidebar expand button visible and clickable even when the
  native toolbar is visually hidden. Expose the collapse control below the
  desktop header. Hide detached sidebar settings/footer when it is collapsed.
- Use horizontal, scrollable navigation when collapsed or on narrow screens;
  reserve its actual height above content. Keep settings in the native sidebar.
- Reuse the existing asset search route on every tab, with the same saved-data
  source/date context. Search does not activate research candidates.

## Accepted behavior constraints

- Research and operating Stage 2 counts remain separate. No provider, Stage
  calculation, data, operating symbol, authentication or deployment changes.
- Market → sector → stock routes, search/filter/sort, row/star/keyboard actions,
  list/grid/paging, daily/weekly charts, default logarithmic 150-bar view,
  volume, selection/scroll memory and private data gates remain regression gates.
- Tab-specific filters, heatmaps and research controls are intentional content
  differences; analysis tabs do not acquire the dashboard's KPI layout.

## Verification

`browser_checks/shell_checks.py` clicks the actual native controls at
1440/800/390px, changes tabs while collapsed, restores the sidebar and checks
reload in demo mode. It captures all six desktop tabs and compares measured
header/navigation/sidebar bounds, font, canvas and content inset. It also runs
inside the existing saved-data dashboard regression. That authenticated local
sequence intentionally skips shell reload: local KIS authentication must expire
on reload; dedicated access/reload checks cover that boundary.

AppTest checks verify brand/search availability and search routing on every tab,
alongside the existing independent mode/state and research/private-access tests.
The browser workflow includes the CSS files in its change triggers.

Screenshots and local test logs stay outside Git. CI success, merge status and
hosted reflection are distinct outcomes and must be reported separately.
