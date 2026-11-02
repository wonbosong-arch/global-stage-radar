"""Real local Streamlit/Chromium interaction; shares the existing offline harness."""
import check_dashboard_navigation as nav
from playwright.sync_api import expect
from grid_checks import assert_footer, pager_button
from table_checks import wait_chart


def exercise(page, base, output):
    page.route('**/*', lambda route: route.continue_()
               if route.request.url.startswith(base + '/') else route.abort())
    page.goto(base, wait_until='domcontentloaded')
    nav.click(page.get_by_text('KIS API · 미국·한국', exact=True))
    page.get_by_label('KIS 모드 비밀번호', exact=True).fill(nav.TEST_PASSWORD)
    nav.click(page.get_by_role('button', name='잠금 해제', exact=True))
    header = page.locator('.st-key-analysis_header')
    nav.click(header.get_by_text('업종', exact=True))
    nav.click(page.get_by_text('중국 본토 SSE · 연구·관찰 12종', exact=True))
    selected = page.locator('.st-key-china_research_selected_chart_asset_card')

    def ready(symbol):
        wait_chart(page, 'china_research_selected_chart', symbol)

    def check_cursor(period):
        chart = selected.locator('.js-plotly-plot')
        page.wait_for_function('''period=>{
          const g=document.querySelector('.st-key-china_research_selected_chart .js-plotly-plot');
          return g?._fullData?.[0]?.name===period && g._fullLayout?.yaxis?.fixedrange
            && g._fullLayout?.yaxis2?.fixedrange && g.querySelector('.radar-crosshair');
        }''', arg=period)
        page.wait_for_function('''()=>!document.querySelector(
          '.st-key-china_research_selected_chart_asset_card [data-stale="true"]')''')
        chart.scroll_into_view_if_needed()
        # Scroll/resize events hide the cursor overlay; let the viewport settle
        # before sending a real pointer event at the final chart coordinates.
        page.wait_for_timeout(300)
        point = chart.evaluate('''g=>{const i=g.data[0].x.length-2,a=g._fullLayout;
          return {i,x:a.xaxis2._offset+a.xaxis2.d2p(g.data[0].x[i]),
            y:a.yaxis._offset+a.yaxis._length*.5,
            bottom:a.yaxis2._offset+a.yaxis2._length,top:a.yaxis._offset};}''')
        box = chart.bounding_box()
        page.mouse.move(0, 0)
        page.mouse.move(box['x']+point['x'], box['y']+point['y'])
        tip = page.locator('.radar-cursor-info:visible')
        expect(tip).to_have_attribute('data-index', str(point['i']))
        for label in ('시가', '고가', '저가', '종가', '거래량',
                      '50일 거래량 평균' if period == '일봉' else '10주 거래량 평균'):
            expect(tip).to_contain_text(label)
        line = chart.locator('.radar-crosshair').bounding_box()
        assert line['height'] >= point['bottom']-point['top']-1
        page.mouse.move(0, 0)

    ready('512800')
    nav.click(selected.get_by_text('일봉', exact=True))
    page.wait_for_function("()=>document.querySelector('.st-key-china_research_selected_chart .js-plotly-plot')?.data?.[0]?.name==='일봉'")
    chart = selected.locator('.js-plotly-plot')
    details = chart.evaluate('''g=>({bars:g.data[0].x.length,volume:g.data.some(t=>t.type==='bar'),
        hover:g.data.some(t=>t.name==='캔들 정보'),axis:g.data.every(t=>t.xaxis==='x2')})''')
    assert details == dict(bars=60, volume=True, hover=True, axis=True), details
    check_cursor('일봉')
    nav.click(selected.get_by_text('주봉', exact=True))
    check_cursor('주봉')
    weekly_bars = chart.evaluate('g=>g.data[0].x.length')
    assert 0 < weekly_bars < 60
    nav.click(selected.get_by_text('일봉', exact=True))
    check_cursor('일봉')
    panel = page.locator('.st-key-china_research_compact_list')
    assert panel.evaluate('e=>e.scrollHeight>e.clientHeight')
    button = page.locator('.st-key-china_research_pick_512880 button')
    button.scroll_into_view_if_needed()
    before = page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')
    nav.click(button)
    ready('512880')
    page.wait_for_timeout(500)
    after = page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')
    assert abs(after-before) < 3, ('selection scroll', before, after)
    selection_delta = after-before
    page.screenshot(path=str(output / 'china-list.png'))
    nav.click(page.get_by_text('3×3 차트', exact=True))
    grid = page.locator('.st-key-china_research_grid_canvas')
    expect(grid.locator('[class*="_asset_card"]')).to_have_count(9)
    assert assert_footer(page, 'china_research') == (1, 2)
    next_button = page.locator('.st-key-china_research_grid_next button:visible')
    expect(next_button).to_have_count(1)
    next_button.scroll_into_view_if_needed()
    before = page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')
    nav.click(next_button)
    expect(grid.locator('[class*="_asset_card"]')).to_have_count(3)
    page.wait_for_timeout(700)
    after = page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')
    assert abs(after-before) < 3, ('pager scroll', before, after)
    pager_delta = after-before
    assert assert_footer(page, 'china_research') == (2, 2)
    blocked = page.locator('.st-key-china_research_grid_512400_asset_card')
    expect(blocked.locator('.js-plotly-plot')).to_have_count(0)
    expect(page.get_by_text('공식 가격 불일치 · 차트 및 Stage 계산 차단', exact=True)).to_be_visible()
    grid.scroll_into_view_if_needed()
    page.screenshot(path=str(output / 'china-grid-blocked.png'))
    for forward, count, number in ((False, 9, 1), (True, 3, 2)):
        button = pager_button(page, 'china_research', forward)
        button.scroll_into_view_if_needed()
        before = page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')
        nav.click(button)
        expect(grid.locator('[class*="_asset_card"]')).to_have_count(count)
        assert assert_footer(page, 'china_research') == (number, 2)
        page.wait_for_timeout(2700)
        assert abs(page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')-before) < 3
    page.set_viewport_size({'width':390, 'height':1000})
    assert assert_footer(page, 'china_research') == (2, 2)
    assert page.locator('[data-testid=stMain]').evaluate('e=>e.scrollWidth') <= 391
    page.screenshot(path=str(output / 'china-grid-mobile.png'))
    page.set_viewport_size({'width':1440, 'height':1000})
    nav.click(page.locator('.st-key-china_research_grid_515220_open button'))
    ready('515220')
    nav.click(header.get_by_text('국가 및 원자재', exact=True))
    # Finish the outward navigation before returning; otherwise ready() could
    # read the previous tab's still-mounted chart during the first rerun.
    expect(selected).to_have_count(0, timeout=30000)
    expect(page.locator('.st-key-markets_commodities_view_mode')).to_be_visible()
    nav.click(header.get_by_text('업종', exact=True))
    expect(page.get_by_role('radio', name='중국 본토 SSE · 연구·관찰 12종', exact=True)).to_be_checked()
    ready('515220')
    nav.click(page.locator('.st-key-china_research_pick_512400 button'))
    expect(selected.locator('.js-plotly-plot')).to_have_count(0)
    expect(page.get_by_text('공식 가격 불일치 · 차트 및 Stage 계산 차단', exact=True)).to_be_visible()
    nav.click(page.locator('.st-key-china_research_pick_512800 button'))
    ready('512800')
    expect(selected.get_by_role('radio', name='일봉', exact=True)).to_be_checked()
    expect(selected.get_by_role('button', name='☆ 관심 등록', exact=False)).to_have_count(0)
    nav.click(page.get_by_text('기존 업종 · 미국 상장 중국 프록시 포함', exact=True))
    expect(page.locator('.st-key-sectors_view_mode')).to_be_visible()
    # The real stored US-listed proxies and country ETFs stay on existing routes.
    for area, symbols in (('sectors', ('KWEB', 'CQQQ')),
                          ('markets_commodities', ('SPY', 'EWY', 'EWJ'))):
        if area == 'markets_commodities':
            nav.click(header.get_by_text('국가 및 원자재', exact=True))
        nav.click(page.locator(f'.st-key-{area}_view_mode').get_by_text('목록', exact=True))
        for symbol in symbols:
            search = page.locator(f'.st-key-{area}_search input')
            search.fill(symbol)
            search.press('Enter')
            nav.click(page.locator(f'.st-key-{area}_selected_symbol_pick_{symbol} button:visible'))
            wait_chart(page, f'{area}_selected_chart', symbol)
            card = page.locator(f'.st-key-{area}_selected_chart_asset_card')
            for period in ('일봉', '주봉'):
                nav.click(card.get_by_text(period, exact=True))
                page.wait_for_function('''({key,symbol,period})=>{
                  const g=document.querySelector(`.st-key-${key} .js-plotly-plot`);
                  return g?.layout?.meta?.asset_symbol===symbol && g._fullData?.[0]?.name===period
                    && g._fullLayout?.yaxis2?.type==='linear';
                }''', arg={'key':f'{area}_selected_chart','symbol':symbol,'period':period})
        search.fill('')
        search.press('Enter')
    assert page.locator('[data-testid=stException]').count() == 0
    return {'china': 'passed', 'daily_chart': details, 'weekly_bars': weekly_bars,
            'cursor_daily_weekly': True, 'selection_scroll_px': selection_delta,
            'pager_scroll_px': pager_delta, 'grid_pages': [9,3,9,3],
            'existing_symbols': ['KWEB','CQQQ','SPY','EWY','EWJ'],
            'blocked_in_list_and_grid': True, 'research_period_restored': True,
            'blocked_symbol': '512400', 'operational_activation': False}


if __name__ == '__main__':
    nav.exercise = exercise
    nav.main()
