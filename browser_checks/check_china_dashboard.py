"""Real local Streamlit/Chromium interaction; shares the existing offline harness."""
import check_dashboard_navigation as nav
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import expect
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
    from china_dashboard import RIGHTS_BLOCK
    expect(page.get_by_text(RIGHTS_BLOCK, exact=True)).to_be_visible()
    expect(page.locator('.js-plotly-plot')).to_have_count(0)
    expect(page.locator('[class*="st-key-china_"] [data-testid=stDownloadButton]')).to_have_count(0)
    expect(page.locator('[class*="st-key-china_research_pick_"]')).to_have_count(0)
    page.reload(wait_until='domcontentloaded')
    # Authentication and the private research selector are session-only.
    page.get_by_label('KIS 모드 비밀번호', exact=True).fill(nav.TEST_PASSWORD)
    nav.click(page.get_by_role('button', name='잠금 해제', exact=True))
    nav.click(header.get_by_text('업종', exact=True))
    nav.click(page.get_by_text('중국 본토 SSE · 연구·관찰 12종', exact=True))
    expect(page.get_by_text(RIGHTS_BLOCK, exact=True)).to_be_visible(timeout=30000)
    expect(page.locator('.js-plotly-plot')).to_have_count(0)
    for width in (1440, 390):
        page.set_viewport_size({'width': width, 'height': 1000})
        expect(page.get_by_text(RIGHTS_BLOCK, exact=True)).to_be_visible()
        page.screenshot(path=str(output / f'china-rights-blocked-{width}.png'))
    page.set_viewport_size({'width':1440, 'height':1000})
    nav.click(header.get_by_text('국가 및 원자재', exact=True))
    expect(page.locator('.st-key-markets_commodities_view_mode')).to_be_visible()
    nav.click(header.get_by_text('업종', exact=True))
    expect(page.get_by_text(RIGHTS_BLOCK, exact=True)).to_be_visible()
    expect(page.locator('.js-plotly-plot')).to_have_count(0)
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
    return {'china_rights_block': 'passed', 'china_charts': 0,
            'china_downloads': 0, 'reload_and_tab_return': True,
            'existing_symbols': ['KWEB','CQQQ','SPY','EWY','EWJ'],
            'operational_activation': False}



if __name__ == '__main__':
    nav.exercise = exercise
    nav.main()
