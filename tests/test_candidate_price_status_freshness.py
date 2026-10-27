from pathlib import Path
import unittest


class CandidatePriceStatusFreshnessTests(unittest.TestCase):
    def test_dashboard_warns_when_candidate_price_status_is_stale(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        self.assertIn("candidate_age_hours > 36", source)
        self.assertIn("신규 수집 실행 결과와 저장된 과거 가격 이력을 구분해 확인하세요.", source)
        self.assertIn("후보 가격 조회 상태의 갱신 시각을 확인할 수 없어 최신 여부를 판단할 수 없습니다.", source)


if __name__ == "__main__":
    unittest.main()
