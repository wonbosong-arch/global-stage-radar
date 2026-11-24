from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CollectionScheduleTests(unittest.TestCase):
    def test_other_collection_jobs_keep_their_0700_kst_schedule(self):
        paths = [
            ".github/workflows/japan_candidate_prices.yml",
            ".github/workflows/china_candidate_prices.yml",
            ".github/workflows/candidate_collection.yml",
            ".github/workflows/yahoo_master_cap_batch.yml",
            ".github/workflows/crypto_prices.yml",
        ]
        for relative in paths:
            with self.subTest(workflow=relative):
                workflow = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn('cron: "0 22 * * 0-5"', workflow)
                self.assertIn("07:00 KST", workflow)

    def test_daily_and_candidate_price_refreshes_are_staggered(self):
        daily_prices = (ROOT / ".github/workflows/daily_prices.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "13 22 * * 0-5"', daily_prices)
        self.assertIn("07:13 KST", daily_prices)

        candidate_prices = (ROOT / ".github/workflows/candidate_prices_manual.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "35 22 * * 0-5"', candidate_prices)
        self.assertIn("07:35 KST", candidate_prices)

    def test_coverage_report_keeps_its_0700_kst_schedule(self):
        coverage = (ROOT / ".github/workflows/candidate_coverage_report.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "0 22 * * 0-5"', coverage)
        self.assertIn("07:00 KST", coverage)


if __name__ == "__main__":
    unittest.main()
