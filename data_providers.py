"""Provider contracts and adapters for normalized daily market data."""
from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from market_data import normalize_ohlcv
from kis_provider import KISOverseasPrices, KISError
from kis_domestic_provider import KISDomesticPrices


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
        markets=("US listings", "global ETF proxy exposures"),
        asset_types=("stock", "market_etf", "sector_etf", "commodity_etf"),
        description="KIS US-listed stocks and ETFs; global market/sector/commodity exposure is proxied by listed ETFs, not direct underlying series.",
    )

    def __init__(self, client: KISOverseasPrices):
        self.client = client

    def supports(self, market: str, asset_type: str) -> bool:
        normalized_market = str(market).strip().lower()
        normalized_type = str(asset_type).strip().lower()
        is_us_stock = (
            normalized_market in {"united states", "us", "usa", "미국"}
            and normalized_type == "stock"
        )
        # US-listed ETFs can proxy exposure to other countries, sectors, or
        # commodities. "market" describes exposure, not listing venue.
        is_us_listed_etf = normalized_type in {
            "market_etf", "sector_etf", "commodity_etf"
        }
        return is_us_stock or is_us_listed_etf

    def fetch_daily(
        self,
        symbol: str,
        market: str,
        asset_type: str,
        exchange: str,
        max_pages: int = 10,
    ) -> pd.DataFrame:
        bars, _exchange_used = self.fetch_daily_with_exchange(
            symbol, market, asset_type, exchange, max_pages=max_pages
        )
        return bars

    def fetch_daily_with_exchange(
        self,
        symbol: str,
        market: str,
        asset_type: str,
        exchange: str,
        max_pages: int = 10,
    ) -> tuple[pd.DataFrame, str]:
        """Return normalized bars plus the KIS exchange code that returned them.

        The exchange code is useful for auditability, but a non-empty response
        still does not independently prove issuer/listing identity.
        """
        if not self.supports(market, asset_type):
            raise ValueError(
                f"KIS provider does not support market={market!r}, asset_type={asset_type!r}. "
                "It supports US stocks and US-listed ETF proxies for global markets/sectors/commodities."
            )
        if exchange.strip().upper() not in {"NAS", "NYS", "AMS"}:
            raise ValueError("US-listed assets require exchange=NAS, NYS, or AMS.")
        requested_exchange = exchange.strip().upper()
        bars = self.client.daily_bars(symbol, exchange=requested_exchange, max_pages=max_pages)
        exchange_used = requested_exchange
        if bars.empty:
            tried = [requested_exchange]
            for fallback_exchange in ("AMS", "NAS", "NYS"):
                if fallback_exchange in tried:
                    continue
                tried.append(fallback_exchange)
                bars = self.client.daily_bars(
                    symbol, exchange=fallback_exchange, max_pages=max_pages
                )
                if not bars.empty:
                    exchange_used = fallback_exchange
                    break
            if bars.empty:
                raise KISError(
                    f"No daily bars returned for {symbol} on KIS exchanges "
                    f"{', '.join(tried)}. Check KIS exchange mapping and symbol availability."
                )
        return normalize_ohlcv(bars), exchange_used



class KISKoreaProvider:
    """KIS KRX daily-price adapter for Korean stocks and ETFs."""

    capabilities = ProviderCapabilities(
        name="KIS Korea daily prices",
        markets=("South Korea",),
        asset_types=("stock", "market_etf", "sector_etf", "commodity_etf"),
        description="KRX daily bars; six-digit tickers; small-watchlist pilot.",
    )

    def __init__(self, client: KISDomesticPrices):
        self.client = client

    def supports(self, market: str, asset_type: str) -> bool:
        normalized_market = str(market).strip().lower()
        normalized_type = str(asset_type).strip().lower()
        return (
            normalized_market in {"south korea", "korea", "republic of korea", "대한민국", "한국"}
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
                f"KIS Korea provider does not support market={market!r}, asset_type={asset_type!r}."
            )
        if exchange.strip().upper() != "KRX":
            raise ValueError("KIS Korea provider currently supports exchange=KRX only.")
        bars = self.client.domestic_daily_bars(symbol, exchange=exchange, max_pages=max_pages)
        return normalize_ohlcv(bars)
