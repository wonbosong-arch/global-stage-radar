"""Regression coverage for layout preferences and real Stage 2 filter reruns."""
import json
from pathlib import Path
import unittest

from analysis_preferences import decode_preferences


class AnalysisWidthTests(unittest.TestCase):
    def test_legacy_default_migrates_and_custom_width_roundtrips(self):
        self.assertEqual(decode_preferences(json.dumps({'width': 33}))['dashboard_list_width'], 52)
        for width in (30, 40, 45, 52, 60):
            self.assertEqual(decode_preferences(json.dumps({'width': width}))['dashboard_list_width'], width)
        for width in (29, 61, True, '52'):
            self.assertNotIn('dashboard_list_width', decode_preferences(json.dumps({'width': width})))


def test_stage2_compact_filters_empty_recovery_and_tab_return(monkeypatch):
    from streamlit.testing.v1 import AppTest
    root=Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    monkeypatch.setattr('requests.sessions.Session.request', lambda *a, **k: (_ for _ in ()).throw(AssertionError('network')))
    app=AppTest.from_file(str(root/'app.py'), default_timeout=45).run()
    app.radio(key='analysis_navigation_choice').set_value('stage2').run()
    assert not app.exception
    assert app.slider(key='dashboard_list_width').value == 52
    original=app.session_state['candidate_quick_chart_symbol']
    app.text_input(key='candidate_quick_search').set_value('no-such-candidate-xyz').run()
    # Sort/view remain mounted even for an empty result, allowing recovery.
    app.selectbox(key='candidate_quick_sort').set_value('30주선 기울기').run()
    app.radio(key='global_asset_view_mode').set_value('3×3 차트').run()
    app.text_input(key='candidate_quick_search').set_value('').run()
    app.radio(key='global_asset_view_mode').set_value('차트 고정 목록').run()
    assert not app.exception
    assert app.session_state['candidate_quick_chart_symbol'] == original
    app.checkbox(key='candidate_quick_new_only').check().run()
    app.checkbox(key='candidate_quick_new_only').uncheck().run()
    app.checkbox(key='candidate_quick_favorites_only').check().run()
    app.checkbox(key='candidate_quick_favorites_only').uncheck().run()
    app.radio(key='analysis_navigation_choice').set_value('sectors').run()
    app.radio(key='analysis_navigation_choice').set_value('stage2').run()
    assert not app.exception
    assert app.session_state['candidate_quick_chart_symbol'] == original
    assert app.selectbox(key='candidate_quick_sort').value == '30주선 기울기'
