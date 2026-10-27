import unittest

import pandas as pd

from refresh_daily_prices import (
    FULL_HISTORY_PAGES,
    LATEST_UPDATE_PAGES,
    build_snapshot_status,
    filter_active_universe,
    merge_daily_snapshots,
    pages_needed,
    preserved_symbols_from_errors,
)


class DailyPriceRefreshTests(unittest.TestCase):
    def test_inactive_research_candidates_are_excluded_from_daily_requests(self):
        universe = pd.DataFrame([
            {"symbol": "SPY", "active": "true"},
            {"symbol": "512800", "active": "false"},
            {"symbol": "512010", "active": "FALSE"},
            {"symbol": "EWJ", "active": "1"},
            {"symbol": "KWEB", "active": ""},
        ])
        result = filter_active_universe(universe)
        self.assertEqual(result["symbol"].tolist(), ["SPY", "EWJ"])

    def test_older_universe_without_active_column_remains_compatible(self):
        universe = pd.DataFrame([{"symbol": "SPY"}, {"symbol": "EWJ"}])
        result = filter_active_universe(universe)
        self.assertEqual(result["symbol"].tolist(), ["SPY", "EWJ"])

    def test_merge_preserves_history_and_prefers_fresh_duplicate_rows(self):
        existing = pd.DataFrame([
            {"date": "2025-01-01", "symbol": "aaa", "close": 10.0},
            {"date": "2025-01-02", "symbol": "AAA", "close": 11.0},
        ])
        fresh = pd.DataFrame([
            {"date": "2025-01-02", "symbol": "AAA", "close": 12.0},
            {"date": "2025-01-03", "symbol": "AAA", "close": 13.0},
            {"date": "not-a-date", "symbol": "AAA", "close": 99.0},
        ])

        result = merge_daily_snapshots(existing, fresh)

        self.assertEqual(list(result["date"]), ["2025-01-01", "2025-01-02", "2025-01-03"])
        self.assertEqual(list(result["close"]), [10.0, 12.0, 13.0])
        self.assertEqual(list(result["symbol"]), ["AAA", "AAA", "AAA"])

    def test_merge_empty_fresh_snapshot_keeps_existing_history(self):
        existing = pd.DataFrame([
            {"date": "2025-01-01", "symbol": "AAA", "close": 10.0},
        ])

        result = merge_daily_snapshots(existing, pd.DataFrame())

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["close"], 10.0)

    def test_page_count_limits_daily_requests_for_established_symbols(self):
        self.assertEqual(pages_needed(0), FULL_HISTORY_PAGES)
        self.assertEqual(pages_needed(249), FULL_HISTORY_PAGES)
        self.assertEqual(pages_needed(250), LATEST_UPDATE_PAGES)
        self.assertEqual(pages_needed(1000), LATEST_UPDATE_PAGES)

    def test_preserved_symbols_only_lists_failed_refreshes_with_existing_history(self):
        existing = pd.DataFrame([
            {"date": "2025-01-01", "symbol": "aaa", "close": 10.0},
            {"date": "2025-01-01", "symbol": "BBB", "close": 20.0},
        ])
        errors = [
            {"symbol": "AAA", "error": "timeout"},
            {"symbol": "NEW", "error": "empty_response"},
            {"symbol": " bbb ", "error": "rate_limit"},
        ]

        self.assertEqual(preserved_symbols_from_errors(existing, errors), ["AAA", "BBB"])

    def test_preserved_symbols_is_empty_without_existing_history(self):
        errors = [{"symbol": "AAA", "error": "timeout"}]
        self.assertEqual(preserved_symbols_from_errors(pd.DataFrame(), errors), [])


    def test_status_lists_fresh_symbols_missing_symbols_and_latest_dates(self):
        universe = pd.DataFrame([{"symbol": "INCO"}, {"symbol": "KWEB"}, {"symbol": "CQQQ"}])
        fresh = pd.DataFrame([
            {"date": "2026-10-26", "symbol": "INCO", "close": 50.0},
            {"date": "2026-10-24", "symbol": "KWEB", "close": 30.0},
        ])
        existing = pd.DataFrame([
            {"date": "2026-10-23", "symbol": "CQQQ", "close": 20.0},
        ])
        prices = merge_daily_snapshots(existing, fresh)
        status = build_snapshot_status(
            universe, fresh, prices, existing,
            [{"symbol": "CQQQ", "error": "timeout"}],
        )
        self.assertEqual(status["requested_symbols"], 3)
        self.assertEqual(status["symbols_with_data"], 3)
        self.assertEqual(status["fresh_data_symbols"], ["INCO", "KWEB"])
        self.assertEqual(status["missing_symbols"], [])
        self.assertEqual(status["latest_date_by_symbol"]["INCO"], "2026-10-26")
        self.assertEqual(status["symbols_preserved_from_previous_snapshot"], ["CQQQ"])


if __name__ == "__main__":
    unittest.main()
