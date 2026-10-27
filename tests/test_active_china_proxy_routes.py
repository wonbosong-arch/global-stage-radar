import unittest
from pathlib import Path

import pandas as pd

from data_providers import KISUSProvider


class FakeClient:
    def __init__(self):
        self.calls = []

    def daily_bars(self, symbol, exchange="NAS", max_pages=5):
        self.calls.append((symbol, exchange, max_pages))
        return pd.DataFrame([{
            "date": "2026-10-27", "symbol": symbol, "open": 100,
            "high": 105, "low": 99, "close": 104, "volume": 12345,
        }])


class ActiveChinaProxyRouteTests(unittest.TestCase):
    def test_active_us_listed_china_proxies_use_us_exchange_routes(self):
        root = Path(__file__).resolve().parents[1]
        universe = pd.read_csv(root / "data" / "monitoring_universe.csv", dtype=str).fillna("")
        active = universe[
            universe["market"].str.strip().str.lower().eq("china")
            & universe["symbol"].str.strip().str.upper().isin({"MCHI", "KWEB", "CQQQ", "CHIQ"})
            & universe["active"].str.strip().str.lower().eq("true")
        ]
        expected = {
            "MCHI": ("market_etf", "NYS"),
            "KWEB": ("sector_etf", "NYS"),
            "CQQQ": ("sector_etf", "NYS"),
            "CHIQ": ("sector_etf", "AMS"),
        }
        self.assertEqual(set(active["symbol"].str.upper()), set(expected))
        for _, row in active.iterrows():
            symbol = row["symbol"].strip().upper()
            asset_type, exchange = expected[symbol]
            with self.subTest(symbol=symbol):
                self.assertEqual(row["asset_type"], asset_type)
                self.assertEqual(row["exchange"].strip().upper(), exchange)
                client = FakeClient()
                result = KISUSProvider(client).fetch_daily(
                    symbol, row["market"], row["asset_type"], row["exchange"], max_pages=2
                )
                self.assertEqual(len(result), 1)
                self.assertEqual(client.calls, [(symbol, exchange, 2)])


if __name__ == "__main__":
    unittest.main()
