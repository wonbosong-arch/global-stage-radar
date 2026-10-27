import unittest

import pandas as pd

from refresh_daily_prices import merge_daily_snapshots


class ActiveSnapshotFutureDateTests(unittest.TestCase):
    def test_merge_discards_future_bars_and_keeps_valid_history(self):
        existing = pd.DataFrame([
            {"date": "2026-10-24", "symbol": "SPY", "close": 100},
            {"date": "2026-10-28", "symbol": "SPY", "close": 999},
        ])
        fresh = pd.DataFrame([
            {"date": "2026-10-27", "symbol": "SPY", "close": 101},
            {"date": "2026-10-29", "symbol": "SPY", "close": 1000},
        ])

        merged = merge_daily_snapshots(existing, fresh, as_of_date="2026-10-27")

        self.assertEqual(merged["date"].tolist(), ["2026-10-24", "2026-10-27"])
        self.assertEqual(merged["close"].tolist(), [100, 101])

    def test_fresh_duplicate_row_wins_for_same_symbol_date(self):
        existing = pd.DataFrame([
            {"date": "2026-10-27", "symbol": "SPY", "close": 100},
        ])
        fresh = pd.DataFrame([
            {"date": "2026-10-27", "symbol": "SPY", "close": 101},
        ])

        merged = merge_daily_snapshots(existing, fresh, as_of_date="2026-10-27")

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged.iloc[0]["close"], 101)


if __name__ == "__main__":
    unittest.main()
