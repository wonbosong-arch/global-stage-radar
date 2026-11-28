from datetime import datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from automation.check_scheduled_daily_prices import parse_scheduled_slot
from china_market_explorer import HK_LARGE, load_explorer, sectors_for
from china_market_fx import COLUMNS, fixing_date
from china_private_delivery import EXPLORER_FILES, sync
from refresh_china_hong_kong_prices import CALENDARS, collect, target_sessions
from tests.test_china_private_delivery import Store


EVENING = datetime.fromisoformat("2026-11-27T18:30:52+09:00")
MORNING = datetime.fromisoformat("2026-11-28T07:00:16+09:00")
FRIDAY = pd.Timestamp("2026-11-27")


class Client:
    def __init__(self, unavailable=()):
        self.calls = []
        self.unavailable = set(unavailable)

    def daily_bars(self, symbol, exchange, end_date, max_pages):
        self.calls.append((exchange, symbol, end_date, max_pages))
        days = xcals.get_calendar(CALENDARS[exchange]).sessions_in_range("2025-09-01", pd.Timestamp(end_date))
        days = days.tz_localize(None)
        if symbol in self.unavailable:
            days = days[:-1]
        if symbol == "03456":
            days = days[-30:]
        growth = 1.003 if symbol == "03033" else 1.002
        close = 10 * growth ** np.arange(len(days))
        return pd.DataFrame(dict(symbol=symbol, date=days, open=close, high=close * 1.01,
                                 low=close * .99, close=close, volume=100))


def quotes(start, end, currencies):
    return pd.DataFrame([(day, currency, .15 if currency == "CNY" else .128)
                         for day in pd.date_range(start, end) for currency in currencies], columns=COLUMNS)


class CollectionTests(unittest.TestCase):
    def test_approved_slots_independent_market_holidays_and_existing_restrictions(self):
        self.assertEqual(target_sessions(EVENING, "2026-11-27T09:30:52Z"), {"SHS": FRIDAY, "HKS": FRIDAY})
        self.assertEqual(target_sessions(MORNING, "2026-11-27T22:00:16Z", catch_up=True),
                         {"SHS": FRIDAY, "HKS": FRIDAY})
        self.assertEqual(target_sessions(EVENING, "2026-10-01T09:30:00Z"), {})
        self.assertEqual(target_sessions(EVENING, "2026-10-02T09:30:00Z"), {"HKS": pd.Timestamp("2026-10-02")})
        self.assertEqual(target_sessions(EVENING, "2026-10-19T09:30:00Z"), {"SHS": pd.Timestamp("2026-10-19")})
        with self.assertRaises(ValueError):
            target_sessions(MORNING, "2026-11-27T22:00:16Z")
        with self.assertRaises(ValueError):
            target_sessions(MORNING, "2026-11-22T22:00:00Z", catch_up=True)
        with self.assertRaises(ValueError):
            parse_scheduled_slot("2026-11-27T09:30:52Z", 30)

    def test_publishes_partial_close_and_retries_only_missing_via_private_delivery(self):
        from hong_kong_etf_research import CANDIDATES
        targets = {"SHS": FRIDAY, "HKS": FRIDAY}
        store = Store()
        client = Client(unavailable={"03033", "512800"})
        fx_calls = []

        def fx(start, end, currencies):
            fx_calls.append((start, end, currencies))
            return quotes(start, end, currencies)

        with TemporaryDirectory() as evening, TemporaryDirectory() as morning, TemporaryDirectory() as dashboard:
            first = collect(Path(evening), store, EVENING, targets, "evening", client_factory=lambda: client,
                            verify=lambda exchange: set(CANDIDATES) if exchange == "HKS" else {"510300"}, get_fx=fx)
            self.assertEqual(first["price_requests"], 43)
            self.assertEqual(set(first["missing_prices"]), {"03033", "512800"})
            self.assertEqual(first["missing_fx"], ["CNY", "HKD"])
            self.assertTrue(first["published"])
            self.assertEqual(fx_calls[-1][1].isoformat(), "2026-11-26")
            original = json.loads(store.objects["current.json"])
            self.assertEqual(set(original["sha256"]), set(EXPLORER_FILES))

            def reject_request():
                self.fail("Repeated slot queried a full batch")

            client = Client()
            result = collect(Path(morning), store, MORNING, targets, "morning", client_factory=lambda: client,
                             verify=lambda exchange: {"03033"}, get_fx=fx)
            self.assertEqual({(exchange, symbol) for exchange, symbol, _, _ in client.calls},
                             {("HKS", "03033"), ("SHS", "512800")})
            self.assertEqual(result["missing_prices"], [])
            self.assertEqual(result["missing_fx"], [])
            self.assertEqual(fx_calls[-1][0], FRIDAY.date())
            self.assertEqual(fx_calls[-1][1], FRIDAY.date())
            again = collect(Path(morning), store, MORNING, targets, "duplicate", client_factory=reject_request,
                            get_fx=lambda *_: self.fail("Repeated FX request"))
            self.assertEqual(again["price_requests"], 0)
            self.assertFalse(again["published"])
            sync(dashboard, store, as_of_date=MORNING.date())
            rows, history, _ = load_explorer(dashboard, MORNING)
            markets = rows.set_index("symbol")
            self.assertEqual(len(history), 43)
            self.assertEqual(int(rows.stage_ready.sum()), 42)
            self.assertEqual(markets.at["03456", "stage_label"], "연구 관찰 · 이력 부족")
            for symbol in ("510300", "02828", "02800"):
                self.assertTrue(pd.notna(markets.at[symbol, "ret26_pct"]))
                self.assertTrue(pd.notna(markets.at[symbol, "ret1y_pct"]))
            hk = sectors_for(rows, history, HK_LARGE).set_index("symbol")
            self.assertGreater(hk.at["03033", "rs_market_26w_pct"], 0)

    def test_fx_holiday_uses_previous_fixing_only_on_a_target_closure(self):
        self.assertEqual(fixing_date(pd.Timestamp("2026-05-01").date()).isoformat(), "2026-04-30")
        self.assertEqual(fixing_date(FRIDAY.date()), FRIDAY.date())
