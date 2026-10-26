import unittest

import numpy as np
import pandas as pd

from provisional_candidate_stage import build_provisional_stage_report


def daily(symbol, start, periods, growth):
    dates = pd.bdate_range(start=start, periods=periods)
    close = 100 * np.exp(np.arange(periods) * growth)
    return pd.DataFrame({
        "date": dates, "symbol": symbol, "open": close * 0.995,
        "high": close * 1.01, "low": close * 0.99, "close": close,
        "volume": np.full(periods, 1000),
    })


class ProvisionalCandidateStageTests(unittest.TestCase):
    def test_pending_candidate_gets_provisional_stage_without_activation(self):
        prices = pd.concat([
            daily("CAND", "2024-01-01", 420, 0.004),
            daily("SPY", "2024-01-01", 420, 0.001),
            daily("XLK", "2024-01-01", 420, 0.002),
        ], ignore_index=True)
        candidates = pd.DataFrame([{
            "symbol": "CAND", "name": "Candidate",
            "proposed_sector": "Technology",
            "proposed_market_benchmark": "SPY",
            "suggested_sector_benchmark": "XLK",
            "activation_status": "pending_review",
        }])
        result = build_provisional_stage_report(
            candidates, prices
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["symbol"], "CAND")
        self.assertEqual(result.iloc[0]["activation_status"], "pending_review_not_activated")
        self.assertNotEqual(result.iloc[0]["provisional_stage_label"], "데이터 부족 · 예비 판정 불가")
        self.assertGreater(result.iloc[0]["weekly_bars"], 35)

    def test_missing_benchmark_is_withheld_and_candidate_stays_pending(self):
        prices = daily("CAND", "2024-01-01", 300, 0.002)
        candidates = pd.DataFrame([{
            "symbol": "CAND", "name": "Candidate",
            "proposed_sector": "Technology",
            "proposed_market_benchmark": "SPY",
            "suggested_sector_benchmark": "",
        }])
        result = build_provisional_stage_report(
            candidates, prices
        )
        self.assertIn("판정 보류", result.iloc[0]["provisional_stage_label"])
        self.assertEqual(result.iloc[0]["activation_status"], "pending_review_not_activated")


if __name__ == "__main__":
    unittest.main()
