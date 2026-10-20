import unittest
import numpy as np
import pandas as pd

from stage_engine import classify_stage, relative_return_difference, weekly_bars


def weekly_frame(closes):
    dates = pd.date_range("2024-01-05", periods=len(closes), freq="W-FRI")
    return pd.DataFrame({
        "date": dates,
        "open": closes,
        "high": np.asarray(closes) * 1.01,
        "low": np.asarray(closes) * 0.99,
        "close": closes,
        "volume": np.full(len(closes), 1000),
    })


class StageEngineTests(unittest.TestCase):
    def test_weekly_bars_aggregates_daily_data(self):
        dates = pd.bdate_range("2024-01-01", periods=300)
        daily = pd.DataFrame({
            "date": dates,
            "open": np.arange(300) + 100.0,
            "high": np.arange(300) + 102.0,
            "low": np.arange(300) + 99.0,
            "close": np.arange(300) + 101.0,
            "volume": np.full(300, 100),
        })
        weekly = weekly_bars(daily)
        self.assertIsNotNone(weekly)
        self.assertGreaterEqual(len(weekly), 35)
        self.assertTrue((weekly["high"] >= weekly["low"]).all())
        self.assertAlmostEqual(weekly.iloc[0]["volume"], 500)

    def test_relative_return_difference_uses_same_dates(self):
        asset = weekly_frame(np.linspace(100, 200, 60))
        benchmark = weekly_frame(np.linspace(100, 110, 60))
        relative = relative_return_difference(asset, benchmark, 26)
        self.assertGreater(relative.iloc[-1], 0)
        self.assertTrue(pd.isna(relative.iloc[0]))

    def test_stock_requires_market_and_sector_outperformance(self):
        label = classify_stage(120, 100, 2.0, 5.0, -1.0, "stock")
        self.assertEqual(label, "Stage 2A 관찰 후보")

    def test_etf_can_be_stage_two_without_sector_relative_series(self):
        label = classify_stage(120, 100, 2.0, 5.0, np.nan, "sector_etf")
        self.assertEqual(label, "Stage 2 후보")

    def test_declining_below_average_is_downtrend_watch(self):
        label = classify_stage(80, 100, -1.0, -3.0, -2.0, "stock")
        self.assertEqual(label, "하락 추세 관찰")


if __name__ == "__main__":
    unittest.main()
