"""Date-aligned 26-week research comparisons for KIS US specialist ETFs."""
from datetime import timedelta
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from candidate_refresh_state import validate_prices
from market_data import MarketDataError, completed_bar_cutoff_date
from stage_engine import is_stale_daily_data, weekly_bars


# The KIS AMS master and quote route were checked in PRs #270 and #271.
RESEARCH_ETFS = {
    "XBI": "바이오테크",
    "KBE": "은행",
    "KIE": "보험",
}


def research_etf_weekly_history(daily, *, symbol, now):
    """Return validated completed weekly candles and the latest KIS session."""
    if symbol not in RESEARCH_ETFS or now.tzinfo is None:
        return None
    try:
        clean = validate_prices(daily, symbol)
    except MarketDataError:
        return None
    if clean.empty or len(clean) != len(daily):
        return None

    cutoff = pd.Timestamp(completed_bar_cutoff_date("AMS", now_kst=now))
    clean["date"] = pd.to_datetime(clean["date"])
    clean = clean.loc[clean.date.le(cutoff)]
    if clean.empty:
        return None
    latest = clean.date.iloc[-1]
    calendar = xcals.get_calendar("XNYS")
    expected_sessions = calendar.sessions_in_range(clean.date.iloc[0], cutoff).tz_localize(None)
    if (not pd.DatetimeIndex(clean.date).equals(expected_sessions)
            or clean.close.pct_change().abs().gt(.5).any()):
        return None

    ny_date = now.astimezone(ZoneInfo("America/New_York")).date()
    last_friday = pd.Timestamp(ny_date - timedelta(days=(ny_date.weekday() - 5) % 7 + 1))
    completed = clean.loc[clean.date.le(last_friday)]
    # KIS pagination can start midweek. Exclude that first partial candle.
    if not completed.empty:
        first_date = completed.date.iloc[0]
        first_monday = first_date - pd.Timedelta(days=first_date.weekday())
        if first_date != calendar.date_to_session(first_monday, direction="next").tz_localize(None):
            completed = completed.loc[completed.date.ge(first_monday + pd.Timedelta(weeks=1))]
    weekly = weekly_bars(completed, as_of_date=last_friday + pd.Timedelta(days=1), calendar_name="XNYS")
    if weekly is None:
        return None
    return weekly, latest.date().isoformat()


def compare_to_specialist_etf(stock_daily, etf_daily, *, stock_symbol, etf_symbol, now):
    """Compare identical completed US weeks, or return None for unusable inputs."""
    if etf_symbol not in RESEARCH_ETFS or now.tzinfo is None:
        return None
    ny_date = now.astimezone(ZoneInfo("America/New_York")).date()
    cutoff = pd.Timestamp(completed_bar_cutoff_date("AMS", now_kst=now))
    # Match the dashboard's completed-week convention, including Friday itself.
    last_friday = pd.Timestamp(ny_date - timedelta(days=(ny_date.weekday() - 5) % 7 + 1))
    first_monday = last_friday - pd.Timedelta(weeks=26, days=4)
    sessions = xcals.get_calendar("XNYS").sessions_in_range(first_monday, last_friday)
    sessions = sessions.tz_localize(None)
    week_ends = pd.Series(sessions, index=sessions).resample("W-FRI").last()
    if len(week_ends) != 27 or week_ends.isna().any():
        return None

    returns = []
    for prices, symbol in ((stock_daily, stock_symbol), (etf_daily, etf_symbol)):
        try:
            clean = validate_prices(prices, symbol)
        except MarketDataError:
            return None
        if clean.empty or len(clean) != len(prices):
            return None
        clean["date"] = pd.to_datetime(clean["date"])
        close = clean.loc[clean.date.le(cutoff)].set_index("date")["close"]
        if close.empty or is_stale_daily_data(close.index.max(), as_of_date=cutoff):
            return None
        # Each week must have its actual last session, including holiday weeks.
        weekly_close = close.reindex(week_ends.tolist())
        if (weekly_close.isna().any()
                or close.loc[week_ends.iloc[0]:].pct_change().abs().gt(.5).any()):
            return None
        returns.append(float((weekly_close.iloc[-1] / weekly_close.iloc[0] - 1) * 100))

    stock_return, etf_return = returns
    difference = stock_return - etf_return
    if not np.isfinite([stock_return, etf_return, difference]).all():
        return None
    return {
        "completed_week": last_friday.date().isoformat(),
        "latest_session": week_ends.iloc[-1].date().isoformat(),
        "stock_return_26w_pct": stock_return,
        "etf_return_26w_pct": etf_return,
        "relative_26w_pp": difference,
    }
