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
        self.assertEqual(state["global_asset_view_mode"], "차트 고정 목록")
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
        self.assertIn('@st.fragment\ndef render_asset_area(area_key, title, subset):', source)
        self.assertIn('@st.fragment\ndef render_candidate_quick_panel(candidates):', source)
        self.assertIn('list_panel, chart_panel = st.columns([1, 2], gap="large")', source)
        self.assertIn('quick_list_panel, quick_chart_panel = st.columns([1, 2], gap="medium")', source)
        self.assertIn('key=f"candidate_quick_pick_{symbol}"', source)
        self.assertNotIn('key="candidate_quick_compact_picker"', source)
        self.assertNotIn('selection_mode="single-row"', source)
        self.assertIn('key=f"{area_key}_pick_{symbol}"', source)
        self.assertIn('key="global_asset_view_mode"', source)
        self.assertIn('key=area_view_key', source)
        self.assertIn('["차트 고정 목록", "3×3 차트"]', source)
        self.assertIn('def open_country_sectors(market):', source)
        self.assertIn('def return_to_country_list():', source)
        self.assertIn('key="back_to_country_list_from_sectors"', source)
        self.assertIn('on_click=return_to_country_list', source)
        self.assertIn('f"{chart_row.get(\'market\', \'선택 국가\')} 업종 보기 →"', source)
        self.assertIn('hovermode="x", dragmode="pan"', source)
        self.assertIn('title_text="가격", fixedrange=True', source)
        self.assertIn('title_text="거래량", fixedrange=True', source)
        self.assertIn('hoverlabel=dict(align="left", namelength=-1)', source)
        self.assertIn('st.rerun(scope="app")', source)


if __name__ == "__main__":
    unittest.main()
