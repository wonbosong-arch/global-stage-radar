import unittest

from collect_stock_candidates import collection_status, summarize_ranking_coverage


class RankingCoverageDiagnosticTests(unittest.TestCase):
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
        self.assertEqual(result["ranking_rows_returned_by_market"]["US_AMS"], 100)
        self.assertEqual(result["ranking_coverage_warnings"], {})


if __name__ == "__main__":
    unittest.main()
