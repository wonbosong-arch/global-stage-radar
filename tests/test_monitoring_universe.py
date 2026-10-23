import unittest
from pathlib import Path

from universe import read_universe


class MonitoringUniverseTests(unittest.TestCase):
    def test_default_universe_contains_global_etf_proxies_and_krx_samples(self):
        path = Path(__file__).resolve().parents[1] / "data" / "monitoring_universe.csv"
        universe = read_universe(path)
        self.assertGreaterEqual(len(universe), 30)
        self.assertIn("QQQ", set(universe["symbol"]))
        self.assertIn("SPY", set(universe["symbol"]))
        self.assertIn("EWJ", set(universe["symbol"]))
        self.assertIn("GLD", set(universe["symbol"]))
        self.assertIn("069500", set(universe["symbol"]))
        self.assertIn("KRX", set(universe["exchange"]))
        self.assertIn("NVDA", set(universe["symbol"]))
        self.assertIn("005930", set(universe["symbol"]))
        self.assertTrue(
            set(universe["asset_type"]).issubset(
                {"market_etf", "sector_etf", "commodity_etf", "stock"}
            )
        )

    def test_all_benchmark_symbols_are_in_default_universe(self):
        path = Path(__file__).resolve().parents[1] / "data" / "monitoring_universe.csv"
        universe = read_universe(path)
        symbols = set(universe["symbol"])
        self.assertTrue(set(universe["market_benchmark"]).issubset(symbols))
        self.assertTrue(set(universe["sector_benchmark"]).issubset(symbols))


if __name__ == "__main__":
    unittest.main()
