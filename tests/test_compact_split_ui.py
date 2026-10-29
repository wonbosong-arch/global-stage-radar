from pathlib import Path

from streamlit.testing.v1 import AppTest

from dashboard_ui import candidate_entry_text, compact_asset_label


def test_compact_rows_prioritize_absolute_return_stage_and_guarded_entry():
    row = {'symbol': 'XLK', 'name': 'Technology Fund', 'sector': 'Technology',
           'market': 'United States', 'asset_type_norm': 'sector_etf',
           'ret26_pct': 12.5, 'rs_market_26w_pct': -99, 'stage_label': 'Stage 2 후보',
           'previous_stage_label': 'Stage 1', 'stage2_new_entry': True}
    label = compact_asset_label(row)
    assert 'Technology' in label and '(XLK)' in label
    assert '+12.50%' in label and 'Stage 2 후보' in label and '🆕 신규 진입' in label
    assert '-99' not in label
    row['previous_stage_label'] = '이전 주 데이터 부족'
    assert candidate_entry_text(row) == '신규 여부 미확인'
    row.update(previous_stage_label='Stage 2 후보', stage2_new_entry=False)
    assert candidate_entry_text(row) == '기존 후보'
    row['stage_label'] = 'Stage 2A 관찰 후보'
    assert candidate_entry_text(row) == '신규 진입 —'


def test_sector_and_candidate_split_preserve_selection_period_and_table_grid(monkeypatch):
    def reject_network(*args, **kwargs):
        raise AssertionError('Snapshot UI requested provider network')
    monkeypatch.setattr('requests.sessions.Session.request', reject_network)
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=45)
    app.secrets['APP_PASSWORD'] = 'local-split-test'
    app.run()
    next(r for r in app.radio if r.label == '모드').set_value('KIS API · 미국·한국').run()
    next(t for t in app.text_input if t.label == 'KIS 모드 비밀번호').set_value('local-split-test')
    next(b for b in app.button if b.label == '잠금 해제').click().run()
    assert not app.exception
    assert app.radio(key='global_asset_view_mode').options == ['차트 고정 목록', '3×3 차트']
    app.radio(key='active_analysis_area').set_value('sectors').run()
    assert app.radio(key='sectors_view_mode').options == ['차트 고정 목록', '3×3 차트']
    picks = [b for b in app.button if b.key and b.key.startswith('sectors_selected_symbol_pick_')]
    assert picks and all('26주' in b.label and ('신규' in b.label or '기존 후보' in b.label) for b in picks)
    symbol = picks[-1].key.removeprefix('sectors_selected_symbol_pick_')
    picks[-1].click().run()
    app.radio(key=f'sectors_selected_period_{symbol}').set_value('일봉').run()
    app.radio(key='sectors_view_mode').set_value('3×3 차트').run()
    app.button(key='sectors_grid_next').click().run()
    assert app.session_state['sectors_grid_page'] == 1
    app.radio(key='sectors_view_mode').set_value('차트 고정 목록').run()
    assert app.session_state['sectors_selected_symbol'] == symbol
    assert app.radio(key=f'sectors_selected_period_{symbol}').value == '일봉'
    app.radio(key='active_analysis_area').set_value('stage2').run()
    quick = [b for b in app.button if b.key and b.key.startswith('candidate_quick_pick_')]
    assert quick and all('26주' in b.label for b in quick)
    quick_symbol = quick[-1].key.removeprefix('candidate_quick_pick_')
    quick[-1].click().run()
    app.radio(key='candidate_quick_chart_period').set_value('일봉').run()
    app.radio(key='global_asset_view_mode').set_value('3×3 차트').run()
    app.button(key='candidate_quick_grid_next').click().run()
    app.radio(key='global_asset_view_mode').set_value('차트 고정 목록').run()
    assert app.session_state['candidate_quick_chart_symbol'] == quick_symbol
    assert app.radio(key='candidate_quick_chart_period').value == '일봉'
    assert app.session_state['sectors_selected_symbol'] == symbol
    app.radio(key='active_analysis_area').set_value('sectors').run()
    assert app.radio(key=f'sectors_selected_period_{symbol}').value == '일봉'
    assert not app.exception


def test_retired_table_session_migrates_without_losing_symbol(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=45)
    for key in ('global_asset_view_mode', 'markets_commodities_view_mode',
                'sectors_saved_view_mode', 'country_return_view'):
        app.session_state[key] = '표 보기'
    app.session_state['markets_commodities_selected_symbol'] = 'USMKT'
    app.session_state['active_analysis_area'] = 'markets_commodities'
    app.run()
    assert not app.exception
    app.radio(key='active_analysis_area').set_value('stage2').run()
    assert app.radio(key='global_asset_view_mode').options == ['차트 고정 목록', '3×3 차트']
    app.radio(key='active_analysis_area').set_value('markets_commodities').run()
    assert app.radio(key='markets_commodities_view_mode').value == '차트 고정 목록'
    assert app.session_state['markets_commodities_selected_symbol'] == 'USMKT'
    assert app.session_state['sectors_saved_view_mode'] == '차트 고정 목록'
    app.radio(key='markets_commodities_view_mode').set_value('히트맵').run()
    assert not app.exception


def test_stock_tab_uses_compact_split_list(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=45).run()
    app.radio(key='active_analysis_area').set_value('stocks').run()
    buttons = [b for b in app.button if b.key and b.key.startswith('stocks_selected_symbol_pick_')]
    assert buttons and all('26주' in b.label for b in buttons)
    symbol = buttons[-1].key.removeprefix('stocks_selected_symbol_pick_')
    buttons[-1].click().run()
    assert app.session_state['stocks_selected_symbol'] == symbol
    assert not app.exception
