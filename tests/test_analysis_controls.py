from pathlib import Path
import pandas as pd
from streamlit.testing.v1 import AppTest
from analysis_controls import analysis_metrics, new_stage2_rows, choose_analysis_symbol


def test_absolute_distance_and_new_entry_guard():
    frame = pd.DataFrame({'symbol':['A','B','C'], 'close':[110,90,10], 'ma30':[100,100,0],
                          'stage_label':['Stage 2 후보']*3, 'stage2_new_entry':[True,True,False],
                          'previous_stage_label':['Stage 1','이전 주 데이터 부족','Stage 2 후보']})
    result = analysis_metrics(frame)
    assert abs(result.ma30_distance_pct.iloc[0]-10)<1e-8
    assert abs(result.ma30_distance_pct.iloc[1]+10)<1e-8
    assert pd.isna(result.ma30_distance_pct.iloc[2])
    assert new_stage2_rows(result).symbol.tolist() == ['A']
    assert choose_analysis_symbol('B', result.head(0), result) == 'B'
    assert choose_analysis_symbol('MISSING', result.head(1), result) == 'A'


def test_filter_and_navigation_preserve_chart_selection(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    app = AppTest.from_file(str(root/'app.py'), default_timeout=45).run()
    app.radio(key='active_analysis_area').set_value('markets_commodities').run()
    app.button(key='markets_commodities_selected_symbol_heatmap_pick_USMKT').click().run()
    app.text_input(key='markets_commodities_search').set_value('NO_SUCH_TICKER').run()
    assert app.session_state['markets_commodities_selected_symbol'] == 'USMKT'
    assert not app.exception
    app.text_input(key='markets_commodities_search').set_value('').run()
    app.selectbox(key='markets_commodities_sort').set_value('30주선 거리(가까운 순)').run()
    assert app.session_state['markets_commodities_selected_symbol'] == 'USMKT'
    app.button(key='markets_commodities_open_country_sectors_USMKT').click().run()
    assert app.radio(key='active_analysis_area').value == 'sectors'
    app.button(key='sectors_selected_symbol_pick_TECH').click().run()
    app.button(key='sectors_open_stocks_TECH').click().run()
    assert app.radio(key='active_analysis_area').value == 'stocks'
    picks = [b for b in app.button if b.key and b.key.startswith('stocks_selected_symbol_pick_')]
    assert picks and all(any(symbol in b.label for symbol in ('ALFA','BETA','GAMMA')) for b in picks)
    selected = app.session_state['stocks_selected_symbol']
    app.checkbox(key='stocks_new_only').check().run()
    assert app.session_state['stocks_selected_symbol'] == selected
    app.button(key='stocks_back_to_sectors').click().run()
    assert app.session_state['sectors_selected_symbol'] == 'TECH'
    app.button(key='back_to_country_list_from_sectors').click().run()
    assert app.session_state['markets_commodities_selected_symbol'] == 'USMKT'
    assert not app.exception
