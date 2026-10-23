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


def main() -> int:
    key = os.environ.get("KIS_APP_KEY", "")
    secret = os.environ.get("KIS_APP_SECRET", "")
    if not key or not secret:
        raise RuntimeError("Set KIS_APP_KEY and KIS_APP_SECRET as GitHub Actions secrets.")
    universe = read_universe(UNIVERSE_PATH)
    client = KISDomesticPrices(app_key=key, app_secret=secret)
    us_provider, kr_provider = KISUSProvider(client), KISKoreaProvider(client)
    frames, errors = [], []
    for row in universe.itertuples(index=False):
        provider = kr_provider if str(row.exchange).upper() == "KRX" else us_provider
        try:
            bars = provider.fetch_daily(
                row.symbol, market=row.market, asset_type=row.asset_type,
                exchange=row.exchange, max_pages=10,
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
    prices = pd.concat(frames, ignore_index=True)
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    prices = prices.dropna(subset=["date"]).drop_duplicates(["date", "symbol"]).sort_values(["symbol", "date"])
    prices.to_csv(PRICES_PATH, index=False)
    status = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "updated_at_kst": datetime.now(timezone.utc).astimezone(__import__("zoneinfo").ZoneInfo("Asia/Seoul")).isoformat(),
        "requested_symbols": len(universe),
        "symbols_with_data": int(prices["symbol"].nunique()),
        "error_count": len(errors),
        "errors": errors,
        "data_note": "Latest available daily bars from KIS; market holidays may leave the last bar date unchanged.",
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in status.items() if k != "errors"}, ensure_ascii=False))
    if errors:
        print("Per-symbol errors:", json.dumps(errors, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
