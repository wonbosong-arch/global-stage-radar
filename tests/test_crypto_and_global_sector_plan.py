import csv
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CryptoAssetRegistryTests(unittest.TestCase):
    def test_bitcoin_and_ethereum_are_registered_without_stock_cap_filter(self):
        path = ROOT / "data" / "crypto_asset_registry.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        by_symbol = {row["symbol"]: row for row in rows}
        self.assertTrue({"BTC", "ETH"}.issubset(by_symbol))
        for symbol in ("BTC", "ETH"):
            row = by_symbol[symbol]
            self.assertEqual(row["asset_class"], "crypto_asset")
            self.assertEqual(row["currency"], "USD")
            self.assertEqual(row["market_cap_filter"], "false")
            self.assertEqual(row["activation_status"], "metadata_only_not_active")
            self.assertTrue(row["provider_symbol"])
            self.assertTrue(row["primary_data_source"])

    def test_crypto_registry_does_not_duplicate_symbols(self):
        path = ROOT / "data" / "crypto_asset_registry.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        symbols = [row["symbol"] for row in rows]
        self.assertEqual(len(symbols), len(set(symbols)))


class GlobalSectorExpansionPlanTests(unittest.TestCase):
    def test_plan_separates_core_and_parallel_regional_work(self):
        path = ROOT / "data" / "global_sector_expansion_plan.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        countries = {row["country_or_region"] for row in rows}
        workstreams = {row["parallel_workstream"] for row in rows}
        self.assertTrue({"United States", "South Korea", "Japan", "United Kingdom",
                         "Canada", "Taiwan", "India", "China", "Brazil", "Australia",
                         "Europe", "Global", "Other major markets"}.issubset(countries))
        self.assertIn("core_sector_mapping", workstreams)
        self.assertIn("regional_sector_research", workstreams)
        self.assertTrue(all(row["acceptance_criteria"].strip() for row in rows))
        self.assertTrue(all(row["coverage_status"].strip() for row in rows))


if __name__ == "__main__":
    unittest.main()
