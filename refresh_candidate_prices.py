"""Refresh pending candidate price history into a separate review-only file."""
from __future__ import annotations
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from data_providers import KISUSProvider
from kis_provider import KISOverseasPrices
from refresh_daily_prices import preserve_failed_symbol_history

ROOT = Path(__file__).resolve().parent
CANDIDATES = ROOT / "data" / "stock_universe_candidates.csv"
UNIVERSE = ROOT / "data" / "monitoring_universe.csv"
PRICES = ROOT / "data" / "candidate_daily_prices.csv"
STATUS = ROOT / "data" / "candidate_daily_prices_status.json"

def main() -> int:
    key, secret = os.environ.get("KIS_APP_KEY", ""), os.environ.get("KIS_APP_SECRET", "")
    if not key or not secret:
        raise RuntimeError("Repository secrets KIS_APP_KEY and KIS_APP_SECRET are required.")
    candidates = pd.read_csv(CANDIDATES, dtype={"symbol": str}).fillna("")
    universe = pd.read_csv(UNIVERSE, dtype={"symbol": str}).fillna("")
    active = set(universe["symbol"].str.strip().str.upper())
    candidates = candidates[candidates["activation_status"].eq("pending_review")].copy()
    candidates["symbol"] = candidates["symbol"].str.strip().str.upper()
    candidates = candidates[~candidates["symbol"].isin(active)].drop_duplicates("symbol")
    provider = KISUSProvider(KISOverseasPrices(app_key=key, app_secret=secret))
    frames, errors, fresh_data_symbols = [], [], []
    for i, row in enumerate(candidates.itertuples(index=False)):
        try:
            bars = provider.fetch_daily(row.symbol, market=row.market, asset_type=row.asset_type, exchange=row.exchange, max_pages=3)
            if bars.empty:
                errors.append({"symbol": row.symbol, "error": "empty_response"})
            else:
                frames.append(bars)
                fresh_data_symbols.append(row.symbol)
        except Exception as exc:
            errors.append({"symbol": row.symbol, "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
        if i + 1 < len(candidates):
            time.sleep(0.75)
    fresh = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "symbol", "open", "high", "low", "close", "volume"])
    fresh, preserved = preserve_failed_symbol_history(fresh, errors, previous_path=PRICES)
    if fresh.empty:
        # Record the failed attempt while preserving any prior snapshot.
        if PRICES.exists():
            fresh = pd.read_csv(PRICES, dtype={"symbol": str}).fillna("")
        else:
            fresh = pd.DataFrame(columns=["date", "symbol", "open", "high", "low", "close", "volume"])
    fresh["symbol"] = fresh["symbol"].astype(str).str.strip().str.upper()
    if not fresh.empty:
        fresh["date"] = pd.to_datetime(fresh["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        fresh = fresh.dropna(subset=["date"]).drop_duplicates(["symbol", "date"]).sort_values(["symbol", "date"])
    fresh.to_csv(PRICES, index=False)
    coverage = []
    for symbol, group in fresh.groupby("symbol"):
        dates = pd.to_datetime(group["date"], errors="coerce").dropna()
        coverage.append({"symbol": symbol, "rows": int(group["date"].nunique()), "first_date": dates.min().strftime("%Y-%m-%d") if not dates.empty else None, "latest_date": dates.max().strftime("%Y-%m-%d") if not dates.empty else None})
    status = {"updated_at_utc": datetime.now(timezone.utc).isoformat(), "updated_at_kst": datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Seoul")).isoformat(), "requested_symbols": int(len(candidates)), "symbols_with_data": int(fresh["symbol"].nunique()), "fresh_data_symbols": sorted(set(fresh_data_symbols)), "fresh_data_symbol_count": len(set(fresh_data_symbols)), "failed_symbols": sorted({item["symbol"] for item in errors if item.get("symbol") != "*"}), "symbols_preserved_from_previous_snapshot": preserved, "error_count": len(errors), "errors": errors, "per_symbol_coverage": coverage, "data_note": "Separate manual review snapshot; never activates candidates."}
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in status.items() if k != "errors"}, ensure_ascii=False))
    if errors:
        print("Per-symbol errors:", json.dumps(errors, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
