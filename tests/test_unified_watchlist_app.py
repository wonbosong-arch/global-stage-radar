from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_shared_star_grid_and_independent_watchlist_filters(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    def no_provider(*args, **kwargs):
        raise AssertionError("UI tests must not request provider data")
    monkeypatch.setattr("requests.sessions.Session.request", no_provider)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=60).run()
    app.radio(key="active_analysis_area").set_value("stocks").run()
    symbol = app.session_state["stocks_selected_symbol"]
    app.button(key="stocks_favorite").click().run()
    records = app.session_state["analysis_favorite_assets"]
    assert len(records) == 1 and records[0]["symbol"] == symbol
    selected = app.session_state["stocks_selected_symbol"]
    app.radio(key="stocks_view_mode").set_value("3×3 차트").run()
    assert app.button(key=f"stocks_grid_{symbol}_favorite").label.startswith("★")
    assert app.session_state["stocks_selected_symbol"] == selected
    app.radio(key="active_analysis_area").set_value("favorites").run()
    assert not app.exception
    assert app.selectbox(key="favorites_sort").value == "26주 절대 수익률순"
    app.selectbox(key="favorites_area_filter").set_value("업종").run()
    assert any("현재 필터" in item.value for item in app.info)
    assert app.session_state["analysis_favorite_assets"] == records
    app.selectbox(key="favorites_area_filter").set_value("종목").run()
    app.radio(key="favorites_view_mode").set_value("3×3 차트").run()
    assert app.button(key=f"favorites_grid_{records[0]['id']}_favorite").label.startswith("★")
    app.button(key=f"favorites_grid_{records[0]['id']}_favorite").click().run()
    assert not app.session_state["analysis_favorite_assets"]
    app.radio(key="active_analysis_area").set_value("stocks").run()
    assert app.radio(key="stocks_view_mode").value == "3×3 차트"
    assert app.button(key=f"stocks_grid_{symbol}_favorite").label.startswith("☆")
    assert not app.exception


def test_missing_prices_and_legacy_bookmarks_survive_reruns(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=60)
    app.session_state["analysis_favorites"] = ["ALFA", "MISSING"]
    app.session_state["active_analysis_area"] = "favorites"
    app.run()
    assert not app.exception
    records = app.session_state["analysis_favorite_assets"]
    assert {r["symbol"] for r in records} == {"ALFA", "MISSING"}
    app.session_state["favorites_selected_id"] = "UNSPECIFIED:MISSING"
    app.run()
    assert any("현재 가격 데이터가 없습니다" in item.value for item in app.info)
    app.radio(key="active_analysis_area").set_value("stage2").run()
    app.selectbox(key="candidate_quick_stage").set_value("Stage 2A만").run()
    app.radio(key="active_analysis_area").set_value("favorites").run()
    assert {r["symbol"] for r in app.session_state["analysis_favorite_assets"]} == {"ALFA", "MISSING"}
    assert not app.exception
