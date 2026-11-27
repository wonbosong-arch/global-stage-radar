from datetime import datetime
from io import BytesIO
import unittest
from zipfile import ZipFile
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd

from china_stage import validated_daily
from hong_kong_etf_research import master_identities, observe
from kis_provider import KISError


class HongKongETFResearchTests(unittest.TestCase):
    def test_master_requires_hkd_type_and_matching_identity(self):
        def line(symbol, name, kind="3", currency="HKD"):
            fields = ["HK", "12", "HKS", "홍콩", symbol, "HKS" + symbol, name, "", kind, currency]
            return "\t".join(fields + [""] * 14)

        raw = BytesIO()
        with ZipFile(raw, "w") as archive:
            archive.writestr("HKSMST.COD", "\r\n".join([
                line("03033", "CSOP HANG SENG TECH HKD"),
                line("03102", "ICBC UBS KRANESHARES KWEB CSI CHINA INTERNET", currency="USD"),
                line("03069", "CHINAAMC HANG SENG HONG KONG BIOTECH", kind="2"),
                line("03456", "UNRELATED ETF"),
            ]).encode("cp949"))
        self.assertEqual(master_identities(raw.getvalue()), {"03033"})

    def test_research_stage_uses_hong_kong_calendar_and_isolates_failed_symbols(self):
        sessions = xcals.get_calendar("XHKG").sessions_in_range(
            "2025-01-02", "2025-12-05"
        ).tz_localize(None)
        frame = pd.DataFrame({"symbol": "03033", "date": sessions, "open": 10,
                              "high": 11, "low": 9, "close": 10, "volume": 100})
        calls = []

        class Client:
            def daily_bars(self, symbol, **kwargs):
                calls.append((symbol, kwargs))
                if symbol == "03102":
                    raise KISError("upstream text")
                if symbol == "03456":
                    return frame.tail(45).assign(symbol=symbol)
                return frame

        now = datetime(2025, 12, 6, 10, tzinfo=ZoneInfo("Asia/Hong_Kong"))
        rows, summary = observe(Client(), {"03033", "03102", "03456"}, now)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0][1], {"exchange": "HKS", "end_date": "20251205", "max_pages": 3})
        states = {x["symbol"]: x["status"] for x in summary["observations"]}
        self.assertEqual(states["03033"], "stage_ready")
        self.assertEqual(states["03102"], "provider_error")
        self.assertEqual(states["03456"], "insufficient_weeks")
        self.assertEqual(states["02828"], "master_unverified")
        self.assertEqual(summary["stage_ready"], 1)
        self.assertTrue(all(not row["operational_eligible"] for row in rows))
        self.assertNotIn("stage_label", summary["observations"][0])
        with self.assertRaisesRegex(ValueError, "비거래일 또는 거래일 누락"):
            validated_daily(frame, as_of_date=now.date())

    def test_previous_session_required_before_close(self):
        sessions = xcals.get_calendar("XHKG").sessions_in_range(
            "2025-01-02", "2025-12-03"
        ).tz_localize(None)
        frame = pd.DataFrame({"symbol": "03033", "date": sessions, "open": 10,
                              "high": 11, "low": 9, "close": 10, "volume": 100})

        class Client:
            def daily_bars(self, symbol, **kwargs):
                return frame

        now = datetime(2025, 12, 5, 15, tzinfo=ZoneInfo("Asia/Hong_Kong"))
        rows, summary = observe(Client(), {"03033"}, now)
        self.assertEqual(summary["latest_expected_session"], "2025-12-04")
        self.assertFalse(rows[0]["stage_ready"])
        self.assertEqual(summary["stage_ready"], 0)
