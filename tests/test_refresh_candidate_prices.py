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


class PreserveFailedSymbolHistoryTests(unittest.TestCase):
    def test_failed_symbol_history_is_preserved_alongside_fresh_data(self):
        import tempfile
        from pathlib import Path
        from refresh_daily_prices import preserve_failed_symbol_history

        with tempfile.TemporaryDirectory() as directory:
            previous_path = Path(directory) / "previous.csv"
            pd.DataFrame([
                {"symbol": "AAA", "date": "2026-10-22", "close": 10},
                {"symbol": "BBB", "date": "2026-10-22", "close": 20},
            ]).to_csv(previous_path, index=False)
            fresh = pd.DataFrame([{"symbol": "AAA", "date": "2026-10-23", "close": 11}])

            combined, preserved = preserve_failed_symbol_history(
                fresh, [{"symbol": "BBB", "error": "timeout"}], previous_path=previous_path
            )

        self.assertEqual(preserved, ["BBB"])
        self.assertEqual(
            set(zip(combined["symbol"], combined["date"])),
            {("AAA", "2026-10-23"), ("BBB", "2026-10-22")},
        )

    def test_successfully_refreshed_symbol_does_not_get_old_history_copied(self):
        import tempfile
        from pathlib import Path
        from refresh_daily_prices import preserve_failed_symbol_history

        with tempfile.TemporaryDirectory() as directory:
            previous_path = Path(directory) / "previous.csv"
            pd.DataFrame([{"symbol": "AAA", "date": "2026-10-22", "close": 10}]).to_csv(
                previous_path, index=False
            )
            fresh = pd.DataFrame([{"symbol": "AAA", "date": "2026-10-23", "close": 11}])

            combined, preserved = preserve_failed_symbol_history(
                fresh, [{"symbol": "AAA", "error": "stale error record"}], previous_path=previous_path
            )

        self.assertEqual(preserved, [])
        self.assertEqual(combined["date"].tolist(), ["2026-10-23"])

    def test_no_errors_leaves_fresh_data_unchanged(self):
        from refresh_daily_prices import preserve_failed_symbol_history

        fresh = pd.DataFrame([{"symbol": "AAA", "date": "2026-10-23", "close": 11}])
        combined, preserved = preserve_failed_symbol_history(fresh, [], previous_path=None)

        self.assertTrue(combined.equals(fresh))
        self.assertEqual(preserved, [])


if __name__ == "__main__":
    unittest.main()
