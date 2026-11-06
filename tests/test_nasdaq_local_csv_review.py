"""Only invented CSV rows. No Nasdaq source records or downloaded fixtures."""
import copy
import csv as csv_module
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import nasdaq_local_csv_review as subject


def manifest(**extra):
    return dict(permission_status="confirmed_by_user", permission_reference="SYNTHETIC test permission",
        manual_download_allowed=True, local_storage_allowed=True, offline_analysis_allowed=True,
        source_url="https://www.nasdaq.com/market-activity/stocks/screener",
        acquisition_method="user_manual_download", downloaded_at_utc="2026-11-05T00:00:00Z",
        source_as_of="2026-11-04", source_as_of_reference="SYNTHETIC test as-of", **extra)


def fixture():
    registry = [dict(symbol=s, exchange=v, name=s + " SYNTHETIC") for s, v in
                (("TEST", "NAS"), ("CLASS/A", "NYS"), ("CLASS/B", "NYS"), ("OTHER", "AMS"))]
    rows = [dict(zip(subject.FIELDS, values)) for values in (
        ("TEST", "TEST SYNTHETIC", "NASDAQ", "Test Sector", "Test Industry", "1000000000"),
        ("CLASS.A", "CLASS/A SYNTHETIC", "NYSE", "Test Sector", "", "N/A"),
        ("CLASS.B", "CLASS/B SYNTHETIC", "NYSE", "N/A", "Test Industry", "NaN"),
        ("OTHER", "OTHER SYNTHETIC", "AMEX", "Test Sector", "Test Industry", "-4"))]
    aliases = [dict(source_symbol="CLASS." + c, kis_symbol="CLASS/" + c, venue="NYS",
                    evidence_reference="SYNTHETIC notation review") for c in ("A", "B")]
    return rows, registry, {"saved_baseline": {"TEST"}, "saved_conditional": {"CLASS/A", "CLASS/B"}}, manifest(symbol_aliases=aliases)


class NasdaqLocalCSVTests(unittest.TestCase):
    def test_native_coverage_dual_classes_and_inputs_preserved(self):
        rows, registry, groups, rights = fixture()
        before = copy.deepcopy((rows, registry, groups, rights))
        result = subject.inspect_rows(rows, list(subject.FIELDS), registry, groups, rights)
        self.assertEqual(result["groups"]["all_us"]["matched"], 4)
        self.assertEqual(result["groups"]["all_us"]["with_sector"], 3)
        self.assertEqual(result["groups"]["saved_conditional"]["with_sector"], 1)
        self.assertEqual(result["quality"]["fields"]["Sector"]["missing_rate"], .25)
        self.assertEqual(result["quality"]["market_cap_invalid_or_nonpositive"], 1)
        self.assertEqual(before, (rows, registry, groups, rights))

    def test_no_ticker_only_or_implicit_punctuation_match(self):
        rows, registry, groups, rights = fixture()
        rights["symbol_aliases"] = []
        rows[0]["Exchange"] = "NYSE"
        result = subject.inspect_rows(rows, list(subject.FIELDS), registry, groups, rights)
        self.assertEqual(result["groups"]["all_us"]["matched"], 1)

    def test_alias_cannot_collapse_classes_or_erase_suffix(self):
        for target in ("CLASS/B", "CLASS", "OTHER/A"):
            with self.subTest(target=target):
                rights = manifest(symbol_aliases=[dict(source_symbol="CLASS.A", kis_symbol=target,
                    venue="NYS", evidence_reference="synthetic")])
                with self.assertRaises(ValueError):
                    subject.aliases_from(rights)

    def test_duplicate_and_alias_collision_are_withheld(self):
        rows, registry, groups, rights = fixture()
        for duplicate in (dict(rows[0]), dict(rows[1], Symbol="CLASS/A")):
            with self.subTest(duplicate=duplicate):
                result = subject.inspect_rows(rows + [duplicate], list(subject.FIELDS), registry, groups, rights)
                self.assertEqual(result["groups"]["all_us"]["matched"], 3)
                self.assertEqual(result["quality"]["duplicate_or_alias_collision_keys"], 1)

    def test_missing_exchange_needs_documented_export_filter(self):
        rows, registry, groups, rights = fixture()
        columns = [c for c in subject.FIELDS if c != "Exchange"]
        result = subject.inspect_rows(rows, columns, registry, groups, rights)
        self.assertEqual(result["groups"]["all_us"]["matched"], 0)
        rights.update(export_exchange="NASDAQ", export_exchange_reference="synthetic filter receipt")
        result = subject.inspect_rows(rows, columns, registry, groups, rights)
        self.assertEqual(result["groups"]["all_us"]["matched"], 1)
        self.assertFalse(result["quality"]["fields"]["Exchange"]["present"])
        self.assertEqual(result["quality"]["venue_attribution"], "documented_export_filter")

    def test_exchange_column_blanks_not_filled_from_filter(self):
        rows, registry, groups, rights = fixture()
        rows[0]["Exchange"] = ""
        rights.update(export_exchange="NASDAQ", export_exchange_reference="synthetic")
        result = subject.inspect_rows(rows, list(subject.FIELDS), registry, groups, rights)
        self.assertEqual(result["quality"]["rows_without_supported_venue"], 1)
        self.assertEqual(result["groups"]["all_us"]["matched"], 3)

    def test_undated_sector_is_not_dated_evidence(self):
        rows, registry, groups, rights = fixture()
        rights["source_as_of"] = None
        result = subject.inspect_rows(rows, list(subject.FIELDS), registry, groups, rights)
        self.assertEqual(result["groups"]["all_us"]["with_sector"], 3)
        self.assertEqual(result["groups"]["all_us"]["with_dated_sector_observation"], 0)

    def test_schema_width_bom_marketcap_and_na_ticker(self):
        headers, columns, rows = subject.read_table(b'\xef\xbb\xbfSymbol,Name,MarketCap\r\nNA,"Synthetic, Inc.",12\r\n')
        self.assertIn("Market Cap", columns)
        self.assertEqual(rows[0]["Name"], "Synthetic, Inc.")
        self.assertFalse(subject.missing("NA", "Symbol"))
        for raw in (b'Symbol,symbol\nA,A\n', b'Symbol,Name\nA,B,C\n', b''):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                subject.read_table(raw)

    def test_empty_and_incomplete_schema_never_supply_evidence(self):
        rows, registry, groups, rights = fixture()
        result = subject.inspect_rows([], list(subject.FIELDS), registry, groups, rights)
        self.assertIsNone(result["quality"]["fields"]["Sector"]["missing_rate"])
        result = subject.inspect_rows(rows, ["Symbol", "Exchange"], registry, groups, rights)
        self.assertEqual(result["groups"]["all_us"]["with_sector"], 0)

    def test_permission_missing_or_bad_time_fails_before_csv_open(self):
        now = datetime(2026, 11, 5, 1, tzinfo=timezone.utc)
        for changes in ({"offline_analysis_allowed": False}, {"permission_reference": ""},
                        {"downloaded_at_utc": "2026-11-05T00:00:00"},
                        {"downloaded_at_utc": "2026-11-06T00:00:00Z"},
                        {"source_as_of": "2026-11-06"}, {"source_as_of_reference": ""}):
            rights = manifest()
            rights.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                subject.check_permission(rights, now)
        with tempfile.TemporaryDirectory() as temp:
            m = Path(temp) / "manifest.json"
            m.write_text('{}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "permission required"):
                subject.build_report(Path(temp) / "DOES_NOT_EXIST.csv", m)

    def test_real_csv_inside_git_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
            csv = root / "input.csv"
            csv.write_text("Symbol\nTEST\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside every Git"):
                subject.outside_git(csv)

    def test_synthetic_end_to_end_reuses_saved_cohorts_and_has_no_real_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            csv = root / "input.csv"
            csv.write_text("Symbol,Name,Exchange,Sector,Industry,Market Cap\nSYNTHETIC,SYNTHETIC,NASDAQ,Test,Test,12\n", encoding="utf-8")
            rights = manifest(dataset_kind="synthetic", csv_sha256=hashlib.sha256(csv.read_bytes()).hexdigest())
            m = root / "manifest.json"
            m.write_text(json.dumps(rights), encoding="utf-8")
            # Discovery grows independently of the saved 85/135 cohorts. Exercise
            # a newly appended listing instead of pinning yesterday's US total.
            with (subject.ROOT / "data/stock_universe_candidates.csv").open(encoding="utf-8-sig", newline="") as stream:
                reader = csv_module.DictReader(stream)
                fields = reader.fieldnames
                registry = list(reader)
            original_us = sum(r["exchange"] in ("NAS", "NYS", "AMS") for r in registry)
            registry.append(dict(symbol="SYNTHETIC", name="SYNTHETIC", exchange="NAS"))
            with (root / "stock_universe_candidates.csv").open("w", encoding="utf-8", newline="") as stream:
                writer = csv_module.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(registry)
            with patch("socket.socket", side_effect=AssertionError("network forbidden")):
                report = subject.build_report(csv, m, data_dir=root, synthetic=True)
            self.assertEqual(report["groups"]["all_us"]["candidates"], original_us + 1)
            self.assertEqual(report["groups"]["saved_baseline"]["candidates"], 85)
            self.assertEqual(report["groups"]["saved_conditional"]["candidates"], 135)
            self.assertEqual(report["real_files_reviewed"], 0)
            self.assertEqual(report["new_stage_eligible"], 0)
            self.assertEqual(report["stage_labels_recomputed"], 0)
            self.assertEqual(report["groups"]["all_us"]["matched"], 1)
            added = next(r for r in report["candidates"] if r["symbol"] == "SYNTHETIC")
            self.assertEqual(added["status"], "matched")
            self.assertTrue(added["sector_present"])
            rights["csv_sha256"] = "wrong"
            m.write_text(json.dumps(rights), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exact CSV hash"):
                subject.build_report(csv, m, synthetic=True)
            with self.assertRaisesRegex(ValueError, "Dataset kind"):
                subject.build_report(csv, m)


if __name__ == "__main__":
    unittest.main()
