import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd

from refresh_candidate_prices import fetch_candidate_daily


class CandidateProviderRoutingTests(unittest.TestCase):
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
