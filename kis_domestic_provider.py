"""KIS domestic Korean stock and ETF daily-price adapter.

Kept separate from the overseas adapter so the web app can load the two modules
independently. Credentials are inherited from KISOverseasPrices and must never
be committed to source control.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import time
from typing import Any

import pandas as pd
import requests

from kis_provider import KISOverseasPrices, KISError
from market_data import normalize_ohlcv


class KISDomesticPrices(KISOverseasPrices):
    """KIS Korea domestic daily OHLCV using the official daily-chart endpoint.

    Uses KRX (J) by default. Historical bars are fetched in pages of up to 100
    records by moving the end-date cursor backward.
    """

    DOMESTIC_DAILY_PATH = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    DOMESTIC_DAILY_TR_ID = "FHKST03010100"

    def domestic_daily_bars(
        self,
        symbol: str,
        exchange: str = "KRX",
        end_date: str | None = None,
        max_pages: int = 5,
        pause_seconds: float = 1.0,
    ) -> pd.DataFrame:
        symbol = str(symbol).strip().upper()
        exchange_map = {"KRX": "J"}
        if not symbol or exchange.strip().upper() not in exchange_map:
            raise ValueError("KIS Korea adapter currently supports KRX only (exchange=KRX).")
        if not symbol.isdigit() or len(symbol) != 6:
            raise ValueError("Korean stock/ETF symbol must be a six-digit code, e.g. 005930.")
        cursor = end_date or datetime.now().strftime("%Y%m%d")
        all_rows: list[dict[str, Any]] = []
        for _ in range(max(1, min(int(max_pages), 10))):
            headers = {
                "authorization": f"Bearer {self._get_token()}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": self.DOMESTIC_DAILY_TR_ID,
                "custtype": "P",
                "content-type": "application/json; charset=utf-8",
            }
            params = {
                "FID_COND_MRKT_DIV_CODE": exchange_map[exchange.strip().upper()],
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": "20000101",
                "FID_INPUT_DATE_2": cursor,
                "FID_PERIOD_DIV_CODE": "D",
                "FID_ORG_ADJ_PRC": "0",
            }
            payload = None
            for attempt in range(4):
                elapsed = time.monotonic() - self._last_request_at
                if self._last_request_at and elapsed < max(0.0, pause_seconds):
                    time.sleep(max(0.0, pause_seconds) - elapsed)
                try:
                    response = self.session.get(
                        self.base_url + self.DOMESTIC_DAILY_PATH,
                        headers=headers,
                        params=params,
                        timeout=self.timeout,
                    )
                except requests.RequestException as exc:
                    self._last_request_at = time.monotonic()
                    if attempt < 3:
                        time.sleep(2 ** attempt)
                        continue
                    raise KISError(f"KIS Korea network request failed for {symbol} after retries.") from exc
                self._last_request_at = time.monotonic()
                if not response.ok:
                    if response.status_code in {429, 500, 502, 503, 504} and attempt < 3:
                        time.sleep(2 ** attempt)
                        continue
                    raise KISError(
                        f"KIS Korea price request failed for {symbol} (HTTP {response.status_code}): "
                        f"{response.text[:300]}"
                    )
                try:
                    payload = response.json()
                except ValueError as exc:
                    if attempt < 3:
                        time.sleep(2 ** attempt)
                        continue
                    raise KISError(f"KIS Korea returned invalid JSON for {symbol}.") from exc
                if str(payload.get("rt_cd", "")) == "0":
                    break
                msg_code = str(payload.get("msg_cd", ""))
                if msg_code == "EGW00201" and attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise KISError(
                    f"KIS Korea price request failed for {symbol}: "
                    f"{payload.get('msg1', 'unknown error')} ({msg_code or 'no error code'})"
                )

            rows = payload.get("output2") or []
            if not rows:
                break
            all_rows.extend(rows)
            dates = [str(row.get("stck_bsop_date", "")) for row in rows]
            valid_dates = [date for date in dates if len(date) == 8 and date.isdigit()]
            if not valid_dates or len(rows) < 100:
                break
            oldest = min(valid_dates)
            cursor = (datetime.strptime(oldest, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")

        if not all_rows:
            return pd.DataFrame(columns=["date", "symbol", "open", "high", "low", "close", "volume"])
        raw = pd.DataFrame(all_rows)
        required = {"stck_bsop_date", "stck_oprc", "stck_hgpr", "stck_lwpr", "stck_clpr", "acml_vol"}
        if not required.issubset(raw.columns):
            raise KISError("KIS Korea response fields differ from the expected daily-chart schema.")
        result = pd.DataFrame({
            "date": pd.to_datetime(raw["stck_bsop_date"], format="%Y%m%d", errors="coerce"),
            "symbol": symbol,
            "open": pd.to_numeric(raw["stck_oprc"], errors="coerce"),
            "high": pd.to_numeric(raw["stck_hgpr"], errors="coerce"),
            "low": pd.to_numeric(raw["stck_lwpr"], errors="coerce"),
            "close": pd.to_numeric(raw["stck_clpr"], errors="coerce"),
            "volume": pd.to_numeric(raw["acml_vol"], errors="coerce"),
        })
        from market_data import normalize_ohlcv
        return normalize_ohlcv(result)
