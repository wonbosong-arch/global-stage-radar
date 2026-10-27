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
        self.assertIn('cron: "0 23 * * 0-5"', workflow)
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

    def test_adr_review_labels_require_official_listing_evidence_not_deposit_ratio_only(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("공식 ADR 근거 미확인", app)
        self.assertIn("공식 발행/상장 구조와 시총 근거 확인 전", app)
        self.assertNotIn("예탁비율 미확인 ADR", app)


if __name__ == "__main__":
    unittest.main()
