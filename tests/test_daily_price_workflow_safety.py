"""Regression checks for daily price refresh reporting and schedule safety."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "daily_prices.yml"


class DailyPriceWorkflowSafetyTests(unittest.TestCase):
    def test_daily_price_workflow_targets_feature_branch_and_skips_sunday_kst(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("ref: data-validation-mvp", workflow)
        self.assertIn('cron: "0 23 * * 0-5"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn('branches: ["main"]', workflow)

    def test_refresh_summary_does_not_misreport_stale_status_after_failure(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("id: refresh_prices", workflow)
        self.assertIn("REFRESH_OUTCOME: ${{ steps.refresh_prices.outcome }}", workflow)
        self.assertIn('if os.environ.get("REFRESH_OUTCOME") != "success":', workflow)
        self.assertIn("any saved status file may be from an earlier run", workflow)
        self.assertIn("symbols needing attention", workflow.lower())


if __name__ == "__main__":
    unittest.main()
