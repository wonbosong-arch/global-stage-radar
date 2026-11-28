from pathlib import Path
import re
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class CollectionScheduleTests(unittest.TestCase):
    def test_github_has_no_cron_schedules(self):
        for workflow in WORKFLOWS.glob("*.y*ml"):
            with self.subTest(workflow=workflow.name):
                self.assertNotRegex(workflow.read_text(encoding="utf-8"), r"(?m)^  schedule:")

    def test_coverage_report_reads_saved_data_and_has_one_automatic_route_per_producer(self):
        coverage = (WORKFLOWS / "candidate_coverage_report.yml").read_text(encoding="utf-8")
        self.assertNotIn("workflow_run:", coverage)
        self.assertNotIn("python yahoo_market_cap_supplement.py", coverage)
        for name in (
            "daily_prices", "candidate_prices_manual",
            "japan_candidate_prices", "candidate_collection", "yahoo_master_cap_batch",
        ):
            with self.subTest(workflow=name):
                workflow = (WORKFLOWS / f"{name}.yml").read_text(encoding="utf-8")
                matches = list(re.finditer(r"gh workflow run candidate_coverage_report\.yml", workflow))
                self.assertEqual(len(matches), 1)
                self.assertGreater(matches[0].start(), workflow.index("git push origin"))

    def test_china_collection_publishes_only_to_private_storage(self):
        workflow = (WORKFLOWS / "china_candidate_prices.yml").read_text(encoding="utf-8")
        self.assertIn("group: daily-closing-price-snapshot", workflow)
        self.assertIn("queue: max", workflow)
        self.assertIn("refresh_china_hong_kong_prices.py", workflow)
        self.assertNotIn("git push", workflow)
        self.assertNotIn("upload-artifact", workflow)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for the Worker dispatch test")
    def test_cloudflare_worker_dispatches_only_expected_workflows(self):
        result = subprocess.run(
            ["node", "--test", str(ROOT / "tests" / "stage-radar-scheduler.test.mjs")],
            cwd=ROOT, capture_output=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
