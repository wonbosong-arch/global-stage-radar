import unittest
from pathlib import Path


class JapanCandidatePriceObservationSafetyTests(unittest.TestCase):
    def test_script_keeps_candidates_isolated_and_does_not_activate_them(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "refresh_japan_candidate_prices.py").read_text(encoding="utf-8")
        workflow = (root / ".github" / "workflows" / "japan_candidate_prices.yml").read_text(encoding="utf-8")
        for symbol in ("221A", "2626", "2638", "2639", "2645", "2646", "2854"):
            self.assertIn(f'"{symbol}"', source)
        self.assertIn("does_not_activate_candidates", source)
        self.assertIn("does_not_modify_active_daily_snapshot", source)
        self.assertIn('PRICES_PATH = ROOT / "data" / "japan_candidate_prices.csv"', source)
        self.assertIn('STATUS_PATH = ROOT / "data" / "japan_candidate_prices_status.json"', source)
        self.assertNotIn('daily_prices.csv"', source)
        self.assertNotIn('daily_prices_status.json"', source)
        self.assertIn('ref: data-validation-mvp', workflow)
        self.assertIn('cron: "0 22 * * 0-5"', workflow)
        self.assertIn("refresh_japan_candidate_prices.py", workflow)


if __name__ == "__main__":
    unittest.main()
