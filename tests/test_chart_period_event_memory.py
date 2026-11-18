"""Protect chart period preferences from stale Streamlit fragment reruns."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

import chart_ui


class ChartPeriodMemoryTests(unittest.TestCase):
    def test_widget_event_records_selected_period_without_resetting_others(self):
        key = "stocks_selected_period_AMGN"
        other = "stocks_selected_period_ADMA"
        state = {
            key: "일봉",
            "analysis_chart_periods": {key: "주봉", other: "주봉"},
        }
        with mock.patch.object(chart_ui, "st", SimpleNamespace(session_state=state)):
            chart_ui._remember_chart_period(key)
            self.assertEqual(state["analysis_chart_periods"][key], "일봉")
            self.assertEqual(state["analysis_chart_periods"][other], "주봉")
            state[key] = "주봉"
            chart_ui._remember_chart_period(key)
            self.assertEqual(state["analysis_chart_periods"][key], "주봉")

    def test_chart_card_uses_event_time_state_not_stale_render_writeback(self):
        source = (Path(__file__).resolve().parents[1] / "chart_ui.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        card = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "render_chart_card")
        text = ast.get_source_segment(source, card)
        self.assertIn("on_change=_remember_chart_period", text)
        self.assertIn("memory.setdefault(period_key, period)", text)
        self.assertNotIn("memory[period_key] = period", text)


if __name__ == "__main__":
    unittest.main()
