"""Regression tests for dashboard selection state without importing the Streamlit app."""
import ast
from pathlib import Path
import unittest
from types import SimpleNamespace
import pandas as pd


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def load_open_symbol_detail(session_state):
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    nodes = [
        item for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name in {"open_symbol_detail", "_sync_candidate_view_mode"}
    ]
    namespace = {"remember_dashboard_state": lambda: None, "st": SimpleNamespace(session_state=session_state)}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(APP_PATH), "exec"), namespace)
    return namespace["open_symbol_detail"]


class DashboardNavigationRegressionTests(unittest.TestCase):
    def test_country_exclusive_views_do_not_leak_into_shared_controls(self):
        state = {'global_asset_view_mode': '차트 고정 목록',
                 'markets_commodities_view_mode': '히트맵',
                 'markets_commodities_saved_view_mode': '히트맵'}
        names = {'_sync_candidate_view_mode', '_sync_area_view_mode', '_change_grid_page'}
        nodes = [node for node in ast.parse(APP_PATH.read_text()).body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
        namespace = {'remember_dashboard_state': lambda: None, 'st': SimpleNamespace(session_state=state)}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(APP_PATH), 'exec'), namespace)
        namespace['_sync_area_view_mode']('markets_commodities')
        self.assertEqual(state['global_asset_view_mode'], '차트 고정 목록')
        namespace['_change_grid_page']('candidate_quick_grid_page', 1)
        self.assertEqual(state['markets_commodities_view_mode'], '히트맵')
        self.assertEqual(state['candidate_quick_grid_page'], 1)
        namespace['_sync_candidate_view_mode']()
        self.assertEqual(state['markets_commodities_view_mode'], '히트맵')

    def test_country_drilldown_restores_heatmap_or_table_view(self):
        for mode in ('히트맵',):
            with self.subTest(mode=mode):
                state = {'global_asset_view_mode': '차트 고정 목록',
                         'markets_commodities_view_mode': mode,
                         'markets_commodities_selected_symbol': 'EWJ'}
                names = {'open_country_sectors', 'return_to_country_list', '_sync_candidate_view_mode'}
                nodes = [node for node in ast.parse(APP_PATH.read_text()).body
                         if isinstance(node, ast.FunctionDef) and node.name in names]
                namespace = {'remember_dashboard_state': lambda: None, 'st': SimpleNamespace(session_state=state),
                             'screen': pd.DataFrame({'asset_type_norm': ['sector_etf'], 'market': ['Japan']})}
                exec(compile(ast.Module(body=nodes, type_ignores=[]), str(APP_PATH), 'exec'), namespace)
                namespace['open_country_sectors']('Japan')
                self.assertEqual(state['sectors_view_mode'], '차트 고정 목록')
                namespace['return_to_country_list']()
                self.assertEqual(state['markets_commodities_view_mode'], mode)
                self.assertEqual(state['markets_commodities_selected_symbol'], 'EWJ')

    def test_country_drilldown_and_return_keep_selection_and_synchronized_modes(self):
        state = {'markets_commodities_selected_symbol': 'EWJ',
                 'markets_commodities_view_mode': '3×3 차트',
                 'global_asset_view_mode': '3×3 차트'}
        names = {'open_country_sectors', 'return_to_country_list', '_sync_candidate_view_mode'}
        nodes = [node for node in ast.parse(APP_PATH.read_text()).body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
        namespace = {'remember_dashboard_state': lambda: None, 'st': SimpleNamespace(session_state=state),
                     'screen': pd.DataFrame({'asset_type_norm': ['sector_etf'], 'market': ['Japan']})}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(APP_PATH), 'exec'), namespace)
        namespace['open_country_sectors']('Japan')
        self.assertEqual(state['active_analysis_area'], 'sectors')
        self.assertEqual(state['sectors_market'], 'Japan')
        self.assertEqual(state['country_sector_filter_notice'], '')
        namespace['return_to_country_list']()
        self.assertEqual(state['active_analysis_area'], 'markets_commodities')
        self.assertEqual(state['markets_commodities_selected_symbol'], 'EWJ')
        self.assertEqual(state['markets_commodities_view_mode'], '차트 고정 목록')
        self.assertEqual(state['sectors_view_mode'], '차트 고정 목록')
        self.assertNotIn('stocks_view_mode', state)
        namespace['open_country_sectors']('Unmapped country')
        self.assertEqual(state['sectors_market'], '전체')
        self.assertIn('Unmapped country', state['country_sector_filter_notice'])

    def test_grid_selection_switches_to_correct_area_and_list_view(self):
        state = {}
        open_symbol_detail = load_open_symbol_detail(state)

        open_symbol_detail("sectors", "EWJ")

        self.assertEqual(state["active_analysis_area"], "sectors")
        self.assertEqual(state.get("global_asset_view_mode"), None)
        self.assertEqual(state["sectors_view_mode"], "차트 고정 목록")
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
        self.assertIn('@st.fragment\ndef render_screening_workspace():', source)
        self.assertIn('def render_asset_area(area_key, title, subset):', source)
        self.assertNotIn('st.rerun(scope="app")', source)
        self.assertIn('def render_candidate_quick_panel(candidates, view_mode):', source)
        self.assertIn('_responsive_analysis_columns(', source)
        self.assertIn('quick_list_panel, quick_chart_panel = _responsive_analysis_columns(\'candidate_quick_analysis_split\')', source)
        self.assertIn('key=(f"candidate_quick_pick_{symbol}" if button_key_prefix == "candidate_quick_pick" else f"{state_key}_pick_{symbol}")', source)
        self.assertIn('button_key_prefix="candidate_quick_pick"', source)
        self.assertNotIn('key="candidate_quick_compact_picker"', source)
        self.assertNotIn('selection_mode="single-row"', source)
        self.assertIn('subset = subset[subset["market"].astype(str).eq(selected_country)].copy()', source)
        self.assertIn('Stage 2 후보 · 이름을 클릭하면 오른쪽 차트가 바뀝니다.', source)
        self.assertIn('자산 목록 · 이름을 클릭하면 오른쪽 차트가 바뀝니다.', source)
        self.assertIn('key=(f"candidate_quick_pick_{symbol}" if button_key_prefix == "candidate_quick_pick" else f"{state_key}_pick_{symbol}")', source)
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
        self.assertIn('sort_options = ["26주 수익률", "30주선 기울기"]', source)
        self.assertIn('"26주 수익률": "ret26_pct"', source)
        self.assertIn('"ret26_pct": "26주 수익률(%)"', source)
        self.assertNotIn('key="candidate_quick_view_mode"', source)
        self.assertIn('render_candidate_quick_panel(candidates, global_view_mode)', source)
        self.assertEqual(source.count('key="global_asset_view_mode"'), 1)
        self.assertIn('["차트 고정 목록", "3×3 차트"]', source)
        self.assertIn('page_key = "candidate_quick_grid_page"', source)
        self.assertIn('key="candidate_quick_grid_prev"', source)
        self.assertIn('key="candidate_quick_grid_next"', source)
        self.assertIn('chosen = quick_chart_options[page * page_size:(page + 1) * page_size]', source)
        self.assertIn('page_key = f"{area_key}_grid_page"', source)
        self.assertIn('st.session_state[page_key] = page', source)
        self.assertIn('key=f"{area_key}_grid_prev"', source)
        self.assertIn('key=f"{area_key}_grid_next"', source)
        # Pagination reruns must not reset the active view selector to list mode.
        self.assertEqual(source.count('on_click=_change_grid_page'), 4)
        self.assertIn('def _change_grid_page(page_key, page):', source)
        self.assertIn('chosen = all_grid_symbols[page * page_size:(page + 1) * page_size]', source)
        self.assertIn('key=f"candidate_quick_grid_chart_{symbol}"', source)


if __name__ == "__main__":
    unittest.main()
