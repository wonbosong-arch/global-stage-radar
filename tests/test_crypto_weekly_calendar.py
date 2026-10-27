import unittest

import pandas as pd

from stage_engine import weekly_bars
from universe import read_universe


class CryptoWeeklyCalendarTests(unittest.TestCase):
    def test_crypto_week_ends_sunday_and_is_complete_on_monday(self):
        dates = pd.date_range("2025-01-01", "2026-10-25", freq="D")
        frame = pd.DataFrame({
            "date": dates,
            "symbol": "BTC",
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": [100.0 + i * 0.1 for i in range(len(dates))],
            "volume": 1000.0,
        })
        result = weekly_bars(frame, as_of_date="2026-10-26", calendar_name="CRYPTO", min_bars=35)
        self.assertIsNotNone(result)
        self.assertEqual(pd.Timestamp(result.iloc[-1]["date"]).weekday(), 6)
        self.assertEqual(pd.Timestamp(result.iloc[-1]["date"]).date().isoformat(), "2026-10-25")

    def test_missing_sunday_source_does_not_count_as_completed_week(self):
        dates = pd.date_range("2025-01-01", "2026-10-24", freq="D")
        frame = pd.DataFrame({
            "date": dates,
            "symbol": "BTC",
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": [100.0 + i * 0.1 for i in range(len(dates))],
            "volume": 1000.0,
        })
        result = weekly_bars(frame, as_of_date="2026-10-26", calendar_name="CRYPTO", min_bars=35)
        self.assertIsNotNone(result)
        self.assertLess(pd.Timestamp(result.iloc[-1]["date"]), pd.Timestamp("2026-10-25"))

    def test_current_sunday_crypto_bar_is_not_used_on_sunday(self):
        dates = pd.date_range("2025-01-01", "2026-10-25", freq="D")
        frame = pd.DataFrame({
            "date": dates,
            "symbol": "ETH",
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": [100.0 + i * 0.1 for i in range(len(dates))],
            "volume": 1000.0,
        })
        result = weekly_bars(frame, as_of_date="2026-10-25", calendar_name="CRYPTO", min_bars=35)
        self.assertIsNotNone(result)
        self.assertLess(pd.Timestamp(result.iloc[-1]["date"]), pd.Timestamp("2026-10-25"))


class CryptoUniverseTests(unittest.TestCase):
    def test_btc_eth_are_enabled_as_separate_crypto_assets(self):
        universe = read_universe("data/monitoring_universe.csv")
        crypto = universe[universe["exchange"].eq("CRYPTO")].set_index("symbol")
        self.assertEqual(set(crypto.index), {"BTC", "ETH"})
        self.assertTrue(crypto["asset_type"].eq("crypto_asset").all())
        self.assertEqual(crypto.loc["ETH", "market_benchmark"], "BTC")
        self.assertEqual(crypto.loc["BTC", "market_benchmark"], "BTC")


if __name__ == "__main__":
    unittest.main()
