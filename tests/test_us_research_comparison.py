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


def test_research_full_dashboard_route_scope_grid_and_selection(monkeypatch):
    monkeypatch.chdir(ROOT)
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
        if kwargs.get('key', '').startswith('research_candidate_quick'):
            candle = next(t for t in fig.data if t.type == 'candlestick')
            charts[kwargs['key']] = (fig.layout.meta['asset_symbol'], candle.name, len(candle.x))
        return original(fig, *a, **kwargs)
    monkeypatch.setattr(st, 'plotly_chart', record)
    app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=60)
    app.secrets['APP_PASSWORD'] = 'synthetic-test-password'
    app.session_state['data_source_mode'] = 'KIS API · 미국·한국'
    app.session_state['kis_authenticated'] = True
    app.run()
    assert not app.exception
    app.radio(key='global_asset_view_mode').set_value('차트 고정 목록').run()
    op_symbol = app.session_state['candidate_quick_chart_symbol']
    app.radio(key='candidate_quick_chart_period').set_value('일봉').run()
    app.radio(key='active_analysis_area').set_value('markets_commodities').run()
    app.button(key='markets_commodities_selected_symbol_heatmap_pick_SPY').click().run()
    app.button(key='markets_commodities_open_country_sectors_SPY').click().run()
    app.button(key='sectors_selected_symbol_pick_XLB').click().run()
    app.session_state['research_candidate_quick_chart_symbol'] = 'RESEARCH64'
    app.button(key='sectors_open_research_XLB').click().run()
    assert not app.exception
    assert app.radio(key='stage2_scope').value == '미국 KIS 연구 후보'
    assert app.selectbox(key='research_candidate_quick_sector').value == 'Materials'
    assert app.session_state['research_candidate_quick_chart_symbol'] != 'RESEARCH64'
    assert len([b for b in app.button if b.key and b.key.startswith('research_candidate_quick_chart_symbol_pick_')]) == 50
    app.button(key='research_candidate_quick_list_grid_next').click().run()
    assert app.session_state['research_candidate_quick_list_page'] == 1
    app.button(key='research_candidate_quick_chart_symbol_pick_RESEARCH05').click().run()
    app.radio(key='research_candidate_quick_chart_period').set_value('일봉').run()
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
    app.radio(key='stage2_scope').set_value('운영 유니버스').run()
    assert app.session_state['candidate_quick_chart_symbol'] == op_symbol
    assert app.radio(key='candidate_quick_chart_period').value == '일봉'
    app.radio(key='stage2_scope').set_value('미국 KIS 연구 후보').run()
    assert app.radio(key='research_candidate_view_mode').value == '3×3 차트'
    assert app.session_state['research_candidate_quick_grid_page'] == 1
    app.radio(key='research_candidate_view_mode').set_value('차트 고정 목록').run()
    assert charts['research_candidate_quick_preview_chart'] == ('RESEARCH05', '일봉', 220)
    app.button(key='research_candidate_back_to_sectors').click().run()
    assert app.session_state['sectors_selected_symbol'] == 'XLB'
    app.radio(key='active_analysis_area').set_value('stage2').run()
    assert app.radio(key='stage2_scope').value == '미국 KIS 연구 후보'
    assert app.session_state['research_candidate_quick_chart_symbol'] == 'RESEARCH05'
    assert not app.exception
    st.cache_data.clear()
