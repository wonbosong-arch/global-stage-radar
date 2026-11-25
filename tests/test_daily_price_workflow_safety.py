"""Regression checks for daily price refresh reporting and schedule safety."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "daily_prices.yml"


class DailyPriceWorkflowSafetyTests(unittest.TestCase):
    def test_daily_price_workflow_uses_external_dispatch_without_a_github_schedule(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("ref: data-validation-mvp", workflow)
        self.assertRegex(workflow, r"(?m)^  workflow_dispatch:\s*$")
        self.assertNotRegex(workflow, r"(?m)^\s*schedule\s*:")

    def test_daily_price_workflow_keeps_push_triggers_and_shared_queue(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("  push:\n    branches:\n      - data-validation-mvp\n", workflow)
        for path in (
            "data/monitoring_universe.csv",
            "data_providers.py",
            "refresh_daily_prices.py",
            ".github/workflows/daily_prices.yml",
        ):
            with self.subTest(path=path):
                self.assertIn(f'      - "{path}"\n', workflow)
        self.assertIn("group: daily-closing-price-snapshot", workflow)
        self.assertIn("queue: max", workflow)
        self.assertIn("cancel-in-progress: false", workflow)

    def test_refresh_summary_does_not_misreport_stale_status_after_failure(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("id: refresh_prices", workflow)
        self.assertIn("REFRESH_OUTCOME: ${{ steps.refresh_prices.outcome }}", workflow)
        self.assertIn('if os.environ.get("REFRESH_OUTCOME") != "success":', workflow)
        self.assertIn("any saved status file may be from an earlier run", workflow)
        self.assertIn("symbols needing attention", workflow.lower())
        self.assertIn('out.write("## Daily price refresh\\n\\n")', workflow)
        self.assertNotIn('out.write("## Daily price refresh\\\\n\\\\n")', workflow)


if __name__ == "__main__":
    unittest.main()
