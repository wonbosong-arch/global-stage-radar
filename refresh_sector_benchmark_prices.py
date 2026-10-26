"""Refresh KIS price history for provisional Korean sector ETF benchmarks.

This is a separate review-only snapshot. It never adds ETFs to the active universe
or approves any candidate-to-benchmark mapping.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from data_providers import KISKoreaProvider
from kis_domestic_provider import KISDomesticPrices

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "data" / "korean_sector_benchmark_candidates.csv"
PRICES = ROOT / "data" / "sector_benchmark_candidate_prices.csv"
STATUS = ROOT / "data" / "sector_benchmark_candidate_prices_status.json"


def merge_snapshot(fresh: pd.DataFrame, previous_path: Path = PRICES) -> pd.DataFrame:
    """Merge new rows with saved history; current response wins duplicate dates."""
    frames = []
    if previous_path.exists():
        try:
            old = pd.read_csv(previous_path, dtype={"symbol": str})
            if not old.empty:
                frames.append(old)
        except (OSError, ValueError, pd.errors.ParserError):
            pass
    if not fresh.empty:
        frames.append(fresh)
    if not frames:
        return pd.DataFrame(columns=["date", "symbol", "open", "high", "low", "close", "volume"])
    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined["symbol"] = combined["symbol"].astype(str).str.strip().str.upper()
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    combined = combined.dropna(subset=["date"]).drop_duplicates(["symbol", "date"], keep="last")
    return combined.sort_values(["symbol", "date"]).reset_index(drop=True)


def main() -> int:
    key, secret = os.environ.get("KIS_APP_KEY", ""), os.environ.get("KIS_APP_SECRET", "")
    if not key or not secret:
        raise RuntimeError("Repository secrets KIS_APP_KEY and KIS_APP_SECRET are required.")
    registry = pd.read_csv(REGISTRY, dtype={"symbol": str}).fillna("")
    provider = KISKoreaProvider(KISDomesticPrices(app_key=key, app_secret=secret))
    frames, errors, observations = [], [], []
    for i, row in enumerate(registry.itertuples(index=False)):
        symbol = str(row.symbol).strip().upper()
        try:
            bars = provider.fetch_daily(
                symbol, market="South Korea", asset_type="sector_etf",
                exchange="KRX", max_pages=5,
            )
            if bars.empty:
                errors.append({"symbol": symbol, "error": "empty_response"})
            else:
                bars = bars.copy()
                bars["symbol"] = symbol
                frames.append(bars)
                dates = pd.to_datetime(bars.get("date", pd.Series(dtype=str)), errors="coerce")
                observations.append({
                    "symbol": symbol,
                    "response_rows": int(dates.nunique()),
                    "latest_response_date": dates.max().strftime("%Y-%m-%d") if dates.notna().any() else None,
                    "observation_scope": "KIS_price_response_only_not_mapping_approval",
                })
        except Exception as exc:
            errors.append({"symbol": symbol, "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
        if i + 1 < len(registry):
            time.sleep(0.75)
    fresh = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["date", "symbol", "open", "high", "low", "close", "volume"]
    )
    combined = merge_snapshot(fresh)
    prices_tmp = PRICES.with_suffix(PRICES.suffix + ".tmp")
    combined.to_csv(prices_tmp, index=False)
    os.replace(prices_tmp, PRICES)
    coverage = []
    for symbol, group in combined.groupby("symbol"):
        dates = pd.to_datetime(group["date"], errors="coerce").dropna()
        coverage.append({
            "symbol": symbol,
            "rows": int(dates.nunique()),
            "first_date": dates.min().strftime("%Y-%m-%d") if not dates.empty else None,
            "latest_date": dates.max().strftime("%Y-%m-%d") if not dates.empty else None,
        })
    now = datetime.now(timezone.utc)
    status = {
        "updated_at_utc": now.isoformat(),
        "updated_at_kst": now.astimezone(ZoneInfo("Asia/Seoul")).isoformat(),
        "requested_symbols": int(len(registry)),
        "fresh_data_symbol_count": len({x["symbol"] for x in observations}),
        "fresh_data_symbols": sorted({x["symbol"] for x in observations}),
        "failed_symbols": sorted({x["symbol"] for x in errors}),
        "error_count": len(errors),
        "errors": errors,
        "per_symbol_coverage": coverage,
        "provider_observations": observations,
        "data_note": "Separate KIS price-response snapshot for provisional sector benchmarks; does not prove identity, index fit, mapping approval, or active-universe eligibility.",
    }
    status_tmp = STATUS.with_suffix(STATUS.suffix + ".tmp")
    status_tmp.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(status_tmp, STATUS)
    print(json.dumps({k: v for k, v in status.items() if k != "errors"}, ensure_ascii=False))
    if errors:
        print("Per-symbol errors:", json.dumps(errors, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
