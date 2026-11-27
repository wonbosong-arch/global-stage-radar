import json
from functools import partial
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

import stage_engine
from market_etf_menu import market_menu_rows
from refresh_daily_prices import filter_active_universe
from universe import read_universe


ROOT = Path(__file__).resolve().parents[1]


def test_market_menu_uses_listing_venue_and_preserves_sector_benchmarks():
    universe = read_universe(ROOT / "data/monitoring_universe.csv")
    universe["asset_type_norm"] = universe["asset_type"]
    menu = market_menu_rows(universe).set_index("symbol")
    assert set(menu.index[menu["market_menu_group"].eq("글로벌 시장")]) == {"ACWI", "URTH", "IEMG"}
    targets = filter_active_universe(universe).set_index("symbol").loc[["URTH", "IEMG"]]
    assert targets["exchange"].eq("AMS").all()
    assert targets["provider"].eq("KIS").all()
    assert targets["market_benchmark"].eq("SPY").all()
    assert menu.loc[["EWJ", "EWY", "SPY", "MCHI"], "market_menu_group"].eq("국가").all()
    assert menu.loc[["GLD", "USO", "CORN"], "market_menu_group"].eq("원자재").all()
    assert {"1306", "069500", "BTC", "ETH"}.isdisjoint(menu.index)
    pd.testing.assert_series_equal(
        universe.set_index("symbol").loc[["XLB", "1615", "091160", "KWEB"], "market_benchmark"],
        pd.Series(["SPY", "1306", "069500", "MCHI"], index=pd.Index(
            ["XLB", "1615", "091160", "KWEB"], name="symbol"), name="market_benchmark"),
    )


def test_saved_market_menu_shares_chart_across_groups_and_modes(monkeypatch):
    monkeypatch.chdir(ROOT)
    read_csv = pd.read_csv
    snapshot = ROOT / "data/daily_prices.csv"

    def read_snapshot_fixture(file, *args, **kwargs):
        rows = read_csv(file, *args, **kwargs)
        if not isinstance(file, (str, Path)) or Path(file).resolve() != snapshot:
            return rows
        dates = rows.loc[rows.symbol.eq("ACWI"), "date"].reset_index(drop=True)
        fixture = []
        for symbol, start in (("URTH", 100), ("IEMG", 50)):
            close = start + dates.index.to_numpy() * 0.1
            fixture.append(pd.DataFrame({
                "date": dates, "symbol": symbol, "open": close - 0.1, "high": close + 0.3,
                "low": close - 0.2, "close": close, "volume": 100_000,
            }))
        return pd.concat([rows.loc[~rows.symbol.isin(["URTH", "IEMG"])], *fixture], ignore_index=True)

    monkeypatch.setattr(pd, "read_csv", read_snapshot_fixture)
    as_of = read_csv(snapshot)["date"].max()
    monkeypatch.setattr(
        stage_engine, "is_stale_daily_data",
        partial(stage_engine.is_stale_daily_data, as_of_date=as_of),
    )
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    app.secrets["APP_PASSWORD"] = "synthetic-test-password"
    app.session_state["data_source_mode"] = "KIS API · 미국·한국"
    app.session_state["kis_authenticated"] = True
    app.session_state["active_analysis_area"] = "markets_commodities"
    app.run()
    assert not app.exception
    acwi = app.button(key="global_market_pick_ACWI")
    assert not acwi.disabled
    assert acwi.label == "전세계"
    assert app.radio(key="markets_commodities_view_mode").value == "차트 고정 목록"
    for symbol, label in (("URTH", "선진국"), ("IEMG", "신흥국")):
        button = app.button(key=f"global_market_pick_{symbol}")
        assert not button.disabled
        assert button.label == label
        button.click().run()
        assert app.session_state["markets_commodities_selected_symbol"] == symbol
        assert app.session_state[f"markets_commodities_selected_period_{symbol}"] == "주봉"
        chart, = app.get("plotly_chart")
        assert json.loads(chart.proto.spec)["layout"]["meta"]["asset_symbol"] == symbol
        assert any(
            caption.value.startswith("Stage 2 후보 ·") and " · 기준일 " in caption.value
            for caption in app.caption
        )

    app.button(key="global_market_pick_ACWI").click().run()
    assert app.session_state["markets_commodities_selected_period_ACWI"] == "주봉"
    app.button(key="markets_commodities_selected_period_ACWI" + "_pick_daily").click().run()
    app.text_input(key="markets_commodities_search").set_value("금").run()
    gold = app.button(key="markets_commodities_selected_symbol_pick_GLD")
    assert gold.label == "금"
    gold.click().run()
    assert app.session_state["markets_commodities_selected_symbol"] == "GLD"

    app.radio(key="markets_commodities_view_mode").set_value("히트맵").run()
    assert app.session_state["markets_commodities_selected_symbol"] == "GLD"
    assert app.button(key="markets_commodities_selected_symbol_heatmap_pick_GLD")
    app.button(key="global_market_pick_ACWI").click().run()
    assert app.session_state["markets_commodities_selected_period_ACWI"] == "일봉"

    app.text_input(key="markets_commodities_search").set_value("").run()
    app.radio(key="markets_commodities_view_mode").set_value("3×3 차트").run()
    assert app.button(key="markets_commodities_grid_next")
    app.button(key="global_market_pick_IEMG").click().run()
    assert app.radio(key="markets_commodities_view_mode").value == "차트 고정 목록"
    assert app.session_state["markets_commodities_selected_period_IEMG"] == "주봉"
    app.radio(key="markets_commodities_view_mode").set_value("히트맵").run()
    app.button(key="global_market_pick_URTH").click().run()
    assert app.session_state["markets_commodities_selected_period_URTH"] == "주봉"

    for symbol, market, local_sector in (
        ("EWJ", "Japan", "1631"),
        ("EWY", "South Korea", "091160"),
        ("MCHI", "China", "KWEB"),
    ):
        app.text_input(key="markets_commodities_search").set_value(symbol).run()
        app.button(key=f"markets_commodities_selected_symbol_heatmap_pick_{symbol}").click().run()
        sector_button = app.button(key=f"markets_commodities_open_country_sectors_{symbol}")
        assert sector_button.label == "업종 보기 →"
        sector_button.click().run()
        assert app.selectbox(key="sectors_market").value == market
        assert app.button(key=f"sectors_selected_symbol_pick_{local_sector}")
        if market == "Japan":
            keys = {button.key for button in app.button}
            assert "sectors_selected_symbol_pick_2644" in keys
            assert "sectors_selected_symbol_pick_1615" not in keys
            assert "sectors_selected_symbol_pick_213A" not in keys
        app.button(key="back_to_country_list_from_sectors").click().run()
        assert app.radio(key="markets_commodities_view_mode").value == "히트맵"
        assert app.session_state["markets_commodities_selected_symbol"] == symbol
        assert not app.exception
