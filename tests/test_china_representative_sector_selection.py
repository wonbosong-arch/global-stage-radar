"""Unit and regression tests for China mainland 30 ETF verification and representative sector selection."""
import csv
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(relative_path):
    with (ROOT / relative_path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class ChinaRepresentativeSectorSelectionTests(unittest.TestCase):
    def setUp(self):
        self.register = read_csv("research/china_mainland_30_etf_verification_register.csv")
        self.audit = read_csv("research/china_mainland_30_etf_ohlcv_structure_audit.csv")
        self.rep_12 = read_csv("research/china_sector_representative_12_selection.csv")
        self.rep_review_original = read_csv("data/china_sector_representative_review.csv")
        self.methodology = read_csv("research/china_index_official_methodology_evidence.csv")

    def test_register_has_all_30_audit_symbols(self):
        audit_symbols = {row["symbol"] for row in self.audit}
        register_symbols = {row["symbol"] for row in self.register}
        self.assertEqual(len(self.register), 30)
        self.assertEqual(audit_symbols, register_symbols)

    def test_representative_count_within_target_range(self):
        representatives = [row for row in self.register if row["representative_selection_status"] == "selected_representative"]
        self.assertGreaterEqual(len(representatives), 8)
        self.assertLessEqual(len(representatives), 12)
        self.assertEqual(len(representatives), 12)
        self.assertEqual(len(self.rep_12), 12)

    def test_selected_representatives_have_distinct_index_codes(self):
        representatives = [row for row in self.register if row["representative_selection_status"] == "selected_representative"]
        index_codes = [row["tracked_index_code"] for row in representatives]
        self.assertEqual(len(index_codes), len(set(index_codes)), "Duplicate index codes among representatives")
        # Index-code uniqueness does not assert sector or holding independence.
        self.assertEqual(len(index_codes), 12)

    def test_duplicate_pairs_are_resolved_properly(self):
        reg_map = {row["symbol"]: row for row in self.register}
        # Same index; observed quantity volume supports only a provisional choice.
        self.assertEqual(reg_map["512800"]["representative_selection_status"], "selected_representative")
        self.assertEqual(reg_map["512700"]["representative_selection_status"], "hold_same_index_duplicate")
        self.assertEqual(reg_map["512800"]["tracked_index_code"], reg_map["512700"]["tracked_index_code"])

        # Different indices; high return correlation does not prove identical holdings.
        self.assertEqual(reg_map["512480"]["representative_selection_status"], "selected_representative")
        self.assertEqual(reg_map["512760"]["representative_selection_status"], "hold_high_correlation_alternative")

    def test_safeguards_all_candidates_inactive_and_unverified_gates_explicit(self):
        for row in self.register:
            with self.subTest(symbol=row["symbol"]):
                self.assertEqual(row["activation_status"], "inactive_research_only")
                self.assertEqual(row["korean_broker_tradability"], "unverified_pending")
                self.assertEqual(row["adjusted_price_quality"], "unverified_pending")
                self.assertIsNone(row.get(None), "CSV formatting overflow")
                self.assertTrue(row["official_source_url"].startswith("https://"))
                self.assertEqual(row["verification_date"], "2026-11-02")
                self.assertTrue(row["identity_status"].startswith("verified_"))
                self.assertIn(row["index_methodology_status"], {"verified_rules_in_cited_version", "partial_scope_confirmed_details_pending"})
                self.assertEqual(row["latest_methodology_version_status"], "unverified_pending")

    def test_original_representative_review_table_preserved_intact(self):
        self.assertEqual(len(self.rep_review_original), 6)
        for row in self.rep_review_original:
            with self.subTest(symbol=row["symbol"]):
                self.assertEqual(row["activation_status"], "inactive_research_only")
                self.assertIsNone(row.get(None), "CSV formatting overflow")

    def test_official_methodology_table_covers_all_indices(self):
        register_indices = {row["tracked_index_code"] for row in self.register}
        methodology_indices = {row["index_code"] for row in self.methodology}
        for code in register_indices:
            self.assertIn(code, methodology_indices, f"Missing methodology evidence for index {code}")


if __name__ == "__main__":
    unittest.main()
