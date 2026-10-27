import unittest
from pathlib import Path

import pandas as pd


class SectorCoverageMatrixTests(unittest.TestCase):
    def test_local_and_global_sector_scopes_are_distinguished(self):
        path = Path(__file__).resolve().parents[1] / "data" / "sector_coverage_matrix.csv"
        matrix = pd.read_csv(path, dtype=str).fillna("").set_index("country_or_region")
        self.assertEqual(matrix.loc["United States", "local_sector_coverage_status"], "local_sector_etfs_in_universe")
        self.assertEqual(matrix.loc["South Korea", "local_sector_coverage_status"], "partial_local_sector_coverage")
        self.assertEqual(matrix.loc["Japan", "local_sector_coverage_status"], "no_country_sector_proxy_approved")
        self.assertEqual(matrix.loc["Global", "local_sector_coverage_status"], "global_sector_etfs_in_universe")
        self.assertEqual(matrix.loc["Japan", "fallback_scope"], "Global")
        self.assertEqual(matrix.loc["Japan", "workstream_priority"], "parallel_research")
        self.assertEqual(matrix.loc["India", "local_sector_coverage_status"], "partial_us_listed_country_sector_proxy")
        self.assertEqual(matrix.loc["India", "us_listed_country_sector_proxy_symbols"], "INCO")
        self.assertEqual(matrix.loc["China", "local_sector_coverage_status"], "partial_us_listed_country_sector_proxy")
        self.assertEqual(matrix.loc["China", "us_listed_country_sector_proxy_symbols"], "KWEB;CQQQ")
        self.assertTrue(matrix["market_proxy_symbol"].ne("").all())
        self.assertTrue(matrix["notes"].ne("").all())
        universe_path = Path(__file__).resolve().parents[1] / "data" / "monitoring_universe.csv"
        universe = pd.read_csv(universe_path, dtype={"symbol": str}).set_index("symbol")
        self.assertEqual(universe.loc["INCO", "asset_type"], "sector_etf")
        self.assertEqual(universe.loc["INCO", "market"], "India")
        self.assertEqual(universe.loc["INCO", "market_benchmark"], "INDA")
        self.assertEqual(universe.loc["KWEB", "market"], "China")
        self.assertEqual(universe.loc["KWEB", "market_benchmark"], "MCHI")
        self.assertEqual(universe.loc["CQQQ", "market"], "China")
        self.assertEqual(universe.loc["CQQQ", "market_benchmark"], "MCHI")


if __name__ == "__main__":
    unittest.main()
