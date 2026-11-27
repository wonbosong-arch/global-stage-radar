"""Japan sector representatives and read-only TSE research ETF analysis."""
from pathlib import Path

import exchange_calendars as xcals
import pandas as pd

from candidate_refresh_state import validate_prices
from stage_engine import weekly_bars, weekly_stage_metrics
from unified_stock_explorer import stock_one_year_returns


JAPAN_MARKET_BENCHMARK = "1306"
# Keep the full TOPIX-17 series and one Japan semiconductor representative.
JAPAN_SECTOR_ALTERNATIVES = {"1615": "1631", "213A": "2644"}
JAPAN_RESEARCH_ETFS = {
    "2626": ("Global X Digital Innovation Japan ETF", "디지털 혁신"),
    "2638": ("Global X Japan Robotics & AI ETF", "로봇·AI"),
    "2639": ("Global X Japan Bio & Med Tech ETF", "바이오·의료기술"),
    "2645": ("Global X Japan Leisure & Entertainment ETF", "레저·엔터테인먼트"),
    "513A": ("Global X Japan Defense Tech ETF", "방산 기술"),
    "2847": ("Global X Japan New Growth Infrastructure ETF", "신성장 인프라"),
}
JAPAN_LIVE_RESEARCH_ETFS = ("513A", "2847")
JAPAN_RESEARCH_SNAPSHOT = Path(__file__).resolve().parent / "data" / "japan_candidate_prices.csv"


def japan_sector_representatives(rows):
    """Collapse duplicates in the sector browser when the representative is present."""
    japan = rows["market"].eq("Japan")
    symbols = set(rows.loc[japan, "symbol"])
    hidden = {symbol for symbol, representative in JAPAN_SECTOR_ALTERNATIVES.items()
              if representative in symbols}
    return rows.loc[~(japan & rows["symbol"].isin(hidden))].copy()


def japan_etf_history(raw, symbol, as_of_date, cutoff):
    """Validate the observed TSE series and return daily and completed weekly bars."""
    try:
        daily = validate_prices(raw, symbol)
        if daily.empty or len(daily) != len(raw):
            return None
        daily["date"] = pd.to_datetime(daily["date"])
        daily = daily.loc[daily.date.le(pd.Timestamp(cutoff))]
        if daily.empty:
            return None

        calendar = xcals.get_calendar("XTKS")
        expected = calendar.sessions_in_range(daily.date.iloc[0], daily.date.iloc[-1]).tz_localize(None)
        if (not pd.DatetimeIndex(daily.date).equals(expected)
                or daily.close.pct_change().abs().gt(.5).any()):
            return None
    except (ValueError, TypeError, KeyError):
        return None

    start = daily.date.iloc[0]
    monday = start - pd.Timedelta(days=start.weekday())
    first_session = calendar.date_to_session(monday, direction="next").tz_localize(None)
    complete = daily if start == first_session else daily.loc[daily.date.ge(monday + pd.Timedelta(weeks=1))]
    weekly = weekly_bars(complete, as_of_date=as_of_date, calendar_name="XTKS", min_bars=1)
    return daily, weekly, daily.date.iloc[-1].date().isoformat()


def japan_research_sectors(prices, as_of_date, cutoff):
    """Build research-only rows and charts against the saved TSE benchmark."""
    histories = {}
    for symbol, raw in prices.groupby("symbol"):
        if symbol in JAPAN_RESEARCH_ETFS or symbol == JAPAN_MARKET_BENCHMARK:
            history = japan_etf_history(raw, symbol, as_of_date, cutoff)
            if history is not None:
                histories[symbol] = history

    benchmark = histories.get(JAPAN_MARKET_BENCHMARK)
    market_weeks = {JAPAN_MARKET_BENCHMARK: benchmark[1]} if benchmark and benchmark[1] is not None else {}
    market_date = benchmark[2] if benchmark else None
    observed_symbols = set(prices["symbol"])
    rows = []
    for symbol, (name, sector) in JAPAN_RESEARCH_ETFS.items():
        history = histories.get(symbol)
        metrics = {"stage_label": "가격 데이터 미확인 · 연구 보류", "stage2_new_entry": False}
        if history is not None:
            daily, weekly, latest = history
            metrics = {
                "stage_label": "완성 주봉 부족 · 연구 보류",
                "stage2_new_entry": False,
                "last_daily_date": pd.Timestamp(latest),
                "ret1y_pct": stock_one_year_returns(daily).get(symbol),
            }
            if weekly is not None and len(weekly) >= 35:
                _, stage = weekly_stage_metrics(
                    symbol, "sector_etf", JAPAN_MARKET_BENCHMARK, "", weekly, market_weeks,
                    {JAPAN_MARKET_BENCHMARK: market_date, symbol: latest}, as_of_date=as_of_date,
                )
                metrics.update(stage)
        elif symbol in observed_symbols:
            metrics["stage_label"] = "가격 검증 실패 · 연구 보류"

        rows.append({
            "symbol": symbol, "name": name, "sector": sector, "market": "Japan",
            "exchange": "TSE", "currency": "JPY", "provider": "KIS",
            "asset_type": "research_sector_etf", "asset_type_norm": "research_sector_etf",
            "market_benchmark": JAPAN_MARKET_BENCHMARK,
            "stage_analysis_status": "일본 테마 ETF · 연구",
            "price_available": history is not None,
            **metrics,
        })
    return pd.DataFrame(rows), {symbol: history for symbol, history in histories.items()
                               if symbol in JAPAN_RESEARCH_ETFS}

