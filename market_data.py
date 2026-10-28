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

    KIS can expose the in-progress Asian-market session as today's daily bar.
    Do not store that partial candle before the relevant local market has closed.
    US-listed instruments use their exchange-local bar dates and are not affected
    by this KST-based cutoff.
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
    close_time = close_cutoffs_kst.get(str(exchange).strip().upper())
    if close_time is not None and now.time().replace(tzinfo=None) < close_time:
        return (now.date() - timedelta(days=1)).isoformat()
    return now.date().isoformat()
