"""Provider contracts and adapters for normalized daily market data."""
from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from market_data import normalize_ohlcv
from kis_provider import KISOverseasPrices


@dataclass(frozen=True)
class ProviderCapabilities:
    name: str
    markets: tuple[str, ...]
    asset_types: tuple[str, ...]
    description: str


class PriceProvider(Protocol):
    """Common interface expected from each source-specific price adapter."""

    capabilities: ProviderCapabilities

    def supports(self, market: str, asset_type: str) -> bool:
        ...

    def fetch_daily(
        self,
        symbol: str,
        market: str,
        asset_type: str,
        exchange: str,
        max_pages: int = 10,
    ) -> pd.DataFrame:
        ...


class KISUSProvider:
    """KIS daily-price adapter limited to US-listed stocks and ETFs."""

    capabilities = ProviderCapabilities(
        name="KIS US daily prices",
        markets=("United States",),
        asset_types=("stock", "market_etf", "sector_etf"),
        description="Small-watchlist pilot; does not provide global markets or verified commodity futures.",
    )

    def __init__(self, client: KISOverseasPrices):
        self.client = client

    def supports(self, market: str, asset_type: str) -> bool:
        normalized_market = str(market).strip().lower()
        normalized_type = str(asset_type).strip().lower()
        return (
            normalized_market in {"united states", "us", "usa", "미국"}
            and normalized_type in self.capabilities.asset_types
        )

    def fetch_daily(
        self,
        symbol: str,
        market: str,
        asset_type: str,
        exchange: str,
        max_pages: int = 10,
    ) -> pd.DataFrame:
        if not self.supports(market, asset_type):
            raise ValueError(
                f"KIS provider does not support market={market!r}, asset_type={asset_type!r}. "
                "It currently supports US-listed stocks and ETFs only; use CSV for other assets."
            )
        bars = self.client.daily_bars(symbol, exchange=exchange, max_pages=max_pages)
        return normalize_ohlcv(bars)
