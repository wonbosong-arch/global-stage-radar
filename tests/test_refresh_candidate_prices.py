import unittest

import pandas as pd

from refresh_candidate_prices import normalize_candidate_bars


class NormalizeCandidateBarsTests(unittest.TestCase):
    def test_invalid_dates_produce_empty_result(self):
        bars = pd.DataFrame([
            {"date": "not-a-date", "symbol": "AAPL", "close": 100},
            {"date": None, "symbol": "AAPL", "close": 101},
        ])
        result = normalize_candidate_bars(bars, "AAPL")
        self.assertTrue(result.empty)

    def test_missing_date_column_produces_empty_result(self):
        result = normalize_candidate_bars(pd.DataFrame([{"symbol": "AAPL", "close": 100}]), "AAPL")
        self.assertTrue(result.empty)
        self.assertIn("symbol", result.columns)

    def test_mixed_dates_are_filtered_and_duplicate_symbol_dates_removed(self):
        bars = pd.DataFrame([
            {"date": "2026-10-23", "symbol": " aapl ", "close": 100},
            {"date": "bad-date", "symbol": "AAPL", "close": 101},
            {"date": "2026-10-23T12:00:00", "symbol": "AAPL", "close": 102},
            {"date": "2026-10-22", "symbol": "", "close": 99},
        ])
        result = normalize_candidate_bars(bars, "aapl")
        self.assertEqual(len(result), 2)
        self.assertEqual(result["symbol"].tolist(), ["AAPL", "AAPL"])
        self.assertEqual(result["date"].tolist(), ["2026-10-23", "2026-10-22"])

    def test_missing_symbol_column_is_filled(self):
        bars = pd.DataFrame([{"date": "2026-10-23", "close": 100}])
        result = normalize_candidate_bars(bars, "msft")
        self.assertEqual(result.loc[0, "symbol"], "MSFT")


if __name__ == "__main__":
    unittest.main()
