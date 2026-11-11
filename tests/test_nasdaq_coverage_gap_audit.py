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
