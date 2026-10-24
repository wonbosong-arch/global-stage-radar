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


def preserve_failed_symbol_history(
    fresh_prices: pd.DataFrame,
    errors: list[dict],
    previous_path: Path = PRICES_PATH,
) -> tuple[pd.DataFrame, list[str]]:
    """Keep the last known history for symbols that failed this refresh."""
    if not errors or not previous_path.exists():
        return fresh_prices, []
    failed_symbols = {str(item.get("symbol", "")).strip() for item in errors}
    fresh_symbols = set(fresh_prices["symbol"].astype(str).str.strip())
    symbols_to_preserve = failed_symbols - fresh_symbols - {""}
    if not symbols_to_preserve:
        return fresh_prices, []
    try:
        previous = pd.read_csv(previous_path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        return fresh_prices, []
    if previous.empty or not {"symbol", "date"}.issubset(previous.columns):
        return fresh_prices, []
    previous["symbol"] = previous["symbol"].astype(str).str.strip()
    preserved = previous[previous["symbol"].isin(symbols_to_preserve)].copy()
    if preserved.empty:
        return fresh_prices, []
    combined = pd.concat([fresh_prices, preserved], ignore_index=True)
    return combined, sorted(preserved["symbol"].unique().tolist())


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
                exchange=row.exchange, max_pages=3,
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
        # Emit the captured provider failures before aborting, so Actions logs
        # distinguish authentication, throttling, and symbol-mapping problems.
        print("No symbols returned price data. Per-symbol errors:", json.dumps(errors, ensure_ascii=False))
        raise RuntimeError("No price data was returned; preserving the previous snapshot.")
    prices = pd.concat(frames, ignore_index=True)
    prices, preserved_symbols = preserve_failed_symbol_history(prices, errors)
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    prices = prices.dropna(subset=["date"]).drop_duplicates(["date", "symbol"]).sort_values(["symbol", "date"])
    prices.to_csv(PRICES_PATH, index=False)
    per_symbol = []
    for symbol, group in prices.groupby(prices["symbol"].astype(str).str.upper()):
        valid_dates = pd.to_datetime(group["date"], errors="coerce").dropna()
        per_symbol.append({
            "symbol": symbol,
            "rows": int(len(group)),
            "first_date": valid_dates.min().strftime("%Y-%m-%d") if not valid_dates.empty else None,
            "latest_date": valid_dates.max().strftime("%Y-%m-%d") if not valid_dates.empty else None,
        })
    status = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "updated_at_kst": datetime.now(timezone.utc).astimezone(__import__("zoneinfo").ZoneInfo("Asia/Seoul")).isoformat(),
        "requested_symbols": len(universe),
        "symbols_with_data": int(prices["symbol"].nunique()),
        "symbols_preserved_from_previous_snapshot": preserved_symbols,
        "error_count": len(errors),
        "errors": errors,
        "per_symbol_coverage": per_symbol,
        "data_note": "Latest available daily bars from KIS; market holidays may leave the last bar date unchanged.",
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in status.items() if k != "errors"}, ensure_ascii=False))
    if errors:
        print("Per-symbol errors:", json.dumps(errors, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
