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
    """KIS daily-price adapter for US listings, Japan sector ETFs, and China-listed sector ETF candidates."""

    capabilities = ProviderCapabilities(
        name="KIS US daily prices",
        markets=("US listings", "global ETF proxy exposures", "Tokyo-listed Japan sector ETFs", "Shanghai/Shenzhen-listed China ETF candidates"),
        asset_types=("stock", "market_etf", "sector_etf", "commodity_etf"),
        description="KIS US-listed stocks/ETFs plus TSE and mainland China SHS/SZS listing routes; symbol-level availability must be confirmed.",
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
        # Japan and mainland China listed sector ETF candidates use KIS overseas-price exchange codes.
        is_japan_local_etf = normalized_market in {"japan", "日本", "일본"} and normalized_type in {"market_etf", "sector_etf"}
        is_china_local_etf = normalized_market in {"china", "中国", "중국"} and normalized_type in {"sector_etf", "market_etf"}
        return is_us_stock or is_us_listed_etf or is_japan_local_etf or is_china_local_etf

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
                "It supports US stocks, US-listed ETF proxies, and selected Japan/China-listed ETF candidates."
            )
        requested_exchange = exchange.strip().upper()
        normalized_market = str(market).strip().lower()
        normalized_type = str(asset_type).strip().lower()
        normalized_symbol = str(symbol).strip().upper()
        is_japan_market = normalized_market in {"japan", "日本", "일본"}
        is_china_market = normalized_market in {"china", "中国", "중국"}
        # Listing venue is explicit in the universe. Use ticker shape only to catch
        # an accidentally misconfigured local ETF candidate, not to infer exposure.
        is_japan_local_etf = (
            is_japan_market and normalized_type in {"market_etf", "sector_etf"}
            and (
                (normalized_symbol.isdigit() and len(normalized_symbol) in {3, 4})
                or (
                    len(normalized_symbol) == 4
                    and normalized_symbol[:3].isdigit()
                    and normalized_symbol[3].isalpha()
                )
            )
        )
        is_china_local_etf_candidate = (
            is_china_market and normalized_type in {"sector_etf", "market_etf"}
            and normalized_symbol.isdigit() and len(normalized_symbol) == 6
        )
        if is_japan_local_sector_candidate and requested_exchange not in {"TSE"}:
            raise ValueError("Japan-listed sector ETF candidates require exchange=TSE.")
        if is_china_local_etf_candidate and requested_exchange not in {"SHS", "SZS"}:
            raise ValueError("Mainland China-listed ETF candidates require exchange=SHS or exchange=SZS.")
        if requested_exchange == "TSE" and not is_japan_local_sector_candidate:
            raise ValueError("TSE route is reserved for Japan-listed sector ETF candidates.")
        if requested_exchange in {"SHS", "SZS"} and not is_china_local_etf_candidate:
            raise ValueError("SHS/SZS route is reserved for mainland China-listed ETF candidates.")
        if requested_exchange not in {"NAS", "NYS", "AMS", "TSE", "SHS", "SZS"}:
            raise ValueError("Unsupported KIS overseas exchange code.")
        bars = self.client.daily_bars(symbol, exchange=requested_exchange, max_pages=max_pages)
        if bars.empty and requested_exchange in {"NAS", "NYS", "AMS"} and normalized_type in {
            "market_etf", "sector_etf", "commodity_etf"
        }:
            # Some US-listed ETFs are classified under a different KIS market
            # code than their broad listing label suggests (notably NYSE Arca).
            # Retry only empty ETF responses, never a non-empty price series.
            tried = [requested_exchange]
            for fallback_exchange in ("AMS", "NAS", "NYS"):
                if fallback_exchange in tried:
                    continue
                tried.append(fallback_exchange)
                bars = self.client.daily_bars(
                    symbol, exchange=fallback_exchange, max_pages=max_pages
                )
                if not bars.empty:
                    break
            if bars.empty:
                raise KISError(
                    f"No daily bars returned for ETF {symbol} on KIS exchanges "
                    f"{', '.join(tried)}. Check KIS exchange mapping and symbol availability."
                )
        return normalize_ohlcv(bars)



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
