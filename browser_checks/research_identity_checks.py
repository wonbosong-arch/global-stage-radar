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

    settings = page.get_by_text('�����͡�ȭ�� ����', exact=True)
    expect(settings).to_be_visible(timeout=60000)
    kis_mode = page.get_by_text('KIS API �� �̱����ѱ�', exact=True)
    if not kis_mode.is_visible():
        click(settings)
    click(kis_mode)
    settled()
    password = page.get_by_label('KIS ��� ��й�ȣ', exact=True)
    unlocked = page.get_by_role('button', name='KIS ��� ��ױ�', exact=True)
    expect(password.or_(unlocked)).to_be_visible(timeout=60000)
    if password.is_visible():
        from check_dashboard_navigation import TEST_PASSWORD
        password.fill(TEST_PASSWORD)
        click(page.get_by_role('button', name='��� ����', exact=True))
        settled()
    expect(unlocked).to_be_visible(timeout=60000)
    tab('����')
    scope = page.locator('.st-key-stocks_market').get_by_role('combobox')
    expect(scope).to_have_value('�̱� �� ��ü ���� ��Ʈ', timeout=60000)
    scope.press('ArrowDown')
    click(page.get_by_role('option', name='�̱� �� ���� �Ϸ�', exact=True))
    expect(scope).to_have_value('�̱� �� ���� �Ϸ�', timeout=60000)
    settled()
    tab('�� ���� ���')
    tab('����')
    expect(scope).to_have_value('�̱� �� ���� �Ϸ�', timeout=60000)
    ready = page.get_by_text(re.compile('�̱� ���Ρ�Stage �м� ������ ���� ���� [0-9,]+��')).first
    expect(ready).to_be_visible(timeout=60000)
    match = re.search(r'���� ���� ([0-9,]+)��', ready.inner_text())
    assert match and int(match.group(1).replace(',', '')) > 0, 'No actual Stage-ready mapped research stocks'
    mapped_ready_count = int(match.group(1).replace(',', ''))
    scope.press('ArrowDown')
    click(page.get_by_role('option', name='�̱� �� ��ü ���� ��Ʈ', exact=True))
    expect(scope).to_have_value('�̱� �� ��ü ���� ��Ʈ', timeout=60000)
    settled()
    expect(page.locator('.st-key-us_research_enabled')).to_have_count(0)
    click(page.get_by_text('�����͡�ȭ�� ����', exact=True))
    settled()
    expect(page.get_by_text('���� �ĺ� ��Ʈ Ž�� �� ���� Ȱ��ȭ�� �и�', exact=True)).to_have_count(0)
    coverage = page.get_by_text(f'�̱� ���� ���� ��Ʈ {expected_chart_count:,}��', exact=False).first
    expect(coverage).to_be_visible(timeout=180000)
    expect(page.get_by_text(re.compile('�ſ� �浹 .*��������Ʈ ����:')).first).to_be_visible()
    chart = page.locator('.st-key-stocks_selected_chart .js-plotly-plot')
    expect(chart).to_be_visible(timeout=60000)
    metrics = {'coverage': coverage.inner_text(), 'mapped_ready_research': mapped_ready_count}
    market = page.locator('.st-key-stocks_market').get_by_role('combobox')
    expect(market).to_have_value('�̱� �� ��ü ���� ��Ʈ')
    settled()
    expect(page.get_by_text(f'{expected_chart_count}�� �ڻ� �� �׸��� ������ ��Ʈ�� ��ȯ�� �� �ֽ��ϴ�.', exact=True)).to_be_visible()
    selected = chart.evaluate('g=>g.layout.meta.asset_symbol')
    click(page.locator(f'.st-key-stocks_selected_period_{selected}').get_by_text('�Ϻ�', exact=True))
    # The Streamlit fragment must finish accepting the radio change before
    # a later list interaction; a checked radio alone can still show old bars.
    settled()
    page.wait_for_function("()=>document.querySelector('.st-key-stocks_selected_chart .js-plotly-plot')?.data[0].name==='�Ϻ�'")
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
    expect(page.get_by_text('������ ���ǿ� �ش��ϴ� �ڻ��� �����ϴ�. ���� ��Ʈ ������ �����մϴ�.', exact=True)).to_be_visible(timeout=60000)
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
    # Otherwise an older fragment rerun can overwrite the 3��3 selection.
    expect(page.get_by_text(f'{expected_chart_count}�� �ڻ� �� �׸��� ������ ��Ʈ�� ��ȯ�� �� �ֽ��ϴ�.', exact=True)).to_be_visible(timeout=60000)
    click(page.locator('.st-key-stocks_view_mode').get_by_text('3��3 ��Ʈ', exact=True))
    expect(page.locator('.st-key-stocks_view_mode').get_by_role('radio', name='3��3 ��Ʈ', exact=True)).to_be_checked(timeout=60000)
    settled()
    check_grid_defaults(page, 'stocks', 9)
    # Nine painted Plotly charts do not prove the fragment is idle. Wait for
    # the complete grid to settle before dispatching a page-change callback.
    settled()
    expect(pager_button(page, 'stocks', True)).to_be_enabled(timeout=60000)
    click(pager_button(page, 'stocks', True))
    expect(page.locator('.st-key-stocks_grid_pager')).to_contain_text('2 /', timeout=60000)
    settled()
    click(page.locator('.st-key-stocks_view_mode').get_by_text('���', exact=True))
    settled()
    expect(page.locator('.st-key-stocks_view_mode').get_by_role('radio', name='���', exact=True)).to_be_checked(timeout=180000)
    expect(chart).to_be_visible(timeout=180000)
    page.wait_for_function("s=>document.querySelector('.st-key-stocks_selected_chart .js-plotly-plot')?.layout.meta.asset_symbol===s", arg=symbol, timeout=180000)
    page.screenshot(path=str(output / 'saved-research-candidates.png'))
    for ticker in dict.fromkeys((short_symbol, 'CORT', 'PRIM', 'NTRS', 'ORCL')):
        search.fill(ticker)
        search.press('Enter')
        settled()
        click(page.locator(f'.st-key-stocks_selected_symbol_pick_{ticker} button:visible'))
        if ticker == short_symbol:
            card = page.locator('.st-key-stocks_selected_chart_asset_card')
            expect(card).to_contain_text('���� �̷� ���� �� Stage ����', timeout=60000)
        period_control = page.locator(f'.st-key-stocks_selected_period_{ticker}')
        for period in ('�Ϻ�', '�ֺ�'):
            radio = period_control.get_by_role('radio', name=period, exact=True)
            expect(radio).to_be_attached(timeout=60000)
            if not radio.is_checked():
                click(period_control.get_by_text(period, exact=True))
                settled()
            page.wait_for_function("""([symbol, period]) => {
                const graph = document.querySelector('.st-key-stocks_selected_chart .js-plotly-plot');
                return graph?.layout?.meta?.asset_symbol === symbol && graph.data[0].name === period;
            }""", arg=[ticker, period], timeout=60000)
    tab('Stage 2 �ĺ�')
    click(page.get_by_text('�̱� KIS ���� �ĺ�', exact=True))
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
    expect(page.get_by_text('���� ���ǿ� �´� �ĺ��� �����ϴ�.', exact=True)).to_be_visible(timeout=60000)
    expect(preview).to_have_count(0)
    search.fill(''); search.press('Enter')
    settled()
    expect_preview()
    click(page.locator('.st-key-research_candidate_quick_chart_period').get_by_text('�Ϻ�', exact=True))
    settled()
    expect_preview('�Ϻ�')
    view = page.locator('.st-key-research_candidate_view_mode')
    click(view.get_by_text('3��3 ��Ʈ', exact=True))
    settled()
    check_grid_defaults(page, 'research_candidate_quick', 9)
    expect(preview).to_have_count(0)
    click(pager_button(page, 'research_candidate_quick', True))
    expect(page.locator('.st-key-research_candidate_quick_grid_pager')).to_contain_text('2 /', timeout=60000)
    settled()
    click(view.get_by_text('���', exact=True))
    # The radio is checked before the fragment replays the saved KIS data.
    # Wait for the old grid to unmount before checking the replacement chart.
    expect(page.locator('.st-key-research_candidate_quick_grid_canvas')).to_have_count(0, timeout=180000)
    settled()
    expect_preview('�Ϻ�')
    expect(page.locator('[data-testid=stException]')).to_have_count(0)
    page.screenshot(path=str(output / 'saved-research-stage2.png'))
    return {'metrics': metrics, 'paging_scroll_delta_px': after-before,
            'quarantined_search_empty': True, 'stage2_grid_page': 2,
            'selection_search_period_preserved': True}
