import unittest
import requests
from datetime import datetime, timezone
from unittest.mock import Mock

import collect_stock_candidates as collector


class CandidateFxRateTests(unittest.TestCase):
    def test_configured_rate_takes_precedence(self):
        rate, source, rate_date = collector.resolve_usdkrw_rate("1375.25")
        self.assertEqual(rate, 1375.25)
        self.assertIn("repository variable", source)
        self.assertIsNone(rate_date)

    def test_kis_ranking_exchange_rate_is_extracted_consistently(self):
        diagnostics = {
            "US_NAS": [{"output1": {"t_rate": "1326.40"}}],
            "US_NYS": [{"output1": {"t_rate": "1326.40"}}],
            "US_AMS": [{"output1": {"t_rate": "1326.50"}}],
        }
        self.assertEqual(collector.extract_kis_ranking_usdkrw_rate(diagnostics), 1326.4)

    def test_kis_ranking_exchange_rate_rejects_material_disagreement(self):
        diagnostics = {
            "US_NAS": [{"output1": {"t_rate": "1326.40"}}],
            "US_NYS": [{"output1": {"t_rate": "1500.00"}}],
        }
        self.assertIsNone(collector.extract_kis_ranking_usdkrw_rate(diagnostics))

    def test_kis_ranking_exchange_rate_rejects_missing_or_implausible_values(self):
        diagnostics = {"US_NAS": [{"output1": {"t_rate": "0"}}]}
        self.assertIsNone(collector.extract_kis_ranking_usdkrw_rate(diagnostics))

    def test_yahoo_daily_close_is_preferred_when_config_is_empty(self):
        timestamp = int(datetime.now(timezone.utc).timestamp())
        response = Mock()
        response.json.return_value = {
            "chart": {"result": [{
                "timestamp": [timestamp],
                "indicators": {"quote": [{"close": [1380.5]}]},
            }]}
        }
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response

        rate, source, rate_date = collector.resolve_usdkrw_rate("", session=session)

        self.assertEqual(rate, 1380.5)
        self.assertEqual(rate_date, datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat())
        self.assertIn("Yahoo Finance", source)
        session.get.assert_called_once()
        self.assertIn("USDKRW=X", session.get.call_args.args[0])

    def test_public_reference_rate_is_used_when_yahoo_fails(self):
        today = datetime.now(timezone.utc).date().isoformat()
        response = Mock()
        response.json.return_value = {"date": today, "base": "USD", "rates": {"KRW": 1380.5}}
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.side_effect = [requests.Timeout("Yahoo unavailable"), response]

        rate, source, rate_date = collector.resolve_usdkrw_rate("", session=session)

        self.assertEqual(rate, 1380.5)
        self.assertEqual(rate_date, today)
        self.assertIn("Frankfurter", source)
        self.assertEqual(session.get.call_count, 2)

    def test_stale_reference_rate_is_not_used(self):
        response = Mock()
        response.json.return_value = {"date": "2020-01-01", "base": "USD", "rates": {"KRW": 1100}}
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response

        rate, source, rate_date = collector.resolve_usdkrw_rate("", session=session)

        self.assertIsNone(rate)
        self.assertEqual(source, "unavailable_or_stale")
        self.assertEqual(rate_date, "2020-01-01")

    def test_provider_failure_leaves_rate_unavailable(self):
        session = Mock()
        session.get.side_effect = requests.Timeout("network unavailable")

        rate, source, rate_date = collector.resolve_usdkrw_rate("", session=session)

        self.assertIsNone(rate)
        self.assertEqual(source, "unavailable")
        self.assertIsNone(rate_date)


if __name__ == "__main__":
    unittest.main()
