import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from collect_stock_candidates import collection_status, summarize_ranking_coverage
import collect_stock_candidates as collector


class RankingCoverageDiagnosticTests(unittest.TestCase):
    def test_collection_propagates_stop_reason_before_dataframe_merge(self):
        raw = pd.DataFrame([{"symb": "AAPL", "ename": "Apple"}])
        raw.attrs.update(ranking_pages_fetched=2, ranking_pagination_stalled=True,
                         ranking_stop_reason="no_new_symbols",
                         ranking_page_diagnostics=[{"rows": 100, "new_symbols": 100},
                                                   {"rows": 100, "new_symbols": 0}])
        master = pd.DataFrame(columns=["listing_exchange", "symbol", "master_security_type",
                                      "master_dr_flag", "master_dr_country_code",
                                      "master_industry_code", "english_name"])
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(collector, "ROOT", Path(tmp)), \
                patch.object(collector, "UNRANKED_US_MASTER_PATH", Path(tmp) / "master.csv"), \
                patch.object(collector, "fetch_us_security_master", return_value=master), \
                patch.object(collector, "fetch_us_market_cap_candidates", side_effect=lambda *a, **k: raw.copy()), \
                patch.object(collector, "fetch_korea_market_cap_candidates", return_value=pd.DataFrame()), \
                patch.object(collector, "build_unranked_us_stock_master", return_value=pd.DataFrame()), \
                patch.object(collector, "normalize_market_cap_candidates", return_value=pd.DataFrame()):
            _, meta = collector.collect_discoveries(object())
        self.assertEqual(meta["ranking_coverage_warning_count"], 3)
        self.assertTrue(meta["partial_collection"])
        for market in ("US_NAS", "US_NYS", "US_AMS"):
            self.assertEqual(meta["ranking_stop_reasons"][market], "no_new_symbols")
            self.assertEqual(meta["ranking_unique_symbols_by_market"][market], 100)

    def test_stalled_or_bounded_collection_is_partial_without_total_mismatch(self):
        for reason in ("no_new_symbols", "page_limit", "unconfirmed_header"):
            for total in (None, "100", "200"):
                with self.subTest(reason=reason, total=total):
                    pages = [{"rows": 100, "new_symbols": 100, "output1": {"trec": total}},
                             {"rows": 100, "new_symbols": 0, "output1": {"trec": total}}]
                    result = summarize_ranking_coverage({"US_NAS": 2}, {"US_NAS": pages},
                                                        {"US_NAS": reason})
                    self.assertEqual(result["ranking_rows_returned_by_market"]["US_NAS"], 200)
                    self.assertEqual(result["ranking_unique_symbols_by_market"]["US_NAS"], 100)
                    self.assertEqual(result["ranking_duplicate_rows_by_market"]["US_NAS"], 100)
                    self.assertEqual(collection_status(result), "partial_success")
                    self.assertIn(reason, result["ranking_coverage_warnings"]["US_NAS"])

    def test_terminal_transport_does_not_force_provider_total_equality(self):
        result = summarize_ranking_coverage(
            {"US_NYS": 1}, {"US_NYS": [{"rows": 2, "new_symbols": 2, "output1": {"trec": "1"}}]},
            {"US_NYS": "terminal_header"})
        self.assertEqual(collection_status(result), "success")
        self.assertEqual(result["ranking_unique_symbols_by_market"]["US_NYS"], 2)

    def test_flags_provider_total_larger_than_returned_ranking_rows(self):
        result = summarize_ranking_coverage(
            {"US_NAS": 1, "US_NYS": 1},
            {
                "US_NAS": [{"rows": 100, "output1": {"trec": "5252"}}],
                "US_NYS": [{"rows": 100, "output1": {"trec": "100"}}],
            },
        )
        self.assertEqual(result["ranking_reported_total_rows"]["US_NAS"], 5252)
        self.assertEqual(result["ranking_rows_returned_by_market"]["US_NAS"], 100)
        self.assertIn("US_NAS", result["ranking_coverage_warnings"])
        self.assertNotIn("US_NYS", result["ranking_coverage_warnings"])
        self.assertEqual(result["ranking_coverage_warning_count"], 1)


    def test_collection_status_is_partial_when_provider_total_exceeds_returned_rows(self):
        coverage = summarize_ranking_coverage(
            {"US_NAS": 1},
            {"US_NAS": [{"rows": 100, "output1": {"trec": "5252"}}]},
        )
        meta = {"partial_collection": False, **coverage}
        self.assertEqual(collection_status(meta), "partial_success")

    def test_collection_status_is_success_when_no_coverage_warning_or_market_error(self):
        self.assertEqual(collection_status({
            "partial_collection": False,
            "ranking_coverage_warning_count": 0,
        }), "success")
        self.assertEqual(collection_status({
            "partial_collection": True,
            "ranking_coverage_warning_count": 0,
        }), "partial_success")

    def test_missing_provider_total_is_not_assumed_complete_or_incomplete(self):
        result = summarize_ranking_coverage(
            {"US_AMS": 1},
            {"US_AMS": [{"rows": 100, "output1": {"nrec": "100"}}]},
        )
        self.assertIsNone(result["ranking_reported_total_rows"]["US_AMS"])
        self.assertIsNone(result["ranking_unique_symbols_by_market"]["US_AMS"])
        self.assertEqual(result["ranking_rows_returned_by_market"]["US_AMS"], 100)
        self.assertEqual(result["ranking_coverage_warnings"], {})


if __name__ == "__main__":
    unittest.main()
