"""Refresh the separate crypto daily snapshot without using KIS stock endpoints."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from crypto_provider import CoinbaseCryptoProvider

ROOT = Path(__file__).resolve().parent
PRICES_PATH = ROOT / "data" / "crypto_daily_prices.csv"
STATUS_PATH = ROOT / "data" / "crypto_daily_prices_status.json"
SYMBOLS = ("BTC", "ETH")
HISTORY_DAYS = 1200


def main():
    provider = CoinbaseCryptoProvider()
    frames = []
    errors = []
    for symbol in SYMBOLS:
        try:
            # At 00:15 UTC the prior UTC daily candle is complete. Treat today's
            # candle as incomplete and keep it out of the Stage calculation.
            end_exclusive = pd.Timestamp(datetime.now(timezone.utc).date())
            bars = provider.fetch_daily(symbol, days=HISTORY_DAYS, end=end_exclusive)
            if bars.empty:
                errors.append({"symbol": symbol, "error": "No completed daily candles returned"})
            else:
                frames.append(bars)
        except Exception as exc:
            errors.append({"symbol": symbol, "error": f"{type(exc).__name__}: {str(exc)[:300]}"})

    existing = pd.DataFrame()
    if PRICES_PATH.exists():
        existing = pd.read_csv(PRICES_PATH, parse_dates=["date"], dtype={"symbol": str})
    fresh = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if existing.empty and fresh.empty:
        merged = pd.DataFrame(columns=["date", "symbol", "open", "high", "low", "close", "volume"])
    else:
        merged = pd.concat([existing, fresh], ignore_index=True, sort=False)
        merged["date"] = pd.to_datetime(merged["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        merged["symbol"] = merged["symbol"].astype(str).str.strip().str.upper()
        merged = merged.dropna(subset=["date"])
        merged = merged[merged["symbol"].isin(SYMBOLS)]
        merged = merged.drop_duplicates(["date", "symbol"], keep="last")
        merged = merged.sort_values(["symbol", "date"]).reset_index(drop=True)
    PRICES_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(PRICES_PATH, index=False)

    status = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Coinbase Exchange public candles",
        "symbols_requested": list(SYMBOLS),
        "symbols_with_data": sorted(merged["symbol"].unique().tolist()) if not merged.empty else [],
        "latest_date_by_symbol": (
            merged.groupby("symbol")["date"].max().to_dict() if not merged.empty else {}
        ),
        "error_count": len(errors),
        "errors": errors,
        "completed_daily_candles_only": True,
        "history_days_requested": HISTORY_DAYS,
    }
    STATUS_PATH.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    # Preserve prior history when a provider fails; only fail the workflow if
    # neither BTC nor ETH has any usable data at all.
    if not status["symbols_with_data"]:
        raise SystemExit("No crypto price history is available for BTC or ETH.")


if __name__ == "__main__":
    main()
