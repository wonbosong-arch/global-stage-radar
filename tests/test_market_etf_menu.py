from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from market_etf_menu import market_menu_rows
from universe import read_universe


ROOT = Path(__file__).resolve().parents[1]


def test_market_menu_uses_listing_venue_and_preserves_sector_benchmarks():
    universe = read_universe(ROOT / "data/monitoring_universe.csv")
    universe["asset_type_norm"] = universe["asset_type"]
    menu = market_menu_rows(universe).set_index("symbol")
    assert menu.loc["ACWI", "market_menu_group"] == "글로벌 시장"
    assert menu.loc[["EWJ", "EWY", "SPY", "MCHI"], "market_menu_group"].eq("국가").all()
    assert menu.loc[["GLD", "USO", "CORN"], "market_menu_group"].eq("원자재").all()
    assert {"1306", "069500", "BTC", "ETH", "URTH", "IEMG"}.isdisjoint(menu.index)
    pd.testing.assert_series_equal(
        universe.set_index("symbol").loc[["XLB", "1615", "091160", "KWEB"], "market_benchmark"],
        pd.Series(["SPY", "1306", "069500", "MCHI"], index=pd.Index(
            ["XLB", "1615", "091160", "KWEB"], name="symbol"), name="market_benchmark"),
    )


def test_saved_market_menu_shares_chart_across_groups_and_modes(monkeypatch):
    monkeypatch.chdir(ROOT)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    app.secrets["APP_PASSWORD"] = "synthetic-test-password"
    app.session_state["data_source_mode"] = "KIS API · 미국·한국"
    app.session_state["kis_authenticated"] = True
    app.session_state["active_analysis_area"] = "markets_commodities"
    app.run()
    assert not app.exception
    assert not app.button(key="global_market_pick_ACWI").disabled
    for symbol in ("URTH", "IEMG"):
        assert app.button(key=f"global_market_pick_{symbol}").disabled
    assert app.radio(key="markets_commodities_view_mode").value == "차트 고정 목록"

    app.button(key="global_market_pick_ACWI").click().run()
    assert app.radio(key="markets_commodities_selected_period_ACWI").value == "주봉"
    app.radio(key="markets_commodities_selected_period_ACWI").set_value("일봉").run()
    app.text_input(key="markets_commodities_search").set_value("GLD").run()
    app.button(key="markets_commodities_selected_symbol_pick_GLD").click().run()
    assert app.session_state["markets_commodities_selected_symbol"] == "GLD"

    app.radio(key="markets_commodities_view_mode").set_value("히트맵").run()
    assert app.session_state["markets_commodities_selected_symbol"] == "GLD"
    assert app.button(key="markets_commodities_selected_symbol_heatmap_pick_GLD")
    app.button(key="global_market_pick_ACWI").click().run()
    assert app.radio(key="markets_commodities_selected_period_ACWI").value == "일봉"

    for symbol, market, local_sector in (
        ("EWJ", "Japan", "1615"),
        ("EWY", "South Korea", "091160"),
        ("MCHI", "China", "KWEB"),
    ):
        app.text_input(key="markets_commodities_search").set_value(symbol).run()
        app.button(key=f"markets_commodities_selected_symbol_heatmap_pick_{symbol}").click().run()
        app.button(key=f"markets_commodities_open_country_sectors_{symbol}").click().run()
        assert app.selectbox(key="sectors_market").value == market
        assert app.button(key=f"sectors_selected_symbol_pick_{local_sector}")
        app.button(key="back_to_country_list_from_sectors").click().run()
        assert app.radio(key="markets_commodities_view_mode").value == "히트맵"
        assert app.session_state["markets_commodities_selected_symbol"] == symbol
        assert not app.exception
