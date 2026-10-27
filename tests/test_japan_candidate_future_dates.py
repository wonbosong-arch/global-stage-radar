import unittest

import pandas as pd

from refresh_japan_candidate_prices import merge_prices


class JapanCandidateFutureDateTests(unittest.TestCase):
    def test_merge_discards_future_dated_rows_and_keeps_history(self):
        existing = pd.DataFrame([
            {"date": "2026-10-24", "symbol": "221A", "close": 100},
            {"date": "2026-10-28", "symbol": "221A", "close": 999},
        ])
        fresh = pd.DataFrame([
            {"date": "2026-10-27", "symbol": "221A", "close": 101},
            {"date": "2026-10-29", "symbol": "221A", "close": 1000},
        ])

        merged = merge_prices(existing, fresh, as_of_date="2026-10-27")

        self.assertEqual(merged["date"].tolist(), ["2026-10-24", "2026-10-27"])
        self.assertEqual(merged["close"].tolist(), [100, 101])

    def test_merge_removes_duplicate_symbol_dates(self):
        existing = pd.DataFrame([
            {"date": "2026-10-27", "symbol": "221A", "close": 100},
        ])
        fresh = pd.DataFrame([
            {"date": "2026-10-27", "symbol": "221A", "close": 101},
        ])

        merged = merge_prices(existing, fresh, as_of_date="2026-10-27")

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged.iloc[0]["close"], 101)


if __name__ == "__main__":
    unittest.main()
