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

    def test_japan_sector_coverage_stays_partial_until_rights_review(self):
        row = self.coverage[self.coverage["country_or_region"].eq("Japan")]
        self.assertEqual(len(row), 1)
        self.assertEqual(row.iloc[0]["local_sector_coverage_status"],
                         "partial_local_sector_coverage")
        self.assertIn("data-use rights review remains pending", row.iloc[0]["notes"])
        plan_path = ROOT / "data" / "global_sector_expansion_plan.csv"
        plan = pd.read_csv(plan_path, dtype=str).fillna("")
        japan_plan = plan[plan["country_or_region"].eq("Japan")]
        self.assertEqual(len(japan_plan), 1)
        self.assertEqual(
            japan_plan.iloc[0]["coverage_status"],
            "local_price_history_confirmed_mapping_and_rights_review_pending",
        )

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

    def test_active_assets_have_resolvable_benchmark_symbols(self):
        active = self.universe[
            self.universe["active"].astype(str).str.lower().isin({"true", "1", "yes"})
        ]
        available_symbols = set(self.universe["symbol"].astype(str).str.upper())
        missing = []
        for row in active.itertuples(index=False):
            for field in ("market_benchmark", "sector_benchmark"):
                benchmark = str(getattr(row, field, "")).strip().upper()
                if benchmark and benchmark not in available_symbols:
                    missing.append((str(row.symbol), field, benchmark))
        self.assertEqual(
            missing, [],
            "Active universe rows reference benchmark symbols absent from the monitoring universe.",
        )

    def test_active_commodity_etfs_use_their_own_price_series_as_benchmarks(self):
        commodities = self.universe[
            self.universe["active"].astype(str).str.lower().isin({"true", "1", "yes"})
            & self.universe["asset_type"].eq("commodity_etf")
        ]
        self.assertGreaterEqual(len(commodities), 10)
        # Relative strength is measured against the broad market; commodity-specific
        # comparison uses the commodity ETF's own price series as its sector benchmark.
        self.assertTrue(commodities["market_benchmark"].astype(str).str.upper().eq("SPY").all())
        self.assertTrue(commodities["sector_benchmark"].astype(str).str.upper().eq(
            commodities["symbol"].astype(str).str.upper()
        ).all())

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
