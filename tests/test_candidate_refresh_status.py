import unittest

import pandas as pd

from candidate_coverage_audit import attach_refresh_attempt_status


class CandidateRefreshStatusTests(unittest.TestCase):
    def setUp(self):
        self.report = pd.DataFrame([
            {"symbol": "AAA", "candidate_price_rows": 300},
            {"symbol": "BBB", "candidate_price_rows": 280},
            {"symbol": "CCC", "candidate_price_rows": 150},
        ])

    def test_distinguishes_fresh_failed_and_preserved_only_symbols(self):
        status = {
            "updated_at_utc": "2026-10-25T08:00:00+00:00",
            "github_run_id": "12345",
            "github_run_url": "https://github.com/example/repo/actions/runs/12345",
            "requested_symbols": 3,
            "fresh_data_symbols": ["AAA"],
            "fresh_data_symbol_count": 1,
            "snapshot_symbols_with_data": 3,
            "symbols_preserved_from_previous_snapshot": 2,
            "failed_symbols": ["BBB"],
            "errors": [{"symbol": "BBB", "error": "rate limit"}],
            "error_count": 1,
        }
        result = attach_refresh_attempt_status(
            self.report, status, now_utc="2026-10-25T10:30:00+00:00"
        ).set_index("symbol")
        self.assertEqual(result.loc["AAA", "refresh_attempt_outcome"], "fresh_data_returned")
        self.assertEqual(result.loc["BBB", "refresh_attempt_outcome"], "request_failed")
        self.assertEqual(result.loc["CCC", "refresh_attempt_outcome"], "not_confirmed_in_latest_attempt")
        self.assertEqual(result.loc["BBB", "refresh_attempt_error"], "rate limit")
        self.assertEqual(result.loc["AAA", "refresh_status_age_hours_at_report"], 2.5)
        self.assertEqual(result.loc["AAA", "refresh_attempt_run_id"], "12345")
        self.assertEqual(result.loc["AAA", "refresh_attempt_preserved_symbol_count"], 2)
        self.assertFalse(bool(result.loc["CCC", "latest_attempt_kis_response_observed"]))

    def test_run_level_failure_overrides_symbol_freshness_claim(self):
        status = {
            "updated_at_utc": "2026-10-25T08:00:00Z",
            "fresh_data_symbols": ["AAA"],
            "failed_symbols": ["*"],
            "errors": [{"symbol": "*", "error": "setup failed"}],
            "error_count": 1,
        }
        result = attach_refresh_attempt_status(
            self.report, status, now_utc="2026-10-25T09:00:00Z"
        )
        self.assertTrue(result["refresh_attempt_run_level_failed"].all())
        self.assertEqual(set(result["refresh_attempt_outcome"]), {"refresh_run_failed"})

    def test_empty_preserved_symbol_list_is_safe_and_reports_zero(self):
        status = {
            "updated_at_utc": "2026-10-25T08:00:00Z",
            "fresh_data_symbols": ["AAA"],
            "symbols_preserved_from_previous_snapshot": [],
        }
        result = attach_refresh_attempt_status(
            self.report, status, now_utc="2026-10-25T09:00:00Z"
        )
        self.assertTrue((result["refresh_attempt_preserved_symbol_count"] == 0).all())

    def test_preserved_symbol_list_reports_count_not_list(self):
        status = {
            "updated_at_utc": "2026-10-25T08:00:00Z",
            "fresh_data_symbols": ["AAA"],
            "symbols_preserved_from_previous_snapshot": ["BBB", "CCC"],
        }
        result = attach_refresh_attempt_status(
            self.report, status, now_utc="2026-10-25T09:00:00Z"
        )
        self.assertTrue((result["refresh_attempt_preserved_symbol_count"] == 2).all())

    def test_missing_status_timestamp_is_reported_as_unknown_age(self):
        result = attach_refresh_attempt_status(
            self.report, {"fresh_data_symbols": []}, now_utc="2026-10-25T09:00:00Z"
        )
        self.assertTrue(result["refresh_status_age_hours_at_report"].isna().all())
        self.assertTrue((result["refresh_attempt_outcome"] == "not_confirmed_in_latest_attempt").all())


if __name__ == "__main__":
    unittest.main()
