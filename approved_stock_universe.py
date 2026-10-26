"""Conservative bridge from reviewed candidate records to the Stage universe.

This is a final data gate, not a substitute for the documented human review.
"""
from __future__ import annotations

import pandas as pd

REQUIRED_CANDIDATE_COLUMNS = {
    "symbol", "name", "market", "sector", "asset_type",
    "market_benchmark", "sector_benchmark", "exchange", "activation_status",
    "identity_status", "provider_status",
}
PRICE_COLUMNS = {"date", "symbol", "open", "high", "low", "close", "volume"}
MIN_DAILY_BARS = 150
MAX_STALE_DAYS = 7
MIN_STOCK_MARKET_CAP_USD = 1_000_000_000


def approved_candidates_for_stage(
    candidates: pd.DataFrame,
    price_history: pd.DataFrame,
    latest_snapshot_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Return only explicitly active candidates passing identity/provider/data gates.

    price_history must contain validated daily bars for candidates and benchmarks.
    Secondary market-cap fields (including Yahoo) are never promoted to verified.
    """
    missing = REQUIRED_CANDIDATE_COLUMNS - set(candidates.columns)
    if missing:
        raise ValueError("Missing candidate columns: " + ", ".join(sorted(missing)))
    missing_prices = PRICE_COLUMNS - set(price_history.columns)
    if missing_prices:
        raise ValueError("Missing price-history columns: " + ", ".join(sorted(missing_prices)))

    frame = candidates.copy()
    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.strip().str.upper()
    status = frame["activation_status"].fillna("").astype(str).str.strip().str.lower()
    active = frame.loc[status.eq("active")].copy()
    columns = [
        "symbol", "name", "market", "sector", "asset_type", "market_cap_usd",
        "market_benchmark", "sector_benchmark", "exchange",
    ]
    if active.empty:
        return pd.DataFrame(columns=columns)

    if active["symbol"].eq("").any() or active["symbol"].duplicated().any():
        raise ValueError("Active candidates must have unique, non-empty symbols.")

    for column in ("name", "market", "sector", "asset_type", "market_benchmark", "sector_benchmark", "exchange"):
        active[column] = active[column].fillna("").astype(str).str.strip()
    for column in ("identity_status", "provider_status"):
        active[column] = active[column].fillna("").astype(str).str.strip().str.lower()

    invalid = active[["name", "market", "sector", "asset_type", "market_benchmark", "exchange"]].eq("").any(axis=1)
    invalid |= active["asset_type"].eq("stock") & active["sector_benchmark"].eq("")
    invalid |= ~active["identity_status"].eq("verified")
    invalid |= ~active["provider_status"].eq("supported")
    # Market cap is a minimum-size screen, not an accounting audit. Prefer an
    # explicitly verified USD value; otherwise accept a positive secondary
    # USD-billions observation for the threshold screen only. This does not
    # change market_cap_status or certify the source value.
    if "market_cap_usd" in active.columns:
        cap = pd.to_numeric(active["market_cap_usd"], errors="coerce")
    else:
        cap = pd.Series(float("nan"), index=active.index)
    if "market_cap_status" in active.columns:
        cap_status = active["market_cap_status"].fillna("").astype(str).str.strip().str.lower()
    else:
        cap_status = pd.Series("", index=active.index)
    needs_screening_estimate = ~cap_status.eq("verified") | cap.isna()
    if "market_cap_usd_b_secondary" in active.columns:
        secondary_b = pd.to_numeric(active["market_cap_usd_b_secondary"], errors="coerce")
        # Field name explicitly defines USD billions; only use it when the
        # direct USD value is absent or the cap has not been formally verified.
        fallback_cap = secondary_b * 1_000_000_000
        cap = cap.where(~needs_screening_estimate, fallback_cap)
    else:
        cap = cap.where(~needs_screening_estimate, float("nan"))
    invalid |= active["asset_type"].eq("stock") & (cap.isna() | (cap <= 0) | (cap < MIN_STOCK_MARKET_CAP_USD))
    if invalid.any():
        symbols = ", ".join(active.loc[invalid, "symbol"].astype(str).tolist()[:10])
        raise ValueError("Active candidates fail identity/provider/cap/mapping gates: " + symbols)

    prices = price_history.copy()
    prices["symbol"] = prices["symbol"].fillna("").astype(str).str.strip().str.upper()
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce").dt.normalize()
    for column in ("open", "high", "low", "close", "volume"):
        prices[column] = pd.to_numeric(prices[column], errors="coerce")
    if prices["date"].isna().any() or prices[list(("open", "high", "low", "close", "volume"))].isna().any().any():
        raise ValueError("Price history contains invalid date or OHLCV values.")
    if (prices[["open", "high", "low", "close"]] <= 0).any().any() or (prices["volume"] < 0).any():
        raise ValueError("Price history contains invalid prices or negative volume.")
    if (prices["high"] < prices[["open", "close", "low"]].max(axis=1)).any() or (prices["low"] > prices[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("Price history contains inconsistent OHLC ranges.")
    if prices.duplicated(["symbol", "date"]).any():
        raise ValueError("Price history contains duplicate symbol/date bars.")

    latest = pd.Timestamp(latest_snapshot_date).normalize() if latest_snapshot_date is not None else prices["date"].max()
    if pd.isna(latest):
        raise ValueError("Price history has no usable dates.")
    required_symbols = set(active["symbol"])
    required_symbols.update(active["market_benchmark"])
    required_symbols.update(active.loc[active["asset_type"].eq("stock"), "sector_benchmark"])
    grouped = {symbol: group for symbol, group in prices.groupby("symbol")}
    for symbol in sorted(required_symbols):
        bars = grouped.get(symbol)
        if bars is None or len(bars) < MIN_DAILY_BARS:
            raise ValueError(f"Insufficient price history for {symbol}: need {MIN_DAILY_BARS} daily bars.")
        if (latest - bars["date"].max()).days > MAX_STALE_DAYS:
            raise ValueError(f"Stale price history for {symbol}: latest bar is over {MAX_STALE_DAYS} days old.")

    result = active[[
        "symbol", "name", "market", "sector", "asset_type",
        "market_benchmark", "sector_benchmark", "exchange",
    ]].copy()
    result["market_cap_usd"] = cap
    return result[columns].reset_index(drop=True)
