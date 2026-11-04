import unittest
from pathlib import Path

from audit_kis_workflow_queue import MEMBERS, audit, concurrency, proposal, proposed_text


class KisWorkflowQueueTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / ".github/workflows"
        self.files = {p.name: p.read_text(encoding="utf-8") for p in root.glob("*.yml")}

    def fixed(self):
        return {n: proposed_text(t) if n in MEMBERS else t for n, t in self.files.items()}

    def test_current_collision_is_detected_and_proposal_resolves_it(self):
        self.assertEqual(5, len(audit(self.files)))
        self.assertTrue(all("pending replacement risk" in x for x in audit(self.files)))
        self.assertEqual([], audit(self.fixed()))

    def test_proposal_preserves_every_existing_line_and_is_idempotent(self):
        before = dict(self.files)
        for name in MEMBERS:
            after = proposed_text(self.files[name])
            self.assertEqual(self.files[name], after.replace("  queue: max\n", "", 1))
            self.assertEqual(after, proposed_text(after))
        self.assertEqual(before, self.files)
        diff = proposal(self.files)
        self.assertEqual(5, diff.count("+  queue: max\n"))
        self.assertFalse(any(s.startswith("-") and not s.startswith("---") for s in diff.splitlines()))

    def test_split_group_cancel_true_and_schedule_drift_are_rejected(self):
        for old, new, message in [("group: daily-closing-price-snapshot", "group: china", "serialization"),
                                  ("cancel-in-progress: false", "cancel-in-progress: true", "protected"),
                                  ("0 22 * * 0-5", "0 23 * * 0-5", "schedule")]:
            files = self.fixed()
            files["china_candidate_prices.yml"] = files["china_candidate_prices.yml"].replace(old, new)
            self.assertTrue(any(message in x for x in audit(files)))

    def test_unknown_member_and_missing_member_need_review(self):
        files = self.fixed()
        files["extra.yml"] = files["china_candidate_prices.yml"]
        self.assertTrue(any("unreviewed" in x for x in audit(files)))
        del files["daily_prices.yml"]
        self.assertTrue(any("missing" in x for x in audit(files)))

    def test_unsupported_yaml_fails_closed(self):
        for text in ["concurrency: thing\n", "concurrency:\n  group: '${{ github.ref }}'\n",
                     "concurrency:\n  queue: max\n  queue: single\n"]:
            with self.assertRaises(ValueError):
                concurrency(text)
