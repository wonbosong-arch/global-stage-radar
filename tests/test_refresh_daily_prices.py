import unittest
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch

import pandas as pd

import refresh_daily_prices as refresh

from refresh_daily_prices import (
    FULL_HISTORY_PAGES,
    LATEST_UPDATE_PAGES,
    build_snapshot_status,
    filter_active_universe,
    merge_daily_snapshots,
    write_status_atomically,
    pages_needed,
    preserved_symbols_from_errors,
)
from market_data import completed_bar_cutoff_date, filter_incomplete_asian_daily_bars


class DailyPriceRefreshTests(unittest.TestCase):
    def test_scheduled_japan_close_retries_missing_etf_only_in_operating_snapshot(self):
        universe = pd.DataFrame([
            {"symbol": "1306", "exchange": "TSE", "market": "Japan", "asset_type": "market_etf"},
            {"symbol": "2644", "exchange": "TSE", "market": "Japan", "asset_type": "sector_etf"},
            {"symbol": "EWJ", "exchange": "NYS", "market": "Japan", "asset_type": "market_etf"},
        ])
        slot = "2026-11-27T07:30:00+00:00"
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            "KIS_APP_KEY": "mock", "KIS_APP_SECRET": "mock", "JAPAN_CLOSE": "true",
            "SCHEDULED_SLOT": slot, "GITHUB_OUTPUT": str(Path(directory) / "outputs"),
        }):
            prices = Path(directory) / "daily_prices.csv"
            operating_status = Path(directory) / "daily_prices_status.json"
            operating_status.write_text("{}", encoding="utf-8")
            pd.DataFrame([
                {"symbol": "1306", "date": "2026-11-27", "close": 10},
                {"symbol": "EWJ", "date": "2026-11-26", "close": 30},
            ]).to_csv(prices, index=False)

            with (
                patch.object(refresh, "read_universe", return_value=universe),
                patch.object(refresh, "PRICES_PATH", prices),
                patch.object(refresh, "STATUS_PATH", operating_status),
                patch.object(refresh, "KISDomesticPrices"),
                patch.object(refresh, "KISUSProvider") as provider,
                patch.object(refresh, "datetime", wraps=datetime) as clock,
            ):
                clock.now.return_value = datetime.fromisoformat(slot).astimezone(ZoneInfo("Asia/Seoul"))
                fetch = provider.return_value.fetch_daily
                fetch.side_effect = [
                    pd.DataFrame([{"symbol": "2644", "date": "2026-11-26", "close": 19}]),
                    pd.DataFrame([{"symbol": "2644", "date": "2026-11-27", "close": 20}]),
                ]
                refresh.main()
                status_path = Path(directory) / "japan_operating_prices_status.json"
                first = json.loads(status_path.read_text())
                self.assertEqual(first["errors"][0]["symbol"], "2644")
                self.assertEqual(first["scheduled_completed_symbols"], ["1306"])
                refresh.main()
                second = json.loads(status_path.read_text())
                self.assertEqual(second["last_completed_scheduled_slot"], slot)
                self.assertEqual(second["scheduled_completed_symbols"], ["1306", "2644"])
                self.assertEqual([call.args[0] for call in fetch.call_args_list], ["2644", "2644"])

            saved = pd.read_csv(prices)
            self.assertEqual(saved.loc[saved.symbol.eq("EWJ"), "close"].tolist(), [30])
            self.assertEqual(json.loads(operating_status.read_text()), {})

    def test_asian_market_cutoff_excludes_in_progress_session_until_close(self):
        before_open = datetime(2026, 10, 28, 9, 30, tzinfo=ZoneInfo("Asia/Seoul"))
        after_korea_close = datetime(2026, 10, 28, 15, 40, tzinfo=ZoneInfo("Asia/Seoul"))
        after_china_close = datetime(2026, 10, 28, 16, 10, tzinfo=ZoneInfo("Asia/Seoul"))
        self.assertEqual(completed_bar_cutoff_date("KRX", before_open), "2026-10-27")
        self.assertEqual(completed_bar_cutoff_date("TSE", before_open), "2026-10-27")
        self.assertEqual(completed_bar_cutoff_date("SHS", before_open), "2026-10-27")
        self.assertEqual(completed_bar_cutoff_date("KRX", after_korea_close), "2026-10-28")
        self.assertEqual(completed_bar_cutoff_date("SHS", after_china_close), "2026-10-28")

    def test_asian_market_cutoff_never_returns_weekend_dates(self):
        saturday_after_close = datetime(2026, 10, 31, 16, 30, tzinfo=ZoneInfo("Asia/Seoul"))
        sunday_before_open = datetime(2026, 11, 1, 8, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        self.assertEqual(completed_bar_cutoff_date("TSE", saturday_after_close), "2026-10-30")
        self.assertEqual(completed_bar_cutoff_date("SHS", sunday_before_open), "2026-10-30")

    def test_dashboard_read_filter_removes_partial_asian_bars_but_keeps_proxies_and_crypto(self):
        now = datetime(2026, 10, 28, 9, 30, tzinfo=ZoneInfo("Asia/Seoul"))
        frame = pd.DataFrame([
            {"date": "2026-10-27", "symbol": "1615", "close": 100},
            {"date": "2026-10-28", "symbol": "1615", "close": 101},
            {"date": "2026-10-28", "symbol": "512800", "close": 200},
            {"date": "2026-10-28", "symbol": "EWJ", "close": 300},
            {"date": "2026-10-28", "symbol": "BTC-USD", "close": 400},
        ])
        filtered = filter_incomplete_asian_daily_bars(
            frame,
            {"1615": "TSE", "512800": "SHS", "EWJ": "NYS", "BTC-USD": "CRYPTO"},
            now_kst=now,
        )
        self.assertEqual(
            list(zip(filtered["symbol"], filtered["date"])),
            [
                ("1615", "2026-10-27"),
                ("EWJ", "2026-10-28"),
                ("BTC-USD", "2026-10-28"),
            ],
        )

    def test_us_exchange_cutoff_uses_completed_new_york_session_date(self):
        before_open = datetime(2026, 10, 28, 9, 30, tzinfo=ZoneInfo("Asia/Seoul"))
        self.assertEqual(completed_bar_cutoff_date("NYS", before_open), "2026-10-27")
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

    def test_status_json_serialization_error_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "daily_prices_status.json"
            target.write_text('{"old": true}', encoding="utf-8")
            with self.assertRaises(TypeError):
                write_status_atomically(target, {"invalid": object()})
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"old": True})
            self.assertEqual([p.name for p in Path(folder).iterdir()], [target.name])

    def test_status_json_atomic_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "daily_prices_status.json"
            target.write_text('{"old": true}', encoding="utf-8")
            payload = {"updated_at_kst": "2026-10-30T07:00:00+09:00", "errors": []}
            write_status_atomically(target, payload)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), payload)
            self.assertEqual([p.name for p in Path(folder).iterdir()], [target.name])

    def test_repeated_identical_refresh_does_not_duplicate_rows(self):
        existing = pd.DataFrame([
            {"date": "2026-10-28", "symbol": "SPY", "close": 100.0},
        ])
        fresh = pd.DataFrame([
            {"date": "2026-10-28", "symbol": "SPY", "close": 101.0},
        ])
        once = merge_daily_snapshots(existing, fresh, as_of_date="2026-10-30")
        twice = merge_daily_snapshots(once, fresh, as_of_date="2026-10-30")
        pd.testing.assert_frame_equal(once, twice)
        self.assertEqual(len(twice), 1)
        self.assertEqual(float(twice.iloc[0]["close"]), 101.0)

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
