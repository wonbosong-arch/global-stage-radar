"""Exercise the real saved-input research path, including venue collisions."""
import re

from playwright.sync_api import expect


def saved_chart_expectations(data):
    """Read the same fixed snapshot as the browser's offline server."""
    import pandas as pd

    from us_research_dashboard import build_research

    def read(name):
        return pd.read_csv(data / name, dtype=str, keep_default_na=False)

    pending, active = read('candidate_daily_prices.csv'), read('daily_prices.csv')
    as_of = pd.Timestamp(min(pending.date.max(), active.date.max())) + pd.Timedelta(days=1)
    report, prices = build_research(
        read('stock_universe_candidates.csv'), read('unranked_us_stock_master.csv'),
        read('monitoring_universe.csv'), pending, active, read('provisional_candidate_stage_report.csv'),
        supplement=read('yahoo_market_cap_supplement.csv'),
        as_of=as_of, now=(as_of + pd.Timedelta(hours=6)).tz_localize('UTC'),
    )
    symbols = set(prices.symbol)
    short = report.loc[report.symbol.isin(symbols) & report.price_history_short]
    return len(symbols), short.sort_values('weekly_bars').symbol.iloc[0]


def check_saved_research(page, output, expected_chart_count, short_symbol):
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
    click(page.locator('.st-key-analysis_navigation').get_by_text('종목', exact=True))
    # The first visit builds the offline snapshot before rendering stock controls.
    # The previous dashboard can still be visible while that data is prepared.
    scope = page.locator('.st-key-stocks_market').get_by_role('combobox')
    expect(scope).to_have_value('미국 · 전체 가격 차트', timeout=180000)
    settled()
    scope.press('ArrowDown')
    click(page.get_by_role('option', name='미국 · 매핑 완료', exact=True))
    expect(scope).to_have_value('미국 · 매핑 완료', timeout=60000)
    settled()
    tab('☆ 관심 목록')
    tab('종목')
    expect(scope).to_have_value('미국 · 매핑 완료', timeout=60000)
    ready = page.get_by_text(re.compile('미국 연구 Stage 분석 [0-9,]+개')).first
    expect(ready).to_be_visible(timeout=60000)
    match = re.search(r'미국 연구 Stage 분석 ([0-9,]+)개', ready.inner_text())
    assert match and int(match.group(1).replace(',', '')) > 0, 'No actual Stage-ready mapped research stocks'
    mapped_ready_count = int(match.group(1).replace(',', ''))
    scope.press('ArrowDown')
    click(page.get_by_role('option', name='미국 · 전체 가격 차트', exact=True))
    expect(scope).to_have_value('미국 · 전체 가격 차트', timeout=60000)
    settled()
    expect(page.locator('.st-key-us_research_enabled')).to_have_count(0)
    click(page.get_by_text('데이터·화면 설정', exact=True))
    settled()
    expect(page.get_by_text('보류 후보 차트 탐색 · 정식 활성화와 분리', exact=True)).to_have_count(0)
    coverage = page.get_by_text(f'미국 가격 차트 {expected_chart_count:,}개', exact=False).first
    expect(coverage).to_be_visible(timeout=180000)
    coverage.scroll_into_view_if_needed()
    click(page.locator('.st-key-stocks_data_footer').get_by_text('데이터 범위', exact=True))
    expect(page.get_by_text(re.compile('신원 충돌 .*연구·차트 보류:')).first).to_be_visible()
    page.locator('[data-testid=stMain]').evaluate('e=>e.scrollTop=0')
    chart = page.locator('.st-key-stocks_selected_chart .js-plotly-plot')
    expect(chart).to_be_visible(timeout=60000)
    metrics = {'coverage': coverage.inner_text(), 'mapped_ready_research': mapped_ready_count}
    market = page.locator('.st-key-stocks_market').get_by_role('combobox')
    expect(market).to_have_value('미국 · 전체 가격 차트')
    settled()
    expect(page.get_by_text(f'현재 조건 {expected_chart_count:,}개', exact=True)).to_be_visible()
    selected = chart.evaluate('g=>g.layout.meta.asset_symbol')
    period_controls = page.locator('.st-key-stocks_selected_chart_controls')
    click(period_controls.get_by_role('button', name='일', exact=True))
    # Wait for the fragment and its new bars before using the list again.
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
    # Streamlit can retain the prior full list while the search fragment
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
    expect(page.get_by_text(f'현재 조건 {expected_chart_count:,}개', exact=True)).to_be_visible(timeout=60000)
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
    for ticker in dict.fromkeys((
        short_symbol, 'CORT', 'PRIM', 'NTRS', 'ORCL', 'TSM', 'BABA', 'HDB', 'IBN', 'GSK',
    )):
        search.fill(ticker)
        search.press('Enter')
        settled()
        click(page.locator(f'.st-key-stocks_selected_symbol_pick_{ticker} button:visible'))
        if ticker == short_symbol:
            card = page.locator('.st-key-stocks_selected_chart_asset_card')
            expect(card).to_contain_text('가격 이력 부족 · Stage 보류', timeout=60000)
        current_period = page.wait_for_function("""symbol => {
            const graph = document.querySelector('.st-key-stocks_selected_chart .js-plotly-plot');
            return graph?.layout?.meta?.asset_symbol === symbol && graph.data?.[0]?.name;
        }""", arg=ticker, timeout=60000).json_value()
        for period in ('일봉', '주봉'):
            period_control = period_controls.get_by_role('button', name=period[0], exact=True)
            expect(period_control).to_be_visible(timeout=60000)
            if current_period != period:
                click(period_control)
                settled()
            current_period = page.wait_for_function("""([symbol, period]) => {
                const graph = document.querySelector('.st-key-stocks_selected_chart .js-plotly-plot');
                const actual = graph?.data?.[0]?.name;
                return graph?.layout?.meta?.asset_symbol === symbol && actual === period && actual;
            }""", arg=[ticker, period], timeout=60000).json_value()
            expect(period_control).to_have_attribute('kind', 'primary')
    tab('Stage 2 후보')
    click(page.get_by_text('미국 KIS 연구 후보', exact=True))
    panel = page.locator('.st-key-research_candidate_quick_chart_symbol_compact_list')
    expect(panel).to_be_visible(timeout=180000)
    preview_selector = '.st-key-research_candidate_quick_preview_chart .js-plotly-plot'
    preview = page.locator(preview_selector)
    expect(preview).to_be_visible(timeout=180000)
    initial = preview.evaluate('g=>g.layout.meta.asset_symbol')
    picks = panel.locator('[class*=st-key-research_candidate_quick_chart_symbol_pick_] button:visible')
    target = picks.filter(has_not_text=re.compile(rf'^{re.escape(initial)}$')).first
    symbol = target.inner_text().strip()

    def expect_preview(period=None):
        page.wait_for_function(
            """([selector, symbol, period]) => {
                const chart = document.querySelector(selector);
                return chart?.layout?.meta?.asset_symbol === symbol
                    && (!period || chart.data?.[0]?.name === period);
            }""",
            arg=[preview_selector, symbol, period],
        )

    click(target)
    settled()
    expect_preview()
    search = page.locator('.st-key-research_candidate_quick_search input')
    search.fill('NO_SUCH_TICKER'); search.press('Enter')
    expect(page.get_by_text('현재 조건에 맞는 후보가 없습니다.', exact=True)).to_be_visible(timeout=60000)
    expect(preview).to_have_count(0)
    search.fill(''); search.press('Enter')
    settled()
    expect_preview()
    click(page.locator('.st-key-research_candidate_quick_chart_period').get_by_text('일봉', exact=True))
    settled()
    expect_preview('일봉')
    view = page.locator('.st-key-research_candidate_view_mode')
    click(view.get_by_text('3×3 차트', exact=True))
    settled()
    check_grid_defaults(page, 'research_candidate_quick', 9)
    expect(preview).to_have_count(0)
    click(pager_button(page, 'research_candidate_quick', True))
    expect(page.locator('.st-key-research_candidate_quick_grid_pager')).to_contain_text('2 /', timeout=60000)
    settled()
    click(view.get_by_text('목록', exact=True))
    # The radio is checked before the fragment replays the saved KIS data.
    # Wait for the old grid to unmount before checking the replacement chart.
    expect(page.locator('.st-key-research_candidate_quick_grid_canvas')).to_have_count(0, timeout=180000)
    settled()
    expect_preview('일봉')
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
    page.screenshot(path=str(output / 'saved-research-stage2.png'))
    return {'metrics': metrics, 'paging_scroll_delta_px': after-before,
            'quarantined_search_empty': True, 'stage2_grid_page': 2,
            'selection_search_period_preserved': True}
