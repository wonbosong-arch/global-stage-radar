"""Regression tests for dashboard selection state without importing the Streamlit app."""
import ast
from pathlib import Path
import unittest
from types import SimpleNamespace


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def load_open_symbol_detail(session_state):
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    node = next(
        item for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == "open_symbol_detail"
    )
    namespace = {"st": SimpleNamespace(session_state=session_state)}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(APP_PATH), "exec"), namespace)
    return namespace["open_symbol_detail"]


class DashboardNavigationRegressionTests(unittest.TestCase):
    def test_grid_selection_switches_to_correct_area_and_list_view(self):
        state = {}
        open_symbol_detail = load_open_symbol_detail(state)

        open_symbol_detail("sectors", "EWJ")

        self.assertEqual(state["active_analysis_area"], "sectors")
        self.assertEqual(state["sectors_view_mode"], "목록")
        self.assertEqual(state["sectors_selected_symbol"], "EWJ")
        self.assertNotIn("markets_commodities_selected_symbol", state)

    def test_switching_area_does_not_overwrite_another_areas_selection(self):
        state = {
            "markets_commodities_selected_symbol": "SPY",
            "sectors_selected_symbol": "KWEB",
        }
        open_symbol_detail = load_open_symbol_detail(state)

        open_symbol_detail("sectors", "EWJ")

        self.assertEqual(state["markets_commodities_selected_symbol"], "SPY")
        self.assertEqual(state["sectors_selected_symbol"], "EWJ")

    def test_list_and_quick_compare_use_clickable_buttons_and_split_panels(self):
        source = APP_PATH.read_text(encoding="utf-8")
        self.assertIn('list_panel, chart_panel = st.columns([1, 2], gap="large")', source)
        self.assertIn('quick_list_panel, quick_chart_panel = st.columns([1, 2], gap="large")', source)
        self.assertIn('key=f"{area_key}_pick_{symbol}"', source)
        self.assertIn('key=f"candidate_quick_pick_{quick_symbol}"', source)
        self.assertIn('key=f"{area_key}_view_mode"', source)


if __name__ == "__main__":
    unittest.main()
