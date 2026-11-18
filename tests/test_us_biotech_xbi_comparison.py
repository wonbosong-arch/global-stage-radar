"""Pure regression contracts for on-demand KIS XBI comparison in the stock tab."""
from pathlib import Path
import ast
import unittest

import numpy as np
import pandas as pd

from us_biotech_xbi_comparison import compare_biotech_to_xbi


def prices(symbol, drift, *, dates=None):
    dates = pd.bdate_range(end="2026-11-17", periods=440) if dates is None else dates
    close = 100 * np.power(1 + drift, np.arange(len(dates)))
    return pd.DataFrame({
        "date": dates, "symbol": symbol,
        "open": close, "high": close * 1.01, "low": close * .99,
        "close": close, "volume": 1000000,
    })


class BiotechXBIReturnsTests(unittest.TestCase):
    def test_aligned_completed_weeks_produce_stock_xbi_and_relative_returns(self):
        stock = prices("BIOTEST", .001)
        xbi = prices("XBI", .0005)
        before_stock, before_xbi = stock.copy(deep=True), xbi.copy(deep=True)
        got = compare_biotech_to_xbi(stock, xbi, as_of_date="2026-11-18")
        self.assertIsNotNone(got)
        self.assertEqual(got["completed_week"], "2026-11-13")
        self.assertGreater(got["stock_return_26w_pct"], got["xbi_return_26w_pct"])
        self.assertAlmostEqual(
            got["relative_26w_pp"],
            got["stock_return_26w_pct"] - got["xbi_return_26w_pct"], places=8,
        )
        self.assertFalse(got["stage_benchmark_changed"])
        pd.testing.assert_frame_equal(stock, before_stock)
        pd.testing.assert_frame_equal(xbi, before_xbi)

    def test_stale_missing_duplicate_and_bad_ohlc_never_infer_comparison(self):
        stock = prices("BIOTEST", .001)
        xbi = prices("XBI", .0005)
        cases = [
            xbi.iloc[:30],
            xbi.iloc[:-24],
            pd.concat([xbi, xbi.iloc[[-1]]]),
            xbi.assign(close=-1),
            xbi.drop(columns=["volume"]),
        ]
        for invalid in cases:
            with self.subTest(reason=str(invalid.shape)):
                self.assertIsNone(compare_biotech_to_xbi(
                    stock, invalid, as_of_date="2026-11-18"))
        self.assertIsNone(compare_biotech_to_xbi(
            stock.iloc[:-24], xbi, as_of_date="2026-11-18"))

    def test_no_future_data_is_used(self):
        dates = pd.bdate_range(end="2026-11-17", periods=440)
        stock = prices("BIOTEST", .001, dates=dates)
        xbi = prices("XBI", .0005, dates=dates)
        # A fictitious future print must not change the completed-week comparison.
        control = compare_biotech_to_xbi(stock, xbi, as_of_date="2026-11-18")
        future = prices("XBI", .9, dates=pd.DatetimeIndex(["2026-11-27"]))
        got = compare_biotech_to_xbi(stock, pd.concat([xbi, future]),
                                      as_of_date="2026-11-18")
        self.assertEqual(got, control)

    def test_stock_tab_integrates_only_one_xbi_live_read(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        area = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "render_asset_area")
        strings = {n.value for n in ast.walk(area)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertIn("XBI", strings)
        self.assertIn("XBI 대비 상대강도", strings)
        self.assertIn("KIS AMS · 완료 주봉 동일 기준일 · 기존 Stage 업종 ETF는 그대로 유지", strings)
        cached = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                      and n.name == "cached_research_xbi_prices")
        self.assertIn('exchange="AMS"', ast.get_source_segment(source, cached))
        self.assertIn("max_pages=4", ast.get_source_segment(source, cached))
        self.assertIn("cached_research_xbi_prices()", ast.get_source_segment(source, area))
        self.assertIn('candidate == "XBI"', ast.get_source_segment(source, area))
        self.assertIn('chart_row.get("analysis_scope") == "연구"',
                      ast.get_source_segment(source, area))


if __name__ == "__main__":
    unittest.main()
