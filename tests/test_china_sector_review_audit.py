"""Cross-file audit of the 30 mainland China ETF review candidates.

Run: python -m unittest tests.test_china_sector_review_audit
No API calls; no activation changes.
"""
import csv
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def records(path):
    with (ROOT / path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def mainland():
    return [r for r in records("data/monitoring_universe.csv")
            if r["country"] == "China" and r["exchange"] == "SHS"]


def review_rows():
    return [r for r in records("data/country_sector_proxy_candidates.csv")
            if r["country"] == "China" and
            "Shanghai Stock Exchange" in r["listing_market"]]


class MainlandChinaAuditTest(unittest.TestCase):
    def test_mainland_symbols_are_unique_and_inactive(self):
        rows = mainland()
        self.assertEqual(30, len(rows))
        self.assertEqual(30, len({r["symbol"] for r in rows}))
        self.assertTrue(all(r["active"].lower() == "false" for r in rows))

    def test_registered_review_symbols_belong_to_universe(self):
        symbols = {r["symbol"] for r in mainland()}
        registered = review_rows()
        self.assertEqual(len(registered), len({r["symbol"] for r in registered}))
        self.assertFalse({r["symbol"] for r in registered} - symbols)

    def test_all_mainland_candidates_have_market_benchmark(self):
        for row in mainland():
            with self.subTest(symbol=row["symbol"]):
                self.assertEqual("MCHI", row["market_benchmark"])
                self.assertEqual("ETF", row["instrument_type"])

    def test_no_delisted_china_etfs_active(self):
        rejected = {r["symbol"] for r in records("data/country_sector_proxy_candidates.csv")
                    if r["country"] == "China" and
                    r["dashboard_status"] == "rejected_delisted"}
        active = {r["symbol"] for r in records("data/monitoring_universe.csv")
                  if r["active"].lower() == "true"}
        self.assertFalse(rejected & active)

    def test_review_registry_gap_is_explicitly_known(self):
        # Deliberately document a review-only gap; don't equate it with missing OHLCV.
        known = {
            "512580", "512660", "512690", "512620", "515050",
            "515220", "515120", "512480", "512700", "512170",
            "515070", "515210", "516150", "516160", "516970",
            "515880", "512290", "515170", "515650", "515790",
        }
        observed = {r["symbol"] for r in mainland()} - {
            r["symbol"] for r in review_rows()
        }
        self.assertEqual(known, observed)


if __name__ == "__main__":
    unittest.main()
