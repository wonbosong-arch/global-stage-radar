"""Exercise the comparison menu with saved US and Korean price histories."""
import re

from playwright.sync_api import expect


def check_chart_comparison(page):
    from check_dashboard_navigation import click

    def tab(name):
        click(page.locator('.st-key-analysis_navigation').get_by_text(name, exact=True))

    selectors = [f'.st-key-chart_comparison_{position}_chart .js-plotly-plot'
                 for position in ('top', 'bottom')]
    plots = [page.locator(selector) for selector in selectors]
    state = """selectors => selectors.map(selector => {
        const graph = document.querySelector(selector);
        const axis = graph?._fullLayout?.xaxis2;
        return axis ? axis.range.map(date => axis.d2l(date)) : null;
    })"""

    def wait_for_pair(top, bottom, period):
        page.wait_for_function("""([selectors, symbols, period]) => selectors.every((selector, i) => {
            const graph = document.querySelector(selector);
            return graph?.layout?.meta?.asset_symbol === symbols[i]
                && graph?._fullLayout?.xaxis2?.type === 'date' && graph.data[0].name === period;
        })""", arg=[selectors, [top, bottom], period], timeout=60000)

    def synced(previous=None):
        page.wait_for_function(f"""([selectors, previous]) => {{
            const [top, bottom] = ({state})(selectors);
            return top && bottom && top.every((value, i) => value === bottom[i])
                && (!previous || top.some((value, i) => value !== previous[i]));
        }}""", arg=[selectors, previous])
        return page.evaluate(state, selectors)[0]

    def select(position, query, ticker):
        box = page.locator(f'.st-key-chart_comparison_{position}').get_by_role('combobox')
        box.fill(query)
        click(page.get_by_role('option', name=re.compile(rf'^{ticker} · ')))

    def gesture(plot, *, zoom):
        drag = plot.locator('.nsewdrag').first
        # Wait for Playwright's hit-target and layout checks after scrolling a chart into view.
        drag.hover()
        box = drag.bounding_box()
        if zoom:
            page.mouse.wheel(0, -220)
        else:
            page.mouse.down()
            page.mouse.move(box['x'] + box['width'] * .5 + 100, box['y'] + box['height'] * .5, steps=8)
            page.mouse.up()

    tab('차트 비교')
    wait_for_pair('SPY', 'QQQ', '주봉')
    for plot in plots:
        assert plot.evaluate('g => g._fullLayout.yaxis.type') == 'log'
    click(page.locator('.st-key-chart_comparison_top_asset_card').get_by_role('switch', name='로그'))
    expect(page.locator('.st-key-chart_comparison_bottom_asset_card').get_by_role('switch', name='로그')).to_be_checked()

    window = synced()
    for plot in plots:
        gesture(plot, zoom=False)
        panned = synced(window)
        assert abs((panned[1] - panned[0]) - (window[1] - window[0])) < 2
        gesture(plot, zoom=True)
        window = synced(panned)
        assert window[1] - window[0] < panned[1] - panned[0]

    select('bottom', 'KODEX 200', '069500')
    wait_for_pair('SPY', '069500', '주봉')
    assert synced() == window
    period = page.locator('.st-key-chart_comparison_period_chart_period_picker')
    click(period.get_by_role('button',name='일', exact=True))
    wait_for_pair('SPY', '069500', '일봉')
    synced()
    assert page.evaluate("""selectors => {
        const [us, kr] = selectors.map(selector => document.querySelector(selector));
        const [usDates, krDates] = [us, kr].map(g => new Set(g.data[0].x));
        const common = [...usDates].find(date => krDates.has(date));
        const [usAxis, krAxis] = [us, kr].map(g => g._fullLayout.xaxis2);
        const pixel = (axis, date) => axis._offset + axis.d2p(date);
        const [left, right] = usAxis.range.map(date => usAxis.d2l(date));
        return [...usDates].some(date => !krDates.has(date)
            && usAxis.d2l(date) >= left && usAxis.d2l(date) <= right)
            && Math.abs(pixel(usAxis, common) - pixel(krAxis, common)) < 1;
    }""", selectors), 'A Korean market holiday must leave a gap on the shared calendar'

    click(period.get_by_role('button',name='주', exact=True))
    wait_for_pair('SPY', '069500', '주봉')
    assert synced() == window
    select('top', 'CORT', 'CORT')
    wait_for_pair('CORT', '069500', '주봉')
    assert synced() == window
    tab('국가 및 원자재')
    tab('차트 비교')
    wait_for_pair('CORT', '069500', '주봉')
    assert synced() == window
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
    return {'bidirectional_pan_and_zoom': True, 'asset_swap_preserves_dates': True,
            'independent_price_scales': True, 'us_kr_holiday_alignment': True}
