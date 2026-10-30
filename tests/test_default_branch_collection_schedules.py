"""Protect the actual default-branch dispatchers, including KST weekday boundaries."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import unittest
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DAILY = ".github/workflows/daily_prices.yml"
CANDIDATES = ".github/workflows/candidate_prices_manual.yml"
SEOUL = ZoneInfo("Asia/Seoul")


def scheduled_kst_times(path):
    text = (ROOT / path).read_text(encoding="utf-8")
    crons = re.findall(r'^\s*- cron: "([^"]+)"\s*$', text, re.MULTILINE)
    if len(crons) != 1:
        raise AssertionError("Expected one explicit dispatcher schedule")
    minute, hour, day, month, weekdays = crons[0].split()
    if (day, month) != ("*", "*"):
        raise AssertionError("Dispatcher must run throughout every month")
    first, last = map(int, weekdays.split("-"))
    start = datetime(2026, 10, 25, tzinfo=timezone.utc)  # Sunday UTC.
    return [instant.astimezone(SEOUL) for offset in range(14)
            for instant in [start + timedelta(days=offset, hours=int(hour), minutes=int(minute))]
            if first <= (instant.weekday() + 1) % 7 <= last]


class DefaultBranchCollectionScheduleTests(unittest.TestCase):
    def assert_policy(self, path, minute):
        actual = scheduled_kst_times(path)
        first_day = datetime(2026, 10, 26, 7, minute, tzinfo=SEOUL)
        expected = [first_day + timedelta(days=offset) for offset in range(14)
                    if (first_day + timedelta(days=offset)).weekday() < 6]
        self.assertEqual(actual, expected)
        self.assertFalse(any(instant.weekday() == 6 for instant in actual))

    def test_daily_dispatch_runs_monday_through_saturday_at_0700_kst(self):
        self.assert_policy(DAILY, 0)

    def test_candidate_dispatch_runs_monday_through_saturday_at_0705_kst(self):
        self.assert_policy(CANDIDATES, 5)

    def test_candidate_dispatch_stays_five_minutes_after_daily_dispatch(self):
        daily, candidates = scheduled_kst_times(DAILY), scheduled_kst_times(CANDIDATES)
        self.assertEqual(len(daily), len(candidates))
        for primary, followup in zip(daily, candidates):
            with self.subTest(day=primary.date()):
                self.assertEqual(followup - primary, timedelta(minutes=5))

    def test_dispatch_still_targets_integration_branch_with_existing_permissions(self):
        for path in (DAILY, CANDIDATES):
            with self.subTest(workflow=path):
                text = (ROOT / path).read_text(encoding="utf-8")
                payloads = re.findall(r"--data '([^']+)'", text)
                self.assertEqual([json.loads(value) for value in payloads],
                                 [{"ref": "data-validation-mvp"}])
                self.assertIn("actions: write", text)
                self.assertIn("contents: read", text)


if __name__ == "__main__":
    unittest.main()
