import unittest
from datetime import datetime, timezone

import pandas as pd

from crypto_provider import CoinbaseCryptoProvider, CryptoProviderError


class FakeResponse:
    def __init__(self, payload, error=None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise RuntimeError(self.error)

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


class CoinbaseCryptoProviderTests(unittest.TestCase):
    def test_fetches_and_normalizes_btc_daily_candles(self):
        # Coinbase candle order is [time, low, high, open, close, volume].
        session = FakeSession([FakeResponse([
            [1792800000, 90, 110, 95, 105, 1234],
            [1792713600, 80, 100, 90, 95, 1000],
        ])])
        provider = CoinbaseCryptoProvider(session=session)
        result = provider.fetch_daily(
            "BTC", days=2, end=datetime(2026, 10, 25, tzinfo=timezone.utc)
        )
        self.assertEqual(set(result.columns), {"date", "symbol", "open", "high", "low", "close", "volume"})
        self.assertEqual(set(result["symbol"]), {"BTC"})
        self.assertTrue(result["date"].is_monotonic_increasing)
        self.assertTrue((result["high"] >= result["low"]).all())
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.calls[0][1]["params"]["granularity"], 86400)

    def test_rejects_symbols_not_in_crypto_registry(self):
        provider = CoinbaseCryptoProvider(session=FakeSession([]))
        with self.assertRaises(ValueError):
            provider.fetch_daily("DOGE", days=30)

    def test_wraps_http_failures_as_provider_errors(self):
        provider = CoinbaseCryptoProvider(session=FakeSession([
            FakeResponse([], error="rate limited")
        ]))
        with self.assertRaises(CryptoProviderError):
            provider.fetch_daily(
                "ETH", days=2, end=datetime(2026, 10, 25, tzinfo=timezone.utc)
            )


if __name__ == "__main__":
    unittest.main()
