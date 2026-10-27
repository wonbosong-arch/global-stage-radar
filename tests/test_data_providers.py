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

    def test_kis_provider_supports_us_listed_global_and_commodity_etf_proxies(self):
        provider = KISUSProvider(FakeClient())
        self.assertTrue(provider.supports("Japan", "market_etf"))
        self.assertTrue(provider.supports("India", "market_etf"))
        self.assertTrue(provider.supports("Commodities", "commodity_etf"))
        self.assertTrue(provider.supports("United States", "sector_etf"))
        self.assertFalse(provider.supports("South Korea", "stock"))
        self.assertFalse(provider.supports("Japan", "stock"))
        self.assertFalse(provider.supports("Commodities", "commodity"))

    def test_japan_local_sector_etf_uses_tse_route(self):
        client = FakeClient()
        provider = KISUSProvider(client)
        self.assertTrue(provider.supports("Japan", "sector_etf"))
        result = provider.fetch_daily(
            "2644", "Japan", "sector_etf", "TSE", max_pages=2
        )
        self.assertEqual(result.iloc[0]["symbol"], "2644")
        self.assertEqual(client.calls, [("2644", "TSE", 2)])

    def test_alphanumeric_japan_etf_ticker_uses_tse_route(self):
        client = FakeClient()
        provider = KISUSProvider(client)
        result = provider.fetch_daily(
            "213A", "Japan", "sector_etf", "TSE", max_pages=2
        )
        self.assertEqual(result.iloc[0]["symbol"], "213A")
        self.assertEqual(client.calls, [("213A", "TSE", 2)])

    def test_china_local_sector_etf_uses_shs_route(self):
        client = FakeClient()
        provider = KISUSProvider(client)
        self.assertTrue(provider.supports("China", "sector_etf"))
        result = provider.fetch_daily(
            "512800", "China", "sector_etf", "SHS", max_pages=2
        )
        self.assertEqual(result.iloc[0]["symbol"], "512800")
        self.assertEqual(client.calls, [("512800", "SHS", 2)])

    def test_us_listed_china_etf_uses_us_route_despite_china_exposure(self):
        client = FakeClient()
        provider = KISUSProvider(client)
        result = provider.fetch_daily(
            "MCHI", "China", "market_etf", "NYS", max_pages=2
        )
        self.assertEqual(result.iloc[0]["symbol"], "MCHI")
        self.assertEqual(client.calls, [("MCHI", "NYS", 2)])

    def test_us_listed_japan_sector_proxy_uses_us_route(self):
        client = FakeClient()
        provider = KISUSProvider(client)
        result = provider.fetch_daily(
            "EWJ", "Japan", "market_etf", "NYS", max_pages=2
        )
        self.assertEqual(result.iloc[0]["symbol"], "EWJ")
        self.assertEqual(client.calls, [("EWJ", "NYS", 2)])

    def test_china_local_etf_rejects_us_exchange_code(self):
        client = FakeClient()
        provider = KISUSProvider(client)
        with self.assertRaisesRegex(ValueError, "exchange=SHS or exchange=SZS"):
            provider.fetch_daily("512800", "China", "sector_etf", "NYS")
        self.assertEqual(client.calls, [])

    def test_japan_local_sector_etf_rejects_us_exchange_code(self):
        client = FakeClient()
        provider = KISUSProvider(client)
        with self.assertRaisesRegex(ValueError, "exchange=TSE"):
            provider.fetch_daily("2644", "Japan", "sector_etf", "NYS")
        self.assertEqual(client.calls, [])

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


    def test_etf_retries_other_kis_exchanges_when_requested_exchange_is_empty(self):
        class ExchangeAwareClient:
            def __init__(self):
                self.calls = []

            def daily_bars(self, symbol, exchange="NAS", max_pages=5):
                self.calls.append(exchange)
                if exchange == "AMS":
                    return pd.DataFrame([{
                        "date": "2026-10-20", "symbol": symbol, "open": 100,
                        "high": 105, "low": 99, "close": 104, "volume": 12345,
                    }])
                return pd.DataFrame(columns=[
                    "date", "symbol", "open", "high", "low", "close", "volume"
                ])

        client = ExchangeAwareClient()
        provider = KISUSProvider(client)
        result = provider.fetch_daily(
            "SPY", "United States", "market_etf", "NYS", max_pages=3
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(client.calls, ["NYS", "AMS"])

    def test_stock_does_not_silently_fallback_to_another_exchange(self):
        class EmptyClient:
            def daily_bars(self, symbol, exchange="NAS", max_pages=5):
                return pd.DataFrame(columns=[
                    "date", "symbol", "open", "high", "low", "close", "volume"
                ])

        provider = KISUSProvider(EmptyClient())
        result = provider.fetch_daily(
            "AAPL", "United States", "stock", "NAS", max_pages=1
        )
        self.assertTrue(result.empty)


    def test_kis_ohlc_cleanup_drops_only_inconsistent_rows(self):
        from kis_provider import _drop_invalid_ohlc_rows

        frame = pd.DataFrame([
            {"date": "2026-10-19", "symbol": "XLC", "open": 100, "high": 105,
             "low": 99, "close": 104, "volume": 1000},
            {"date": "2026-10-20", "symbol": "XLC", "open": 100, "high": 98,
             "low": 99, "close": 101, "volume": 1200},
            {"date": "2026-10-21", "symbol": "XLC", "open": 104, "high": 108,
             "low": 103, "close": 107, "volume": 1500},
        ])
        cleaned = _drop_invalid_ohlc_rows(frame)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned["date"].tolist(), ["2026-10-19", "2026-10-21"])

if __name__ == "__main__":
    unittest.main()
