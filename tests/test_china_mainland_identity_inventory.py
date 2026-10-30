"""Regression checks for research-only mainland China ETF identity inventory."""
import csv
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(relative_path):
    with (ROOT / relative_path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class ChinaIdentityInventoryTests(unittest.TestCase):
    def test_identity_inventory_matches_observed_symbols(self):
        observed = read_csv("research/china_mainland_30_etf_ohlcv_structure_audit.csv")
        previous = read_csv("data/china_candidate_official_identity_review.csv")
        new = read_csv("research/china_mainland_12_sse_identity_evidence.csv")
        agriculture = read_csv("research/china_mainland_etf_verified_identity.csv")
        observed_symbols = [row["symbol"] for row in observed]
        identified = [row["symbol"] for rows in (previous, new, agriculture) for row in rows]
        self.assertEqual(len(observed_symbols), 30)
        self.assertEqual(len(observed_symbols), len(set(observed_symbols)))
        self.assertEqual(len(identified), len(set(identified)), "Duplicate identity records")
        self.assertEqual(set(observed_symbols), set(identified), "Identity coverage mismatch")

    def test_no_research_candidate_is_activated(self):
        new = read_csv("research/china_mainland_12_sse_identity_evidence.csv")
        self.assertTrue(new)
        for row in new:
            with self.subTest(symbol=row["symbol"]):
                self.assertEqual(row["activation_status"], "inactive_research_only")
                self.assertEqual(row["index_methodology"], "pending")
                self.assertTrue(row["source_url"].startswith("https://"))
        agriculture = read_csv("research/china_mainland_etf_verified_identity.csv")
        self.assertEqual(len(agriculture), 1)
        self.assertEqual(agriculture[0]["active"].lower(), "false")

    def test_structure_audit_does_not_claim_full_price_validation(self):
        for row in read_csv("research/china_mainland_30_etf_ohlcv_structure_audit.csv"):
            with self.subTest(symbol=row["symbol"]):
                self.assertEqual(row["structure_check"], "pass")
                self.assertEqual(int(row["rows"]), int(row["unique_dates"]))
                for field in ("duplicate_dates", "ohlc_violations", "nonpositive_price_rows", "invalid_volume_rows", "nonmonotonic_date_rows"):
                    self.assertEqual(int(row[field]), 0)


if __name__ == "__main__":
    unittest.main()
