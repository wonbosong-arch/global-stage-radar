import tempfile
import unittest
from pathlib import Path

import pandas as pd

from refresh_candidate_prices import preserve_failed_symbol_history


class CandidatePriceHistoryPreservationTests(unittest.TestCase):
    def test_preserves_only_failed_symbols_and_prefers_fresh_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous_path = Path(tmp) / "previous.csv"
            pd.DataFrame([
                {"date": "2026-01-01", "symbol": "AAA", "close": 10.0},
                {"date": "2026-01-02", "symbol": "AAA", "close": 11.0},
                {"date": "2026-01-01", "symbol": "BBB", "close": 20.0},
            ]).to_csv(previous_path, index=False)
            fresh = pd.DataFrame([
                {"date": "2026-01-02", "symbol": "AAA", "close": 12.0},
                {"date": "2026-01-01", "symbol": "CCC", "close": 30.0},
            ])
            errors = [
                {"symbol": "AAA", "error": "timeout"},
                {"symbol": "BBB", "error": "empty_response"},
                {"symbol": "CCC", "error": "retryable_error"},
            ]

            result, preserved = preserve_failed_symbol_history(fresh, errors, previous_path)

            self.assertEqual(preserved, ["AAA", "BBB"])
            self.assertEqual(
                set(result["symbol"]),
                {"AAA", "BBB", "CCC"},
            )
            aaa_jan2 = result[(result["symbol"] == "AAA") & (result["date"] == "2026-01-02")]
            self.assertEqual(float(aaa_jan2.iloc[0]["close"]), 12.0)
            self.assertEqual(len(result), 4)

    def test_missing_previous_snapshot_returns_fresh_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            fresh = pd.DataFrame([{"date": "2026-01-01", "symbol": "AAA", "close": 10.0}])
            result, preserved = preserve_failed_symbol_history(
                fresh, [{"symbol": "AAA", "error": "timeout"}], Path(tmp) / "missing.csv"
            )
            self.assertEqual(len(result), 1)
            self.assertEqual(preserved, [])

    def test_run_level_marker_does_not_select_a_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous_path = Path(tmp) / "previous.csv"
            pd.DataFrame([{"date": "2026-01-01", "symbol": "AAA", "close": 10.0}]).to_csv(previous_path, index=False)
            fresh = pd.DataFrame(columns=["date", "symbol", "close"])
            result, preserved = preserve_failed_symbol_history(
                fresh, [{"symbol": "*", "error": "run failed"}], previous_path
            )
            self.assertTrue(result.empty)
            self.assertEqual(preserved, [])


if __name__ == "__main__":
    unittest.main()
