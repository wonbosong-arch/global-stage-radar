from datetime import date, timedelta

import exchange_calendars as xcals
import pandas as pd

from japan_sector_research import japan_research_sectors, japan_sector_representatives


def make_prices(symbol, start, end):
    sessions = xcals.get_calendar("XTKS").sessions_in_range(start, end).tz_localize(None)
    close = pd.Series(range(len(sessions)), dtype=float) + 100
    return pd.DataFrame({
        "date": sessions, "symbol": symbol, "open": close, "high": close + 1,
        "low": close - 1, "close": close, "volume": 1000,
    })


def test_japan_sector_representatives_preserve_other_markets_and_missing_representatives():
    rows = pd.DataFrame({
        "symbol": ["1615", "1631", "213A", "2644", "1615"],
        "market": ["Japan", "Japan", "Japan", "Japan", "Other"],
    })
    assert japan_sector_representatives(rows).symbol.tolist() == ["1631", "2644", "1615"]
    assert japan_sector_representatives(rows.iloc[[0, 2]]).symbol.tolist() == ["1615", "213A"]
    assert len(rows) == 5


def test_japan_research_sectors_use_topix_and_hold_short_or_invalid_data():
    cutoff = date(2026, 11, 26)
    start = cutoff - timedelta(weeks=42)
    benchmark = make_prices("1306", start, cutoff)
    comparable = make_prices("2626", start, cutoff)
    short = make_prices("513A", cutoff - timedelta(weeks=20), cutoff)
    duplicate = make_prices("2638", start, cutoff)
    gap = make_prices("2639", start, cutoff).drop(index=42)
    prices = pd.concat([benchmark, comparable, short, duplicate, duplicate.iloc[[0]], gap])

    rows, charts = japan_research_sectors(prices, cutoff + timedelta(days=1), cutoff)
    rows = rows.set_index("symbol")

    assert rows.market_benchmark.eq("1306").all()
    assert rows.asset_type.eq("research_sector_etf").all()
    assert rows.loc["2626", "rs_market_26w_pct"] == 0
    assert len(charts["2626"][1]) >= 35
    assert rows.loc["513A", "stage_label"] == "완성 주봉 부족 · 연구 보류"
    assert set(charts) == {"2626", "513A"}
    for symbol in ("2638", "2639"):
        assert rows.loc[symbol, "stage_label"] == "가격 검증 실패 · 연구 보류"
    assert rows.loc["2847", "stage_label"] == "가격 데이터 미확인 · 연구 보류"

