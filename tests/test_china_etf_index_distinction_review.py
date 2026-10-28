import unittest
from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "data" / "china_etf_index_distinction_review.csv"


class ChinaETFIndexDistinctionReviewTests(unittest.TestCase):
    def test_review_keeps_all_candidates_inactive(self):
        review = pd.read_csv(REVIEW_PATH, dtype={"symbol": str, "index_code": str})
        self.assertEqual(set(review["symbol"]), {"512700", "512800", "512010", "512170", "512480", "512760"})
        self.assertTrue(review["activation_status"].eq("inactive_research_only").all())

    def test_bank_pair_is_same_underlying_index(self):
        review = pd.read_csv(REVIEW_PATH, dtype={"symbol": str, "index_code": str}).set_index("symbol")
        self.assertEqual(review.loc["512700", "index_code"], review.loc["512800", "index_code"])
        self.assertEqual(review.loc["512700", "underlying_index"], review.loc["512800", "underlying_index"])

    def test_healthcare_and_semiconductor_pairs_are_not_labelled_as_same_index(self):
        review = pd.read_csv(REVIEW_PATH, dtype={"symbol": str, "index_code": str}).set_index("symbol")
        for left, right in [("512010", "512170"), ("512480", "512760")]:
            self.assertNotEqual(review.loc[left, "index_code"], review.loc[right, "index_code"])
            self.assertNotEqual(review.loc[left, "underlying_index"], review.loc[right, "underlying_index"])

    def test_every_row_records_remaining_checks_and_source(self):
        review = pd.read_csv(REVIEW_PATH, dtype={"symbol": str})
        self.assertTrue(review["source_url"].fillna("").str.startswith("http").all())
        self.assertTrue(review["remaining_checks"].fillna("").str.len().gt(20).all())


if __name__ == "__main__":
    unittest.main()
