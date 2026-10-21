"""Pure helper functions for weekly Stage Analysis; no UI or network access."""
import numpy as np
import pandas as pd


def weekly_bars(daily: pd.DataFrame):
    """Resample daily OHLCV rows to Friday-ending weekly bars."""
    frame = daily.copy().sort_values("date").set_index("date")
    weekly = frame.resample("W-FRI").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna(subset=["close"]).reset_index()

    # Do not classify from a still-forming current week. The W-FRI label
    # can be in the future when today's data arrives Monday through Thursday.
    if not weekly.empty and weekly["date"].max().normalize() > pd.Timestamp.today().normalize():
        weekly = weekly[weekly["date"] <= pd.Timestamp.today().normalize()].copy()

    if len(weekly) < 35:
        return None
    weekly["ma30"] = weekly["close"].rolling(30, min_periods=30).mean()
    weekly["slope4_pct"] = (weekly["ma30"] / weekly["ma30"].shift(4) - 1) * 100
    weekly["ret13_pct"] = weekly["close"].pct_change(13) * 100
    weekly["ret26_pct"] = weekly["close"].pct_change(26) * 100
    weekly["vol_ratio"] = weekly["volume"] / weekly["volume"].rolling(10, min_periods=10).mean()
    return weekly


def relative_return_difference(asset_weekly: pd.DataFrame, benchmark_weekly: pd.DataFrame, weeks: int = 26) -> pd.Series:
    """Asset minus benchmark cumulative return over the same number of weekly bars, in percentage points."""
    asset_returns = asset_weekly.set_index("date")["close"].pct_change(weeks) * 100
    benchmark_returns = benchmark_weekly.set_index("date")["close"].pct_change(weeks) * 100
    return asset_returns - benchmark_returns.reindex(asset_returns.index)


def classify_stage(close, ma30, slope4_pct, market_rs, sector_rs, asset_type: str) -> str:
    """Internal heuristic labels, not official Weinstein labels or validated trade signals."""
    above = pd.notna(ma30) and pd.notna(close) and close > ma30
    rising = pd.notna(slope4_pct) and slope4_pct > 0
    market_outperformance = pd.notna(market_rs) and market_rs > 0
    sector_outperformance = pd.notna(sector_rs) and sector_rs > 0
    normalized_type = str(asset_type).lower()
    is_stock = normalized_type == "stock"
    is_market_proxy = normalized_type == "market_etf"

    # A broad-market proxy cannot outperform itself; classify its own trend
    # without requiring a relative-strength value against itself.
    market_condition = market_outperformance or is_market_proxy

    if above and rising and market_condition and (sector_outperformance if is_stock else True):
        return "Stage 2 후보"
    if above and pd.notna(slope4_pct) and slope4_pct > -0.5 and market_condition:
        return "Stage 2A 관찰 후보"
    if not above and pd.notna(slope4_pct) and slope4_pct < -0.5:
        return "하락 추세 관찰"
    return "중립 / 추가 확인"
