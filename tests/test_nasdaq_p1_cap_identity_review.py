"""Synthetic evidence only: no real ticker-to-live-result assignments."""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import requests

import nasdaq_p1_cap_identity_review as subject


def probes():
    base = dict(mode="nasdaq_p1_kis_history_probe_review_only", source_sha256="source",
                input_file_hashes={"stock_universe_candidates.csv": "c",
                                   "unranked_us_stock_master.csv": "m"},
                p1_inventory_count=2, eligible_missing_with_matched_reference=2,
                selected_count=1, attempted_symbols=1, live_probe_performed=True,
                stopped_early_reason=None)
    return [dict(run_id=1, summary={**deepcopy(base), "result_counts": {"insufficient_history": 1}}),
            dict(run_id=2, summary={**deepcopy(base), "selected_start_index": 1,
                                   "result_counts": {"saved_history_thresholds_met_review_only": 1}})]


def inputs():
    gaps = {"source_sha256": "source", "review_rows": [
        dict(symbol=s, issuer_identity_review_cohort=subject.P1,
             kis_venues_by_ticker=["NAS"], nasdaq_reported_cap_usd="1500000000")
        for s in ("AAA", "BBB")]}
    registry = dict(operational_additions=0, record_count=2, records=[
        dict(symbol=s, kis_venue="NAS", security_class="Class A common stock",
             source_url="https://www.sec.gov/Archives/edgar/data/1/test.htm",
             filing_period_or_date="2026-09-30", review_note="venue transition pending",
             evidence_status="sec_filing_security_and_symbol_checked", activation_status="pending_review")
        for s in ("AAA", "BBB")])
    yahoo = pd.DataFrame([dict(symbol="AAA", market_cap_usd_b_secondary="0.999999999",
                              market_cap_currency="USD", observation_status="observed_usd",
                              market_cap_asof="2026-11-11", market_cap_asof_basis="quote_time",
                              fetched_at_utc="2026-11-12T00:00:00+00:00", quote_type="EQUITY")])
    return gaps, yahoo, registry


class P1CapIdentityTests(unittest.TestCase):
    def test_disjoint_counts_cannot_assign_pass_ticker(self):
        aggregate = subject.aggregate_probes(probes())
        self.assertEqual(aggregate["attempted_symbols"], 2)
        self.assertEqual(aggregate["result_counts"]["saved_history_thresholds_met_review_only"], 1)
        self.assertFalse(aggregate["individual_ticker_mapping_available"])
        self.assertEqual(aggregate["identified_history_pass_tickers"], 0)

    def test_incompatible_or_incomplete_probes_rejected(self):
        for field, value in (("selected_start_index", 0), ("attempted_symbols", 0),
                             ("source_sha256", "changed"), ("stopped_early_reason", "rate_limited"),
                             ("input_file_hashes", {}), ("result_counts", {"pass": -1}),
                             ("unapproved_preview", [{"symbol": "AAA"}]),
                             ("live_probe_performed", False)):
            with self.subTest(field=field):
                entries = probes()
                entries[1]["summary"][field] = value
                with self.assertRaises(ValueError):
                    subject.aggregate_probes(entries)
        with self.assertRaises(ValueError):
            subject.aggregate_probes(probes()[:1])
        entries = probes()
        entries[1]["run_id"] = 1
        with self.assertRaises(ValueError):
            subject.aggregate_probes(entries)

    def test_cap_boundary_is_decimal_and_date_is_not_fetch_time(self):
        for value, status in (("0.999999999", "below_usd1b_observation_only"),
                              ("1", "at_or_above_usd1b_observation_only"),
                              ("NaN", "missing_or_unusable_observation"),
                              ("Infinity", "missing_or_unusable_observation"),
                              ("-1", "missing_or_unusable_observation")):
            row = dict(market_cap_usd_b_secondary=value, market_cap_currency="USD",
                       observation_status="observed_usd", market_cap_asof="2026-11-11",
                       market_cap_asof_basis="regularMarketTime", fetched_at_utc="2026-11-12")
            with self.subTest(value=value):
                result = subject.cap_observation(row)
                self.assertEqual(result["cap_threshold_observation"], status)
                self.assertIsNone(result["cap_effective_date"])
                self.assertFalse(result["security_cap_verified"])
        row["market_cap_asof_basis"] = "source_provided_market_cap_date"
        self.assertEqual(subject.cap_observation(row)["cap_effective_date"], "2026-11-11")
        row["market_cap_asof"] = "2026-02-30"
        self.assertIsNone(subject.cap_observation(row)["cap_effective_date"])

    def test_non_usd_and_failed_observation_unusable(self):
        for currency, status in (("EUR", "observed_usd"), ("USD", "request_failed")):
            result = subject.cap_observation(dict(market_cap_usd_b_secondary="3",
                                                market_cap_currency=currency, observation_status=status))
            self.assertEqual(result["cap_threshold_observation"], "missing_or_unusable_observation")

    def test_join_keeps_class_notes_and_unknown_live_status_without_mutation(self):
        gaps, yahoo, registry = inputs()
        before = yahoo.copy(deep=True)
        with patch.object(requests.sessions.Session, "request", side_effect=AssertionError("network")):
            result = subject.review_evidence(gaps, yahoo, registry, probes(),
                                              {"stock_universe_candidates.csv": "c",
                                               "unranked_us_stock_master.csv": "m"})
        pd.testing.assert_frame_equal(yahoo, before)
        self.assertTrue(result["current_metadata_hashes_match_probe"])
        self.assertEqual(result["missing_cap_effective_dates"], 2)
        self.assertEqual(result["cap_observation_counts"]["missing_or_unusable_observation"], 1)
        for row in result["review_rows"]:
            self.assertEqual(row["live_history_status"], "unknown_aggregate_only")
            self.assertEqual(row["sec_security_class"], "Class A common stock")
            self.assertEqual(row["sec_review_note"], "venue transition pending")
            self.assertFalse(row["listing_continuity_verified"])
            self.assertFalse(row["activation_approved"])
        self.assertEqual(result["operational_additions"], 0)

    def test_changed_master_does_not_bind_historical_cohort(self):
        gaps, yahoo, registry = inputs()
        result = subject.review_evidence(gaps, yahoo, registry, probes(),
                                          {"stock_universe_candidates.csv": "c",
                                           "unranked_us_stock_master.csv": "changed"})
        self.assertFalse(result["current_metadata_hashes_match_probe"])

    def test_duplicate_observations_and_venue_mismatch(self):
        gaps, yahoo, registry = inputs()
        with self.assertRaises(ValueError):
            subject.review_evidence(gaps, pd.concat([yahoo, yahoo]), registry, probes(), {})
        registry["records"][0]["kis_venue"] = "NYS"
        result = subject.review_evidence(gaps, yahoo, registry, probes(), {})
        self.assertFalse(result["review_rows"][0]["sec_saved_venue_matches"])

    def test_cli_default_hides_rows_and_uses_read_only_inputs(self):
        gaps, yahoo, registry = inputs()
        result = subject.review_evidence(gaps, yahoo, registry, probes(), {})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {"source": b"synthetic", "receipt": b"{}", "sec": b"{}", "probe": b"[]"}
            for name, data in files.items():
                (root / name).write_bytes(data)
            argv = ["review", "--nasdaq-csv", str(root / "source"), "--receipt", str(root / "receipt"),
                    "--sec-registry", str(root / "sec"), "--probe-evidence", str(root / "probe")]
            stdout = io.StringIO()
            with patch("sys.argv", argv), patch.object(subject, "build_report", return_value=result), contextlib.redirect_stdout(stdout):
                self.assertEqual(subject.main(), 0)
            output = json.loads(stdout.getvalue())
            self.assertNotIn("review_rows", output)
            self.assertNotIn("unapproved_preview", output)
            self.assertNotIn("AAA", stdout.getvalue())
            self.assertEqual({p.name: p.read_bytes() for p in root.iterdir()}, files)


if __name__ == "__main__":
    unittest.main()
