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
        previous = read_csv("data/china_candidate_official_identity_review.csv")
        for row in previous:
            with self.subTest(existing_symbol=row["symbol"]):
                self.assertEqual(row["activation_status"], "inactive_research_only")
                self.assertIsNone(row.get(None), "Malformed CSV field overflow")
                self.assertTrue(row["source_url"].startswith("https://"))
                self.assertTrue(row["identity_status"].startswith("verified_"))
        agriculture = read_csv("research/china_mainland_etf_verified_identity.csv")
        self.assertEqual(len(agriculture), 1)
        self.assertEqual(agriculture[0]["active"].lower(), "false")

    def test_china_etf_promotion_gates_are_closed(self):
        rows = read_csv("research/china_etf_promotion_gates.csv")
        expected = {"512800", "512700", "512010", "512170", "512480", "512760"}
        self.assertEqual({row["symbol"] for row in rows}, expected)
        self.assertEqual(len(rows), len(expected))
        for row in rows:
            with self.subTest(symbol=row["symbol"]):
                self.assertIsNone(row.get(None), "Malformed promotion gate CSV")
                self.assertEqual(row["activate"].lower(), "false")
                self.assertTrue(row["primary_source_url"].startswith("https://"))
                for field in ("broker_tradability_verified", "adjusted_prices_verified", "data_rights_verified"):
                    self.assertEqual(row[field].lower(), "false")
        banks = {row["symbol"]: row for row in rows if row["scope"] == "banks"}
        self.assertEqual(banks["512800"]["decision"], "research_preferred_duplicate_bank_proxy")
        self.assertEqual(banks["512700"]["decision"], "hold_duplicate")

    def test_primary_source_mapping_has_no_csv_overflow(self):
        for path in (
            "research/china_bank_etf_issuer_verification.csv",
            "research/china_healthcare_etf_official_index_mapping.csv",
            "research/china_semiconductor_index_evidence_queue.csv",
            "research/china_index_official_methodology_evidence.csv",
        ):
            rows = read_csv(path)
            self.assertTrue(rows, path)
            for row in rows:
                with self.subTest(path=path, symbol=row.get("symbol", row.get("index_code"))):
                    self.assertIsNone(row.get(None), "Malformed CSV field overflow")
                    self.assertTrue(any(value.startswith("https://") for value in row.values() if isinstance(value, str)))

    def test_historical_broker_eligibility_is_not_current_orderability(self):
        rows = read_csv("research/china_etf_korean_broker_eligibility_2022.csv")
        self.assertEqual({row["symbol"] for row in rows}, {"512700", "512800", "512010", "512170", "512480", "512760"})
        self.assertEqual(len(rows), 6)
        for row in rows:
            with self.subTest(symbol=row["symbol"]):
                self.assertIsNone(row.get(None), "Malformed broker eligibility CSV")
                self.assertEqual(row["listed_in_2022_eligible_universe"], "true")
                self.assertEqual(row["current_orderability_verified"], "false")
                self.assertEqual(row["production_active"], "false")
                self.assertTrue(row["broker_document_url"].startswith("https://"))

    def test_512480_issuer_uses_recent_sse_prospectus(self):
        rows = read_csv("data/china_candidate_official_identity_review.csv")
        matches = [row for row in rows if row["symbol"] == "512480"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["issuer"], "Guolianan Fund Management")

    def test_structure_audit_does_not_claim_full_price_validation(self):
        for row in read_csv("research/china_mainland_30_etf_ohlcv_structure_audit.csv"):
            with self.subTest(symbol=row["symbol"]):
                self.assertEqual(row["structure_check"], "pass")
                self.assertEqual(int(row["rows"]), int(row["unique_dates"]))
                for field in ("duplicate_dates", "ohlc_violations", "nonpositive_price_rows", "invalid_volume_rows", "nonmonotonic_date_rows"):
                    self.assertEqual(int(row[field]), 0)


if __name__ == "__main__":
    unittest.main()
