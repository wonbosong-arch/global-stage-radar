import unittest

import pandas as pd

from refresh_china_candidate_prices import CANDIDATE_SYMBOLS, merge_prices


class ChinaCandidatePriceObservationTests(unittest.TestCase):
    def test_candidate_set_is_limited_to_ten_mainland_etfs(self):
        self.assertEqual(len(CANDIDATE_SYMBOLS), 10)
        self.assertIn("512800", CANDIDATE_SYMBOLS)
        self.assertIn("515030", CANDIDATE_SYMBOLS)

    def test_merge_preserves_old_bars_and_prefers_fresh_duplicate(self):
        old = pd.DataFrame([
            {"date": "2026-10-20", "symbol": "512800", "close": 100},
            {"date": "2026-10-21", "symbol": "512800", "close": 101},
        ])
        fresh = pd.DataFrame([
            {"date": "2026-10-21", "symbol": "512800", "close": 102},
            {"date": "2026-10-22", "symbol": "512800", "close": 103},
        ])
        merged = merge_prices(old, fresh)
        self.assertEqual(merged["date"].tolist(), ["2026-10-20", "2026-10-21", "2026-10-22"])
        self.assertEqual(float(merged.loc[merged["date"].eq("2026-10-21"), "close"].iloc[0]), 102)

    def test_empty_inputs_return_a_well_formed_empty_snapshot(self):
        merged = merge_prices(pd.DataFrame(), pd.DataFrame())
        self.assertTrue({"date", "symbol", "open", "high", "low", "close", "volume"}.issubset(merged.columns))
        self.assertTrue(merged.empty)


if __name__ == "__main__":
    unittest.main()
