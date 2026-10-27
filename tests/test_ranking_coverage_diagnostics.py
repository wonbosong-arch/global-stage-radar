import unittest

from collect_stock_candidates import summarize_ranking_coverage


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
