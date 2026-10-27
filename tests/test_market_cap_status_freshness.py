from pathlib import Path
import unittest


class MarketCapStatusFreshnessWarningTests(unittest.TestCase):
    def test_dashboard_warns_when_market_cap_progress_is_stale(self):
        app_source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        self.assertIn("status_age_hours > 36", app_source)
        self.assertIn("새 배치가 실행되기 전까지는 아래 진행률을 최신 진행 상황으로 간주하지 마세요.", app_source)
        self.assertIn("상태의 갱신 시각을 해석할 수 없어 최신 여부를 확인할 수 없습니다.", app_source)


if __name__ == "__main__":
    unittest.main()
