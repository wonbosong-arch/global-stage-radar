"""Behavior-level reruns with synthetic data; no private input needed."""
import json
from pathlib import Path
import pandas as pd
from streamlit.testing.v1 import AppTest
from china_stage import stage_readiness
from tests.test_china_readiness_validation import history


def test_private_filter_pagination_and_tab_round_trip(monkeypatch):
    import china_dashboard
    metadata = json.loads(Path('china_sector_metadata.json').read_text(encoding='utf-8'))
    rows, frames = [], []
    for index, item in enumerate(metadata):
        frame = history(45).assign(symbol=item['symbol'])
        if index >= 2:
            frame[['open', 'high', 'low', 'close']] = [10., 11., 9., 10.]
        result = stage_readiness(frame, as_of_date='2025-12-27', price_basis='KIS_ADJUSTED')
        rows.append(dict(item, **result, preview_status=result['stage_reason']))
        frames.append(frame)
    monkeypatch.setattr(china_dashboard, 'load_research', lambda: (
        pd.DataFrame(rows), pd.concat(frames), dict(price_basis='KIS_ADJUSTED', research_commit='synthetic')))
    app = AppTest.from_string('''
import streamlit as st
import plotly.graph_objects as go
from china_dashboard import render_china_dashboard
area = st.radio('area', ['china', 'other'], key='area')
def pager(prefix, key, page, pages):
    def next_page():
        st.session_state[key] = (page + 1) % pages
    st.button('next', key='next', on_click=next_page)
if area == 'china':
    render_china_dashboard(lambda *a, **k: go.Figure(go.Scatter(x=[1,2], y=[1,2])),
                           lambda key: st.columns([1,2]), pager)
''', default_timeout=30).run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 12
    assert len([b for b in app.button if str(b.key).startswith('china_research_pick_')]) == 12
    app.radio(key='china_research_view').set_value('3×3 차트').run()
    assert len(app.get('plotly_chart')) == 9
    app.button(key='next').click().run()
    assert len(app.get('plotly_chart')) == 3
    app.checkbox(key='china_kis_stage2_only').check().run()
    assert len(app.dataframe[0].value) == 2
    assert len(app.get('plotly_chart')) == 2
    assert app.session_state['china_research_grid_page'] == 0
    app.radio(key='area').set_value('other').run()
    app.radio(key='area').set_value('china').run()
    assert app.checkbox(key='china_kis_stage2_only').value
    assert len(app.get('plotly_chart')) == 2
    app.radio(key='china_research_view').set_value('차트 고정 목록').run()
    assert len([b for b in app.button if str(b.key).startswith('china_research_pick_')]) == 2
    assert not app.exception
