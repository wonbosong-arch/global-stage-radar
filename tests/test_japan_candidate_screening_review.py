import unittest
import pandas as pd

from japan_candidate_screening_review import build_review


class JapanCandidateScreeningReviewTests(unittest.TestCase):
    def test_stage_and_relative_strength_review_remains_inactive(self):
        dates = pd.date_range("2025-06-06", periods=60, freq="W-FRI")
        candidate = pd.DataFrame({
            "date": dates, "symbol": ["221A"] * len(dates),
            "close": [100 + i * 2 for i in range(len(dates))],
            "volume": [1000] * len(dates),
        })
        benchmark = pd.DataFrame({
            "date": dates, "symbol": ["1306"] * len(dates),
            "close": [100 + i for i in range(len(dates))],
            "volume": [2000] * len(dates),
        })
        metadata = pd.DataFrame([{
            "country": "Japan", "symbol": "221A", "sector_or_theme": "Semiconductors",
            "instrument_scope": "Japan semiconductor sector ETF",
            "dashboard_status": "provider_route_available_activation_pending",
        }])
        report = build_review(candidate, benchmark, metadata)
        self.assertEqual(len(report), 1)
        row = report.iloc[0]
        self.assertEqual(row["symbol"], "221A")
        self.assertEqual(row["activation_status"], "inactive_research_only")
        self.assertGreater(row["pct_vs_30w_sma"], 0)
        self.assertTrue(bool(row["30w_sma_rising_over_4w"]))
        self.assertGreater(row["relative_strength_13w_vs_local_market_pct_points"], 0)
        self.assertGreater(row["relative_strength_26w_vs_local_market_pct_points"], 0)

    def test_local_benchmark_from_isolated_candidate_prices_is_used(self):
        dates = pd.date_range("2025-06-06", periods=60, freq="W-FRI")
        candidate = pd.DataFrame({
            "date": list(dates) + list(dates),
            "symbol": ["221A"] * len(dates) + ["1306"] * len(dates),
            "close": [100 + i * 2 for i in range(len(dates))] + [100 + i for i in range(len(dates))],
            "volume": [1000] * len(dates) + [2000] * len(dates),
        })
        metadata = pd.DataFrame([{
            "country": "Japan", "symbol": "221A", "sector_or_theme": "Semiconductors",
            "instrument_scope": "Japan semiconductor ETF",
            "dashboard_status": "research_only_theme_candidate",
        }])
        # The active dashboard snapshot intentionally has no Japan benchmark row.
        active = pd.DataFrame(columns=["date", "symbol", "close", "volume"])
        report = build_review(candidate, active, metadata)
        row = report.iloc[0]
        self.assertNotEqual(row["relative_strength_13w_vs_local_market_pct_points"], "")
        self.assertNotEqual(row["relative_strength_26w_vs_local_market_pct_points"], "")
        self.assertEqual(row["local_market_benchmark_latest_date"], str(dates[-1].date()))
        self.assertEqual(row["activation_status"], "inactive_research_only")

    def test_missing_benchmark_leaves_relative_strength_blank(self):
        dates = pd.date_range("2025-06-06", periods=40, freq="W-FRI")
        candidate = pd.DataFrame({"date": dates, "symbol": ["221A"] * len(dates), "close": [100 + i for i in range(len(dates))]})
        metadata = pd.DataFrame(columns=["country", "symbol", "sector_or_theme"])
        report = build_review(candidate, pd.DataFrame(columns=["date", "symbol", "close"]), metadata)
        self.assertEqual(report.iloc[0]["relative_strength_13w_vs_local_market_pct_points"], "")
        self.assertEqual(report.iloc[0]["activation_status"], "inactive_research_only")


if __name__ == "__main__":
    unittest.main()
