"""Regression guards for mainland China ETF review metadata.

These checks do not activate candidates or fetch prices.
"""
import csv
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with (ROOT / path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class ChinaSectorReviewRegistryTest(unittest.TestCase):
    def test_review_csv_has_exactly_nine_columns_per_record(self):
        with (ROOT / "data/country_sector_proxy_candidates.csv").open(
            encoding="utf-8-sig", newline=""
        ) as handle:
            reader = csv.reader(handle)
            expected = len(next(reader))
            self.assertEqual(9, expected)
            for row in reader:
                with self.subTest(row_number=reader.line_num):
                    self.assertEqual(expected, len(row))

    def test_512600_manager_agrees_between_registries(self):
        universe = {row["symbol"]: row for row in read_csv("data/monitoring_universe.csv")}
        candidates = {row["symbol"]: row for row in read_csv("data/country_sector_proxy_candidates.csv")}
        self.assertIn("512600", universe)
        self.assertIn("512600", candidates)
        self.assertIn("Harvest", universe["512600"]["name"])
        self.assertIn("Harvest", candidates["512600"]["instrument_scope"])
        self.assertNotIn("ChinaAMC", candidates["512600"]["instrument_scope"])

    def test_mainland_review_universe_stays_inactive(self):
        rows = read_csv("data/monitoring_universe.csv")
        mainland = [row for row in rows if row["country"] == "China" and row["exchange"] == "SHS"]
        self.assertEqual(30, len(mainland))
        self.assertEqual(30, len({row["symbol"] for row in mainland}))
        self.assertTrue(all(row["active"].lower() == "false" for row in mainland))


if __name__ == "__main__":
    unittest.main()
