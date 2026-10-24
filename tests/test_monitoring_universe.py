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


    def test_stock_market_cap_metadata_is_explicit_and_etfs_are_not_cap_filtered(self):
        import pandas as pd

        path = Path(__file__).resolve().parents[1] / "data" / "monitoring_universe.csv"
        raw = pd.read_csv(path, dtype={"symbol": str}).fillna("")
        active = raw[raw["active"].astype(str).str.lower().eq("true")]
        stocks = active[active["asset_type"].eq("stock")]
        proxies = active[active["asset_type"].isin(["market_etf", "sector_etf", "commodity_etf"])]

        us_stocks = stocks[stocks["exchange"].isin(["NAS", "NYS", "AMS"])]
        krx_stocks = stocks[stocks["exchange"].eq("KRX")]
        self.assertTrue((us_stocks["market_cap_usd"].astype(str).str.strip() != "").all())
        self.assertTrue((us_stocks["market_cap_asof"].astype(str).str.strip() != "").all())
        self.assertTrue((us_stocks["sector_source"].astype(str).str.strip() != "").all())
        self.assertTrue((pd.to_numeric(us_stocks["market_cap_usd"], errors="coerce") > 0).all())
        self.assertTrue((us_stocks["market_cap_source_url"].astype(str).str.strip() != "").all())
        self.assertTrue(us_stocks["market_cap_source_url"].astype(str).str.contains("finhacker.cz").all())
        self.assertTrue((krx_stocks["market_cap_source_url"].astype(str).str.strip() == "").all())
        self.assertTrue((krx_stocks["market_cap_usd"].astype(str).str.strip() == "").all())
        self.assertTrue((krx_stocks["market_cap_asof"].astype(str).str.strip() == "").all())
        self.assertTrue(krx_stocks["sector_source"].astype(str).str.contains("USD FX conversion unverified").all())
        self.assertTrue((proxies["market_cap_usd"].astype(str).str.strip() == "").all())
        self.assertTrue((proxies["market_cap_asof"].astype(str).str.strip() == "").all())

    def test_korean_stock_symbols_keep_leading_zeroes(self):
        path = Path(__file__).resolve().parents[1] / "data" / "monitoring_universe.csv"
        universe = read_universe(path)
        symbols = set(universe["symbol"].astype(str))
        self.assertIn("005930", symbols)
        self.assertIn("000660", symbols)
        self.assertNotIn("5930", symbols)
        self.assertNotIn("660", symbols)


if __name__ == "__main__":
    unittest.main()
