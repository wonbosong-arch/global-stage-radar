"""Exercise navigation callbacks, weekly data loss, and persistent analysis state."""
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_crypto_only_input_keeps_the_empty_friday_briefing_usable():
    app = AppTest.from_string('''
import pandas as pd
import streamlit as st
from weekly_briefing import render_weekly_briefing
rows = pd.DataFrame([dict(symbol='BTC', asset_type_norm='crypto_asset',
    stage_label='Stage 2 후보', previous_stage_label='Stage 2 후보',
    last_date='2026-11-08', ret26_pct=10, market='Crypto')])
render_weekly_briefing(st, rows, {}, [], lambda *a: None, lambda *a: None)
''').run()
    assert not app.exception
    assert next(m.value for m in app.metric if m.label == 'Stage 2 진입·이탈') == '비교 불가'
    assert not app.get('plotly_chart')


def test_briefing_no_charts_real_unknowns_row_routes_stars_and_analysis_state(monkeypatch):
    monkeypatch.chdir(ROOT)
    def deny(*args, **kwargs):
        raise AssertionError('Weekly overview must not fetch prices or metadata')
    monkeypatch.setattr('requests.sessions.Session.request', deny)
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=60).run()
    assert not app.exception
    assert app.radio(key='analysis_navigation_choice').value == 'briefing'
    assert not app.get('plotly_chart')
    assert any('가상 데모' in item.value for item in app.warning)
    app.button(key='briefing_area_stocks').click().run()
    symbol = app.session_state['stocks_selected_symbol']
    app.button(key='stocks_favorite').click().run()
    app.radio(key=f'stocks_selected_period_{symbol}').set_value('일봉').run()
    app.radio(key='stocks_view_mode').set_value('3×3 차트').run()
    app.radio(key='analysis_navigation_choice').set_value('briefing').run()
    assert not app.exception and not app.get('plotly_chart')
    assert len([b for b in app.button if b.key and b.key.startswith('briefing_watch_')]) == 1
    app.button(key='briefing_area_stocks').click().run()
    assert app.session_state['stocks_selected_symbol'] == symbol
    assert app.radio(key='stocks_view_mode').value == '3×3 차트'
    app.radio(key='analysis_navigation_choice').set_value('briefing').run()
    # A named briefing row clears stale filters using the existing favorite route.
    row = next(b for b in app.button if b.key and b.key.startswith('briefing_markets_'))
    row.click().run()
    assert app.radio(key='analysis_navigation_choice').value == 'markets_commodities'
    assert app.radio(key='markets_commodities_view_mode').value == '차트 고정 목록'
    assert app.session_state['markets_commodities_selected_symbol'] == 'USMKT'
    app.radio(key='analysis_navigation_choice').set_value('stocks').run()
    app.radio(key='stocks_view_mode').set_value('차트 고정 목록').run()
    assert app.radio(key=f'stocks_selected_period_{symbol}').value == '일봉'
    assert not app.exception


def test_missing_prior_history_is_visibly_unavailable_with_no_sample_substitute(monkeypatch):
    monkeypatch.chdir(ROOT)
    import weekly_briefing
    original = weekly_briefing.weekly_snapshot
    def without_prior(screen, histories):
        return original(screen.assign(previous_stage_label='이전 주 데이터 부족'),
                        {key: frame.iloc[-1:] for key, frame in histories.items()})
    monkeypatch.setattr(weekly_briefing, 'weekly_snapshot', without_prior)
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=60).run()
    assert not app.exception
    assert not app.get('plotly_chart')
    briefing = {m.label: m.value for m in app.metric if m.label.startswith('Stage 2 ')}
    assert briefing['Stage 2 진입·이탈'] == '비교 불가'
    assert sum(c.value == '비교 불가' for c in app.caption) >= 3
    assert not any('↑' in b.label or '↓' in b.label for b in app.button if b.key and b.key.startswith('briefing_markets_'))


def test_research_summary_stays_separate_and_opens_existing_scope(monkeypatch):
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr('private_analysis_access.private_analysis_deployment', lambda st: True)
    from test_us_research_comparison import fixture
    report, prices = fixture()
    monkeypatch.setattr('us_research_dashboard.approved_classification', lambda: (b'synthetic', {'downloaded_on_utc':'2026-10-23'}))
    monkeypatch.setattr('us_research_dashboard.build_research', lambda *a, **kw: (report.copy(), prices.copy()))
    import streamlit as st
    st.cache_data.clear()
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=60)
    app.secrets['APP_PASSWORD'] = 'test-only'
    app.run()
    assert not app.exception
    app.button(key='briefing_load_research').click().run()
    assert any('연구 분석 65개 · Stage 2 64개 · Stage 2A 1개' in c.value for c in app.caption)
    assert not app.get('plotly_chart')
    assert next(m.value for m in app.metric if m.label == 'Stage 2 종목') == '0'
    app.button(key='briefing_open_research').click().run()
    assert app.radio(key='stage2_scope').value == '미국 KIS 연구 후보'
    assert not app.exception
    assert app.get('plotly_chart')
