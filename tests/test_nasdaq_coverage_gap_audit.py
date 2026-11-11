"""Only synthetic Nasdaq data; real uploaded issuer rows stay out of tests."""
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
import requests

import nasdaq_coverage_gap_audit as subject
from nasdaq_monthly_refresh import FIELDS


NOW = datetime(2026, 11, 11, 9, tzinfo=timezone.utc)


def sample():
    defaults = {
        "Last Sale": "$40.00", "Net Change": "1", "% Change": "2%",
        "Country": "United States", "IPO Year": "2020", "Volume": "800",
        "Sector": "Technology", "Industry": "Semiconductors",
    }
    specs = [
        ("AAA", "AAA Co. Common Stock", "5000000000"),
        ("BBB", "BBB Co. Common Stock", "3000000000"),
        ("PREF", "PREF Co. Preferred Stock", "4000000000"),
        ("ADS", "ADS Co. American Depositary Shares", "6000000000"),
        ("LOW", "LOW Co. Common Stock", "900000000"),
        ("MISS", "MISS Co. Common Stock", ""),
    ]
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for symbol, name, cap in specs:
        writer.writerow({**defaults, "Symbol": symbol, "Name": name, "Market Cap": cap})
    raw = buf.getvalue().encode("utf-8")
    receipt = {
        "version": 1,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "downloaded_on_utc": "2026-11-09",
        "approved_at_utc": "2026-11-11T04:09:10+00:00",
    }
    candidates = pd.DataFrame([
        {"symbol": "AAA", "exchange": "NAS"},
        # Same ticker in Korean registry must not count as US coverage.
        {"symbol": "BBB", "exchange": "KRX"},
    ])
    master = pd.DataFrame([
        {"symbol": "AAA", "listing_exchange": "NAS"},
        {"symbol": "PREF", "listing_exchange": "NAS"},
        {"symbol": "ADS", "listing_exchange": "NYS"},
        # Same ticker across two KIS venues is not proof of listing identity.
        {"symbol": "ADS", "listing_exchange": "NAS"},
    ])
    return raw, receipt, candidates, master


class NasdaqCoverageGapAuditTests(unittest.TestCase):
    def test_gap_count_and_no_activation(self):
        raw, receipt, candidates, master = sample()
        candidate_before = candidates.copy(deep=True)
        master_before = master.copy(deep=True)
        with patch.object(requests, "request",
                          side_effect=AssertionError("Network must remain disabled")):
            report = subject.audit_gap(
                raw, receipt, candidates, master, now=NOW, min_rows=1)
        self.assertEqual(report["source_rows"], 6)
        self.assertEqual(report["source_ge_cap"], 4)
        self.assertEqual(report["source_ge_cap_existing_candidate_ticker"], 1)
        self.assertEqual(report["missing_from_candidate_ticker_inventory"], 3)
        self.assertEqual(report["missing_candidate_with_kis_master_ticker"], 2)
        self.assertEqual(report["missing_candidate_without_kis_master_ticker"], 1)
        self.assertEqual(report["operational_additions"], 0)
        self.assertEqual(report["network_requests"], 0)
        self.assertEqual(report["source_sha256"], receipt["sha256"])
        self.assertEqual(report["gap_by_nasdaq_sector"], {"Technology": 3})
        self.assertEqual([row["symbol"] for row in report["review_rows"]],
                         ["ADS", "PREF", "BBB"])
        self.assertTrue(all(row["review_status"] == "research_only_not_approved"
                            for row in report["review_rows"]))
        self.assertEqual(report["gap_name_warnings"], {
            "no_obvious_name_warning_unverified": 1,
            "source_adr_ratio_unconfirmed": 1,
            "source_non_common_security_signal": 1,
        })
        self.assertEqual(report["gap_security_name_signals"], {
            "depositary_receipt": 1, "preferred_security": 1,
            "no_explicit_security_type_signal_unverified": 1,
        })
        self.assertEqual(report["gap_identity_review_flags"], {
            "kis_master_ticker_collision": 1,
            "no_kis_master_ticker": 1,
            "source_security_type_requires_review": 2,
        })
        # Duplicate ADS master venues take precedence over depositary type:
        # no single KIS identity may be inferred from the ticker alone.
        self.assertEqual(report["gap_issuer_identity_review_cohorts"], {
            "P3_noncommon_instrument_review": 1,
            "P4_kis_master_missing": 1,
            "P4_kis_ticker_or_venue_ambiguous": 1,
        })
        self.assertEqual(report["review_rows"][0]["issuer_identity_review_cohort"],
                         "P4_kis_ticker_or_venue_ambiguous")
        self.assertTrue(all(row["operational_approval_granted"] is False
                            for row in report["review_rows"]))
        self.assertEqual(report["review_rows"][0]["security_name_signal"],
                         "depositary_receipt")
        self.assertEqual(report["review_rows"][1]["security_name_signal"],
                         "preferred_security")
        self.assertEqual(report["review_rows"][2]["security_name_signal"],
                         "no_explicit_security_type_signal_unverified")
        self.assertEqual(report["review_rows"][0]["kis_venues_by_ticker"], ["NAS", "NYS"])
        self.assertFalse(report["review_rows"][-1]["kis_ticker_present"])
        pd.testing.assert_frame_equal(candidates, candidate_before)
        pd.testing.assert_frame_equal(master, master_before)

    def test_untrusted_receipt_or_csv_fails_closed(self):
        raw, receipt, candidates, master = sample()
        for invalid in (
            {**receipt, "sha256": "0" * 64},
            {**receipt, "bytes": len(raw) + 1},
            {**receipt, "approved_at_utc": "2026-11-12T00:00:00+00:00"},
        ):
            with self.assertRaises(ValueError):
                subject.audit_gap(raw, invalid, candidates, master, now=NOW, min_rows=1)

        duplicate = raw + raw.split(b"\n")[1] + b"\n"
        dupe_receipt = {
            **receipt, "bytes": len(duplicate),
            "sha256": hashlib.sha256(duplicate).hexdigest(),
        }
        with self.assertRaises(ValueError):
            subject.audit_gap(duplicate, dupe_receipt, candidates, master,
                              now=NOW, min_rows=1)
        with self.assertRaises(ValueError):
            subject.audit_gap(raw, receipt, candidates, master, now=NOW)

    def test_security_name_risk_examples_never_certify_common_stock(self):
        examples = {
            "Comcast Holdings ZONES": "debt_or_structured_security",
            "AT&T Inc. 5.350% Global Notes due 2066": "debt_or_structured_security",
            "Brookfield Finance Inc. Subordinated Notes": "debt_or_structured_security",
            "BrightSpring Inc. Tangible Equity Unit": "debt_or_structured_security",
            "Some Firm 6% Mandatory Convertible Preferred Stock": "preferred_security",
            "Sample Corporation Contingent Value Rights": "warrant_or_right",
            "Sample Inc. Warrants": "warrant_or_right",
            "PIMCO Dynamic Income Fund": "fund_or_trust",
            "Sample ETF": "fund_or_trust",
            "Example American Depositary Shares": "depositary_receipt",
            "Example American Depository Shares": "depositary_receipt",
            "Example American Depositary Receipts": "depositary_receipt",
            "Example NY Registry Shares": "depositary_receipt",
            "ABC Common Units": "unit_or_partnership",
            "Example plc Class B Common Stock": "share_class_requires_identity_review",
            "Example plc Ordinary Shares": "no_explicit_security_type_signal_unverified",
        }
        for name, expected in examples.items():
            with self.subTest(name=name):
                self.assertEqual(subject.security_name_signal("TEST", name), expected)
        self.assertEqual(subject.security_name_signal("LEN.B", "Lennar Corporation"),
                         "share_class_requires_identity_review")

    def test_kis_dr_flag_is_a_review_signal_not_approval(self):
        raw, receipt, candidates, master = sample()
        master["master_dr_flag"] = ["N", "N", "Y", "Y"]
        master["master_security_type"] = ["2", "2", "2", "2"]
        report = subject.audit_gap(raw, receipt, candidates, master, now=NOW, min_rows=1)
        self.assertEqual(report["gap_identity_review_flags"], {
            "kis_dr_flag_requires_ratio_and_identity_review": 1,
            "kis_master_ticker_collision": 1,
            "no_kis_master_ticker": 1,
            "source_security_type_requires_review": 2,
        })
        ads = report["review_rows"][0]
        self.assertEqual(ads["kis_master_dr_flags"], ["Y"])
        self.assertEqual(ads["kis_master_security_type_codes_unverified"], ["2"])
        self.assertEqual(ads["review_status"], "research_only_not_approved")
        self.assertEqual(ads["identity_review_flags"], [
            "kis_dr_flag_requires_ratio_and_identity_review",
            "kis_master_ticker_collision",
            "source_security_type_requires_review",
        ])

    def test_cross_source_issuer_name_and_instrument_risk(self):
        source = {
            "Symbol": "SPRC", "Name": "Pioneer Diagnostics Incorporated Common Stock",
            "Country": "United States",
        }
        master = {
            "english_name": "PIONEER DIAGNOSTICS INC",
            "listing_exchange": "NAS", "master_security_type": "2", "master_dr_flag": "N",
        }
        def classify(source_row=source, rows=None):
            result = subject.issuer_identity_triage(
                source_row, "SPRC", [master] if rows is None else rows)
            self.assertFalse(result["operational_approval_granted"])
            return result

        good = classify()
        self.assertEqual(good["issuer_name_basis"], "normalized_issuer_tokens")
        self.assertEqual(good["issuer_identity_review_cohort"],
                         "P1_kis_name_coherent_primary_evidence_pending")

        hidden_adr = classify(rows=[{**master, "english_name": "PIONEER DIAGNOSTICS SPON ADR EACH 2 ORD"}])
        self.assertEqual(hidden_adr["issuer_identity_review_cohort"], "P3_depositary_or_ratio_review")
        self.assertEqual(classify(rows=[{**master, "master_dr_flag": "Y"}])[
            "issuer_identity_review_cohort"], "P3_depositary_or_ratio_review")
        self.assertEqual(classify(rows=[{**master, "english_name": "PIONEER DIAGNOSTICS DEP SHS PRF"}])[
            "issuer_identity_review_cohort"], "P3_noncommon_instrument_review")
        self.assertEqual(classify(rows=[{**master, "master_security_type": "3"}])[
            "issuer_identity_review_cohort"], "P4_kis_security_type_unresolved")
        self.assertEqual(classify(rows=[{**master, "english_name": "OTHER ENTERPRISE CO"}])[
            "issuer_identity_review_cohort"], "P2_issuer_name_mismatch_or_missing")
        self.assertEqual(classify(source_row={**source, "Country": "Australia"})[
            "issuer_identity_review_cohort"], "P3_foreign_issuer_listing_review")
        self.assertEqual(classify(source_row={**source, "Name": "Pioneer Diagnostics Incorporated"})[
            "issuer_identity_review_cohort"], "P2_common_share_label_missing")
        self.assertEqual(classify(rows=[])[
            "issuer_identity_review_cohort"], "P4_kis_master_missing")
        self.assertEqual(classify(rows=[master, master])[
            "issuer_identity_review_cohort"], "P4_kis_ticker_or_venue_ambiguous")

    def test_hidden_instruments_in_source_and_kis_names(self):
        for name, label in {
            "Pioneer Holdings Depositary Shares": "depositary_receipt",
            "Pioneer Holdings Depository Shares": "depositary_receipt",
            "PIONEER HOLDINGS DEP SHS": "depositary_receipt",
            "PIONEER HOLDINGS SER A PRF": "preferred_security",
            "Goldman STRATS trust preferred": "debt_or_structured_security",
            "BlackRock Technology Private Equity Trust": "fund_or_trust",
        }.items():
            with self.subTest(name=name):
                self.assertEqual(subject.security_name_signal("TEST", name), label)

    def test_sec_filings_metadata_is_not_an_activation_registry(self):
        path = (Path(__file__).resolve().parents[1] / "docs" / "evidence"
                / "us-nasdaq-issuer-listing-sec-20261111.json")
        registry = json.loads(path.read_text(encoding="utf-8"))
        records = registry["records"]
        self.assertEqual(registry["record_count"], len(records))
        self.assertEqual(len(records), 22)
        cnl = next(row for row in records if row["symbol"] == "CNL")
        self.assertEqual(cnl["security_class"], "common shares")
        self.assertIn("Canadian-incorporated", cnl["review_note"])
        self.assertIn("Nasdaq Screener CSV Country is United States", cnl["review_note"])
        self.assertIn("NYSE American to Nasdaq", cnl["review_note"])
        self.assertEqual(registry["operational_additions"], 0)
        self.assertEqual(len({r["symbol"] for r in records}), len(records))
        for row in records:
            with self.subTest(symbol=row["symbol"]):
                self.assertTrue(row["source_url"].startswith(
                    "https://www.sec.gov/Archives/edgar/data/"))
                self.assertIn(row["kis_venue"], {"NAS", "NYS", "AMS"})
                self.assertIn("common", row["security_class"].lower()
                              if row["security_class"] != "ordinary shares" else "common")
                self.assertEqual(row["activation_status"], "pending_review")
                self.assertEqual(row["evidence_status"],
                                 "sec_filing_security_and_symbol_checked")

    def test_sec_registry_correlates_p1_only_as_review_reference(self):
        raw, receipt, candidates, master = sample()
        # The KIS record now provides a matching ordinary-share issuer for BBB;
        # the candidate registry still contains only a Korean BBB row.
        master = pd.concat([master, pd.DataFrame([{
            "symbol": "BBB", "listing_exchange": "NAS",
            "english_name": "BBB CO", "master_security_type": "2",
            "master_dr_flag": "N",
        }])], ignore_index=True)
        receipt_before = dict(receipt)
        master_before = master.copy(deep=True)
        def record(symbol, venue):
            return {
                "symbol": symbol, "kis_venue": venue,
                "source_url": "https://www.sec.gov/Archives/edgar/data/123/filing",
                "activation_status": "pending_review",
                "evidence_status": "sec_filing_security_and_symbol_checked",
            }
        registry = {"operational_additions": 0, "record_count": 2,
                    "records": [record("BBB", "NAS"), record("ADS", "AMS")]}
        with patch.object(requests, "request", side_effect=AssertionError("network")):
            report = subject.audit_gap(raw, receipt, candidates, master, now=NOW,
                                       min_rows=1, sec_registry=registry)
        self.assertEqual(report["gap_issuer_identity_review_cohorts"].get(
            "P1_kis_name_coherent_primary_evidence_pending"), 1)
        self.assertEqual(report["p1_sec_reference_statuses"], {
            "sec_reference_same_saved_kis_venue_review_only": 1,
        })
        self.assertEqual(report["gap_sec_reference_statuses"], {
            "sec_reference_same_saved_kis_venue_review_only": 1,
            "sec_reference_saved_kis_venue_disagreement": 1,
            "sec_reference_not_registered": 1,
        })
        bbb = next(r for r in report["review_rows"] if r["symbol"] == "BBB")
        self.assertEqual(bbb["sec_reference_url"], registry["records"][0]["source_url"])
        self.assertFalse(bbb["operational_approval_granted"])
        self.assertEqual(bbb["review_status"], "research_only_not_approved")
        self.assertEqual(report["operational_additions"], 0)
        self.assertEqual(receipt, receipt_before)
        pd.testing.assert_frame_equal(master, master_before)

    def test_sec_evidence_registry_validation_fails_closed(self):
        raw, receipt, candidates, master = sample()
        good = {
            "operational_additions": 0, "record_count": 1,
            "records": [{
                "symbol": "PREF", "kis_venue": "NAS",
                "source_url": "https://www.sec.gov/Archives/edgar/data/12/test",
                "activation_status": "pending_review",
                "evidence_status": "sec_filing_security_and_symbol_checked",
            }],
        }
        for invalid in (
            {**good, "operational_additions": 1},
            {**good, "record_count": 2},
            {**good, "records": good["records"] * 2, "record_count": 2},
            {**good, "records": [{**good["records"][0],
                                  "source_url": "https://example.org/filing"}]},
            {**good, "records": [{**good["records"][0],
                                  "activation_status": "approved"}]},
            {**good, "records": [{**good["records"][0],
                                  "kis_venue": "KRX"}]},
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    subject.audit_gap(raw, receipt, candidates, master, now=NOW,
                                      min_rows=1, sec_registry=invalid)
        unchecked = subject.audit_gap(raw, receipt, candidates, master,
                                      now=NOW, min_rows=1)
        self.assertEqual(unchecked["gap_sec_reference_statuses"],
                         {"sec_registry_not_loaded": 3})

    def test_us_ticker_inventory_schema_required(self):
        raw, receipt, candidates, master = sample()
        with self.assertRaisesRegex(ValueError, "symbol and venue"):
            subject.audit_gap(raw, receipt, candidates.drop(columns=["exchange"]),
                              master, now=NOW, min_rows=1)
        with self.assertRaisesRegex(ValueError, "symbol and venue"):
            subject.audit_gap(raw, receipt, candidates,
                              master.drop(columns=["listing_exchange"]), now=NOW, min_rows=1)


if __name__ == "__main__":
    unittest.main()
