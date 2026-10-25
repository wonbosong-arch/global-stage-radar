"""Pure helper functions for weekly Stage Analysis; no UI or network access."""
import numpy as np
import pandas as pd


def weekly_bars(daily: pd.DataFrame, as_of_date=None, calendar_name=None):
    """Resample daily OHLCV to completed Friday-ending bars only.

    `as_of_date` is optional and mainly supports deterministic tests. The
    current week's bar is excluded through Friday; a Friday bar is complete
    on Saturday/Sunday only when Friday's data is actually present.
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

        # Never use the current week's partial bar. Also guard against stale data:
        # if the latest available session is from an earlier week but falls before
        # Friday, W-FRI would label that incomplete bar as Friday and make it look
        # like a completed weekly close. Conservatively exclude that bar too.
        if current_week_start <= latest_source_date <= as_of:
            # Friday's bar is not final during Friday itself, but is complete
            # on weekends. If the latest source date is earlier than Thursday
            # (e.g. a holiday or stale feed), conservatively exclude that week.
            current_week_is_incomplete = as_of.weekday() < 5
            if as_of.weekday() >= 5 and calendar_name:
                try:
                    import exchange_calendars as xcals
                    calendar = xcals.get_calendar(calendar_name)
                    sessions = calendar.sessions_in_range(
                        current_week_start.strftime("%Y-%m-%d"),
                        current_week_friday.strftime("%Y-%m-%d"),
                    )
                    expected_last_session = (
                        pd.Timestamp(sessions[-1]).tz_localize(None).normalize()
                        if len(sessions) else None
                    )
                    current_week_is_incomplete = (
                        expected_last_session is None
                        or latest_source_date != expected_last_session
                    )
                except Exception:
                    current_week_is_incomplete = True
            elif as_of.weekday() >= 5:
                current_week_is_incomplete = latest_source_date.weekday() < 4
            if current_week_is_incomplete:
                weekly = weekly[weekly["date"].dt.normalize() < current_week_friday].copy()
        elif latest_source_date < current_week_start and latest_source_date.weekday() < 4:
            latest_week_label = latest_source_date + pd.Timedelta(days=4 - latest_source_date.weekday())
            weekly = weekly[weekly["date"].dt.normalize() < latest_week_label].copy()

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


def is_stale_daily_data(last_date, as_of_date=None, max_age_days: int = 10) -> bool:
    """Return True when a symbol's last daily bar is too old for a current Stage label."""
    if pd.isna(last_date):
        return True
    as_of = pd.Timestamp(as_of_date).normalize() if as_of_date is not None else pd.Timestamp.today().normalize()
    last = pd.Timestamp(last_date).normalize()
    if last > as_of:
        return True
    return (as_of - last).days > max_age_days


def classify_stage(close, ma30, slope4_pct, market_rs, sector_rs, asset_type: str, symbol=None, market_benchmark=None) -> str:
    """Classify Stage using 30-week trend and country-index RS; sector_rs is ignored for now."""
    above = pd.notna(ma30) and pd.notna(close) and close > ma30
    rising = pd.notna(slope4_pct) and slope4_pct > 0
    market_outperformance = pd.notna(market_rs) and market_rs > 0
    normalized_type = str(asset_type).lower()
    if symbol is not None and market_benchmark is not None:
        # Only self-benchmarked broad-market ETFs use their own trend without RS.
        is_market_proxy = normalized_type == "market_etf" and str(symbol).strip().upper() == str(market_benchmark).strip().upper()
    else:
        # Without explicit benchmark identity, never bypass relative strength.
        # Callers must prove that a broad-market ETF is self-benchmarked.
        is_market_proxy = False

    market_condition = market_outperformance or is_market_proxy

    if above and rising and market_condition:
        return "Stage 2 후보"
    if above and pd.notna(slope4_pct) and slope4_pct > -0.5 and market_condition:
        return "Stage 2A 관찰 후보"
    if not above and pd.notna(slope4_pct) and slope4_pct < -0.5:
        return "하락 추세 관찰"
    return "중립 / 추가 확인"


def stage_label_with_data_guards(label: str, freshness_status: str, market_rs_missing: bool = False, sector_rs_missing: bool = False) -> str:
    """Withhold Stage labels when required daily or relative-strength inputs are not trustworthy."""
    if freshness_status == "asset_stale":
        return "데이터 오래됨 · 판정 보류"
    if freshness_status == "market_benchmark_stale":
        return "국가 대표지수 데이터 오래됨 · 판정 보류"
    # Sector benchmark freshness is informational while sector RS is disabled.
    if market_rs_missing:
        return "벤치마크 데이터 부족 · 판정 보류"
    return label


def stage_data_freshness_status(symbol: str, asset_type: str, market_benchmark: str, sector_benchmark: str, latest_dates: dict, as_of_date=None) -> str:
    """Return a conservative status when the asset or required benchmark is stale."""
    if is_stale_daily_data(latest_dates.get(symbol), as_of_date=as_of_date):
        return "asset_stale"
    symbol_key = str(symbol).strip().upper()
    benchmark_key = str(market_benchmark).strip().upper() if market_benchmark is not None else ""
    if benchmark_key != symbol_key and is_stale_daily_data(latest_dates.get(market_benchmark), as_of_date=as_of_date):
        return "market_benchmark_stale"
    # Sector benchmarks are metadata only; Stage decisions currently use the
    # country's representative market index exclusively.
    return "fresh"
