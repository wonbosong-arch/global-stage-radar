"""Synthetic-only tests: no official JPX rows, paid data, APIs or EXAONE calls."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import japan_topix100_review as audit


def sample_rows():
    codes = list(audit.SECTOR_TO_GROUP)
    rows = []
    for i in range(100):
        sector = codes[i % 33]
        group = audit.SECTOR_TO_GROUP[sector]
        rows.append({
            "Effective Date": "20261031",
            "Local Code": f"{1000 + i}",
            "Name (English)": f"FAKE COMPANY {i:03d}",
            "Section/Products": "Prime Market (Domestic)",
            "33 Sector(Code)": sector,
            "33 Sector(name)": "SYNTHETIC 33",
            "17 Sector(Code)": str(group),
            "17 Sector(name)": audit.GROUPS[group][0],
            "Size Code (New Index Series)": "1" if i < 30 else "2",
            "Size (New Index Series)": "TOPIX Core30" if i < 30 else "TOPIX Large70",
        })
    return rows


def identities(rows):
    return {row["Local Code"]: row["Name (English)"] for row in rows}


class JapanTopix100ValidatorTests(unittest.TestCase):
    def test_taxonomy_complete_and_etfs_cover_every_topix17(self):
        self.assertEqual(len(audit.SECTOR_TO_GROUP), 33)
        self.assertEqual(set(audit.GROUPS), set(range(1, 18)))
        self.assertEqual({str(1616 + group) for group in audit.GROUPS},
                         {str(code) for code in range(1617, 1634)})
        self.assertEqual(audit.SECTOR_TO_GROUP["0050"], 1)
        self.assertEqual(audit.SECTOR_TO_GROUP["7100"], 16)
        self.assertEqual(audit.SECTOR_TO_GROUP["9050"], 10)

    def test_100_rows_require_30_core_and_70_large(self):
        data = sample_rows()
        results, summary = audit.review(data, expected_date="2026-10-31",
                                        identities=identities(data), reference_url='https://test.example/identity', reference_as_of='2026-10-31', input_source_url=audit.OFFICIAL_SOURCE)
        self.assertEqual(summary["input_rows"], 100)
        self.assertEqual(summary["selected_rows"], 100)
        self.assertTrue(summary["topix100_confirmed"])
        self.assertEqual(summary["core30"], 30)
        self.assertEqual(summary["large70"], 70)
        self.assertEqual(summary["verified"], 100)
        self.assertEqual(summary["review_required"], 0)
        self.assertEqual(summary["sector_crosswalk_confirmed"], 100)
        self.assertTrue(all(result["mapping_kind"] ==
                            "index_sector_proxy_not_confirmed_etf_holding" for result in results))

    def test_missing_identity_reference_is_not_claimed_verified(self):
        rows, report = audit.review(sample_rows(), expected_date="2026-10-31")
        self.assertTrue(report["topix100_confirmed"])
        self.assertEqual(report["verified"], 0)
        self.assertEqual(report["review_required"], 100)
        self.assertIn("independent_identity_check_missing", rows[0]["review_reasons"])
        self.assertEqual(report["sector_crosswalk_confirmed"], 100)

    def test_official_input_source_must_be_declared_and_is_not_authenticated(self):
        data = sample_rows()
        rows, report = audit.review(
            data, expected_date="2026-10-31", identities=identities(data),
            reference_url="https://test.example/independent", reference_as_of="2026-10-31")
        self.assertEqual(report["verified"], 0)
        self.assertIn("official_input_provenance_missing", rows[0]["review_reasons"])
        self.assertEqual(report["source_provenance"],
                         "user_declared_not_cryptographically_authenticated")

    def test_independent_reference_requires_its_own_source_and_date(self):
        data = sample_rows()
        rows, report = audit.review(data, expected_date="2026-10-31",
                                    identities=identities(data))
        self.assertEqual(report["verified"], 0)
        self.assertIn("identity_reference_source_missing", rows[0]["review_reasons"])
        self.assertIn("identity_reference_date_missing", rows[0]["review_reasons"])
        rows, report = audit.review(data, expected_date="2026-10-31",
                                    identities=identities(data),
                                    reference_url="https://test.example/identity",
                                    reference_as_of="2026-09-30")
        self.assertEqual(report["verified"], 0)
        self.assertIn("identity_reference_date_mismatch", rows[0]["review_reasons"])

    def test_wrong_sector_and_date_and_code_name_conflict_are_review_required(self):
        data = sample_rows()
        refs = identities(data)
        data[0]["17 Sector(Code)"] = "14"
        data[1]["33 Sector(Code)"] = "9999"
        data[2]["33 Sector(name)"] = "-"
        data[3]["Effective Date"] = "20260930"
        data[4]["Local Code"] = data[5]["Local Code"]
        data[4]["Name (English)"] = "CONFLICT"
        data[6]["Name (English)"] = "WRONG NAME"
        rows, report = audit.review(data, expected_date="2026-10-31", identities=refs, reference_url='https://test.example/identity', reference_as_of='2026-10-31', input_source_url=audit.OFFICIAL_SOURCE)
        self.assertFalse(report["topix100_confirmed"])
        self.assertGreaterEqual(report["review_required"], 7)
        self.assertEqual(report["classification_mismatch"], 1)
        self.assertGreaterEqual(report["identity_mismatch"], 2)
        self.assertIn("33_to_17_mismatch", rows[0]["review_reasons"])
        self.assertEqual(rows[0]["sector_etf"], "")
        self.assertIn("unknown_33_sector_code", rows[1]["review_reasons"])
        self.assertIn("missing_33_sector_name", rows[2]["review_reasons"])
        self.assertIn("source_date_mismatch", rows[3]["review_reasons"])
        self.assertIn("duplicate_symbol", rows[5]["review_reasons"])
        self.assertIn("company_name_code_mismatch", rows[6]["review_reasons"])

    def test_incomplete_index_is_never_silently_relabelled_topix100(self):
        data = sample_rows()[:97]
        rows, result = audit.review(data, expected_date="2026-10-31", identities=identities(data), reference_url='https://test.example/identity', reference_as_of='2026-10-31', input_source_url=audit.OFFICIAL_SOURCE)
        self.assertFalse(result["topix100_confirmed"])
        self.assertEqual(result["selected_rows"], 97)
        self.assertEqual(result["verified"], 0)
        self.assertTrue(all("unconfirmed_topix100_constituents" in row["review_reasons"]
                            for row in rows))
        self.assertEqual(result["sample_label"], "UNCONFIRMED_INDEX_OR_FALLBACK")

    def test_fallback_is_explicitly_not_topix100(self):
        data = sample_rows()
        rows, report = audit.review(data, expected_date="2026-10-31",
                                    identities=identities(data), reference_url='https://test.example/identity', reference_as_of='2026-10-31', input_source_url=audit.OFFICIAL_SOURCE, selection="prime100_fallback")
        self.assertFalse(report["topix100_confirmed"])
        self.assertEqual(report["selected_rows"], 100)
        self.assertTrue(all("fallback_not_topix100" in row["review_reasons"] for row in rows))

    def test_read_csv_and_private_output_are_allowed_outside_repo(self):
        data = sample_rows()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "licensed_synthetic.csv"
            with source.open("w", encoding="utf-8", newline="") as file:
                w = csv.DictWriter(file, fieldnames=audit.COLUMNS)
                w.writeheader()
                w.writerows(data)
            parsed = audit.load_rows(source)
            self.assertEqual(len(parsed), 100)
            outputs, summary = audit.review(parsed, expected_date="2026-10-31",
                                            identities=identities(parsed), reference_url='https://test.example/identity', reference_as_of='2026-10-31', input_source_url=audit.OFFICIAL_SOURCE)
            audit.write_private(root / "review", outputs, summary)
            with (root / "review/japan_topix_sector_review.csv").open(encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            saved = json.loads((root / "review/japan_topix_sector_summary.json").read_text())
            self.assertEqual(len(rows), 100)
            self.assertEqual(saved["verified"], 100)
            self.assertNotIn("ETF_HOLDING_CONFIRMED", rows[0]["mapping_kind"])

    def test_no_private_raw_or_derived_data_inside_repo(self):
        with self.assertRaisesRegex(ValueError, "outside_checkout"):
            audit.safe_outside_repo(audit.REPO / "data" / "jpx_official.xlsx")
        with self.assertRaisesRegex(ValueError, "outside_checkout"):
            audit.write_private(audit.REPO / "data" / "jp100-results", [], {})
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.csv"
            path.write_text("wrong,headers\nfoo,bar\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing_jpx_columns"):
                audit.load_rows(path)

    def test_dates_and_sector_code_normalization_fail_closed(self):
        self.assertEqual(audit.norm_code("50", width=4), "0050")
        self.assertEqual(audit.norm_code("0050"), "0050")
        self.assertEqual(audit.normalized_date("20261031"), "2026-10-31")
        for bad in ("20260230", "", "2026/10/31", "2026-13-01"):
            with self.subTest(bad=bad), self.assertRaises((ValueError, OverflowError)):
                audit.normalized_date(bad)
        data = sample_rows()
        data[7]["Effective Date"] = ""
        rows, summary = audit.review(data, expected_date="2026-10-31",
                                     identities=identities(data), reference_url='https://test.example/identity', reference_as_of='2026-10-31', input_source_url=audit.OFFICIAL_SOURCE)
        self.assertIn("missing_or_invalid_source_date", rows[7]["review_reasons"])
        self.assertEqual(summary["verified"], 99)

    def test_cli_refuses_unapproved_commercial_input_before_reading_file(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit) as err:
                audit.main(["--jpx-file", str(Path(d) / "does-not-exist.xlsx"),
                            "--out", str(Path(d) / "out"), "--as-of", "2026-10-31"])
            self.assertEqual(err.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
