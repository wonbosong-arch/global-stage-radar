# Chart browser regression

This check renders the application's actual chart-building code with synthetic
daily and weekly data. It covers full, compact and pending-review figures:
150 visible bars without truncating stored history, OHLC and volume on the same
hover date, a crosshair through both panels, wheel zoom, horizontal pan and locked
vertical scales. Separate unit tests cover short histories. No application
passwords, KIS credentials, live provider calls or candidate activation are used.

Install the ordinary project requirements plus `playwright`, then run:

```sh
python -m playwright install --with-deps chromium
python browser_checks/check_price_chart.py
```

An existing local Chromium can be selected with `--browser /usr/bin/chromium`.
Use `--output-dir /tmp/chart-browser` to keep local results outside the checkout.
The checker starts and stops its own loopback Streamlit server. Browser requests
outside that server are blocked. Screenshots, a JSON result and server logs are
saved for review; the `Chart browser regression` workflow uploads these artifacts.
This is a local browser check, not verification of the hosted Streamlit deployment.

`python browser_checks/check_dashboard_navigation.py` also runs the real app
against stored snapshots with an isolated fake test password and provider calls
rejected. It verifies grid paging, area round trips, synchronized list/grid
controls, actual selected chart titles and preserved scroll offsets. It uses
the same optional `--browser` and `--output-dir` arguments and is included in CI.

The dashboard check also exercises the default absolute-return heatmap, compact
sector/Stage 2 split panes at 1440/800/390px, independent
candidate selection and daily-period restoration after grid/list round trips.

Footer geometry is read only after Plotly initialization and Streamlit stale-node
cleanup, in one browser frame. A deterministic Chromium fixture delays both
steps and confirms that a permanent misalignment still fails (the 2px alignment
and 4px centering limits are unchanged). The fixture runs with the dashboard
checker, including in the existing browser CI job.

`python browser_checks/check_china_dashboard.py` uses the same offline harness
to check the isolated SSE research preview, daily/weekly cursor and volume,
9+3 page round trips, 390px footer, blocked 512400 in list and grid, tab/period
restoration, and existing KWEB/CQQQ/SPY/EWY/EWJ daily/weekly charts. It accepts
the same browser/output arguments. This additional checker is run locally;
the Actions workflows are unchanged. On Windows, set `PYTHONUTF8=1` for the
repository's UTF-8 source/assets when the default locale is not UTF-8.
