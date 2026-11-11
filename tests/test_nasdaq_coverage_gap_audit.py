"""Only synthetic Nasdaq data; real uploaded issuer rows stay out of tests."""
import csv
from datetime import datetime, timezone
import hashlib
import io

import pandas as pd
import pytest

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
        # Same ticker in Korean registry must not claim US candidate coverage.
        {"symbol": "BBB", "exchange": "KRX"},
    ])
    master = pd.DataFrame([
        {"symbol": "AAA", "listing_exchange": "NAS"},
        {"symbol": "PREF", "listing_exchange": "NAS"},
        {"symbol": "ADS", "listing_exchange": "NYS"},
        # Duplicates across US venues are not resolved into a single listing.
        {"symbol": "ADS", "listing_exchange": "NAS"},
    ])
    return raw, receipt, candidates, master


def test_gap_count_and_no_activation(monkeypatch):
    import requests

    def deny(*args, **kwargs):
        raise AssertionError("The coverage audit must not contact GitHub or KIS")

    monkeypatch.setattr(requests, "request", deny)
    raw, receipt, candidates, master = sample()
    candidate_before = candidates.copy(deep=True)
    master_before = master.copy(deep=True)
    report = subject.audit_gap(raw, receipt, candidates, master, now=NOW, min_rows=1)
    assert report["source_rows"] == 6
    assert report["source_ge_cap"] == 4
    assert report["source_ge_cap_existing_candidate_ticker"] == 1
    assert report["missing_from_candidate_ticker_inventory"] == 3
    assert report["missing_candidate_with_kis_master_ticker"] == 2
    assert report["missing_candidate_without_kis_master_ticker"] == 1
    assert report["operational_additions"] == report["network_requests"] == 0
    assert report["source_sha256"] == receipt["sha256"]
    assert report["gap_by_nasdaq_sector"] == {"Technology": 3}
    assert [row["symbol"] for row in report["review_rows"]] == ["ADS", "PREF", "BBB"]
    assert all(row["review_status"] == "research_only_not_approved" for row in report["review_rows"])
    assert report["gap_name_warnings"] == {
        "no_obvious_name_warning_unverified": 1,
        "source_adr_ratio_unconfirmed": 1,
        "source_non_common_security_signal": 1,
    }
    assert report["review_rows"][0]["kis_venues_by_ticker"] == ["NAS", "NYS"]
    assert report["review_rows"][-1]["kis_ticker_present"] is False
    pd.testing.assert_frame_equal(candidates, candidate_before)
    pd.testing.assert_frame_equal(master, master_before)


def test_untrusted_receipt_or_csv_fails_closed():
    raw, receipt, candidates, master = sample()
    for invalid_receipt in (
        {**receipt, "sha256": "0" * 64},
        {**receipt, "bytes": len(raw) + 1},
        {**receipt, "approved_at_utc": "2026-11-12T00:00:00+00:00"},
    ):
        with pytest.raises(ValueError):
            subject.audit_gap(raw, invalid_receipt, candidates, master, now=NOW, min_rows=1)

    # The quality gate catches duplicate source tickers before a gap is reported.
    duplicate = raw + raw.split(b"\n")[1] + b"\n"
    dupe_receipt = {**receipt, "bytes": len(duplicate), "sha256": hashlib.sha256(duplicate).hexdigest()}
    with pytest.raises(ValueError):
        subject.audit_gap(duplicate, dupe_receipt, candidates, master, now=NOW, min_rows=1)
    with pytest.raises(ValueError):
        subject.audit_gap(raw, receipt, candidates, master, now=NOW)


def test_us_ticker_inventory_schema_required():
    raw, receipt, candidates, master = sample()
    with pytest.raises(ValueError, match="symbol and venue"):
        subject.audit_gap(raw, receipt, candidates.drop(columns=["exchange"]),
                          master, now=NOW, min_rows=1)
    with pytest.raises(ValueError, match="symbol and venue"):
        subject.audit_gap(raw, receipt, candidates,
                          master.drop(columns=["listing_exchange"]), now=NOW, min_rows=1)
