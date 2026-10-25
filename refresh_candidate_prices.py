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
    candidates = pd.read_csv(CANDIDATES, dtype={"symbol": str})
    universe = pd.read_csv(UNIVERSE, dtype={"symbol": str})
    # Fill only textual columns; blanket fillna("") on numeric columns emits
    # pandas compatibility warnings and may become an error in future releases.
    for frame in (candidates, universe):
        text_columns = frame.select_dtypes(include=["object", "string"]).columns
        frame[text_columns] = frame[text_columns].fillna("")
    active = set(universe["symbol"].str.strip().str.upper())
    candidates = candidates[candidates["activation_status"].eq("pending_review")].copy()
    candidates["symbol"] = candidates["symbol"].str.strip().str.upper()
    candidates = candidates[~candidates["symbol"].isin(active)].drop_duplicates("symbol")
    provider = KISUSProvider(KISOverseasPrices(app_key=key, app_secret=secret))
    frames, errors, fresh_data_symbols, provider_observations = [], [], [], []
    for i, row in enumerate(candidates.itertuples(index=False)):
        try:
            bars, exchange_used = provider.fetch_daily_with_exchange(
                row.symbol, market=row.market, asset_type=row.asset_type,
                exchange=row.exchange, max_pages=3
            )
            if bars.empty:
                errors.append({"symbol": row.symbol, "error": "empty_response"})
            else:
                frames.append(bars)
                fresh_data_symbols.append(row.symbol)
                parsed_dates = pd.to_datetime(bars["date"], errors="coerce") if "date" in bars.columns else pd.Series(dtype="datetime64[ns]")
                provider_observations.append({
                    "symbol": row.symbol,
                    "requested_exchange": str(row.exchange).strip().upper(),
                    "response_exchange": exchange_used,
                    "response_rows": int(bars["date"].nunique()) if "date" in bars.columns else int(len(bars)),
                    "latest_response_date": parsed_dates.max().strftime("%Y-%m-%d") if parsed_dates.notna().any() else None,
                    "observation_scope": "price_response_only_not_identity_verification",
                })
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
    # Replace snapshots atomically so an interrupted write cannot leave a partial CSV.
    prices_tmp = PRICES.with_suffix(PRICES.suffix + ".tmp")
    fresh.to_csv(prices_tmp, index=False)
    os.replace(prices_tmp, PRICES)
    coverage = []
    for symbol, group in fresh.groupby("symbol"):
        dates = pd.to_datetime(group["date"], errors="coerce").dropna()
        coverage.append({"symbol": symbol, "rows": int(group["date"].nunique()), "first_date": dates.min().strftime("%Y-%m-%d") if not dates.empty else None, "latest_date": dates.max().strftime("%Y-%m-%d") if not dates.empty else None})
    status = {"updated_at_utc": datetime.now(timezone.utc).isoformat(), "updated_at_kst": datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Seoul")).isoformat(), "github_run_id": os.environ.get("GITHUB_RUN_ID", ""), "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""), "github_run_url": (f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}" if os.environ.get("GITHUB_REPOSITORY") and os.environ.get("GITHUB_RUN_ID") else ""), "requested_symbols": int(len(candidates)), "symbols_with_data": len(set(fresh_data_symbols)), "snapshot_symbols_with_data": int(fresh["symbol"].nunique()), "fresh_data_symbols": sorted(set(fresh_data_symbols)), "fresh_data_symbol_count": len(set(fresh_data_symbols)), "failed_symbols": sorted({item["symbol"] for item in errors if item.get("symbol") != "*"}), "symbols_preserved_from_previous_snapshot": preserved, "error_count": len(errors), "errors": errors, "per_symbol_coverage": coverage, "provider_observations": provider_observations, "data_note": "symbols_with_data counts symbols returning data in this attempt; snapshot_symbols_with_data counts symbols in the saved snapshot, including preserved history. Exchange response metadata is diagnostic only and never verifies identity or activates candidates."}
    # Publish status atomically; readers see either the previous complete status or this complete status.
    status_tmp = STATUS.with_suffix(STATUS.suffix + ".tmp")
    status_tmp.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(status_tmp, STATUS)
    print(json.dumps({k: v for k, v in status.items() if k != "errors"}, ensure_ascii=False))
    if errors:
        print("Per-symbol errors:", json.dumps(errors, ensure_ascii=False))
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
