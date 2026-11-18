"""Research-only 26-week comparison of a US biotech stock against KIS XBI.

Only observed, date-aligned completed weekly returns are compared. This never
replaces a Stage benchmark, authorizes an ETF, or changes saved market data.
"""
from __future__ import annotations

import pandas as pd

from stage_engine import weekly_bars, relative_return_difference, is_stale_daily_data


def compare_biotech_to_xbi(stock_daily: pd.DataFrame, xbi_daily: pd.DataFrame,
                           *, as_of_date=None) -> dict | None:
    """Return aligned stock / XBI 26-week returns, or None if unsafe to compare."""
    as_of = pd.Timestamp(as_of_date or pd.Timestamp.today()).normalize()
    frames = []
    required = {"date", "open", "high", "low", "close", "volume"}
    for source in (stock_daily, xbi_daily):
        if source is None or source.empty or not required.issubset(source.columns):
            return None
        frame = source.copy()
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        for field in ("open", "high", "low", "close", "volume"):
            frame[field] = pd.to_numeric(frame[field], errors="coerce")
        frame = frame.loc[frame["date"].notna() & frame["date"].le(as_of)].copy()
        if len(frame) < 35 or frame["date"].duplicated().any():
            return None
        if (frame[["open", "high", "low", "close", "volume"]].isna().any().any()
                or frame[["open", "high", "low", "close"]].le(0).any().any()
                or frame["volume"].lt(0).any()):
            return None
        if (frame["high"].lt(frame[["open", "close", "low"]].max(axis=1)).any()
                or frame["low"].gt(frame[["open", "close", "high"]].min(axis=1)).any()):
            return None
        if is_stale_daily_data(frame.date.max(), as_of_date=as_of, max_age_days=10):
            return None
        weekly = weekly_bars(frame, as_of_date=as_of, min_bars=35)
        if weekly is None or weekly.empty:
            return None
        frames.append(weekly)

    stock, xbi = frames
    # Never compare an ETF's latest week with the stock's older week.
    common = pd.DatetimeIndex(stock.date).intersection(pd.DatetimeIndex(xbi.date))
    if common.empty:
        return None
    end = common.max()
    if (as_of - end).days > 14:
        return None
    stock_index = stock.set_index("date")
    xbi_index = xbi.set_index("date")
    if end not in stock_index.index or end not in xbi_index.index:
        return None
    stock_ret = stock_index.loc[end, "ret26_pct"]
    xbi_ret = xbi_index.loc[end, "ret26_pct"]
    difference = relative_return_difference(stock, xbi, weeks=26).loc[end]
    if any(pd.isna(v) for v in (stock_ret, xbi_ret, difference)):
        return None
    return {
        "completed_week": end.date().isoformat(),
        "stock_return_26w_pct": float(stock_ret),
        "xbi_return_26w_pct": float(xbi_ret),
        "relative_26w_pp": float(difference),
        "stage_benchmark_changed": False,
    }
