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
        self.assertIn('cron: "0 22 * * 0-5"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn('branches: ["main"]', workflow)
        # Workflow-generated status/data changes may leave a dirty worktree before a retry.
        # Preserve them safely when rebasing onto a concurrently updated target branch.
        self.assertIn("git rebase --autostash origin/data-validation-mvp", workflow)

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

    def test_candidate_price_schedule_has_a_full_pass_budget_without_extending_dispatches(self):
        workflow = (ROOT / ".github" / "workflows" / "candidate_prices_manual.yml").read_text(encoding="utf-8")
        self.assertNotRegex(workflow, r"(?m)^\s*schedule\s*:")
        self.assertIn("07:35 KST", workflow)
        self.assertIn("timeout-minutes: ${{ inputs.scheduled_at != '' && 120 || 30 }}", workflow)
        self.assertIn(
            "CANDIDATE_REFRESH_BUDGET_SECONDS: ${{ inputs.scheduled_at != '' && '6300' "
            "|| inputs.refresh_budget_seconds || '900' }}",
            workflow,
        )
        self.assertIn("options: ['900', '1']", workflow)
        self.assertIn("queue: max", workflow)
        self.assertIn("group: daily-closing-price-snapshot", workflow)
        self.assertIn("cancel-in-progress: false", workflow)

    def test_candidate_duplicate_guard_precedes_collection_and_publish(self):
        workflow = (ROOT / ".github" / "workflows" / "candidate_prices_manual.yml").read_text(encoding="utf-8")
        self.assertLess(workflow.index("ref: data-validation-mvp"), workflow.index("id: scheduled_collection"))
        self.assertLess(workflow.index("id: scheduled_collection"), workflow.index("id: refresh_benchmarks"))
        self.assertIn("check_scheduled_daily_prices.py --candidate", workflow)
        self.assertIn("CANDIDATE_SCHEDULED_SLOT: ${{ steps.scheduled_collection.outputs.scheduled_slot }}", workflow)
        for step in ("Commit review snapshot and diagnostics", "Trigger coverage report after candidate refresh"):
            self.assertIn(
                f"- name: {step}\n        if: always() && steps.scheduled_collection.outcome == 'success' "
                "&& steps.scheduled_collection.outputs.skip != 'true'",
                workflow,
            )

    def test_adr_review_labels_require_official_listing_evidence_not_deposit_ratio_only(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("공식 ADR 근거 미확인", app)
        self.assertIn("공식 발행/상장 구조와 시총 근거 확인 전", app)
        self.assertNotIn("예탁비율 미확인 ADR", app)


if __name__ == "__main__":
    unittest.main()
