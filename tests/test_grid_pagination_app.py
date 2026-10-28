"""Run actual Streamlit widgets: source checks cannot catch widget-state errors."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_grid_pages_survive_reruns_and_area_changes_without_widget_state_errors(monkeypatch):
    # Local snapshot browsing must never issue a provider request.
    def reject_network(*args, **kwargs):
        raise AssertionError('Snapshot navigation unexpectedly requested the network')
    monkeypatch.setattr('requests.sessions.Session.request', reject_network)
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=45)
    app.secrets['APP_PASSWORD'] = 'local-regression-password'

    def healthy():
        assert not app.exception, [item.value for item in app.exception]

    def grid_mode():
        healthy()
        assert app.session_state['global_asset_view_mode'] == '3×3 차트'
        area = app.session_state['active_analysis_area']
        assert app.radio(key=f'{area}_view_mode').value == '3×3 차트'

    app.run()
    healthy()
    next(widget for widget in app.radio if widget.label == '모드').set_value('KIS API · 미국·한국').run()
    next(widget for widget in app.text_input if widget.label == 'KIS 모드 비밀번호').set_value('local-regression-password')
    next(widget for widget in app.button if widget.label == '잠금 해제').click().run()
    healthy()

    # The area's selector synchronizes the independent quick-comparison panel.
    app.radio(key='markets_commodities_view_mode').set_value('3×3 차트').run()
    grid_mode()
    first_page = {widget.key for widget in app.radio if widget.key and widget.key.startswith('markets_commodities_grid_period_')}
    assert len(first_page) == 9
    app.button(key='markets_commodities_grid_next').click().run()
    grid_mode()
    assert app.session_state['markets_commodities_grid_page'] == 1
    second_page = {widget.key for widget in app.radio if widget.key and widget.key.startswith('markets_commodities_grid_period_')}
    assert second_page and first_page.isdisjoint(second_page)
    app.run()
    grid_mode()

    # Quick-panel pagination must not reset the main area's page or mode.
    app.button(key='candidate_quick_grid_next').click().run()
    grid_mode()
    assert app.session_state['candidate_quick_grid_page'] == 1
    assert app.session_state['markets_commodities_grid_page'] == 1
    app.button(key='candidate_quick_grid_prev').click().run()
    grid_mode()
    assert app.session_state['candidate_quick_grid_page'] == 0
    app.radio(key='active_analysis_area').set_value('sectors').run()
    grid_mode()
    app.radio(key='active_analysis_area').set_value('markets_commodities').run()
    grid_mode()
    assert app.session_state['markets_commodities_grid_page'] == 1
    app.button(key='markets_commodities_grid_prev').click().run()
    grid_mode()
    assert app.session_state['markets_commodities_grid_page'] == 0

    # Existing list selection and daily/weekly controls still work after paging.
    app.radio(key='markets_commodities_view_mode').set_value('차트 고정 목록').run()
    healthy()
    picks = [widget for widget in app.button if widget.key and widget.key.startswith('markets_commodities_selected_symbol_pick_')]
    selected = picks[-1].key.removeprefix('markets_commodities_selected_symbol_pick_')
    picks[-1].click().run()
    healthy()
    assert app.session_state['markets_commodities_selected_symbol'] == selected
    app.radio(key=f'markets_commodities_selected_period_{selected}').set_value('일봉').run()
    healthy()
    assert app.session_state['global_asset_view_mode'] == '차트 고정 목록'
    app.radio(key='global_asset_view_mode').set_value('3×3 차트').run()
    grid_mode()
