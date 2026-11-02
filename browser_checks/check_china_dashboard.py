"""Real local Streamlit/Chromium interaction; shares the existing offline harness."""
import check_dashboard_navigation as nav
from playwright.sync_api import expect


def exercise(page, base, output):
    page.route('**/*', lambda route: route.continue_()
               if route.request.url.startswith(base + '/') else route.abort())
    page.goto(base, wait_until='domcontentloaded')
    header = page.locator('.st-key-analysis_header')
    nav.click(header.get_by_text('업종', exact=True))
    nav.click(page.get_by_text('중국 본토 SSE · 연구·관찰 12종', exact=True))
    selected = page.locator('.st-key-china_research_selected_chart_asset_card')

    def ready(symbol):
        page.wait_for_function('''s=>document.querySelector('.st-key-china_research_selected_chart .js-plotly-plot')?.layout?.meta?.asset_symbol===s''', arg=symbol)

    ready('512800')
    nav.click(selected.get_by_text('일봉', exact=True))
    page.wait_for_function("()=>document.querySelector('.st-key-china_research_selected_chart .js-plotly-plot')?.data?.[0]?.name==='일봉'")
    chart = selected.locator('.js-plotly-plot')
    details = chart.evaluate('''g=>({bars:g.data[0].x.length,volume:g.data.some(t=>t.type==='bar'),
        hover:g.data.some(t=>t.name==='캔들 정보'),axis:g.data.every(t=>t.xaxis==='x2')})''')
    assert details == dict(bars=60, volume=True, hover=True, axis=True), details
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
    page.screenshot(path=str(output / 'china-list.png'))
    nav.click(page.get_by_text('3×3 차트', exact=True))
    grid = page.locator('.st-key-china_research_grid_canvas')
    expect(grid.locator('[class*="_asset_card"]')).to_have_count(9)
    next_button = page.locator('.st-key-china_research_grid_next button:visible')
    expect(next_button).to_have_count(1)
    next_button.scroll_into_view_if_needed()
    before = page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')
    nav.click(next_button)
    expect(grid.locator('[class*="_asset_card"]')).to_have_count(3)
    page.wait_for_timeout(700)
    after = page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')
    assert abs(after-before) < 3, ('pager scroll', before, after)
    blocked = page.locator('.st-key-china_research_grid_512400_asset_card')
    expect(blocked.locator('.js-plotly-plot')).to_have_count(0)
    expect(page.get_by_text('공식 가격 불일치 · 차트 및 Stage 계산 차단', exact=True)).to_be_visible()
    grid.scroll_into_view_if_needed()
    page.screenshot(path=str(output / 'china-grid-blocked.png'))
    nav.click(page.locator('.st-key-china_research_grid_515220_open button'))
    ready('515220')
    nav.click(header.get_by_text('국가 및 원자재', exact=True))
    nav.click(header.get_by_text('업종', exact=True))
    ready('515220')
    nav.click(page.get_by_text('기존 업종 · 미국 상장 중국 프록시 포함', exact=True))
    expect(page.locator('.st-key-sectors_view_mode')).to_be_visible()
    assert page.locator('[data-testid=stException]').count() == 0
    return {'china': 'passed', 'daily_chart': details, 'selection_scroll_px': after-before,
            'blocked_symbol': '512400', 'operational_activation': False}


if __name__ == '__main__':
    nav.exercise = exercise
    nav.main()
