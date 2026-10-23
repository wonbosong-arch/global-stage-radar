"""Pure helper functions for weekly Stage Analysis; no UI or network access."""
import numpy as np
import pandas as pd


def weekly_bars(daily: pd.DataFrame, as_of_date=None):
    """Resample daily OHLCV to completed Friday-ending bars only.

    `as_of_date` is optional and mainly supports deterministic tests. The
    current week's bar is excluded even on Friday, when it may still be forming.
    """
    frame = daily.copy().sort_values("date").set_index("date")
    weekly = frame.resample("W-FRI").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna(subset=["close"]).reset_index()

    # W-FRI assigns the current week's partial data a Friday label. Drop
    # that bar for the entire current week, including Friday, to avoid signals
    # changing during the session. Keep the last bar for historical datasets.
    as_of = pd.Timestamp(as_of_date).normalize() if as_of_date is not None else pd.Timestamp.today().normalize()
    source_dates = pd.to_datetime(daily["date"], errors="coerce").dropna()
    if not source_dates.empty:
        latest_source_date = source_dates.max().normalize()
        current_week_start = as_of - pd.Timedelta(days=as_of.weekday())
        current_week_friday = current_week_start + pd.Timedelta(days=4)
        if current_week_start <= latest_source_date <= as_of:
            weekly = weekly[weekly["date"].dt.normalize() < current_week_friday].copy()
        weekly = weekly[weekly["date"].dt.normalize() <= as_of].copy()

    if len(weekly) < 35:
        return None
    weekly["ma30"] = weekly["close"].rolling(30, min_periods=30).mean()
    weekly["slope4_pct"] = (weekly["ma30"] / weekly["ma30"].shift(4) - 1) * 100
    weekly["ret13_pct"] = weekly["close"].pct_change(13) * 100
    weekly["ret26_pct"] = weekly["close"].pct_change(26) * 100
    weekly["vol_ratio"] = weekly["volume"] / weekly["volume"].rolling(10, min_periods=10).mean()
    return weekly



def volume_confirmation(volume_ratio) -> str:
    """Soft volume context for Stage review; never a standalone pass/fail condition.

    vol_ratio is the current bar's volume divided by its rolling 10-bar average.
    Thresholds are descriptive heuristics, not statistically validated cutoffs.
    """
    if pd.isna(volume_ratio):
        return "거래량 데이터 부족"
    ratio = float(volume_ratio)
    if ratio >= 1.5:
        return "거래량 동반 · 추세 보강"
    if ratio < 0.7:
        return "거래량 약함 · 참고만"
    return "거래량 보통"

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
