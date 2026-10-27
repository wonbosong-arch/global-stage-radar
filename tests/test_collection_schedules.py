from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CollectionScheduleTests(unittest.TestCase):
    def test_primary_market_and_candidate_refreshes_share_0700_kst(self):
        paths = [
            ".github/workflows/daily_prices.yml",
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

    def test_followup_jobs_remain_after_primary_refresh(self):
        candidate_prices = (ROOT / ".github/workflows/candidate_prices_manual.yml").read_text(encoding="utf-8")
        coverage = (ROOT / ".github/workflows/candidate_coverage_report.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "5 22 * * 0-5"', candidate_prices)
        self.assertIn("07:05 KST", candidate_prices)
        self.assertIn('cron: "0 23 * * 0-5"', coverage)
        self.assertIn("08:00 KST", coverage)


if __name__ == "__main__":
    unittest.main()
