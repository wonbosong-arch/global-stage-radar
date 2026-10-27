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
        self.assertTrue(matrix["market_proxy_symbol"].ne("").all())
        self.assertTrue(matrix["notes"].ne("").all())


if __name__ == "__main__":
    unittest.main()
