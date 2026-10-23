"""Minimal KIS overseas and domestic daily-price adapters for private research use.

Credentials must be supplied via environment variables or Streamlit secrets;
never commit credentials. Verify current KIS API terms and endpoint docs before
using this adapter in a hosted/public service.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import requests

LIVE_BASE_URL = "https://openapi.koreainvestment.com:9443"
PAPER_BASE_URL = "https://openapivts.koreainvestment.com:29443"
TOKEN_PATH = "/oauth2/tokenP"
DAILY_PATH = "/uapi/overseas-price/v1/quotations/dailyprice"
DAILY_TR_ID = "HHDFS76240000"


def _drop_invalid_ohlc_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Remove isolated rows with impossible OHLC ranges from a KIS price series."""
    if frame is None or frame.empty:
        return frame.copy() if frame is not None else pd.DataFrame(
            columns=["date", "symbol", "open", "high", "low", "close", "volume"]
        )
    invalid_ohlc = (
        (frame["high"] < frame[["open", "low", "close"]].max(axis=1))
        | (frame["low"] > frame[["open", "high", "close"]].min(axis=1))
    )
    return frame.loc[~invalid_ohlc].copy().reset_index(drop=True)


class KISError(RuntimeError):
    """Raised when KIS authentication or price retrieval fails."""


def _credential(name: str, explicit: str | None = None) -> str:
    value = explicit or os.getenv(name, "")
    if not value:
        raise KISError(
            f"{name} is missing. Set it in your local environment or Streamlit secrets; "
            "do not paste API credentials into chat or commit them to GitHub."
        )
    return value


class KISOverseasPrices:
    """Fetch daily OHLCV for US-listed stocks/ETFs via KIS REST API.

    `exchange` uses KIS market codes: NAS (Nasdaq), NYS (NYSE), AMS (NYSE American).
    This adapter is for a small personal-use pilot, not bulk-universe ingestion.
    """

    def __init__(
        self,
        app_key: str | None = None,
        app_secret: str | None = None,
        paper: bool = False,
        timeout: int = 20,
        session: requests.Session | None = None,
    ) -> None:
        self.app_key = _credential("KIS_APP_KEY", app_key)
        self.app_secret = _credential("KIS_APP_SECRET", app_secret)
        self.base_url = PAPER_BASE_URL if paper else LIVE_BASE_URL
        self.timeout = timeout
        self.session = session or requests.Session()
        self._token: str | None = None
        self._token_expiry = 0.0
        # Throttle requests across symbols as well as pagination pages.
        self._last_request_at = 0.0

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expiry:
            return self._token
        response = self.session.post(
            self.base_url + TOKEN_PATH,
            json={
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
            },
            headers={"content-type": "application/json; charset=utf-8"},
            timeout=self.timeout,
        )
        if not response.ok:
            # Include the provider's diagnostic response (truncated) so hosted
            # deployments can distinguish bad credentials from environment/permission issues.
            # The request credentials are never included in this message.
            detail = response.text[:400].replace("\\n", " ").replace("\\r", " ")
            raise KISError(
                f"KIS token request failed (HTTP {response.status_code}). "
                f"Provider response: {detail or 'empty response'}. "
                "Verify that KIS_APP_KEY and KIS_APP_SECRET are the matching pair for the live-investment app."
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise KISError(
                f"KIS token response was not valid JSON (HTTP {response.status_code}): "
                f"{response.text[:300]}"
            ) from exc
        token = payload.get("access_token")
        if not token:
            raise KISError(f"KIS token response did not include access_token: {payload.get('msg1', 'unknown error')}")
        expires_in = int(payload.get("expires_in", 86400))
        self._token = str(token)
        self._token_expiry = time.time() + max(60, expires_in - 120)
        return self._token

    def daily_bars(
        self,
        symbol: str,
        exchange: str = "NAS",
        end_date: str | None = None,
        max_pages: int = 5,
        pause_seconds: float = 1.0,
    ) -> pd.DataFrame:
        """Return normalized daily OHLCV. end_date is YYYYMMDD; default means latest."""
        symbol = symbol.strip().upper()
        exchange = exchange.strip().upper()
        if not symbol or exchange not in {"NAS", "NYS", "AMS"}:
            raise ValueError("Provide a ticker and a KIS US exchange code: NAS, NYS, or AMS.")
        cursor = end_date or ""
        all_rows: list[dict[str, Any]] = []
        continuation = ""
        for _ in range(max(1, min(int(max_pages), 10))):
            headers = {
                "authorization": f"Bearer {self._get_token()}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": DAILY_TR_ID,
                "custtype": "P",
            }
            if continuation:
                headers["tr_cont"] = "N"
            params = {
                "AUTH": "",
                "EXCD": exchange,
                "SYMB": symbol,
                "GUBN": "0",
                "BYMD": cursor,
                "MODP": "1",
            }
            # KIS limits apply across requests, including consecutive symbols.
            # Retry only known transient/rate-limit failures, with bounded backoff.
            payload = None
            for attempt in range(4):
                elapsed = time.monotonic() - self._last_request_at
                if self._last_request_at and elapsed < max(0.0, pause_seconds):
                    time.sleep(max(0.0, pause_seconds) - elapsed)
                try:
                    response = self.session.get(
                        self.base_url + DAILY_PATH,
                        headers=headers,
                        params=params,
                        timeout=self.timeout,
                    )
                except requests.RequestException as exc:
                    self._last_request_at = time.monotonic()
                    if attempt < 3:
                        time.sleep(2 ** attempt)
                        continue
                    raise KISError(f"KIS network request failed for {symbol} after retries: {type(exc).__name__}") from exc
                self._last_request_at = time.monotonic()

                body = response.text[:500]
                retryable_http = response.status_code in {429, 500, 502, 503, 504}
                if not response.ok:
                    if retryable_http and attempt < 3:
                        time.sleep(2 ** attempt)
                        continue
                    raise KISError(
                        f"KIS price request failed for {symbol} (HTTP {response.status_code}): {body}"
                    )
                try:
                    payload = response.json()
                except ValueError as exc:
                    if attempt < 3:
                        time.sleep(2 ** attempt)
                        continue
                    raise KISError(f"KIS returned invalid JSON for {symbol} after retries.") from exc

                # KIS documents rt_cd="0" as success. A missing code is
                # an unknown response, not proof of success.
                if str(payload.get("rt_cd", "")) == "0":
                    break
                msg_code = str(payload.get("msg_cd", ""))
                if msg_code == "EGW00201" and attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise KISError(
                    f"KIS price request failed for {symbol}: "
                    f"{payload.get('msg1', 'unknown error')} ({msg_code or 'no error code'})"
                )
            rows = payload.get("output2") or []
            if not rows:
                break
            all_rows.extend(rows)
            oldest = rows[-1].get("xymd", "")
            continuation = response.headers.get("tr_cont", "")
            if not oldest or continuation not in {"M", "F"}:
                break
            # Move one calendar day before the oldest row to avoid inclusive-cursor duplicates.
            try:
                cursor = (datetime.strptime(oldest, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
            except ValueError:
                break
            time.sleep(max(0, pause_seconds))

        if not all_rows:
            return pd.DataFrame(columns=["date", "symbol", "open", "high", "low", "close", "volume"])
        raw = pd.DataFrame(all_rows)
        required = {"xymd", "open", "high", "low", "clos", "tvol"}
        if not required.issubset(raw.columns):
            raise KISError("KIS response fields differ from the expected daily-price schema; check current API docs.")
        result = pd.DataFrame({
            "date": pd.to_datetime(raw["xymd"], format="%Y%m%d", errors="coerce"),
            "symbol": symbol,
            "open": pd.to_numeric(raw["open"], errors="coerce"),
            "high": pd.to_numeric(raw["high"], errors="coerce"),
            "low": pd.to_numeric(raw["low"], errors="coerce"),
            "close": pd.to_numeric(raw["clos"], errors="coerce"),
            "volume": pd.to_numeric(raw["tvol"], errors="coerce"),
        })
        result = (
            result.dropna(subset=["date", "open", "high", "low", "close", "volume"])
            .query("open > 0 and high > 0 and low > 0 and close > 0 and volume >= 0")
            .drop_duplicates(["symbol", "date"])
            .sort_values("date")
            .reset_index(drop=True)
        )
        return _drop_invalid_ohlc_rows(result)


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
