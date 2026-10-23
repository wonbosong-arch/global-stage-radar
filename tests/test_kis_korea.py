import unittest
from unittest.mock import patch

from kis_provider import KISDomesticPrices, KISError
from data_providers import KISKoreaProvider


class FakeResponse:
    status_code = 200
    ok = True
    headers = {}
    text = "ok"

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def post(self, *args, **kwargs):
        return FakeResponse({"access_token": "test-token", "expires_in": 3600})

    def get(self, *args, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse(self.payload)


class KoreanProviderTests(unittest.TestCase):
    @patch("kis_provider.time.sleep")
    def test_kis_domestic_daily_bars_normalizes_response(self, _sleep):
        session = FakeSession({
            "rt_cd": "0",
            "output2": [{
                "stck_bsop_date": "20261020",
                "stck_oprc": "70000",
                "stck_hgpr": "71000",
                "stck_lwpr": "69500",
                "stck_clpr": "70500",
                "acml_vol": "123456",
            }],
        })
        client = KISDomesticPrices(app_key="test-key", app_secret="test-secret", session=session)
        result = client.domestic_daily_bars("005930", max_pages=1, pause_seconds=0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["symbol"], "005930")
        self.assertEqual(float(result.iloc[0]["close"]), 70500.0)
        self.assertEqual(session.calls[0]["params"]["FID_ORG_ADJ_PRC"], "0")

    def test_kis_domestic_rejects_non_six_digit_ticker(self):
        client = KISDomesticPrices(app_key="test-key", app_secret="test-secret", session=FakeSession({"rt_cd": "0"}))
        with self.assertRaisesRegex(ValueError, "six-digit"):
            client.domestic_daily_bars("5930", max_pages=1, pause_seconds=0)

    def test_korea_provider_supports_krx_stocks(self):
        class StubClient:
            def domestic_daily_bars(self, symbol, exchange="KRX", max_pages=5):
                import pandas as pd
                return pd.DataFrame([{
                    "date": "2026-10-20", "symbol": symbol, "open": 100,
                    "high": 105, "low": 99, "close": 104, "volume": 123,
                }])
        provider = KISKoreaProvider(StubClient())
        self.assertTrue(provider.supports("South Korea", "stock"))
        self.assertTrue(provider.supports("South Korea", "commodity_etf"))
        result = provider.fetch_daily("005930", "South Korea", "stock", "KRX", max_pages=1)
        self.assertEqual(result.iloc[0]["symbol"], "005930")

    def test_korea_provider_rejects_non_krx_exchange(self):
        class StubClient:
            def domestic_daily_bars(self, *args, **kwargs):
                raise AssertionError("must not fetch")
        provider = KISKoreaProvider(StubClient())
        with self.assertRaisesRegex(ValueError, "KRX only"):
            provider.fetch_daily("005930", "South Korea", "stock", "NXT")


if __name__ == "__main__":
    unittest.main()
