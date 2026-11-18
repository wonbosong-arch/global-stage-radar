"""Synthetic checks: KIS ETF observation cannot become Stage or a new data file."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from unittest import TestCase, mock

import pandas as pd

from kis_provider import KISError
from us_specialist_etf_kis_probe import ETF_SYMBOLS, observe_history, main

NOW = datetime(2026, 11, 18, 20, 0, tzinfo=timezone.utc)


def bars(symbol, days=250, end="2026-11-17"):
    return pd.DataFrame([
        {"date": day, "symbol": symbol, "open": 100.0,
         "high": 102.0, "low": 99.0, "close": 101.0, "volume": 10000}
        for day in pd.bdate_range(end=end, periods=days)
    ])


class StubKIS:
    def __init__(self, cases):
        self.cases = cases
        self.calls = []

    def daily_bars(self, symbol, exchange, max_pages, pause_seconds):
        self.calls.append((symbol, exchange, max_pages, pause_seconds))
        found = self.cases[symbol]
        if isinstance(found, Exception):
            raise found
        return found.copy(deep=True)


class ETFProbeTests(TestCase):
    def test_complete_batch_is_metadata_only(self):
        cases = {symbol: bars(symbol) for symbol in ETF_SYMBOLS}
        client = StubKIS(cases)
        result = observe_history(client, NOW)
        self.assertEqual(result["attempted"], 6)
        self.assertEqual(result["requested"], 6)
        self.assertEqual(len(client.calls), 6)
        self.assertTrue(all(call[1:] == ("NYS", 4, 2.0) for call in client.calls))
        self.assertTrue(all(d["status"] == "price_history_sufficient_identity_unverified"
                            and d["daily_rows"] >= 150 and d["completed_weeks"] >= 35
                            and not d["kis_instrument_identity_verified"]
                            and not d["analysis_activated"]
                            for d in result["details"]))
        self.assertFalse(result["source_prices_saved"])
        self.assertFalse(result["universe_updated"])
        self.assertNotIn("open", str(result))
        self.assertNotIn("close", str(result))

    def test_missing_short_stale_and_invalid_are_held_without_fallback(self):
        cases = {symbol: bars(symbol) for symbol in ETF_SYMBOLS}
        cases["IGV"] = pd.DataFrame()
        cases["XBI"] = bars("XBI", days=80)
        cases["IYR"] = bars("IYR", days=250, end="2026-07-01")
        cases["KBE"] = bars("UNRELATED")
        client = StubKIS(cases)
        report = observe_history(client, NOW)
        by = {r["symbol"]: r for r in report["details"]}
        self.assertEqual(by["IGV"]["status"], "nys_price_empty_support_unknown")
        self.assertEqual(by["XBI"]["status"], "price_history_short_or_stale_review")
        self.assertEqual(by["IYR"]["status"], "price_history_short_or_stale_review")
        self.assertEqual(by["KBE"]["status"], "kis_probe_error_validation_error")
        self.assertEqual(len(client.calls), 6)
        self.assertEqual({call[1] for call in client.calls}, {"NYS"})
        self.assertTrue(all(not row["analysis_activated"] for row in report["details"]))

    def test_arca_route_is_explicit_fixed_five_etf_cohort_only(self):
        from us_specialist_etf_kis_probe import ARCA_ETF_SYMBOLS

        self.assertEqual(set(ARCA_ETF_SYMBOLS),
                         {"XBI", "IYR", "KBE", "KIE", "JETS"})
        self.assertNotIn("IGV", ARCA_ETF_SYMBOLS)
        client = StubKIS({s: bars(s) for s in ARCA_ETF_SYMBOLS})
        result = observe_history(client, NOW, venue="AMS")
        self.assertEqual(result["attempted"], 5)
        self.assertEqual(result["requested"], 5)
        self.assertEqual({row["symbol"] for row in result["details"]},
                         set(ARCA_ETF_SYMBOLS))
        self.assertEqual({row["queried_venue"] for row in result["details"]}, {"AMS"})
        self.assertEqual({call[1] for call in client.calls}, {"AMS"})
        self.assertTrue(all(row["status"] == "price_history_sufficient_identity_unverified"
                            for row in result["details"]))
        self.assertTrue(all(not row["analysis_activated"]
                            and not row["kis_instrument_identity_verified"]
                            for row in result["details"]))
        self.assertFalse(result["source_prices_saved"])
        self.assertFalse(result["universe_updated"])

    def test_arca_empty_does_not_mean_kis_non_support_or_trigger_fallback(self):
        from us_specialist_etf_kis_probe import ARCA_ETF_SYMBOLS

        client = StubKIS({s: pd.DataFrame() for s in ARCA_ETF_SYMBOLS})
        result = observe_history(client, NOW, venue="AMS")
        self.assertEqual(result["counts"], {"ams_price_empty_support_unknown": 5})
        self.assertEqual(len(client.calls), 5)
        self.assertFalse(result["source_prices_saved"])
        with self.assertRaises(ValueError):
            observe_history(client, NOW, venue="NAS")
        self.assertEqual(len(client.calls), 5)

    def test_arca_cli_is_still_offline_without_execute(self):
        with mock.patch("us_specialist_etf_kis_probe.KISOverseasPrices") as constructor:
            with mock.patch("sys.argv", ["probe", "--venue", "AMS"]):
                output = StringIO()
                with redirect_stdout(output):
                    main()
            constructor.assert_not_called()
            import json
            plan = json.loads(output.getvalue())
            self.assertEqual(plan["proposed_quote_venue"], "AMS")
            self.assertEqual(plan["symbols"], ["XBI", "IYR", "KBE", "KIE", "JETS"])
            self.assertFalse(plan["automatic_venue_fallback"])


    def test_systemic_error_stops_the_remaining_tickers(self):
        client = StubKIS({"IGV": KISError("KIS token request failed HTTP 403")})
        report = observe_history(client, NOW)
        self.assertEqual(report["attempted"], 1)
        self.assertEqual(report["stopped_early_reason"], "authentication_failed")
        self.assertEqual(report["details"][0]["status"],
                         "kis_probe_error_authentication_failed")
        self.assertEqual(len(client.calls), 1)

    def test_default_is_offline_and_bounds_reject_before_network(self):
        with mock.patch("us_specialist_etf_kis_probe.KISOverseasPrices") as constructor:
            with mock.patch("sys.argv", ["probe"]):
                output = StringIO()
                with redirect_stdout(output):
                    main()
            constructor.assert_not_called()
            self.assertIn("offline_plan_no_network", output.getvalue())
        client = StubKIS({})
        for pages, pause in [(0, 2), (6, 2), (2, 1.0), (2, 31.0)]:
            with self.subTest(pages=pages, pause=pause), self.assertRaises(ValueError):
                observe_history(client, NOW, max_pages=pages, pause_seconds=pause)
        self.assertEqual(client.calls, [])

    def test_never_accepts_an_in_progress_session(self):
        cases = {s: bars(s) for s in ETF_SYMBOLS}
        cases["IGV"] = pd.concat([cases["IGV"], bars("IGV", days=1, end="2026-11-18")])
        result = observe_history(StubKIS(cases), NOW)
        first = result["details"][0]
        self.assertEqual(first["latest_session"], "2026-11-17")
        self.assertEqual(first["daily_rows"], 250)
