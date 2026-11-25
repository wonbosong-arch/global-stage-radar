from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_default_tabs_and_management_preserve_independent_modes(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=45).run()
    assert not app.exception
    assert any('Global Stage Radar</h3>' in m.value for m in app.markdown)
    tabs = app.radio(key='analysis_navigation_choice')
    assert tabs.value == 'briefing'
    assert tabs.options == [
        '대시보드', 'Stage 2 후보', '국가 및 원자재', '업종', '종목', '차트 비교', '☆ 관심 목록',
    ]
    management = next(e for e in app.expander if e.label == '데이터 관리')
    assert not management.proto.expanded
    assert any(m.label == 'Stage 판정 보류' for m in app.metric)
    app.radio(key='analysis_navigation_choice').set_value('stage2').run()
    app.radio(key='global_asset_view_mode').set_value('3×3 차트').run()
    app.radio(key='analysis_navigation_choice').set_value('markets_commodities').run()
    assert app.radio(key='markets_commodities_view_mode').value == '차트 고정 목록'
    app.radio(key='markets_commodities_view_mode').set_value('히트맵').run()
    app.radio(key='analysis_navigation_choice').set_value('sectors').run()
    assert app.radio(key='sectors_view_mode').value == '차트 고정 목록'
    app.radio(key='analysis_navigation_choice').set_value('stage2').run()
    assert app.radio(key='global_asset_view_mode').value == '3×3 차트'
    app.radio(key='analysis_navigation_choice').set_value('markets_commodities').run()
    assert app.radio(key='markets_commodities_view_mode').value == '히트맵'
    assert not app.exception


def test_every_analysis_area_reuses_brand_search_and_native_navigation(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **kw: (_ for _ in ()).throw(AssertionError('provider request')))
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=60).run()
    for area in ('stage2', 'markets_commodities', 'sectors', 'stocks', 'chart_comparison', 'favorites', 'briefing'):
        app.radio(key='analysis_navigation_choice').set_value(area).run()
        assert not app.exception
        assert any('Global Stage Radar</h3>' in m.value for m in app.markdown)
        assert len(app.selectbox(key='briefing_global_search').options) > 0
    # Search from an analysis tab uses the same selected-asset route as briefing.
    app.radio(key='analysis_navigation_choice').set_value('sectors').run()
    app.selectbox(key='briefing_global_search').set_value(0).run()
    assert not app.exception
    assert app.session_state['active_analysis_area'] != 'briefing'
    assert app.get('plotly_chart')
