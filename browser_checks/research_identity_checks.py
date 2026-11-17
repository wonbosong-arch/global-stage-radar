"""Exercise the real saved-input research path, including venue collisions."""
import re

from playwright.sync_api import expect


def check_saved_research(page, output):
    from grid_checks import check_grid_defaults, pager_button
    from check_dashboard_navigation import click

    def tab(name):
        click(page.locator('.st-key-analysis_navigation').get_by_text(name, exact=True))
        settled()

    def settled():
        page.wait_for_function("()=>document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')==='notRunning'", timeout=180000)
        page.wait_for_timeout(300)

    tab('종목')
    click(page.get_by_text('데이터·화면 설정', exact=True))
    click(page.get_by_text('KIS API · 미국·한국', exact=True))
    settled()
    password = page.get_by_label('KIS 모드 비밀번호', exact=True)
    if password.count():
        from check_dashboard_navigation import TEST_PASSWORD
        password.fill(TEST_PASSWORD)
        click(page.get_by_role('button', name='잠금 해제', exact=True))
        settled()
    tab('종목')
    expect(page.locator('.st-key-us_research_enabled')).to_be_visible(timeout=60000)
    click(page.get_by_text('데이터·화면 설정', exact=True))
    settled()
    click(page.locator('.st-key-us_research_enabled').get_by_text('미국 KIS 보유 데이터 · 업종/Stage 연구 분석', exact=True))
    explorer = page.get_by_text('보류 후보 차트 탐색 · 정식 활성화와 분리', exact=True)
    click(explorer)
    expect(page.get_by_text('미국 연구 Stage 분석 가능', exact=True)).to_be_visible(timeout=180000)
    expect(page.get_by_text(re.compile('신원 충돌 .*연구·차트 보류:')).first).to_be_visible()
    chart = page.locator('.st-key-pending_candidate_review_chart .js-plotly-plot')
    expect(chart).to_be_visible(timeout=60000)
    metrics = page.locator('[data-testid=stMetric]').all_text_contents()
    assert not page.get_by_text('보류 후보 차트 자료를 읽지 못했습니다', exact=False).count()
    click(page.locator('.st-key-pending_candidate_chart_period').get_by_text('일봉', exact=True))
    page.wait_for_function("()=>document.querySelector('.st-key-pending_candidate_review_chart .js-plotly-plot')?.data[0].name==='일봉'")
    selected = page.locator('.st-key-pending_candidate_chart_symbol input').input_value()
    before = page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')
    click(page.locator('.st-key-pending_candidate_table_grid_next button'))
    expect(page.locator('.st-key-pending_candidate_chart_symbol input')).to_have_value(selected)
    page.wait_for_timeout(500)
    after = page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')
    assert abs(after-before) < 3
    row = page.locator('.st-key-pending_candidate_research_list button').first
    symbol = row.inner_text().split(' · ')[0]
    click(row)
    expect(page.locator('.st-key-pending_candidate_chart_symbol input')).to_have_value(re.compile(re.escape(symbol)))
    search = page.locator('.st-key-pending_candidate_chart_search input')
    search.fill('TESTIDENTITY'); search.press('Enter')
    expect(page.get_by_text('검색/필터에 해당하는 후보가 없습니다.', exact=True)).to_be_visible()
    search.fill(''); search.press('Enter')
    page.screenshot(path=str(output / 'saved-research-candidates.png'))
    tab('Stage 2 후보')
    click(page.get_by_text('미국 KIS 연구 후보', exact=True))
    panel = page.locator('.st-key-research_candidate_quick_chart_symbol_compact_list')
    expect(panel).to_be_visible(timeout=180000)
    picks = panel.locator('[class*=st-key-research_candidate_quick_chart_symbol_pick_] button')
    symbol = picks.first.inner_text().strip()
    click(picks.first)
    search = page.locator('.st-key-research_candidate_quick_search input')
    search.fill('NO_SUCH_TICKER'); search.press('Enter')
    search.fill(''); search.press('Enter')
    click(page.locator('.st-key-research_candidate_quick_chart_period').get_by_text('일봉', exact=True))
    click(page.locator('.st-key-research_candidate_view_mode').get_by_text('3×3 차트', exact=True))
    check_grid_defaults(page, 'research_candidate_quick', 9)
    click(pager_button(page, 'research_candidate_quick', True))
    expect(page.locator('.st-key-research_candidate_quick_grid_pager')).to_contain_text('2 /')
    click(page.locator('.st-key-research_candidate_view_mode').get_by_text('목록', exact=True))
    page.wait_for_function("s=>document.querySelector('.st-key-research_candidate_quick_preview_chart .js-plotly-plot')?.layout.meta.asset_symbol===s", arg=symbol)
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
    page.screenshot(path=str(output / 'saved-research-stage2.png'))
    return {'metrics': metrics, 'paging_scroll_delta_px': after-before,
            'quarantined_search_empty': True, 'stage2_grid_page': 2,
            'selection_search_period_preserved': True}
