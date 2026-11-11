"""Only synthetic Nasdaq data; real uploaded issuer rows stay out of tests."""
import csv
from datetime import datetime, timezone
import hashlib
import io
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
