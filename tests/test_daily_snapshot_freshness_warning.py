from pathlib import Path
import unittest


class DailySnapshotFreshnessWarningTests(unittest.TestCase):
    def test_dashboard_warns_when_snapshot_is_stale_or_has_saved_errors(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        self.assertIn("snapshot_age_hours > 36", source)
        self.assertIn("이 스냅샷의 가격·Stage 판정을 최신 시장 데이터로 간주하지 마세요.", source)
        self.assertIn("마지막 저장 스냅샷에 가격 수집 오류가 남아 있습니다:", source)
        self.assertIn("오류는 미해결 상태입니다.", source)


if __name__ == "__main__":
    unittest.main()
