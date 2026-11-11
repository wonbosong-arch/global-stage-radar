"""Synthetic saved-price inventory; no real issuer datasets or live requests."""
from contextlib import redirect_stdout
import csv
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import requests

import nasdaq_gap_price_readiness as subject
from nasdaq_monthly_refresh import FIELDS

NOW = datetime.fromisoformat("2026-11-11T15:30:00+09:00")


def gaps(*symbols):
    return {"source_sha256": "a" * 64, "review_rows": [
        {"symbol": s, "issuer_identity_review_cohort": subject.P1,
         "kis_venues_by_ticker": ["NAS"],
         "sec_reference_status": "sec_reference_same_saved_kis_venue_review_only"}
        for s in symbols]}


def history(symbol="SYN", periods=200, end="2026-11-10"):
    return pd.DataFrame([
        dict(symbol=symbol, date=str(d.date()), open=100+i, high=103+i,
             low=99+i, close=101+i, volume=1000)
        for i, d in enumerate(pd.bdate_range(end=end, periods=periods))])


class P1PriceInventoryTests(unittest.TestCase):
    def one(self, frame, now=NOW):
        return subject.price_inventory(gaps("SYN"), frame, now)["review_rows"][0]

    def test_long_fresh_history_is_review_only_and_does_not_mutate_or_call_network(self):
        frame = history()
        before = frame.copy(deep=True)
        with patch.object(requests.sessions.Session, "request", side_effect=AssertionError("network")):
            result = subject.price_inventory(gaps("SYN"), frame, NOW)
        row = result["review_rows"][0]
        self.assertEqual(row["price_inventory_status"], "saved_history_thresholds_met_review_only")
        self.assertEqual(row["completed_daily_rows"], 200)
        self.assertEqual(row["completed_weeks"], 40)
        self.assertEqual(row["latest_completed_session"], "2026-11-10")
        self.assertEqual(row["price_blockers"], [])
        self.assertFalse(row["operational_approval_granted"])
        self.assertFalse(row["live_kis_support_verified"])
        self.assertIn("security_level_usd_cap_basis_and_date", row["remaining_review_gates"])
        self.assertFalse(result["stage_labels_calculated"])
        self.assertEqual(result["operational_additions"], 0)
        pd.testing.assert_frame_equal(frame, before)

    def test_only_p1_cohort_is_inventoried(self):
        report = gaps("SYN", "OTHER")
        report["review_rows"][1]["issuer_identity_review_cohort"] = "P3_depositary_or_ratio_review"
        result = subject.price_inventory(report, pd.concat([history(), history("OTHER")]), NOW)
        self.assertEqual(result["p1_symbols"], 1)
        self.assertEqual(result["review_rows"][0]["symbol"], "SYN")

    def test_missing_short_and_stale_remain_distinct(self):
        missing = self.one(history("OTHER"))
        self.assertEqual(missing["price_inventory_status"], "missing")
        self.assertEqual(missing["stored_rows"], 0)
        short = self.one(history(periods=10))
        self.assertEqual(short["price_inventory_status"], "insufficient_history")
        self.assertIn("completed_weeks35_missing", short["price_blockers"])
        stale = self.one(history(end="2026-10-20"))
        self.assertEqual(stale["price_inventory_status"], "stale")
        self.assertFalse(stale["fresh7"])
        self.assertEqual(stale["price_blockers"], ["freshness7_missing"])

    def test_invalid_rows_are_not_filtered_into_a_valid_tail(self):
        good = history()
        variants = [
            pd.concat([good, good.tail(1)]),
            good.assign(close=float("inf")), good.assign(volume=-1),
            good.assign(low=10000), good.assign(open=0),
            pd.concat([good, good.tail(1).assign(date="bad-date")]),
            pd.concat([good, good.tail(1).assign(date="2026-11-08")]),
            pd.concat([good, good.tail(1).assign(date="2026-11-12")]),
            pd.concat([good, good.tail(1).assign(date="2026-11-10T00:00:00Z")]),
        ]
        for frame in variants:
            with self.subTest(last_date=frame.iloc[-1].date):
                row = self.one(frame)
                self.assertEqual(row["price_inventory_status"], "invalid")
                self.assertFalse(row["saved_ohlcv_quality_pass"])
                self.assertEqual(row["completed_daily_rows"], 0)

    def test_unclosed_us_daily_session_and_current_week_are_excluded(self):
        now = datetime.fromisoformat("2026-11-11T03:00:00+09:00")  # Nov 10 intraday NY
        row = self.one(history(), now)
        self.assertEqual(row["completed_bar_cutoff"], "2026-11-09")
        self.assertEqual(row["excluded_unclosed_rows"], 1)
        self.assertEqual(row["completed_daily_rows"], 199)
        self.assertEqual(row["completed_weeks"], 40)
        self.assertEqual(row["latest_completed_session"], "2026-11-09")

    def test_large_close_move_requires_review_without_reconstructing_adjustments(self):
        frame = history()
        frame.loc[frame.index[-1], ["open", "high", "low", "close"]] = [700, 710, 690, 705]
        row = self.one(frame)
        self.assertEqual(row["price_inventory_status"], "price_anomaly_review")
        self.assertIn("large_close_move_requires_review", row["price_blockers"])

    def test_invalid_contract_and_naive_clock_fail_closed(self):
        for report, frame, now in (
            (gaps("SYN"), history().drop(columns="volume"), NOW),
            (gaps("SYN"), history(), NOW.replace(tzinfo=None)),
            (gaps("SYN", "SYN"), history(), NOW),
        ):
            with self.assertRaises(ValueError):
                subject.price_inventory(report, frame, now)
        report = gaps("SYN")
        report["review_rows"][0]["kis_venues_by_ticker"] = ["NAS", "NYS"]
        with self.assertRaises(ValueError):
            subject.price_inventory(report, history(), NOW)

    def test_cli_receipt_cohort_join_hashes_and_aggregate_only_output(self):
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for i in range(5000):
            writer.writerow(dict(Symbol="SYN" if i == 0 else f"LOW{i}",
                Name="Synthetic Example Common Stock" if i == 0 else f"Low{i} Common Stock",
                **{"Last Sale": "$40", "Net Change": "1", "% Change": "2%",
                   "Market Cap": "2000000000" if i == 0 else "1000000", "Country": "United States",
                   "IPO Year": "2020", "Volume": "800", "Sector": "Technology", "Industry": "Semiconductors"}))
        raw = buf.getvalue().encode()
        receipt = dict(version=1, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                       downloaded_on_utc="2026-11-09", approved_at_utc="2026-11-11T04:09:10+00:00")
        registry = dict(operational_additions=0, record_count=0, records=[])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source.csv").write_bytes(raw)
            (root / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
            (root / "sec.json").write_text(json.dumps(registry), encoding="utf-8")
            pd.DataFrame([dict(symbol="EXISTING", exchange="NAS")]).to_csv(root / "stock_universe_candidates.csv", index=False)
            pd.DataFrame([dict(symbol="SYN", listing_exchange="NAS", master_dr_flag="N",
                               master_security_type="2", english_name="Synthetic Example")]).to_csv(root / "unranked_us_stock_master.csv", index=False)
            history("BENCH").to_csv(root / "daily_prices.csv", index=False)
            history().to_csv(root / "candidate_daily_prices.csv", index=False)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            stdout = io.StringIO()
            with patch("sys.argv", ["audit", "--nasdaq-csv", str(root / "source.csv"),
                       "--receipt", str(root / "receipt.json"), "--sec-registry", str(root / "sec.json"),
                       "--data-dir", str(root), "--evaluated-at", NOW.isoformat()]), redirect_stdout(stdout), \
                    patch.object(requests.sessions.Session, "request", side_effect=AssertionError("network")):
                self.assertEqual(subject.main(), 0)
            report = json.loads(stdout.getvalue())
            self.assertEqual(report["p1_symbols"], 1)
            self.assertNotIn("review_rows", report)
            self.assertNotIn("unapproved_preview", report)
            self.assertNotIn('"SYN"', stdout.getvalue())
            self.assertEqual(report["source_sha256"], receipt["sha256"])
            self.assertEqual(report["input_files"]["daily_prices.csv"]["sha256"],
                             hashlib.sha256(before["daily_prices.csv"]).hexdigest())
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})


if __name__ == "__main__":
    unittest.main()
