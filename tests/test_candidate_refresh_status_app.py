"""Render v2 diagnostics through actual Streamlit widgets without provider I/O."""
import json
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_partial_refresh_metrics_and_checkpoint_warning_survive_reruns(monkeypatch):
    def reject_network(*args, **kwargs):
        raise AssertionError("Unexpected provider request")
    monkeypatch.setattr("requests.sessions.Session.request", reject_network)
    status = {
        "status_schema_version": 2, "requested_symbols": 5, "attempted_symbol_count": 3,
        "fresh_data_symbol_count": 2, "symbols_with_data": 4,
        "error_count": 1, "failed_symbol_count": 1, "failed_symbols": ["BAD"],
        "deferred_symbols": ["LATER1", "LATER2"], "deferred_symbol_count": 2,
        "preserved_symbol_count": 2, "missing_symbol_count": 1, "skipped_symbol_count": 0,
        "refresh_complete": False, "collection_phase": "finished",
        "updated_at_utc": "2026-10-30T00:00:00+00:00",
        "errors": [{"symbol": "BAD", "category": "rate_limited", "error": "HTTP 429"}],
    }
    original = Path.read_text
    def read_text(path, *args, **kwargs):
        if path.as_posix() == "data/candidate_daily_prices_status.json":
            return json.dumps(status)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read_text)
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    app = AppTest.from_file(str(root / "app.py"), default_timeout=60).run()
    assert not app.exception
    metrics = {item.label: item.value for item in app.metric}
    assert metrics["조회 오류"] == "1"
    assert metrics["실제 조회 시도"] == "3"
    assert metrics["시간 제한 보류"] == "2"
    assert metrics["이전 이력 보존"] == "2"
    assert metrics["가격 이력 없음"] == "1"
    assert any("2개 후보 조회를 다음 실행" in warning.value for warning in app.warning)
    assert any("전체 갱신 완료: 아니오" in caption.value for caption in app.caption)
    status["collection_phase"] = "in_progress"
    app.run()
    assert not app.exception
    assert any("체크포인트" in warning.value for warning in app.warning)
