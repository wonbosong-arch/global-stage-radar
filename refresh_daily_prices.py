"""Fetch the curated monitoring universe once per scheduled run and persist daily bars."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from data_providers import KISUSProvider, KISKoreaProvider
from kis_domestic_provider import KISDomesticPrices
from universe import read_universe

ROOT = Path(__file__).resolve().parent
UNIVERSE_PATH = ROOT / "data" / "monitoring_universe.csv"
PRICES_PATH = ROOT / "data" / "daily_prices.csv"
STATUS_PATH = ROOT / "data" / "daily_prices_status.json"
MIN_HISTORY_BARS = 250  # ~one year of trading days, well beyond the 30-week trend window
FULL_HISTORY_PAGES = 10
LATEST_UPDATE_PAGES = 1


def merge_daily_snapshots(existing: pd.DataFrame, fresh: pd.DataFrame) -> pd.DataFrame:
    """Merge fresh KIS bars into stored history, preferring fresh duplicate rows."""
    if existing.empty:
        combined = fresh.copy()
    elif fresh.empty:
        combined = existing.copy()
    else:
        combined = pd.concat([existing, fresh], ignore_index=True, sort=False)
    if combined.empty:
        return combined
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    combined["symbol"] = combined["symbol"].astype(str).str.strip().str.upper()
    combined = combined.dropna(subset=["date"])
    combined = combined[combined["symbol"].ne("")]
    return combined.drop_duplicates(["date", "symbol"], keep="last").sort_values(
        ["symbol", "date"]
    ).reset_index(drop=True)


def pages_needed(existing_rows: int) -> int:
    """Use one recent page for established symbols; backfill more for short histories."""
    return LATEST_UPDATE_PAGES if existing_rows >= MIN_HISTORY_BARS else FULL_HISTORY_PAGES


def preserved_symbols_from_errors(existing: pd.DataFrame, errors: list[dict]) -> list[str]:
    """List symbols whose failed refresh leaves previously stored history in place."""
    if existing.empty or "symbol" not in existing.columns:
        return []
    existing_symbols = set(existing["symbol"].astype(str).str.strip().str.upper())
    return sorted({
        str(item.get("symbol", "")).strip().upper()
        for item in errors
        if str(item.get("symbol", "")).strip().upper() in existing_symbols
    })


def build_snapshot_status(universe: pd.DataFrame, fresh_prices: pd.DataFrame,
                          prices: pd.DataFrame, errors: list[dict],
                          updated_at: datetime | None = None) -> dict:
    """Summarize requested, freshly fetched, and actually available symbols separately."""
    requested = sorted(set(universe["symbol"].astype(str).str.strip().str.upper()))
    fresh = sorted(set(fresh_prices["symbol"].astype(str).str.strip().str.upper())) if not fresh_prices.empty and "symbol" in fresh_prices.columns else []
    available = sorted(set(prices["symbol"].astype(str).str.strip().str.upper())) if not prices.empty and "symbol" in prices.columns else []
    requested_set = set(requested)
    available_requested = sorted(requested_set.intersection(available))
    fresh_requested = sorted(requested_set.intersection(fresh))
    latest_dates = {}
    if not prices.empty and {"symbol", "date"}.issubset(prices.columns):
        snapshot = prices[prices["symbol"].astype(str).str.strip().str.upper().isin(requested_set)].copy()
        snapshot["date"] = pd.to_datetime(snapshot["date"], errors="coerce")
        snapshot["symbol"] = snapshot["symbol"].astype(str).str.strip().str.upper()
        latest_dates = {
            str(symbol): date.strftime("%Y-%m-%d")
            for symbol, date in snapshot.dropna(subset=["date"]).groupby("symbol")["date"].max().items()
        }
    now = updated_at or datetime.now(timezone.utc)
    return {
        "updated_at_utc": now.isoformat(),
        "updated_at_kst": now.astimezone(__import__("zoneinfo").ZoneInfo("Asia/Seoul")).isoformat(),
        "requested_symbols": len(requested),
        "requested_symbol_list": requested,
        "symbols_with_data": len(available_requested),
        "fresh_data_symbols": fresh_requested,
        "missing_symbols": sorted(requested_set.difference(available_requested)),
        "latest_date_by_symbol": latest_dates,
        "symbols_preserved_from_previous_snapshot": preserved_symbols_from_errors(prices, errors),
        "error_count": len(errors),
        "errors": errors,
        "data_note": "Latest available daily bars from KIS; market holidays may leave the last bar date unchanged.",
    }


def main() -> int:
    key = os.environ.get("KIS_APP_KEY", "")
    secret = os.environ.get("KIS_APP_SECRET", "")
    if not key or not secret:
        raise RuntimeError("Set KIS_APP_KEY and KIS_APP_SECRET as GitHub Actions secrets.")
    universe = read_universe(UNIVERSE_PATH)
    # Crypto uses its own 24/7 provider and snapshot workflow, never KIS endpoints.
    universe = universe[~universe["exchange"].astype(str).str.upper().eq("CRYPTO")].copy()
    client = KISDomesticPrices(app_key=key, app_secret=secret)
    us_provider, kr_provider = KISUSProvider(client), KISKoreaProvider(client)
    existing = pd.read_csv(PRICES_PATH) if PRICES_PATH.exists() else pd.DataFrame()
    existing_counts = (
        existing.groupby(existing["symbol"].astype(str).str.upper()).size().to_dict()
        if not existing.empty and "symbol" in existing.columns else {}
    )
    frames, errors = [], []
    for row in universe.itertuples(index=False):
        provider = kr_provider if str(row.exchange).upper() == "KRX" else us_provider
        try:
            bars = provider.fetch_daily(
                row.symbol, market=row.market, asset_type=row.asset_type,
                exchange=row.exchange,
                max_pages=pages_needed(int(existing_counts.get(str(row.symbol).upper(), 0))),
            )
            if bars.empty:
                errors.append({"symbol": row.symbol, "exchange": row.exchange, "error": "empty_response"})
                continue
            frames.append(bars)
        except Exception as exc:
            errors.append({
                "symbol": row.symbol, "exchange": row.exchange,
                "error": f"{type(exc).__name__}: {str(exc)[:250]}",
            })
    if not frames:
        raise RuntimeError("No price data was returned; preserving the previous snapshot.")
    fresh_prices = pd.concat(frames, ignore_index=True)
    prices = merge_daily_snapshots(existing, fresh_prices)
    prices.to_csv(PRICES_PATH, index=False)
    status = build_snapshot_status(universe, fresh_prices, prices, errors)
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in status.items() if k != "errors"}, ensure_ascii=False))
    if errors:
        print("Per-symbol errors:", json.dumps(errors, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
