"""Fetch Japan-listed sector/theme ETF candidates in an isolated research snapshot.

This observes route/data availability only. It never activates candidates or writes
to the active monitoring-universe price snapshot.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from data_providers import KISUSProvider
from market_data import completed_bar_cutoff_date
from kis_provider import KISOverseasPrices

ROOT = Path(__file__).resolve().parent
PRICES_PATH = ROOT / "data" / "japan_candidate_prices.csv"
STATUS_PATH = ROOT / "data" / "japan_candidate_prices_status.json"
CANDIDATES = {
    "221A": "Japan semiconductor sector ETF",
    "2626": "Japan digital innovation theme ETF",
    "2638": "Japan robotics and AI theme ETF",
    "2639": "Japan biotechnology and medtech theme ETF",
    "2645": "Japan leisure and entertainment theme ETF",
    "2646": "Japan metal business theme ETF",
    "2854": "Japan technology leaders theme ETF",
}
HISTORY_PAGES = 3
COLUMNS = ["date", "symbol", "open", "high", "low", "close", "volume"]


def merge_prices(
    existing: pd.DataFrame,
    fresh: pd.DataFrame,
    as_of_date: str | None = None,
) -> pd.DataFrame:
    """Merge observations, retain history, and reject future-dated bars."""
    frames = [frame for frame in (existing, fresh) if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=COLUMNS)
    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined["symbol"] = combined["symbol"].astype(str).str.strip().str.upper()
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    combined = combined.dropna(subset=["date"])
    cutoff = as_of_date or datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    combined = combined[combined["date"] <= cutoff]
    return combined.drop_duplicates(["symbol", "date"], keep="last").sort_values(
        ["symbol", "date"]
    ).reset_index(drop=True)


def main() -> int:
    key = os.environ.get("KIS_APP_KEY", "")
    secret = os.environ.get("KIS_APP_SECRET", "")
    if not key or not secret:
        raise RuntimeError("Set KIS_APP_KEY and KIS_APP_SECRET as GitHub Actions secrets.")

    provider = KISUSProvider(KISOverseasPrices(app_key=key, app_secret=secret))
    existing = pd.read_csv(PRICES_PATH, dtype={"symbol": str}) if PRICES_PATH.exists() else pd.DataFrame()
    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    as_of_date = now_kst.date().isoformat()
    completed_cutoff = completed_bar_cutoff_date("TSE", now_kst=now_kst)
    frames, errors, observations = [], [], []
    for symbol, scope in sorted(CANDIDATES.items()):
        try:
            bars = provider.fetch_daily(
                symbol, market="Japan", asset_type="sector_etf",
                exchange="TSE", max_pages=HISTORY_PAGES,
            )
            if bars.empty:
                errors.append({"symbol": symbol, "exchange": "TSE", "error": "empty_response"})
                observations.append({"symbol": symbol, "scope": scope, "result": "empty_response", "rows_received": 0})
                continue
            bars["symbol"] = symbol
            bars["date"] = pd.to_datetime(bars["date"], errors="coerce")
            bars = bars[bars["date"].dt.strftime("%Y-%m-%d") <= completed_cutoff].copy()
            if bars.empty:
                errors.append({"symbol": symbol, "exchange": "TSE", "error": "no_rows_on_or_before_as_of_date"})
                observations.append({"symbol": symbol, "scope": scope, "result": "no_eligible_rows", "rows_received": 0})
                continue
            frames.append(bars)
            latest = pd.to_datetime(bars["date"], errors="coerce").max()
            observations.append({
                "symbol": symbol, "scope": scope, "result": "bars_received",
                "rows_received": int(len(bars)),
                "latest_date": str(latest.date()) if pd.notna(latest) else None,
            })
        except Exception as exc:
            errors.append({"symbol": symbol, "exchange": "TSE", "error": f"{type(exc).__name__}: {str(exc)[:250]}"})
            observations.append({"symbol": symbol, "scope": scope, "result": "request_error", "rows_received": 0})

    fresh = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    merged = merge_prices(existing, fresh, as_of_date=completed_cutoff)
    merged.to_csv(PRICES_PATH, index=False)
    now = datetime.now(timezone.utc)
    status = {
        "updated_at_utc": now.isoformat(),
        "updated_at_kst": now.astimezone(ZoneInfo("Asia/Seoul")).isoformat(),
        "as_of_date_kst": as_of_date,
        "purpose": "Isolated automated price-route observation for inactive Japan-listed sector/theme ETF candidates.",
        "does_not_activate_candidates": True,
        "does_not_modify_active_daily_snapshot": True,
        "requested_symbols": len(CANDIDATES),
        "symbols_with_saved_data": int(merged[merged["symbol"].isin(CANDIDATES)]["symbol"].nunique()) if not merged.empty else 0,
        "fresh_data_symbols": sorted(set(fresh["symbol"].astype(str).str.upper())) if not fresh.empty else [],
        "fresh_data_symbol_count": int(fresh["symbol"].nunique()) if not fresh.empty else 0,
        "missing_symbols": sorted(set(CANDIDATES) - (set(merged["symbol"].astype(str).str.upper()) if not merged.empty else set())),
        "error_count": len(errors),
        "observations": observations,
        "errors": errors,
        "data_note": "Returned bars confirm only a successful response for this request; they do not establish full history, sector-index fit, data-use rights, or activation readiness.",
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in status.items() if k != "errors"}, ensure_ascii=False))
    if errors:
        print("Per-symbol errors:", json.dumps(errors, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
