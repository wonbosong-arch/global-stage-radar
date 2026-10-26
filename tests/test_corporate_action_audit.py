import unittest

import pandas as pd

from audit_corporate_actions import split_continuity_report


class CorporateActionAuditTests(unittest.TestCase):
    def test_split_adjusted_prices_pass_when_close_is_continuous(self):
        frame = pd.DataFrame({
            "date": ["2024-06-07", "2024-06-10", "2024-06-11"],
            "close": [120.0, 121.0, 122.0],
        })
        report = split_continuity_report(frame, "2024-06-10", "NVDA", "10-for-1 split")
        self.assertEqual(report["status"], "PASS")
        self.assertAlmostEqual(report["post_pre_close_ratio"], 121.0 / 120.0, places=5)

    def test_unadjusted_split_discontinuity_fails(self):
        frame = pd.DataFrame({
            "date": ["2024-06-07", "2024-06-10"],
            "close": [1200.0, 121.0],
        })
        report = split_continuity_report(frame, "2024-06-10", "NVDA", "10-for-1 split")
        self.assertEqual(report["status"], "FAIL")

    def test_missing_event_side_fails_closed(self):
        frame = pd.DataFrame({"date": ["2024-06-10"], "close": [121.0]})
        report = split_continuity_report(frame, "2024-06-10", "NVDA", "10-for-1 split")
        self.assertEqual(report["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
