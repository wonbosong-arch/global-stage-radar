import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
