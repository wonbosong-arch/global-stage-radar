from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import numpy as np
import pandas as pd
try:
    import pytest
except ImportError:
    import unittest
    raise unittest.SkipTest("pytest-only private explorer regressions")
from streamlit.testing.v1 import AppTest

from china_market_explorer import (
    HK_CHINA, HK_LARGE, HK_LOCAL, MAINLAND, CSI300, CSI300_REPORT, load_explorer, sectors_for,
)
from hong_kong_etf_research import REPORT_FILE, observe
from china_kis_stage import PRICE_FILE, prepare


NOW = datetime(2026, 11, 28, 10, tzinfo=ZoneInfo("Asia/Seoul"))
ROOT = Path(__file__).resolve().parents[1]


def history(symbol, calendar, growth):
    dates = xcals.get_calendar(calendar).sessions_in_range("2025-09-01", "2026-11-27").tz_localize(None)
    close = 10 * growth ** np.arange(len(dates))
    return pd.DataFrame(dict(symbol=symbol, date=dates, open=close, high=close * 1.01,
                             low=close * .99, close=close, volume=1000))


def store_json(path, payload):
    path.write_text(json.dumps(payload, default=str), encoding="utf-8")


@pytest.fixture
def private_reports(tmp_path):
    mainland = history("512800", "XSHG", 1.002)
    mainland.to_csv(tmp_path / PRICE_FILE, index=False)
    prepare(tmp_path, source_commit="test", observed_symbols=["512800"])
    csi300 = history(CSI300, "XSHG", 1.001)
    store_json(tmp_path / CSI300_REPORT, dict(exchange="SHS", currency="CNY", master_verified=True,
                                             price_basis="KIS_ADJUSTED", history=csi300.to_dict("records")))

    class Client:
        def daily_bars(self, symbol, **kwargs):
            return history(symbol, "XHKG", {"02800": 1.001, "02828": 1.002, "03033": 1.003}[symbol])

    histories = {}
    rows, summary = observe(Client(), {"02800", "02828", "03033"}, NOW, histories=histories)
    store_json(tmp_path / REPORT_FILE, dict(summary=summary, results=rows, histories=histories))
    fx = csi300[["date"]].assign(currency="CNY", usd_per_unit=np.linspace(.13, .15, len(csi300)))
    fx.to_csv(tmp_path / "china_market_fx.csv", index=False)
    return tmp_path


def test_private_prices_supply_same_currency_rs_and_usd_market_returns(private_reports):
    rows, histories, _ = load_explorer(private_reports, NOW)
    symbols = rows.set_index("symbol")
    mainland = sectors_for(rows, histories, MAINLAND).set_index("symbol")
    china = sectors_for(rows, histories, HK_CHINA).set_index("symbol")
    hong_kong = sectors_for(rows, histories, HK_LARGE).set_index("symbol")
    assert len(mainland) == 30
    assert len(hong_kong) == 10
    assert "03102" not in china.index and "03102" in hong_kong.index
    assert sectors_for(rows, histories, HK_LOCAL).empty
    assert mainland.at["512800", "rs_market_26w_pct"] > 0
    assert hong_kong.at["03033", "rs_market_26w_pct"] > china.at["03033", "rs_market_26w_pct"] > 0
    assert symbols.at[CSI300, "ret26_pct"] > histories[CSI300][1].iloc[-1].ret26_pct
    assert pd.isna(symbols.at["02828", "ret26_pct"])
    assert not symbols.at["03456", "stage_ready"]
    assert symbols.at["03456", "stage_label"] == "연구 관찰 · 이력 부족"

    future = NOW.replace(month=12, day=1, hour=22)
    later, later_history, notes = load_explorer(private_reports, future)
    assert not later.stage_ready.any()
    assert not sectors_for(later, later_history, MAINLAND).rs_market_26w_pct.notna().any()
    assert "홍콩 보고서 거래일 2026-11-27" in notes


def test_country_sector_stock_round_trip(monkeypatch, private_reports):
    import china_market_explorer

    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("CHINA_PRIVATE_SNAPSHOT_DIR", str(private_reports))
    load = china_market_explorer.load_explorer
    monkeypatch.setattr(china_market_explorer, "load_explorer", lambda root: load(root, NOW))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=65)
    app.secrets["APP_PASSWORD"] = "test"
    app.session_state["data_source_mode"] = "KIS API · 미국·한국"
    app.session_state["kis_authenticated"] = True
    app.session_state["active_analysis_area"] = "markets_commodities"
    app.run()
    assert not app.exception
    app.button(key="markets_commodities_selected_symbol_pick_02828").click().run()
    app.button(key="markets_commodities_open_country_sectors_02828").click().run()
    assert not app.exception
    assert app.selectbox(key="sectors_market").value == HK_CHINA
    app.button(key="sectors_selected_symbol_pick_03033").click().run()
    assert any("2828 대비" in c.value for c in app.caption)
    assert not app.exception
    app.button(key="sectors_open_stocks_03033").click().run()
    assert not app.exception
    assert any("연결된 현지 상장 개별 종목 데이터가 없습니다" in message.value for message in app.info)
    app.button(key="stocks_back_to_sectors").click().run()
    assert app.session_state["sectors_selected_symbol"] == "03033"
    app.radio(key="sectors_view_mode").set_value("3×3 차트").run()
    assert not app.exception
    app.button(key="back_to_country_list_from_sectors").click().run()
    assert not app.exception
    assert app.session_state["markets_commodities_selected_symbol"] == "02828"
