import copy
from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest
from us_research_dashboard import comparison_rows

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    rows = []
    prices = []
    for i in range(66):
        symbol = f'RESEARCH{i:02}'
        rows.append(dict(symbol=symbol, name=f'Research Company {i}', exchange='NYS',
            proposed_sector='Materials' if i < 62 else 'Financials',
            suggested_sector_benchmark='XLB' if i < 62 else 'XLF', market_benchmark='SPY',
            research_eligible=i != 65, provisional_stage_label='Stage 2 후보' if i != 64 else 'Stage 2A 관찰 후보',
            close=100+i, ma30=90, ma30_slope_4w_pct=1, market_rs_26w_pct=i,
            sector_rs_26w_pct=i/2, ret26_pct=i, ret13_pct=i/2, vol_ratio=1,
            candidate_latest_daily_date='2026-10-23', completed_weekly_date='2026-10-23',
            volume_context='보통', activation_status='pending_review_not_activated'))
        for d in pd.bdate_range(end='2026-10-23', periods=220):
            prices.append(dict(symbol=symbol, date=d, open=99+i, high=102+i,
                               low=98+i, close=100+i, volume=1000))
    return pd.DataFrame(rows), pd.DataFrame(prices)


def test_adapter_excludes_holds_preserves_pending_and_metrics():
    report, _ = fixture()
    before = copy.deepcopy(report)
    rows = comparison_rows(report)
    assert len(rows) == 65
    assert 'RESEARCH65' not in set(rows.symbol)
    assert rows.activation_status.eq('pending_review_not_activated').all()
    assert rows.ret26_pct.tolist() == list(range(65))
    assert rows.rs_sector_26w_pct.tolist() == [i/2 for i in range(65)]
    assert not rows.stage2_new_entry.any()
    assert rows.previous_stage_label.eq('이전 주 데이터 부족').all()
    pd.testing.assert_frame_equal(report, before)


def _research_full_dashboard_route_scope_grid_and_selection(monkeypatch, read_only):
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr('private_analysis_access.private_analysis_deployment', lambda st: read_only)
    report, prices = fixture()
    monkeypatch.setattr('us_research_dashboard.approved_classification', lambda: (b'synthetic', {'downloaded_on_utc':'2026-10-23'}))
    monkeypatch.setattr('us_research_dashboard.build_research', lambda *a, **k: (report.copy(), prices.copy()))
    def forbidden(*a, **k):
        raise AssertionError('Unexpected provider call')
    monkeypatch.setattr('requests.sessions.Session.request', forbidden)
    st.cache_data.clear()
    charts = {}
    original = st.plotly_chart
    def record(fig, *a, **kwargs):
        if kwargs.get('key', '').startswith(('research_candidate_quick', 'candidate_quick')):
            candle = next(t for t in fig.data if t.type == 'candlestick')
            charts[kwargs['key']] = (fig.layout.meta['asset_symbol'], candle.name, len(candle.x))
        return original(fig, *a, **kwargs)
    monkeypatch.setattr(st, 'plotly_chart', record)
    app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=60)
    app.secrets['APP_PASSWORD'] = 'synthetic-test-password'
    app.session_state['data_source_mode'] = 'KIS API · 미국·한국'
    app.session_state['kis_authenticated'] = not read_only
    app.run()
    assert not app.exception
    if read_only:
        assert not [b for b in app.button if b.label in (
            'KIS에서 가격 조회', '한국 공식 종목 마스터 조회 (검토용)')]
        assert not app.get('file_uploader')
        assert not app.get('download_button')
    app.radio(key='analysis_navigation_choice').set_value('stage2').run()
    app.radio(key='global_asset_view_mode').set_value('차트 고정 목록').run()
    op_symbol = app.session_state['candidate_quick_chart_symbol']
    app.button(key='candidate_quick_chart_period' + "_pick_daily").click().run()
    app.radio(key='analysis_navigation_choice').set_value('markets_commodities').run()
    app.button(key='markets_commodities_selected_symbol_pick_SPY').click().run()
    app.button(key='markets_commodities_open_country_sectors_SPY').click().run()
    app.radio(key='sectors_view_mode').set_value('3×3 차트').run()
    assert not app.exception
    assert not any('_open_research_' in key for key in app.session_state['dashboard_widget_memory'])
    app.radio(key='sectors_view_mode').set_value('차트 고정 목록').run()
    assert not app.exception
    app.button(key='sectors_selected_symbol_pick_XLB').click().run()
    app.session_state['research_candidate_quick_chart_symbol'] = 'RESEARCH64'
    app.button(key='sectors_open_research_XLB').click().run()
    assert not app.exception
    assert app.session_state['stage2_scope'] == '미국 KIS 연구 후보'
    assert not any(radio.key == 'stage2_scope' for radio in app.radio)
    assert app.selectbox(key='research_candidate_quick_sector').value == 'Materials'
    assert app.session_state['research_candidate_quick_chart_symbol'] != 'RESEARCH64'
    assert len([b for b in app.button if b.key and b.key.startswith('research_candidate_quick_chart_symbol_pick_')]) == 50
    app.button(key='research_candidate_quick_list_grid_next').click().run()
    assert app.session_state['research_candidate_quick_list_page'] == 1
    app.button(key='research_candidate_quick_chart_symbol_pick_RESEARCH05').click().run()
    app.button(key='research_candidate_quick_chart_period' + "_pick_daily").click().run()
    assert charts['research_candidate_quick_preview_chart'] == ('RESEARCH05', '일봉', 220)
    assert app.checkbox(key='research_candidate_quick_new_only').disabled
    assert not [b for b in app.button if b.key and b.key.startswith('research_candidate_quick') and b.key.endswith('_favorite')]
    app.text_input(key='research_candidate_quick_search').set_value('absent').run()
    app.text_input(key='research_candidate_quick_search').set_value('').run()
    assert app.session_state['research_candidate_quick_chart_symbol'] == 'RESEARCH05'
    app.multiselect(key='research_candidate_watchlist_symbols').set_value(['RESEARCH05', 'RESEARCH06']).run()
    assert any('관심 후보 2개' in c.value for c in app.caption)
    app.radio(key='research_candidate_view_mode').set_value('3×3 차트').run()
    app.button(key='research_candidate_quick_grid_next').click().run()
    assert app.session_state['research_candidate_quick_grid_page'] == 1
    assert app.radio(key='research_candidate_view_mode').value == '3×3 차트'
    assert app.session_state['dashboard_widget_memory']['global_asset_view_mode'] == '차트 고정 목록'
    app.button(key='stage2_back_to_operating').click().run()
    assert app.session_state['candidate_quick_chart_symbol'] == op_symbol
    assert app.session_state['candidate_quick_chart_period'] == '일봉'
    app.radio(key='analysis_navigation_choice').set_value('briefing').run()
    app.button(key='briefing_open_research').click().run()
    app.selectbox(key='research_candidate_quick_sector').set_value('Materials').run()
    assert app.radio(key='research_candidate_view_mode').value == '3×3 차트'
    assert app.session_state['research_candidate_quick_grid_page'] == 1
    app.radio(key='research_candidate_view_mode').set_value('차트 고정 목록').run()
    assert charts['research_candidate_quick_preview_chart'] == ('RESEARCH05', '일봉', 220)
    app.button(key='research_candidate_back_to_sectors').click().run()
    assert app.session_state['sectors_selected_symbol'] == 'XLB'
    app.radio(key='analysis_navigation_choice').set_value('stage2').run()
    assert app.session_state['stage2_scope'] == '운영 유니버스'
    assert charts['candidate_quick_preview_chart'][0] == op_symbol
    assert not app.exception
    if read_only:
        assert not app.get('download_button')
        assert not app.dataframe
    st.cache_data.clear()


def test_research_full_dashboard_route_scope_grid_and_selection(monkeypatch):
    _research_full_dashboard_route_scope_grid_and_selection(monkeypatch, False)


def test_private_research_full_dashboard_route_scope_grid_and_selection(monkeypatch):
    _research_full_dashboard_route_scope_grid_and_selection(monkeypatch, True)


def test_specialist_sector_charts_and_related_stock_route(monkeypatch):
    import exchange_calendars as xcals
    from market_data import completed_bar_cutoff_date
    from kis_provider import KISError
    from us_specialist_etf_comparison import RESEARCH_ETFS

    monkeypatch.chdir(ROOT)
    monkeypatch.setattr('private_analysis_access.private_analysis_deployment', lambda st: True)
    monkeypatch.setattr('us_research_dashboard.approved_classification',
                        lambda: (b'synthetic', {'downloaded_on_utc': '2026-10-23'}))
    report, _ = fixture()
    tickers = ['XBI', 'KBE', 'KIE', 'IGV', 'IHI', 'XHB', 'XRT', 'XOP']
    report = report.iloc[:9].assign(
        preferred_sector_etf_review=['XBI', 'KBE', 'KIE', '', '', '', '', '', 'IGV'],
        verified_specialist_etf=['', '', '', 'IGV', 'IHI', 'XHB', 'XRT', 'XOP', ''],
        suggested_sector_benchmark='XLF')
    cutoff = pd.Timestamp(completed_bar_cutoff_date('AMS'))
    sessions = xcals.get_calendar('XNYS').sessions_in_range(cutoff - pd.Timedelta(days=372), cutoff)
    history = pd.DataFrame(dict(date=sessions, open=100., high=102., low=98., close=101., volume=1000))
    read_csv = pd.read_csv

    def with_fixture_market_snapshot(path, *args, **kwargs):
        frame = read_csv(path, *args, **kwargs)
        if str(path) == 'data/daily_prices.csv':
            spy = history.assign(symbol='SPY', date=history.date.dt.strftime('%Y-%m-%d'))
            frame = pd.concat([frame.loc[frame.symbol.ne('SPY')], spy], ignore_index=True)
        return frame

    monkeypatch.setattr(pd, 'read_csv', with_fixture_market_snapshot)
    prices = pd.concat([history.assign(symbol=symbol) for symbol in report.symbol], ignore_index=True)
    monkeypatch.setattr('us_research_dashboard.build_research', lambda *a, **kw: (report.copy(), prices.copy()))
    calls = []
    failures = set()
    charts = {}
    sector_rows = {}
    original_chart = st.plotly_chart
    from asset_table import render_asset_table

    def record_table(frame, state_key, *a, **kwargs):
        if state_key == 'sectors_selected_symbol':
            sector_rows.clear()
            sector_rows.update(frame.set_index('symbol').to_dict('index'))
        return render_asset_table(frame, state_key, *a, **kwargs)

    class FixtureKIS:
        def __init__(self, **kwargs):
            pass

        def daily_bars(self, symbol, *, exchange, **kwargs):
            assert exchange == 'AMS'
            calls.append(symbol)
            if symbol in failures:
                raise KISError('synthetic failure')
            close = 100 + pd.Series(range(len(history))) * (tickers.index(symbol) + 1) / 100
            return history.assign(symbol=symbol, open=close, high=close + 1, low=close - 1, close=close)

    def record_chart(fig, *a, **kwargs):
        key = kwargs.get('key', '')
        if key.startswith('sectors_'):
            candle = next(t for t in fig.data if t.type == 'candlestick')
            charts[fig.layout.meta['asset_symbol']] = candle.name, len(candle.x)
        return original_chart(fig, *a, **kwargs)

    monkeypatch.setattr('kis_provider.KISOverseasPrices', FixtureKIS)
    monkeypatch.setattr(st, 'plotly_chart', record_chart)
    monkeypatch.setattr('asset_table.render_asset_table', record_table)
    st.cache_data.clear()
    st.cache_resource.clear()
    try:
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=60)
        app.secrets['APP_PASSWORD'] = 'synthetic-test-password'
        app.run()
        app.radio(key='analysis_navigation_choice').set_value('sectors').run()
        app.button(key='sectors_selected_symbol_pick_XLF').click().run()
        assert calls == tickers
        assert '미국 세부업종 ETF · 연구용' not in app.selectbox(key='sectors_market').options
        xlf_metrics = {key: sector_rows['XLF'][key] for key in ('ret13_pct', 'ret26_pct', 'ret1y_pct', 'stage_label')}
        assert all(pd.notna(value) for value in xlf_metrics.values())
        for ticker in tickers:
            row = sector_rows[ticker]
            assert row['stage_label'] == 'Stage 2 후보'
            assert row['name'] == RESEARCH_ETFS[ticker]
            assert row['market_benchmark'] == 'SPY'
            assert row['rs_market_26w_pct'] > 0
            assert row['asset_type_norm'] == 'research_sector_etf'
            assert 0 < row['ret13_pct'] < row['ret26_pct'] < row['ret1y_pct']
        for column in ('ret1y_pct', 'ret26_pct'):
            app.button(key=f'asset_table_sort_pick_sectors_selected_symbol_{column}').click().run()
            assert [symbol for symbol in sector_rows if symbol in tickers] == tickers[::-1]
            assert {key: sector_rows['XLF'][key] for key in xlf_metrics} == xlf_metrics
        for ticker in tickers:
            app.button(key=f'sectors_selected_symbol_pick_{ticker}').click().run()
            period, bars = charts[ticker]
            assert period == '주봉' and bars >= 35
            assert any('KIS 최신 일봉' in c.value for c in app.caption)
        assert calls == tickers

        app.selectbox(key='sectors_stage_filter').set_value('Stage 2 후보').run()
        assert set(tickers).issubset(sector_rows)
        app.text_input(key='sectors_search').set_value('소프트웨어').run()
        assert list(sector_rows) == ['IGV']
        app.selectbox(key='sectors_stage_filter').set_value('전체').run()
        app.text_input(key='sectors_search').set_value('IGV').run()
        assert list(sector_rows) == ['IGV']
        app.button(key='sectors_selected_symbol_pick_IGV').click().run()
        app.radio(key='sectors_view_mode').set_value('3×3 차트').run()
        assert app.get('plotly_chart')
        app.radio(key='sectors_view_mode').set_value('차트 고정 목록').run()
        assert app.session_state['sectors_selected_symbol'] == 'IGV'
        app.button(key='sectors_open_stocks_IGV').click().run()
        assert app.radio(key='analysis_navigation_choice').value == 'stocks'
        assert {b.label for b in app.button if b.key and
                b.key.startswith('stocks_selected_symbol_pick_')} == {'RESEARCH03'}
        assert not any('비교 기준일' in c.value for c in app.caption)
        assert not any(m.label == 'IGV 26주 수익률' for m in app.metric)

        app.button(key='stocks_back_to_sectors').click().run()
        assert app.session_state['sectors_selected_symbol'] == 'IGV'
        assert app.text_input(key='sectors_search').value == 'IGV'
        failures.add('IGV')
        st.cache_data.clear()
        calls.clear()
        app.run()
        assert calls == tickers
        assert sector_rows['IGV']['stage_label'] == '가격 데이터 미확인 · 판정 보류'
        assert pd.isna(sector_rows['IGV']['ret13_pct'])
        assert pd.isna(sector_rows['IGV']['ret26_pct'])
        assert app.button(key='asset_table_sort_pick_sectors_selected_symbol_ret1y_pct')
        assert not app.get('plotly_chart')
        assert app.button(key='sectors_open_stocks_IGV').label == '관련 종목 보기 →'
        app.text_input(key='sectors_search').set_value('').run()
        app.button(key='sectors_selected_symbol_pick_XLF').click().run()
        assert app.get('plotly_chart')
        assert not app.exception
    finally:
        st.cache_data.clear()
        st.cache_resource.clear()
