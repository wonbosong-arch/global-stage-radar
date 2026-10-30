from hashlib import sha256
from pathlib import Path
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

from asset_table import cell_text, entry_value, sorted_rows, table_columns


class AssetTableTests(unittest.TestCase):
    def test_unknown_entry_is_hidden_and_never_fabricated(self):
        frame = pd.DataFrame([{'symbol': 'A', 'stage_label': 'Stage 2 후보',
                               'stage2_new_entry': True, 'previous_stage_label': '이전 주 데이터 부족'}])
        self.assertIsNone(entry_value(frame.iloc[0]))
        self.assertNotIn('_new', [c[0] for c in table_columns(frame)])
        frame['previous_stage_label'] = 'Stage 1'
        self.assertTrue(entry_value(frame.iloc[0]))
        self.assertIn('_new', [c[0] for c in table_columns(frame)])
        self.assertEqual(cell_text(frame.iloc[0], '_new'), 'N')

    def test_columns_exclude_names_and_ma_distance_and_hide_empty_metrics(self):
        frame = pd.DataFrame([{'symbol': 'A', 'name': 'Fund Name', 'ret26_pct': 8.25,
                               'ma30_distance_pct': 7, 'ret13_pct': None}])
        self.assertEqual([c[0] for c in table_columns(frame)], ['symbol', 'ret26_pct', '_favorite'])
        self.assertEqual(cell_text(frame.iloc[0], 'ret26_pct'), '+8.25%')

    def test_numeric_sort_is_stable_null_last_and_does_not_mutate_source(self):
        frame = pd.DataFrame({'symbol': ['B', 'C', 'A', 'D'], 'ret26_pct': [9, None, 100, 9]})
        original = frame.copy(deep=True)
        self.assertEqual(sorted_rows(frame, 'ret26_pct', False).symbol.tolist(), ['A', 'B', 'D', 'C'])
        self.assertEqual(sorted_rows(frame, 'ret26_pct', True).symbol.tolist(), ['B', 'D', 'A', 'C'])
        pd.testing.assert_frame_equal(frame, original)

    def test_new_sort_does_not_treat_unknown_as_existing(self):
        frame = pd.DataFrame([
            {'symbol': 'U', 'previous_stage_label': None, 'stage2_new_entry': True, 'stage_label': 'Stage 2 후보'},
            {'symbol': 'O', 'previous_stage_label': 'Stage 2 후보', 'stage2_new_entry': False, 'stage_label': 'Stage 2 후보'},
            {'symbol': 'N', 'previous_stage_label': 'Stage 1', 'stage2_new_entry': True, 'stage_label': 'Stage 2 후보'},
        ])
        self.assertEqual(sorted_rows(frame, '_new', False).symbol.tolist(), ['N', 'O', 'U'])


def test_table_sort_and_star_preserve_selected_chart(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    app = AppTest.from_file(str(root / 'app.py'), default_timeout=60).run()
    app.radio(key='active_analysis_area').set_value('stocks').run()
    def picks():
        return [b.label for b in app.button if b.key and b.key.startswith('stocks_selected_symbol_pick_')]
    original_order = picks()
    selected = app.session_state['stocks_selected_symbol']
    other = next(s for s in original_order if s != selected)
    token = sha256(other.encode()).hexdigest()[:16]
    app.button(key=f'stocks_selected_symbol_table_star_{token}_favorite').click().run()
    assert other in app.session_state['analysis_favorites']
    assert app.session_state['stocks_selected_symbol'] == selected
    app.button(key='asset_table_sort_pick_stocks_selected_symbol_ret26_pct').click().run()
    assert picks() == original_order
    app.button(key='asset_table_sort_pick_stocks_selected_symbol_ret26_pct').click().run()
    assert picks() == list(reversed(original_order))
    assert app.session_state['stocks_selected_symbol'] == selected
    app.checkbox(key='stocks_favorites_only').check().run()
    assert picks() == [other]
    assert app.session_state['stocks_selected_symbol'] == selected
    app.radio(key='active_analysis_area').set_value('sectors').run()
    app.radio(key='active_analysis_area').set_value('stocks').run()
    assert app.session_state['stocks_selected_symbol_table_sort'] == ('ret26_pct', True)
    assert not app.exception
