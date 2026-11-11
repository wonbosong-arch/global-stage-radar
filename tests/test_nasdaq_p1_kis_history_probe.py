"""Synthetic regression coverage for explicit, bounded Nasdaq P1 KIS probing."""
from datetime import datetime
import unittest

import pandas as pd

from kis_provider import KISError
from nasdaq_p1_kis_history_probe import (
    MATCHED_SEC_VENUE, probe_live, select_probe_rows,
)

NOW = datetime.fromisoformat("2026-11-11T15:30:00+09:00")


def review(symbol, status="missing", sec_status=MATCHED_SEC_VENUE, venue="NAS"):
    return {
        "symbol": symbol, "saved_kis_venue": venue,
        "price_inventory_status": status, "sec_reference_status": sec_status,
    }


def history(symbol, days=200, end="2026-11-10"):
    return pd.DataFrame([
        dict(date=day, symbol=symbol, open=100 + i,
             high=103 + i, low=99 + i, close=101 + i, volume=1000)
        for i, day in enumerate(pd.bdate_range(end=end, periods=days))
    ])


class StubKIS:
    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def daily_bars(self, symbol, exchange, max_pages, pause_seconds):
        self.calls.append((symbol, exchange, max_pages, pause_seconds))
        answer = self.answers[symbol]
        if isinstance(answer, Exception):
            raise answer
        return answer.copy(deep=True)


class P1KISProbeTests(unittest.TestCase):
    def test_only_missing_p1_with_correlated_sec_venue_are_selected(self):
        rows = [
            review("GOOD"), review("STORED", status="stale"),
            review("UNLINKED", sec_status="sec_reference_not_registered"),
            review("BADVENUE", venue="TSE"),
        ]
        selected, eligible = select_probe_rows(
            {"p1_symbols": len(rows), "review_rows": rows}, 16)
        self.assertEqual(eligible, 1)
        self.assertEqual([item["symbol"] for item in selected], ["GOOD"])

    def test_deterministic_small_batch_and_no_network_for_planning(self):
        rows = [review("Z"), review("A"), review("B")]
        selected, eligible = select_probe_rows(
            {"p1_symbols": 3, "review_rows": rows}, 2)
        self.assertEqual(eligible, 3)
        self.assertEqual([item["symbol"] for item in selected], ["A", "B"])

    def test_limits_and_unexpected_duplicate_cohort_fail_closed(self):
        for number in (0, 17):
            with self.assertRaises(ValueError):
                select_probe_rows({"p1_symbols": 1, "review_rows": [review("ONE")]}, number)
        with self.assertRaises(ValueError):
            select_probe_rows({"p1_symbols": 2,
                               "review_rows": [review("ONE"), review("ONE")]}, 2)
        with self.assertRaises(ValueError):
            select_probe_rows({"p1_symbols": 17,
                               "review_rows": [review(str(i)) for i in range(17)]}, 16)

    def test_live_long_history_is_review_only_and_never_activated(self):
        fake = StubKIS({"SYN": history("SYN")})
        report = probe_live([review("SYN")], fake, NOW, 3, 2.0)
        self.assertTrue(report["live_probe_performed"])
        self.assertEqual(report["attempted_symbols"], 1)
        self.assertEqual(fake.calls, [("SYN", "NAS", 3, 2.0)])
        self.assertEqual(report["result_counts"], {
            "saved_history_thresholds_met_review_only": 1
        })
        row = report["review_rows"][0]
        self.assertGreaterEqual(row["completed_daily_rows"], 150)
        self.assertGreaterEqual(row["completed_weeks"], 35)
        self.assertFalse(row["security_cap_verified"])
        self.assertFalse(row["activation_approved"])

    def test_short_and_empty_do_not_become_false_unsupported(self):
        fake = StubKIS({
            "EMPTY": pd.DataFrame(columns=["date", "symbol", "open", "high", "low", "close", "volume"]),
            "SHORT": history("SHORT", days=10),
        })
        report = probe_live([review("EMPTY"), review("SHORT")], fake, NOW, 1, 2.0)
        self.assertEqual(report["result_counts"], {
            "insufficient_history": 1, "kis_empty_response_support_unknown": 1
        })
        self.assertEqual(report["attempted_symbols"], 2)

    def test_rate_and_auth_error_stop_without_retrying_other_symbols(self):
        for message, expected in (
            ("EGW00201 rate limit", "rate_limited"),
            ("HTTP 403 forbidden", "authentication_failed"),
            ("HTTP 500 server failure", "temporary_server_error"),
        ):
            with self.subTest(message=message):
                fake = StubKIS({"BAD": KISError(message), "NEXT": history("NEXT")})
                report = probe_live([review("BAD"), review("NEXT")], fake, NOW, 3, 2.0)
                self.assertEqual(report["attempted_symbols"], 1)
                self.assertEqual(report["stopped_early_reason"], expected)
                self.assertEqual(report["result_counts"], {"kis_error_" + expected: 1})
                self.assertEqual(len(fake.calls), 1)

    def test_probe_bounds_reject_before_calls(self):
        fake = StubKIS({"SYN": history("SYN")})
        for pages, pause in ((0, 2.0), (6, 2.0), (3, 1.0), (3, 40.0)):
            with self.subTest(pages=pages, pause=pause), self.assertRaises(ValueError):
                probe_live([review("SYN")], fake, NOW, pages, pause)
        self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()
