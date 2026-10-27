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
        self.assertTrue(
            set(universe["asset_type"]).issubset(
                {"market_etf", "sector_etf", "commodity_etf"}
            )
        )

    def test_all_benchmark_symbols_are_in_default_universe(self):
        path = Path(__file__).resolve().parents[1] / "data" / "monitoring_universe.csv"
        universe = read_universe(path)
        symbols = set(universe["symbol"])
        self.assertTrue(set(universe["market_benchmark"]).issubset(symbols))
        self.assertTrue(set(universe["sector_benchmark"]).issubset(symbols))

    def test_country_commodity_and_sector_coverage_are_explicit(self):
        path = Path(__file__).resolve().parents[1] / "data" / "monitoring_universe.csv"
        universe = read_universe(path)
        market_symbols = set(universe.loc[universe["asset_type"].eq("market_etf"), "symbol"])
        commodity_symbols = set(universe.loc[universe["asset_type"].isin(["commodity_etf", "commodity"]), "symbol"])
        sector_symbols = set(universe.loc[universe["asset_type"].eq("sector_etf"), "symbol"])

        # Market proxies cover the US plus major regional/country exposures.
        self.assertTrue({"SPY", "ACWI", "EWC", "VGK", "EWJ", "EWY", "EWT", "EWH", "INDA", "MCHI", "EWZ", "EWA", "EWW", "EWU", "EWG", "EWQ", "EWL", "EWS", "EIDO", "EZA", "069500"}.issubset(market_symbols))
        # Liquid commodity proxies are tracked separately from market and sector ETFs.
        self.assertTrue({"GLD", "SLV", "USO", "UNG", "CPER", "DBA", "DBB", "PDBC", "PPLT", "CORN", "WEAT", "SOYB"}.issubset(commodity_symbols))
        # The 11 broad US sector sleeves are present; semiconductor ETFs are additional specialist proxies.
        self.assertTrue({"XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"}.issubset(sector_symbols))
        self.assertTrue({"SOXX", "SMH"}.issubset(sector_symbols))
        self.assertTrue({"IXN", "IXC", "IXG", "IXJ", "EXI", "RXI", "KXI", "MXI", "JXI", "IXP", "REET"}.issubset(sector_symbols))
        self.assertTrue({"091160", "091180", "091170", "102970", "117680", "117700", "140700", "305720", "244580"}.issubset(sector_symbols))


if __name__ == "__main__":
    unittest.main()
