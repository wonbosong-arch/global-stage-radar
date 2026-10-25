import unittest

import pandas as pd

from candidate_coverage_audit import build_candidate_coverage_report


class CandidateCoverageFreshnessTests(unittest.TestCase):
    def _report(self, price_date: str, as_of_date: str = "2026-10-25") -> pd.Series:
        candidates = pd.DataFrame([{
            "symbol": "TEST",
            "market_benchmark": "SPY",
            "sector_benchmark": "",
            "identity_status": "verified",
            "provider_status": "supported",
            "instrument_type": "common_stock",
            "activation_status": "pending_review",
        }])
        universe = pd.DataFrame([{"symbol": "SPY"}])
        prices = pd.DataFrame([
            {"symbol": "TEST", "date": price_date},
            {"symbol": "SPY", "date": price_date},
        ])
        return build_candidate_coverage_report(
            candidates, universe, prices, as_of_date=as_of_date
        ).iloc[0]

    def test_freshness_is_measured_against_report_date_not_snapshot_max(self):
        row = self._report("2026-10-23")
        self.assertEqual(row["report_as_of_date"], "2026-10-25")
        self.assertEqual(row["candidate_lag_calendar_days_vs_as_of"], 2)
        self.assertNotIn("candidate_price_date_may_be_stale", row["review_blockers"])
        self.assertNotIn("market_benchmark_date_may_be_stale", row["review_blockers"])

    def test_old_snapshot_is_flagged_even_when_candidate_and_benchmark_match(self):
        row = self._report("2026-10-15")
        self.assertEqual(row["candidate_lag_calendar_days_vs_as_of"], 10)
        self.assertIn("candidate_price_date_may_be_stale", row["review_blockers"])
        self.assertIn("market_benchmark_date_may_be_stale", row["review_blockers"])

    def test_invalid_as_of_date_is_rejected(self):
        candidates = pd.DataFrame([{"symbol": "TEST"}])
        universe = pd.DataFrame([{"symbol": "SPY"}])
        prices = pd.DataFrame([{"symbol": "TEST", "date": "2026-10-23"}])
        with self.assertRaises(ValueError):
            build_candidate_coverage_report(
                candidates, universe, prices, as_of_date="not-a-date"
            )


if __name__ == "__main__":
    unittest.main()
