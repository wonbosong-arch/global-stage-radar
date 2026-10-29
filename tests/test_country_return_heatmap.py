from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from dashboard_ui import absolute_return_text, heatmap_tile_label, return_tile_color


def test_heatmap_uses_absolute_returns_and_keeps_missing_values_distinct():
    row = {'symbol': 'EWJ', 'market': 'Japan', 'sector': 'Market',
           'asset_type_norm': 'market_etf', 'stage_label': 'Stage 2 후보',
           'ret26_pct': 12.5, 'rs_market_26w_pct': -99}
    label = heatmap_tile_label(row)
    assert 'Japan (EWJ)' in label and '+12.50%' in label and 'Stage 2 후보' in label
    assert '-99' not in label
    assert absolute_return_text(0) == '+0.00%'
    assert absolute_return_text(pd.NA) == '수익률 없음'
    assert absolute_return_text(float('nan')) == '수익률 없음'
    assert return_tile_color(5) != return_tile_color(-5)
    assert return_tile_color(float('nan')) == return_tile_color(None)


def test_heatmap_selection_survives_period_area_table_and_grid_round_trips(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=45).run()
    assert not app.exception
    app.radio(key='active_analysis_area').set_value('markets_commodities').run()
    assert app.radio(key='markets_commodities_view_mode').value == '히트맵'
    key = 'markets_commodities_selected_symbol_heatmap_pick_USMKT'
    assert 'Stage' in app.button(key=key).label
    app.button(key=key).click().run()
    assert app.session_state['markets_commodities_selected_symbol'] == 'USMKT'
    app.radio(key='markets_commodities_selected_period_USMKT').set_value('일봉').run()
    app.radio(key='active_analysis_area').set_value('sectors').run()
    app.radio(key='active_analysis_area').set_value('markets_commodities').run()
    assert app.radio(key='markets_commodities_view_mode').value == '히트맵'
    assert app.session_state['markets_commodities_selected_symbol'] == 'USMKT'
    assert app.radio(key='markets_commodities_selected_period_USMKT').value == '일봉'
    app.radio(key='markets_commodities_view_mode').set_value('3×3 차트').run()
    app.radio(key='markets_commodities_view_mode').set_value('히트맵').run()
    assert not app.exception
    assert app.session_state['markets_commodities_selected_symbol'] == 'USMKT'
    assert app.radio(key='markets_commodities_selected_period_USMKT').value == '일봉'
