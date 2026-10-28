"""Fetch mainland China ETF candidates separately from the active daily snapshot.

This is an automated, isolated route-availability observation. It never activates
symbols or writes to data/daily_prices.csv / data/daily_prices_status.json.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

import pandas as pd

from data_providers import KISUSProvider
from market_data import completed_bar_cutoff_date
from kis_domestic_provider import KISDomesticPrices

ROOT = Path(__file__).resolve().parent
UNIVERSE_PATH = ROOT / "data" / "monitoring_universe.csv"
PRICES_PATH = ROOT / "data" / "china_candidate_prices.csv"
STATUS_PATH = ROOT / "data" / "china_candidate_prices_status.json"
MANIFEST_PATH = ROOT / "data" / "china_candidate_observation_manifest.csv"
CANDIDATE_SYMBOLS = set(
    pd.read_csv(MANIFEST_PATH, dtype={"symbol": str})["symbol"]
    .fillna("").astype(str).str.strip().str.upper()
)
HISTORY_PAGES = 3


def merge_prices(existing: pd.DataFrame, fresh: pd.DataFrame) -> pd.DataFrame:
    """Merge observations while retaining previously fetched history."""
    frames = [frame for frame in (existing, fresh) if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=["date", "symbol", "open", "high", "low", "close", "volume"])
    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined["symbol"] = combined["symbol"].astype(str).str.strip().str.upper()
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    combined = combined.dropna(subset=["date"])
    return combined.drop_duplicates(["symbol", "date"], keep="last").sort_values(
        ["symbol", "date"]
    ).reset_index(drop=True)


def main() -> int:
    key, secret = os.environ.get("KIS_APP_KEY", ""), os.environ.get("KIS_APP_SECRET", "")
    if not key or not secret:
        raise RuntimeError("Set KIS_APP_KEY and KIS_APP_SECRET as GitHub Actions secrets.")

    universe = pd.read_csv(UNIVERSE_PATH, dtype={"symbol": str})
    universe["symbol"] = universe["symbol"].fillna("").astype(str).str.strip().str.upper()
    universe["exchange"] = universe["exchange"].fillna("").astype(str).str.strip().str.upper()
    universe["active_norm"] = universe["active"].fillna("").astype(str).str.strip().str.lower()
    candidates = universe[
        universe["symbol"].isin(CANDIDATE_SYMBOLS)
        & universe["exchange"].isin(["SHS", "SZS"])
        & universe["active_norm"].isin(["false", "0", "no"])
    ].copy()
    found = set(candidates["symbol"])
    missing_config = sorted(CANDIDATE_SYMBOLS - found)
    if missing_config:
        raise RuntimeError("China candidate configuration missing or unexpectedly active: " + ", ".join(missing_config))

    client = KISDomesticPrices(app_key=key, app_secret=secret)
    provider = KISUSProvider(client)
    existing = pd.read_csv(PRICES_PATH, dtype={"symbol": str}) if PRICES_PATH.exists() else pd.DataFrame()
    frames, errors, observations = [], [], []
    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    for row in candidates.sort_values("symbol").itertuples(index=False):
        symbol, exchange = str(row.symbol), str(row.exchange)
        try:
            bars = provider.fetch_daily(
                symbol, market="China", asset_type=str(row.asset_type),
                exchange=exchange, max_pages=HISTORY_PAGES,
            )
            if bars.empty:
                errors.append({"symbol": symbol, "exchange": exchange, "error": "empty_response"})
                observations.append({"symbol": symbol, "exchange": exchange, "result": "empty_response", "rows_received": 0})
                continue
            bars["symbol"] = symbol
            bars["date"] = pd.to_datetime(bars["date"], errors="coerce")
            completed_cutoff = completed_bar_cutoff_date(exchange, now_kst=now_kst)
            bars = bars[bars["date"].dt.strftime("%Y-%m-%d") <= completed_cutoff].copy()
            if bars.empty:
                errors.append({"symbol": symbol, "exchange": exchange, "error": "no_completed_daily_bars_yet"})
                observations.append({"symbol": symbol, "exchange": exchange, "result": "no_completed_daily_bars_yet", "rows_received": 0})
                continue
            frames.append(bars)
            observations.append({
                "symbol": symbol, "exchange": exchange, "result": "bars_received",
                "rows_received": int(len(bars)),
                "latest_date": str(pd.to_datetime(bars["date"], errors="coerce").max().date()),
            })
        except Exception as exc:
            errors.append({"symbol": symbol, "exchange": exchange, "error": f"{type(exc).__name__}: {str(exc)[:250]}"})
            observations.append({"symbol": symbol, "exchange": exchange, "result": "request_error", "rows_received": 0})

    fresh = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    merged = merge_prices(existing, fresh)
    if not merged.empty:
        merged_dates = pd.to_datetime(merged["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        allowed = pd.Series(True, index=merged.index)
        for row in candidates.itertuples(index=False):
            symbol, exchange = str(row.symbol), str(row.exchange)
            cutoff = completed_bar_cutoff_date(exchange, now_kst=now_kst)
            mask = merged["symbol"].astype(str).str.strip().str.upper().eq(symbol)
            allowed.loc[mask] = merged_dates.loc[mask].le(cutoff)
        merged = merged.loc[allowed].reset_index(drop=True)
    merged.to_csv(PRICES_PATH, index=False)
    now = datetime.now(timezone.utc)
    status = {
        "updated_at_utc": now.isoformat(),
        "updated_at_kst": now.astimezone(__import__("zoneinfo").ZoneInfo("Asia/Seoul")).isoformat(),
        "purpose": "Isolated automated price-route observation for inactive mainland China ETF candidates.",
        "does_not_activate_candidates": True,
        "does_not_modify_active_daily_snapshot": True,
        "requested_symbols": len(candidates),
        "symbols_with_data": int(merged[merged["symbol"].isin(CANDIDATE_SYMBOLS)]["symbol"].nunique()) if not merged.empty else 0,
        "fresh_data_symbols": sorted(set(fresh["symbol"].astype(str).str.upper())) if not fresh.empty else [],
        "fresh_data_symbol_count": int(fresh["symbol"].nunique()) if not fresh.empty else 0,
        "missing_symbols": sorted(CANDIDATE_SYMBOLS - (set(merged["symbol"].astype(str).str.upper()) if not merged.empty else set())),
        "error_count": len(errors),
        "observations": observations,
        "errors": errors,
        "data_note": "A returned bar confirms only that KIS returned data for that request; it does not establish complete history, instrument identity, or activation readiness.",
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in status.items() if k != "errors"}, ensure_ascii=False))
    if errors:
        print("Per-symbol errors:", json.dumps(errors, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
