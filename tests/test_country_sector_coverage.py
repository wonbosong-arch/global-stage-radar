"""Regression checks for country/sector coverage and instrument routing."""
from pathlib import Path
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_PATH = ROOT / "data" / "monitoring_universe.csv"
COVERAGE_PATH = ROOT / "data" / "sector_coverage_matrix.csv"


class CountrySectorCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.universe = pd.read_csv(UNIVERSE_PATH, dtype={"symbol": str}).fillna("")
        cls.coverage = pd.read_csv(COVERAGE_PATH, dtype=str).fillna("")

    def test_japan_local_sector_etfs_use_japan_market_benchmark(self):
        japan = self.universe[
            self.universe["country"].eq("Japan")
            & self.universe["asset_type"].eq("sector_etf")
        ]
        self.assertGreaterEqual(len(japan), 19)
        self.assertTrue(japan["market_benchmark"].eq("EWJ").all())
        self.assertTrue(japan["sector_benchmark"].eq("EWJ").all())
        self.assertTrue(japan["exchange"].eq("TSE").all())

    def test_china_us_listed_proxies_are_not_mislabeled_as_local_listings(self):
        expected = {"KWEB", "CQQQ", "CHIQ"}
        china = self.universe[self.universe["symbol"].isin(expected)]
        self.assertEqual(set(china["symbol"]), expected)
        self.assertTrue(china["country"].eq("China").all())
        self.assertTrue(china["market_benchmark"].eq("MCHI").all())
        self.assertTrue(china["exchange"].isin(["NYS", "NAS", "AMS"]).all())
        row = self.coverage[self.coverage["country_or_region"].eq("China")].iloc[0]
        self.assertEqual(row["local_sector_coverage_status"], "partial_us_listed_country_sector_proxy")

    def test_china_mainland_candidates_remain_inactive_until_reviewed(self):
        expected = {
            "512010", "512200", "512400", "512600", "512720",
            "512760", "512800", "512880", "512980", "515030",
        }
        candidates = self.universe[self.universe["symbol"].isin(expected)]
        self.assertEqual(set(candidates["symbol"]), expected)
        self.assertTrue(candidates["exchange"].eq("SHS").all())
        self.assertTrue(candidates["market_benchmark"].eq("MCHI").all())
        self.assertTrue(candidates["sector_benchmark"].eq("MCHI").all())
        self.assertTrue(candidates["active"].astype(str).str.lower().eq("false").all())

    def test_crypto_assets_use_coinbase_not_kis_routing(self):
        crypto = self.universe[self.universe["symbol"].isin(["BTC", "ETH"])]
        self.assertEqual(set(crypto["symbol"]), {"BTC", "ETH"})
        self.assertTrue(crypto["provider"].eq("Coinbase").all())
        self.assertTrue(crypto["asset_type"].eq("crypto_asset").all())

    def test_japan_and_china_are_marked_core_priority(self):
        for country in ("Japan", "China"):
            row = self.coverage[self.coverage["country_or_region"].eq(country)]
            self.assertEqual(len(row), 1)
            self.assertEqual(row.iloc[0]["workstream_priority"], "core")


if __name__ == "__main__":
    unittest.main()
