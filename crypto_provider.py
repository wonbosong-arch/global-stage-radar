"""Public Coinbase Exchange daily candles for crypto research assets.

This adapter is intentionally separate from KIS: crypto trades 24/7 and must
not be sent to stock-exchange endpoints. Check Coinbase API terms and availability
before using this source in a hosted deployment.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from market_data import normalize_ohlcv


COINBASE_PRODUCTS = {"BTC": "BTC-USD", "ETH": "ETH-USD"}
CANDLES_URL = "https://api.exchange.coinbase.com/products/{product}/candles"
CANDLE_SECONDS = 86400
MAX_CANDLES_PER_REQUEST = 300


class CryptoProviderError(RuntimeError):
    """Raised when a crypto market-data request fails or returns invalid data."""


class CoinbaseCryptoProvider:
    """Fetch daily USD OHLCV bars for Bitcoin and Ethereum from Coinbase Exchange."""

    def __init__(self, session=None, timeout=20):
        self.session = session or requests.Session()
        self.timeout = timeout

    def supports(self, symbol: str) -> bool:
        return str(symbol).strip().upper() in COINBASE_PRODUCTS

    def fetch_daily(self, symbol: str, days: int = 1200, end=None) -> pd.DataFrame:
        normalized_symbol = str(symbol).strip().upper()
        if normalized_symbol not in COINBASE_PRODUCTS:
            raise ValueError(f"Unsupported crypto symbol: {symbol!r}. Supported: BTC, ETH.")
        if int(days) < 1:
            raise ValueError("days must be a positive integer")

        product = COINBASE_PRODUCTS[normalized_symbol]
        end_dt = self._utc_datetime(end) if end is not None else datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=int(days))
        frames = []
        cursor = start_dt
        while cursor < end_dt:
            chunk_end = min(
                end_dt,
                cursor + timedelta(days=MAX_CANDLES_PER_REQUEST - 1),
            )
            params = {
                "granularity": CANDLE_SECONDS,
                "start": cursor.isoformat().replace("+00:00", "Z"),
                "end": chunk_end.isoformat().replace("+00:00", "Z"),
            }
            try:
                response = self.session.get(
                    CANDLES_URL.format(product=product),
                    params=params,
                    headers={"Accept": "application/json", "User-Agent": "GlobalStageAnalysis/1.0"},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:
                raise CryptoProviderError(
                    f"Coinbase daily candles failed for {normalized_symbol}: {exc}"
                ) from exc
            if not isinstance(payload, list):
                raise CryptoProviderError(f"Unexpected Coinbase candle response for {normalized_symbol}.")
            if payload:
                frame = pd.DataFrame(
                    payload,
                    columns=["timestamp", "low", "high", "open", "close", "volume"],
                )
                frame["date"] = pd.to_datetime(frame["timestamp"], unit="s", utc=True).dt.tz_convert(None)
                frame["symbol"] = normalized_symbol
                frames.append(frame[["date", "symbol", "open", "high", "low", "close", "volume"]])
            cursor = chunk_end + timedelta(days=1)

        if not frames:
            return normalize_ohlcv(pd.DataFrame(columns=[
                "date", "symbol", "open", "high", "low", "close", "volume"
            ]))
        result = normalize_ohlcv(pd.concat(frames, ignore_index=True))
        result = result[result["date"].ge(pd.Timestamp(start_dt.date()))]
        result = result[result["date"].lt(pd.Timestamp(end_dt.date()) + pd.Timedelta(days=1))]
        return result.drop_duplicates(subset=["symbol", "date"], keep="last").sort_values("date").reset_index(drop=True)

    @staticmethod
    def _utc_datetime(value):
        stamp = pd.Timestamp(value)
        if stamp.tzinfo is None:
            stamp = stamp.tz_localize("UTC")
        else:
            stamp = stamp.tz_convert("UTC")
        return stamp.to_pydatetime()
