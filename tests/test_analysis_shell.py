from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_default_tabs_and_management_preserve_independent_modes(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=45).run()
    assert not app.exception
    assert any(m.value == '### Global Stage Radar' for m in app.markdown)
    tabs = app.radio(key='active_analysis_area')
    assert tabs.value == 'stage2'
    assert tabs.options == ['Stage 2 후보', '국가 및 원자재', '업종', '종목', '☆ 관심 목록']
    management = next(e for e in app.expander if e.label == '데이터 관리')
    assert not management.proto.expanded
    assert any(m.label == 'Stage 판정 보류' for m in app.metric)
    app.radio(key='global_asset_view_mode').set_value('3×3 차트').run()
    app.radio(key='active_analysis_area').set_value('markets_commodities').run()
    assert app.radio(key='markets_commodities_view_mode').value == '히트맵'
    app.radio(key='markets_commodities_view_mode').set_value('차트 고정 목록').run()
    app.radio(key='active_analysis_area').set_value('sectors').run()
    assert app.radio(key='sectors_view_mode').value == '차트 고정 목록'
    app.radio(key='active_analysis_area').set_value('stage2').run()
    assert app.radio(key='global_asset_view_mode').value == '3×3 차트'
    app.radio(key='active_analysis_area').set_value('markets_commodities').run()
    assert app.radio(key='markets_commodities_view_mode').value == '차트 고정 목록'
    assert not app.exception
