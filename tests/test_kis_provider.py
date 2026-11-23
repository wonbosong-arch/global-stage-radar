import unittest
from unittest.mock import Mock, patch

from kis_provider import KISOverseasPrices, KISError


class KISProviderTests(unittest.TestCase):
    def test_missing_credentials_fail_with_safe_guidance(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(KISError) as ctx:
                KISOverseasPrices()
        self.assertIn("do not paste API credentials", str(ctx.exception))

    def test_invalid_exchange_fails_before_network_request(self):
        provider = KISOverseasPrices(app_key="test-key", app_secret="test-secret")
        with self.assertRaises(ValueError):
            provider.daily_bars("AAPL", exchange="INVALID")

    def test_page_limit_skips_trailing_wait_but_preserves_next_request_interval(self):
        def response(date):
            return Mock(ok=True, text="", headers={"tr_cont": "M"}, json=Mock(return_value={
                "rt_cd": "0", "output2": [
                    {"xymd": date, "open": "10", "high": "11", "low": "9", "clos": "10", "tvol": "100"}
                ],
            }))

        session = Mock()
        session.get.side_effect = [response("20261120"), response("20261119"), response("20261120")]
        clock = 100.0

        def sleep(seconds):
            nonlocal clock
            clock += seconds

        client = KISOverseasPrices(app_key="test-key", app_secret="test-secret", session=session)
        with patch.object(client, "_get_token", return_value="test-token"), \
             patch("kis_provider.time.monotonic", side_effect=lambda: clock), \
             patch("kis_provider.time.sleep", side_effect=sleep) as wait:
            history = client.daily_bars("AAPL", max_pages=2)
            self.assertEqual(clock, 101.0)
            self.assertEqual(wait.call_count, 1)
            clock += 0.75
            recent = client.daily_bars("MSFT", max_pages=1)
            wait.assert_called_with(0.25)
            self.assertEqual(wait.call_count, 2)

        self.assertEqual(history["date"].dt.strftime("%Y%m%d").tolist(), ["20261119", "20261120"])
        self.assertEqual(recent["symbol"].tolist(), ["MSFT"])
        self.assertEqual(
            [call.kwargs["params"]["BYMD"] for call in session.get.call_args_list], ["", "20261119", ""]
        )

    def test_token_rate_limit_retries_once_after_provider_window(self):
        class FakeResponse:
            def __init__(self, status_code, payload=None, text=""):
                self.status_code = status_code
                self._payload = payload or {}
                self.text = text
                self.ok = 200 <= status_code < 400

            def json(self):
                return self._payload

        class FakeSession:
            def __init__(self):
                self.responses = [
                    FakeResponse(403, text='{"error_code":"EGW00133","error_description":"one per minute"}'),
                    FakeResponse(200, payload={"access_token": "test-token", "expires_in": 3600}),
                ]
                self.calls = 0

            def post(self, *args, **kwargs):
                self.calls += 1
                return self.responses.pop(0)

        session = FakeSession()
        provider = KISOverseasPrices(
            app_key="test-key", app_secret="test-secret", session=session
        )
        with patch("kis_provider.time.sleep") as sleep:
            token = provider._get_token()

        self.assertEqual(token, "test-token")
        self.assertEqual(session.calls, 2)
        sleep.assert_called_once_with(65)

    def test_token_does_not_retry_invalid_credentials(self):
        class FakeResponse:
            ok = False
            status_code = 403
            text = '{"error_code":"invalid_appkey","error_description":"bad credentials"}'

        class FakeSession:
            def __init__(self):
                self.calls = 0

            def post(self, *args, **kwargs):
                self.calls += 1
                return FakeResponse()

        session = FakeSession()
        provider = KISOverseasPrices(
            app_key="test-key", app_secret="test-secret", session=session
        )
        with patch("kis_provider.time.sleep") as sleep:
            with self.assertRaises(KISError):
                provider._get_token()

        self.assertEqual(session.calls, 1)
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
