import unittest
import pandas as pd

from data_providers import KISUSProvider


class FakeClient:
    def __init__(self):
        self.calls = []

    def daily_bars(self, symbol, exchange="NAS", max_pages=5):
        self.calls.append((symbol, exchange, max_pages))
        return pd.DataFrame([{
            "date": "2026-10-20", "symbol": symbol, "open": 100,
            "high": 105, "low": 99, "close": 104, "volume": 12345,
        }])


class ProviderAdapterTests(unittest.TestCase):
    def test_kis_provider_supports_us_stocks_and_etfs(self):
        provider = KISUSProvider(FakeClient())
        self.assertTrue(provider.supports("United States", "stock"))
        self.assertTrue(provider.supports("US", "market_etf"))
        self.assertTrue(provider.supports("US", "commodity_etf"))
        self.assertTrue(provider.supports("미국", "sector_etf"))

    def test_kis_provider_does_not_claim_global_or_commodity_coverage(self):
        provider = KISUSProvider(FakeClient())
        self.assertFalse(provider.supports("South Korea", "stock"))
        self.assertFalse(provider.supports("Japan", "stock"))
        self.assertFalse(provider.supports("Commodities", "commodity"))

    def test_fetch_returns_normalized_ohlcv(self):
        client = FakeClient()
        provider = KISUSProvider(client)
        result = provider.fetch_daily("aapl", "United States", "stock", "NAS", max_pages=3)
        self.assertEqual(result.iloc[0]["symbol"], "AAPL")
        self.assertEqual(client.calls, [("aapl", "NAS", 3)])

    def test_unsupported_asset_is_rejected_before_fetch(self):
        client = FakeClient()
        provider = KISUSProvider(client)
        with self.assertRaisesRegex(ValueError, "does not support"):
            provider.fetch_daily("005930", "South Korea", "stock", "NAS")
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
