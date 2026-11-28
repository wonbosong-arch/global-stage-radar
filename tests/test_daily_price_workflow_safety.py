"""Regression checks for daily price refresh reporting and schedule safety."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from automation.check_scheduled_daily_prices import (
    completed_symbols,
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

    def test_daily_price_workflow_limits_push_to_universe_changes_and_keeps_shared_queue(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("  push:\n    branches:\n      - data-validation-mvp\n", workflow)
        push = workflow.split("  workflow_dispatch:", 1)[0]
        self.assertIn('      - "data/monitoring_universe.csv"\n', push)
        self.assertNotIn(".py", push)
        self.assertNotIn(".yml", push)
        self.assertIn("|| 'daily-closing-price-snapshot'", workflow)
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
            self.assertRegex(
                workflow,
                rf"- name: {step}\n(?:        id: \w+\n)?"
                "        if: steps.scheduled_collection.outputs.skip != 'true'",
            )

    def test_only_complete_saved_snapshots_cover_a_scheduled_dispatch(self):
        slot = parse_scheduled_slot("2026-11-22T22:00:00Z")
        with TemporaryDirectory() as directory:
            status = Path(directory) / "status.json"
            prices = Path(directory) / "prices.csv"
            prices.write_text("saved prices", encoding="utf-8")
            for saved, expected in (
                ({"last_completed_scheduled_slot": slot.isoformat()}, True),
                ({"last_completed_scheduled_slot": "2026-11-20T22:00:00Z"}, False),
                ({"last_completed_scheduled_slot": "2026-11-22T22:13:00Z"}, False),
                ({"scheduled_slot": slot.isoformat(), "scheduled_completed_symbols": ["A"]}, False),
            ):
                with self.subTest(saved=saved):
                    status.write_text(json.dumps(saved), encoding="utf-8")
                    self.assertEqual(snapshot_covers_slot(slot, status, prices, "operating"), expected)
            prices.unlink()
            self.assertFalse(snapshot_covers_slot(slot, status, prices, "operating"))

    def test_partial_retries_only_reuse_symbols_completed_for_the_same_slot(self):
        slot = "2026-11-22T22:00:00+00:00"
        progress = {"scheduled_slot": slot, "scheduled_completed_symbols": ["A"]}
        self.assertEqual(completed_symbols(progress, slot), {"A"})
        self.assertEqual(completed_symbols(progress, "2026-11-23T22:00:00+00:00"), set())
        self.assertEqual(completed_symbols(progress, ""), set())

    def test_candidate_duplicate_guard_requires_a_saved_matching_snapshot(self):
        slot = parse_scheduled_slot("2026-11-22T22:00:19.500Z")
        with TemporaryDirectory() as directory:
            status = Path(directory) / "status.json"
            prices = Path(directory) / "prices.csv"
            prices.write_bytes(b"candidate prices")
            digest = sha256(prices.read_bytes()).hexdigest()
            for saved_slot, saved_digest, expected in (
                ("2026-11-22T22:00:00+00:00", digest, True),
                ("2026-11-23T22:00:00+00:00", digest, True),
                ("2026-11-20T22:00:00+00:00", digest, False),
                (None, digest, False),
                (slot.isoformat(), "stale", False),
            ):
                with self.subTest(saved_slot=saved_slot, saved_digest=saved_digest):
                    status.write_text(json.dumps({
                        "last_completed_scheduled_slot": saved_slot,
                        "snapshot_sha256": saved_digest,
                    }), encoding="utf-8")
                    self.assertEqual(candidate_snapshot_covers_slot(slot, status, prices), expected)

    def test_cloudflare_dispatches_keep_collection_specific_slots(self):
        for timestamp, mode, hour, minute in (
            ("2026-11-25T22:00:05.000Z", "operating", 22, 0),
            ("2026-11-25T07:30:45.000Z", "japan", 7, 30),
            ("2026-11-25T09:30:19.000Z", "china", 9, 30),
            ("2026-11-25T00:15:19.000Z", "crypto", 0, 15),
        ):
            with self.subTest(timestamp=timestamp):
                self.assertEqual(
                    parse_scheduled_slot(timestamp, mode),
                    datetime(2026, 11, 25, hour, minute, tzinfo=timezone.utc),
                )

    def test_scheduled_slot_still_rejects_future_seconds_in_the_scheduled_minute(self):
        with patch("automation.check_scheduled_daily_prices.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 11, 25, 22, 0, 44, tzinfo=timezone.utc)
            with self.assertRaises(ValueError):
                parse_scheduled_slot("2026-11-25T22:00:45.000Z")

    def test_slots_reject_old_times_and_market_weekends(self):
        for timestamp, mode in (
            ("2026-11-22T22:13:00Z", "operating"),
            ("2026-11-22T22:35:00Z", "operating"),
            ("2026-11-21T22:00:00Z", "operating"),
            ("2026-11-27T22:00:00Z", "china"),
            ("2026-11-21T09:30:00Z", "china"),
            ("2026-11-22T07:30:00Z", "japan"),
        ):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                parse_scheduled_slot(timestamp, mode)


if __name__ == "__main__":
    unittest.main()
