"""Regression checks for daily price refresh reporting and schedule safety."""
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from automation.check_scheduled_daily_prices import (
    candidate_snapshot_covers_slot,
    parse_scheduled_slot,
    snapshot_covers_slot,
)


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

    def test_scheduled_collection_checks_saved_status_before_fetch_or_publish(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("    inputs:\n      scheduled_at:\n", workflow)
        self.assertIn("SCHEDULED_AT: ${{ inputs.scheduled_at }}", workflow)
        self.assertLess(workflow.index("id: scheduled_collection"), workflow.index("id: refresh_prices"))
        for step in ("Fetch latest daily bars", "Commit updated snapshot when changed"):
            self.assertIn(f"- name: {step}\n        if: steps.scheduled_collection.outputs.skip != 'true'", workflow)

    def test_only_complete_recent_snapshots_cover_a_scheduled_dispatch(self):
        slot = "2026-11-22T22:13:00.000Z"
        complete = {
            "updated_at_utc": "2026-11-22T22:16:00+00:00",
            "requested_symbols": 2,
            "fresh_data_symbols": ["A", "B"],
            "symbols_with_data": 2,
            "errors": [],
        }
        cases = [
            ("completed duplicate", slot, {}, True),
            ("recent push or manual save", slot, {"updated_at_utc": "2026-11-22T22:00:00+00:00"}, True),
            ("stale save", slot, {"updated_at_utc": "2026-11-22T21:42:59+00:00"}, False),
            ("partial save", slot, {"fresh_data_symbols": ["A"], "errors": [{"symbol": "B"}]}, False),
            ("manual or push event", "", {}, False),
        ]
        with TemporaryDirectory() as directory:
            status = Path(directory) / "status.json"
            self.assertFalse(snapshot_covers_slot(slot, status))
            for label, scheduled_at, changes, expected in cases:
                with self.subTest(label=label):
                    status.write_text(json.dumps(complete | changes), encoding="utf-8")
                    self.assertEqual(snapshot_covers_slot(scheduled_at, status), expected)
            with self.assertRaises(ValueError):
                snapshot_covers_slot("2026-11-21T22:13:00.000Z", status)

    def test_candidate_duplicate_guard_requires_a_saved_matching_snapshot(self):
        slot = parse_scheduled_slot("2026-11-22T22:35:00.000Z", 35)
        with TemporaryDirectory() as directory:
            status = Path(directory) / "status.json"
            prices = Path(directory) / "prices.csv"
            prices.write_bytes(b"candidate prices")
            digest = sha256(prices.read_bytes()).hexdigest()
            for saved_slot, saved_digest, expected in (
                (slot.isoformat(), digest, True),
                ("2026-11-23T22:35:00+00:00", digest, True),
                ("2026-11-20T22:35:00+00:00", digest, False),
                (None, digest, False),
                (slot.isoformat(), "stale", False),
            ):
                with self.subTest(saved_slot=saved_slot, saved_digest=saved_digest):
                    status.write_text(json.dumps({
                        "last_completed_scheduled_slot": saved_slot,
                        "snapshot_sha256": saved_digest,
                    }), encoding="utf-8")
                    self.assertEqual(candidate_snapshot_covers_slot(slot, status, prices), expected)

    def test_candidate_slot_rejects_operating_price_time_and_sunday_kst(self):
        for timestamp in ("2026-11-22T22:13:00.000Z", "2026-11-21T22:35:00.000Z"):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                parse_scheduled_slot(timestamp, 35)


if __name__ == "__main__":
    unittest.main()
