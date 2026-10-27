"""Regression checks for scheduled candidate discovery workflow safeguards."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "candidate_collection.yml"
COLLECTOR_PATH = ROOT / "collect_stock_candidates.py"


class CandidateWorkflowSafetyTests(unittest.TestCase):
    def test_candidate_workflow_targets_feature_branch_and_skips_sunday_kst(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn('ref: data-validation-mvp', workflow)
        self.assertIn('cron: "30 22 * * 0-5"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn('branches: ["main"]', workflow)

    def test_candidate_discovery_is_review_only_and_never_activates_new_rows(self):
        collector = COLLECTOR_PATH.read_text(encoding="utf-8")
        self.assertIn('"activation_status": "pending_review"', collector)
        self.assertIn("def merge_candidate_discoveries", collector)
        self.assertIn("never overwri", collector.lower())
        self.assertIn('new = new[~new["symbol"].isin(known | active)]', collector)

    def test_price_refresh_only_triggers_when_new_candidates_are_added(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("steps.candidate_delta.outputs.new_candidates_added != '0'", workflow)
        self.assertIn("candidate_prices_manual.yml/dispatches", workflow)


if __name__ == "__main__":
    unittest.main()
