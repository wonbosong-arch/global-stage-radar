"""Exercise the real saved-input research path, including venue collisions."""
import re

from playwright.sync_api import expect


def check_saved_research(page, output):
    from grid_checks import check_grid_defaults, pager_button
    from check_dashboard_navigation import click
    page.set_viewport_size({'width': 1440, 'height': 1000})

    def tab(name):
        click(page.locator('.st-key-analysis_navigation').get_by_text(name, exact=True))
        settled()

    def settled():
        # Fragment reruns can retain the root's `running` attribute after their
        # widgets/charts have painted. Await actual rendering, then assert each
        # requested outcome below rather than this full-script status flag.
        page.wait_for_timeout(500)
        expect(page.locator('[data-testid=stSpinner]')).to_have_count(0, timeout=180000)
        expect(page.locator('.st-key-analysis_workspace [data-stale="true"]')).to_have_count(0, timeout=60000)

    settings = page.get_by_text('데이터·화면 설정', exact=True)
    expect(settings).to_be_visible(timeout=60000)
    kis_mode = page.get_by_text('KIS API · 미국·한국', exact=True)
    if not kis_mode.is_visible():
        click(settings)
    click(kis_mode)
    settled()
    password = page.get_by_label('KIS 모드 비밀번호', exact=True)
    unlocked = page.get_by_role('button', name='KIS 모드 잠그기', exact=True)
    expect(password.or_(unlocked)).to_be_visible(timeout=60000)
    if password.is_visible():
        from check_dashboard_navigation import TEST_PASSWORD
        password.fill(TEST_PASSWORD)
        click(page.get_by_role('button', name='잠금 해제', exact=True))
        settled()
    expect(unlocked).to_be_visible(timeout=60000)
    tab('종목')
    # Mapped, Stage-ready US research stocks are the default; all retained
    # charts must still be reachable without another research entry point.
    scope = page.locator('.st-key-stocks_mapping_scope')
    expect(scope.get_by_role('radio', name='매핑·Stage 분석 가능')).to_be_checked(timeout=60000)
    ready = page.get_by_text(re.compile('업종 ETF 매핑·Stage 분석 가능한 [0-9,]+개 우선 탐색')).first
    expect(ready).to_be_visible(timeout=60000)
    match = re.search(r'분석 가능한 ([0-9,]+)개 우선 탐색', ready.inner_text())
    assert match and int(match.group(1).replace(',', '')) > 0, 'No actual Stage-ready mapped research stocks'
    mapped_ready_count = int(match.group(1).replace(',', ''))
    click(scope.get_by_text('전체 가격 차트', exact=True))
    expect(scope.get_by_role('radio', name='전체 가격 차트')).to_be_checked(timeout=60000)
    settled()
    expect(page.locator('.st-key-us_research_enabled')).to_have_count(0)
    click(page.get_by_text('데이터·화면 설정', exact=True))
    settled()
    expect(page.get_by_text('보류 후보 차트 탐색 · 정식 활성화와 분리', exact=True)).to_have_count(0)
    coverage = page.get_by_text(re.compile('미국 보유 가격 차트 2,335개')).first
    expect(coverage).to_be_visible(timeout=180000)
    expect(page.get_by_text(re.compile('신원 충돌 .*연구·차트 보류:')).first).to_be_visible()
    chart = page.locator('.st-key-stocks_selected_chart .js-plotly-plot')
    expect(chart).to_be_visible(timeout=60000)
    metrics = {'coverage': coverage.inner_text(), 'mapped_ready_research': mapped_ready_count}
    market = page.locator('.st-key-stocks_market').get_by_role('combobox')
    market.press('ArrowDown')
    click(page.get_by_role('option', name='미국', exact=True))
    settled()
    expect(page.get_by_text('2335개 자산 · 항목을 선택해 차트를 전환할 수 있습니다.', exact=True)).to_be_visible()
    selected = chart.evaluate('g=>g.layout.meta.asset_symbol')
    click(page.locator(f'.st-key-stocks_selected_period_{selected}').get_by_text('일봉', exact=True))
    # The Streamlit fragment must finish accepting the radio change before
    # a later list interaction; a checked radio alone can still show old bars.
    settled()
    page.wait_for_function("()=>document.querySelector('.st-key-stocks_selected_chart .js-plotly-plot')?.data[0].name==='일봉'")
    before = page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')
    click(page.locator('.st-key-stocks_table_grid_next button'))
    settled()
    assert chart.evaluate('g=>g.layout.meta.asset_symbol') == selected
    page.wait_for_timeout(500)
    after = page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop')
    assert abs(after-before) < 3
    row = page.locator('[class*=st-key-stocks_selected_symbol_pick_] button:visible').first
    symbol = row.inner_text().strip()
    click(row)
    page.wait_for_function("s=>document.querySelector('.st-key-stocks_selected_chart .js-plotly-plot')?.layout.meta.asset_symbol===s", arg=symbol)
    search = page.locator('.st-key-stocks_search input')
    search.fill('TESTIDENTITY'); search.press('Enter')
    # Streamlit can retain the prior 2,335-row list while the search fragment
    # reruns; await the new result instead of interpreting a queued event as
    # a selection/search regression.
    settled()
    expect(page.get_by_text('선택한 조건에 해당하는 자산이 없습니다. 기존 차트 선택은 유지합니다.', exact=True)).to_be_visible(timeout=60000)
    assert chart.evaluate('g=>g.layout.meta.asset_symbol') == symbol
    # Search the whole universe, including a ticker outside the first 50 rows.
    search.fill(symbol); search.press('Enter')
    settled()
    # Streamlit mounts a hidden duplicate button for its tooltip layout.
    searched_row = page.locator(f'.st-key-stocks_selected_symbol_pick_{symbol} button:visible')
    expect(searched_row).to_have_count(1, timeout=60000)
    expect(searched_row).to_be_visible()
    search.fill(''); search.press('Enter')
    settled()
    # The filter reset must have reached the server before switching modes.
    # Otherwise an older fragment rerun can overwrite the 3×3 selection.
    expect(page.get_by_text('2335개 자산 · 항목을 선택해 차트를 전환할 수 있습니다.', exact=True)).to_be_visible(timeout=60000)
    click(page.locator('.st-key-stocks_view_mode').get_by_text('3×3 차트', exact=True))
    expect(page.locator('.st-key-stocks_view_mode').get_by_role('radio', name='3×3 차트', exact=True)).to_be_checked(timeout=60000)
    settled()
    check_grid_defaults(page, 'stocks', 9)
    # Nine painted Plotly charts do not prove the fragment is idle. Wait for
    # the complete grid to settle before dispatching a page-change callback.
    settled()
    expect(pager_button(page, 'stocks', True)).to_be_enabled(timeout=60000)
    click(pager_button(page, 'stocks', True))
    expect(page.locator('.st-key-stocks_grid_pager')).to_contain_text('2 /', timeout=60000)
    settled()
    click(page.locator('.st-key-stocks_view_mode').get_by_text('목록', exact=True))
    settled()
    expect(page.locator('.st-key-stocks_view_mode').get_by_role('radio', name='목록', exact=True)).to_be_checked(timeout=180000)
    expect(chart).to_be_visible(timeout=180000)
    page.wait_for_function("s=>document.querySelector('.st-key-stocks_selected_chart .js-plotly-plot')?.layout.meta.asset_symbol===s", arg=symbol, timeout=180000)
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
    settled()
    search.fill(''); search.press('Enter')
    settled()
    click(page.locator('.st-key-research_candidate_quick_chart_period').get_by_text('일봉', exact=True))
    click(page.locator('.st-key-research_candidate_view_mode').get_by_text('3×3 차트', exact=True))
    check_grid_defaults(page, 'research_candidate_quick', 9)
    click(pager_button(page, 'research_candidate_quick', True))
    expect(page.locator('.st-key-research_candidate_quick_grid_pager')).to_contain_text('2 /', timeout=60000)
    settled()
    click(page.locator('.st-key-research_candidate_view_mode').get_by_text('목록', exact=True))
    page.wait_for_function("s=>document.querySelector('.st-key-research_candidate_quick_preview_chart .js-plotly-plot')?.layout.meta.asset_symbol===s", arg=symbol)
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
    page.screenshot(path=str(output / 'saved-research-stage2.png'))
    return {'metrics': metrics, 'paging_scroll_delta_px': after-before,
            'quarantined_search_empty': True, 'stage2_grid_page': 2,
            'selection_search_period_preserved': True}
