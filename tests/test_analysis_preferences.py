import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
from analysis_preferences import decode_preferences


def test_url_preferences_are_whitelisted_and_bounded():
    assert decode_preferences('[') == {}
    assert decode_preferences('[]') == {}
    assert decode_preferences('x'*4097) == {}
    result = decode_preferences(json.dumps({'tab':'stocks','source':'가상 데모', 'kis_authenticated':True,
        'stocks':{'mode':'3×3 차트','symbol':'ALFA','period':'일봉','page':1},
        'stage2':{'mode':'히트맵','symbol':'<script>','page':-1}}))
    assert 'kis_authenticated' not in result
    assert result['stocks_view_mode'] == '3×3 차트'
    assert result['stocks_saved_view_mode'] == '3×3 차트'
    assert result['stocks_selected_period_ALFA'] == '일봉'
    assert 'global_asset_view_mode' not in result
    assert 'candidate_quick_chart_symbol' not in result


def test_session_favorites_width_and_refresh_preferences(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    app = AppTest.from_file(str(root/'app.py'),default_timeout=45).run()
    app.radio(key='active_analysis_area').set_value('stocks').run()
    picks = [b for b in app.button if b.key and b.key.startswith('stocks_selected_symbol_pick_')]
    symbol = picks[0].key.removeprefix('stocks_selected_symbol_pick_')
    picks[0].click().run()
    app.button(key='stocks_favorite').click().run()
    assert symbol in app.session_state['analysis_favorites']
    assert app.button(key=f'stocks_selected_symbol_pick_{symbol}').label.startswith('★')
    app.checkbox(key='stocks_favorites_only').check().run()
    assert len([b for b in app.button if b.key and b.key.startswith('stocks_selected_symbol_pick_')]) == 1
    app.radio(key=f'stocks_selected_period_{symbol}').set_value('일봉').run()
    app.radio(key='active_analysis_area').set_value('sectors').run()
    app.radio(key='active_analysis_area').set_value('stocks').run()
    assert app.checkbox(key='stocks_favorites_only').value
    app.slider(key='dashboard_list_width').set_value(40).run()
    assert app.session_state['stocks_selected_symbol'] == symbol
    app.radio(key='stocks_view_mode').set_value('3×3 차트').run()
    restored = AppTest.from_file(str(root/'app.py'),default_timeout=45)
    restored.query_params['radar'] = app.query_params['radar']
    restored.run()
    assert not restored.exception
    assert restored.radio(key='active_analysis_area').value == 'stocks'
    assert restored.radio(key='stocks_view_mode').value == '3×3 차트'
    assert restored.session_state['stocks_selected_symbol'] == symbol
    assert restored.slider(key='dashboard_list_width').value == 40
    restored.radio(key='stocks_view_mode').set_value('차트 고정 목록').run()
    assert restored.radio(key=f'stocks_selected_period_{symbol}').value == '일봉'
    assert not restored.session_state['analysis_favorites']
    assert not app.exception
