"""Shared normalized OHLCV contract for CSV and future market-data providers."""
import pandas as pd

PRICE_COLUMNS = ("date", "symbol", "open", "high", "low", "close", "volume")


class MarketDataError(ValueError):
    """Raised when price data cannot safely be used by the Stage engine."""


def normalize_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize a price frame and reject malformed or conflicting OHLCV rows.

    All providers should return these columns with dates normalized to pandas
    timestamps and one row per symbol/date. This is a data-quality gate, not a
    corporate-action adjustment or licensing check.
    """
    if frame is None or frame.empty:
        return pd.DataFrame(columns=list(PRICE_COLUMNS))
    d = frame.copy()
    d.columns = [str(column).strip().lower() for column in d.columns]
    missing = set(PRICE_COLUMNS) - set(d.columns)
    if missing:
        raise MarketDataError("가격 데이터 필수 열 누락: " + ", ".join(sorted(missing)))

    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d["symbol"] = d["symbol"].fillna("").astype(str).str.strip().str.upper()
    for column in ("open", "high", "low", "close", "volume"):
        d[column] = pd.to_numeric(d[column], errors="coerce")

    invalid_required = d[list(PRICE_COLUMNS)].isna().any(axis=1) | d["symbol"].eq("")
    if invalid_required.any():
        raise MarketDataError(f"날짜·종목·OHLCV 값이 누락되거나 숫자가 아닌 행이 {int(invalid_required.sum())}개 있습니다.")
    if (d[["open", "high", "low", "close"]] <= 0).any(axis=None):
        raise MarketDataError("시가·고가·저가·종가는 모두 0보다 커야 합니다.")
    if (d["volume"] < 0).any():
        raise MarketDataError("거래량은 음수일 수 없습니다.")
    invalid_ohlc = (
        (d["high"] < d[["open", "low", "close"]].max(axis=1))
        | (d["low"] > d[["open", "high", "close"]].min(axis=1))
    )
    if invalid_ohlc.any():
        raise MarketDataError(f"고가/저가가 OHLC 값과 모순되는 행이 {int(invalid_ohlc.sum())}개 있습니다.")

    duplicate_mask = d.duplicated(["symbol", "date"], keep=False)
    if duplicate_mask.any():
        duplicated = d.loc[duplicate_mask].sort_values(["symbol", "date"])
        conflicts = duplicated.groupby(["symbol", "date"], dropna=False)[list(PRICE_COLUMNS[2:])].nunique().gt(1).any(axis=1)
        if conflicts.any():
            raise MarketDataError("동일 종목·날짜에 서로 다른 가격 행이 있습니다. 중복 데이터를 확인하세요.")
        d = d.drop_duplicates(["symbol", "date"], keep="last")

    return d[list(PRICE_COLUMNS)].sort_values(["symbol", "date"]).reset_index(drop=True)



def completed_bar_cutoff_date(exchange: str, now_kst=None) -> str:
    """Return the latest date allowed for completed daily bars.

    KIS can expose the in-progress session as today's daily bar.
    Do not store that partial candle before the relevant local market has closed.
    US-listed instruments use New York session dates and a conservative 16:05
    local cutoff (including DST), rather than the date on the Korean clock.
    """
    from datetime import datetime, time, timedelta
    from zoneinfo import ZoneInfo

    now = now_kst or datetime.now(ZoneInfo("Asia/Seoul"))
    if now.tzinfo is None:
        now = now.replace(tzinfo=ZoneInfo("Asia/Seoul"))
    else:
        now = now.astimezone(ZoneInfo("Asia/Seoul"))

    close_cutoffs_kst = {
        "KRX": time(15, 35),
        "TSE": time(15, 35),
        "SHS": time(16, 5),
        "SZS": time(16, 5),
    }
    exchange = str(exchange).strip().upper()
    if exchange in {"NAS", "NYS", "AMS"}:
        now = now.astimezone(ZoneInfo("America/New_York"))
        close_time = time(16, 5)
    else:
        close_time = close_cutoffs_kst.get(exchange)
    cutoff = now.date()
    if close_time is not None and now.time().replace(tzinfo=None) < close_time:
        cutoff -= timedelta(days=1)
    # Never accept a weekend-dated daily candle for exchanges that do not trade
    # on Saturday/Sunday. Exchange holidays are handled by the provider's actual
    # available bars; this weekday guard prevents obvious weekend partial rows.
    while cutoff.weekday() >= 5:
        cutoff -= timedelta(days=1)
    return cutoff.isoformat()



def filter_incomplete_daily_bars(frame: pd.DataFrame, exchange_by_symbol: dict[str, str], now_kst=None) -> pd.DataFrame:
    """Reject incomplete local stock sessions from new or previously saved data.

    Crypto and unknown venues retain their separate calendar policies. This
    conservative cutoff does not infer holiday sessions from fabricated rows.
    """
    if frame is None or frame.empty or not {"date", "symbol"}.issubset(frame.columns):
        return frame.copy() if frame is not None else pd.DataFrame()
    supported_exchanges = {"KRX", "TSE", "SHS", "SZS", "NAS", "NYS", "AMS"}
    dates = pd.to_datetime(frame["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    symbols = frame["symbol"].astype(str).str.strip().str.upper()
    allowed = dates.notna()
    for symbol, exchange in exchange_by_symbol.items():
        exchange = str(exchange).strip().upper()
        if exchange not in supported_exchanges:
            continue
        cutoff = completed_bar_cutoff_date(exchange, now_kst=now_kst)
        mask = symbols.eq(str(symbol).strip().upper())
        allowed.loc[mask] = dates.loc[mask].notna() & dates.loc[mask].le(cutoff)
    return frame.loc[allowed].copy().reset_index(drop=True)


def filter_incomplete_asian_daily_bars(frame: pd.DataFrame, exchange_by_symbol: dict[str, str], now_kst=None) -> pd.DataFrame:
    """Legacy Asian-only filter; new callers should use the venue-aware filter."""
    asian = {symbol: exchange for symbol, exchange in exchange_by_symbol.items()
             if str(exchange).strip().upper() in {"KRX", "TSE", "SHS", "SZS"}}
    return filter_incomplete_daily_bars(frame, asian, now_kst=now_kst)
