import unittest
import pandas as pd

from china_candidate_screening_review import build_review


class ChinaCandidateScreeningReviewTests(unittest.TestCase):
    def test_stage_and_relative_strength_review_is_inactive_only(self):
        dates = pd.date_range("2025-06-06", periods=60, freq="W-FRI")
        candidate = pd.DataFrame({
            "date": dates, "symbol": ["512700"] * len(dates),
            "close": [100 + i * 2 for i in range(len(dates))],
            "volume": [1000] * len(dates),
        })
        benchmark = pd.DataFrame({
            "date": dates, "symbol": ["MCHI"] * len(dates),
            "close": [100 + i for i in range(len(dates))],
            "volume": [2000] * len(dates),
        })
        universe = pd.DataFrame([{
            "symbol": "512700", "name": "Banks ETF", "sector": "Banks",
            "active": "false", "exchange": "SHS",
        }])
        report = build_review(candidate, benchmark, universe)
        self.assertEqual(len(report), 1)
        row = report.iloc[0]
        self.assertEqual(row["symbol"], "512700")
        self.assertEqual(row["activation_status"], "inactive_research_only")
        self.assertGreater(row["pct_vs_30w_sma"], 0)
        self.assertTrue(bool(row["30w_sma_rising_over_4w"]))
        self.assertGreater(row["relative_strength_13w_vs_MCHI_pct_points"], 0)
        self.assertGreater(row["relative_strength_26w_vs_MCHI_pct_points"], 0)

    def test_missing_benchmark_keeps_relative_strength_blank(self):
        dates = pd.date_range("2025-06-06", periods=40, freq="W-FRI")
        candidate = pd.DataFrame({
            "date": dates, "symbol": ["512700"] * len(dates),
            "close": [100 + i for i in range(len(dates))],
        })
        universe = pd.DataFrame([{
            "symbol": "512700", "name": "Banks ETF", "sector": "Banks",
            "active": "false", "exchange": "SHS",
        }])
        report = build_review(candidate, pd.DataFrame(columns=["date", "symbol", "close"]), universe)
        self.assertEqual(report.iloc[0]["relative_strength_13w_vs_MCHI_pct_points"], "")
        self.assertEqual(report.iloc[0]["activation_status"], "inactive_research_only")


if __name__ == "__main__":
    unittest.main()
