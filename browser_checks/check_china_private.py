"""Opt-in private-input Chromium journey. Never fetches provider prices."""
import check_dashboard_navigation as nav
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
    wait_chart(page, 'china_research_selected_chart', '512800')
    for period in ('일봉', '주봉'):
        nav.click(page.locator('.st-key-china_research_selected_chart_asset_card').get_by_text(period, exact=True))
        wait_chart(page, 'china_research_selected_chart', '512800')
    nav.click(page.locator('.st-key-china_research_pick_512880 button'))
    wait_chart(page, 'china_research_selected_chart', '512880')
    nav.click(page.get_by_text('3×3 차트', exact=True).last)
    expect(page.locator('[class*="st-key-china_research_grid_"][class*="_asset_card"]')).to_have_count(9)
    # The blocked 512400 remains a card without a chart; never silently substitutes prices.
    nav.click(page.locator('.st-key-china_research_grid_next button'))
    expect(page.locator('[class*="st-key-china_research_grid_"][class*="_asset_card"]')).to_have_count(3)
    nav.click(header.get_by_text('국가 및 원자재', exact=True))
    nav.click(header.get_by_text('업종', exact=True))
    expect(page.locator('[class*="st-key-china_research_grid_"][class*="_asset_card"]')).to_have_count(3)
    assert not page.locator('[data-testid=stException]').count()
    return {'private_china': True, 'grid_pages': [9,3], 'stage_eligible':0, 'stage_held':12}


if __name__ == '__main__':
    nav.exercise = exercise
    nav.main()
