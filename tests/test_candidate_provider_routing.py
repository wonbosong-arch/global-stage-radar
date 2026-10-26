import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd

from refresh_candidate_prices import fetch_candidate_daily, history_pages_for_candidate, merge_listing_transfer_history


class CandidateProviderRoutingTests(unittest.TestCase):
    def test_et_history_merges_pre_transfer_nyse_bars_with_current_venue_bars(self):
        prior_dates = pd.date_range("2025-08-15", "2026-10-02", freq="B")
        current_dates = pd.date_range("2026-10-05", "2026-10-23", freq="B")
        prior = pd.DataFrame({
            "date": prior_dates, "symbol": "ET", "close": range(100, 100 + len(prior_dates))
        })
        current = pd.DataFrame({
            "date": current_dates, "symbol": "ET", "close": range(500, 500 + len(current_dates))
        })

        merged, rows_added = merge_listing_transfer_history(current, prior, "2026-10-05")

        self.assertEqual(rows_added, len(prior_dates))
        self.assertEqual(merged["date"].nunique(), len(prior_dates) + len(current_dates))
        self.assertEqual(pd.to_datetime(merged["date"]).min().strftime("%Y-%m-%d"), "2025-08-15")
        self.assertEqual(pd.to_datetime(merged["date"]).max().strftime("%Y-%m-%d"), "2026-10-23")
        self.assertFalse(merged["date"].duplicated().any())

    def test_et_history_extension_keeps_current_bars_when_prior_exchange_returns_empty(self):
        current = pd.DataFrame([
            {"date": "2026-10-05", "symbol": "ET", "close": 20.0},
            {"date": "2026-10-06", "symbol": "ET", "close": 20.1},
        ])

        merged, rows_added = merge_listing_transfer_history(current, pd.DataFrame(), "2026-10-05")

        self.assertEqual(rows_added, 0)
        self.assertEqual(merged["date"].tolist(), current["date"].tolist())

    def test_new_candidate_gets_initial_history_backfill(self):
        self.assertEqual(history_pages_for_candidate("NEW", {}), 3)

    def test_short_existing_history_gets_deeper_backfill(self):
        for symbol, rows in {"ET": 15, "HONA": 83, "SKHY": 75, "SPCX": 93}.items():
            with self.subTest(symbol=symbol):
                self.assertEqual(history_pages_for_candidate(symbol, {symbol: rows}), 5)

    def test_stage_ready_existing_history_gets_only_recent_page(self):
        self.assertEqual(history_pages_for_candidate("NVDA", {"NVDA": 300}), 1)

    def test_korean_listing_uses_domestic_provider(self):
        us_provider = Mock()
        korea_provider = Mock()
        bars = pd.DataFrame([{"date": "2026-10-23", "symbol": "005930", "close": 70000}])
        korea_provider.fetch_daily.return_value = bars
        row = SimpleNamespace(symbol="005930", market="South Korea", asset_type="stock", exchange="KRX")

        result, exchange = fetch_candidate_daily(row, us_provider, korea_provider)

        self.assertIs(result, bars)
        self.assertEqual(exchange, "KRX")
        korea_provider.fetch_daily.assert_called_once_with(
            "005930", market="South Korea", asset_type="stock", exchange="KRX", max_pages=3
        )
        us_provider.fetch_daily.assert_not_called()

    def test_us_listing_routes_by_exchange_not_issuer_country(self):
        us_provider = Mock()
        korea_provider = Mock()
        bars = pd.DataFrame([{"date": "2026-10-23", "symbol": "ASML", "close": 1000}])
        us_provider.fetch_daily.return_value = bars
        # Candidate issuer country can be non-US while the listing is US.
        row = SimpleNamespace(symbol="ASML", market="Netherlands", asset_type="stock", exchange="NAS")

        result, exchange = fetch_candidate_daily(row, us_provider, korea_provider, max_pages=1)

        self.assertIs(result, bars)
        self.assertEqual(exchange, "NAS")
        us_provider.fetch_daily.assert_called_once_with(
            "ASML", market="United States", asset_type="stock", exchange="NAS", max_pages=1
        )
        korea_provider.fetch_daily.assert_not_called()


if __name__ == "__main__":
    unittest.main()
