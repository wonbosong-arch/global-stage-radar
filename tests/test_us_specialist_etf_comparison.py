from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from us_specialist_etf_comparison import compare_to_specialist_etf, research_etf_weekly_history


NOW = datetime(2026, 11, 20, 7, tzinfo=ZoneInfo("Asia/Seoul"))


def prices(symbol, drift, start="2025-12-01"):
    sessions = xcals.get_calendar("XNYS").sessions_in_range(start, "2026-11-19")
    close = 100 * np.power(1 + drift, np.arange(len(sessions)))
    return pd.DataFrame({
        "date": sessions.tz_localize(None), "symbol": symbol,
        "open": close, "high": close * 1.01, "low": close * .99,
        "close": close, "volume": 1000000,
    })


class SpecialistETFReturnsTests(unittest.TestCase):
    def compare(self, stock, etf, etf_symbol="XBI", now=NOW):
        return compare_to_specialist_etf(
            stock, etf, stock_symbol="TEST", etf_symbol=etf_symbol, now=now,
        )

    def test_all_three_etfs_use_identical_completed_endpoints(self):
        stock = prices("TEST", .001)
        for ticker in ("XBI", "KBE", "KIE"):
            with self.subTest(ticker=ticker):
                etf = prices(ticker, .0005)
                got = self.compare(stock, etf, ticker)
                self.assertEqual(got["completed_week"], "2026-11-13")
                self.assertEqual(got["latest_session"], "2026-11-13")
                for source, field in ((stock, "stock_return_26w_pct"), (etf, "etf_return_26w_pct")):
                    close = source.set_index("date").close
                    expected = (close.loc["2026-11-13"] / close.loc["2026-05-15"] - 1) * 100
                    self.assertAlmostEqual(got[field], expected)
                self.assertAlmostEqual(got["relative_26w_pp"],
                                       got["stock_return_26w_pct"] - got["etf_return_26w_pct"])

    def test_missing_stale_duplicate_or_corrupt_price_is_unavailable(self):
        stock, etf = prices("TEST", .001), prices("XBI", .0005)
        invalid = [
            None, etf.iloc[:30], etf.iloc[:-24], etf.assign(symbol="KBE"),
            pd.concat([etf, etf.iloc[[-1]]]), etf.assign(close=np.inf),
            etf.assign(volume=-1), etf.assign(date=pd.NaT),
            etf.loc[~etf.date.eq("2026-05-15")],
            etf.loc[~etf.date.eq("2026-08-07")],
            etf.loc[~etf.date.eq("2026-11-13")],
        ]
        for frame in invalid:
            with self.subTest(frame=None if frame is None else frame.shape):
                self.assertIsNone(self.compare(stock, frame))
        self.assertIsNone(self.compare(stock.iloc[:-24], etf))
        self.assertIsNone(self.compare(stock, etf, "JETS"))

    def test_holiday_week_uses_the_actual_last_session(self):
        now = datetime(2026, 7, 4, 12, tzinfo=ZoneInfo("America/New_York"))
        got = self.compare(prices("TEST", .001), prices("XBI", .0005), now=now)
        self.assertEqual(got["completed_week"], "2026-07-03")
        self.assertEqual(got["latest_session"], "2026-07-02")

    def test_weekly_history_excludes_partial_weeks_and_accepts_holidays(self):
        etf = prices("KBE", .001)
        weekly, latest = research_etf_weekly_history(etf.iloc[1:], symbol="KBE", now=NOW)
        self.assertEqual(latest, "2026-11-19")
        self.assertEqual(weekly.date.iloc[0], pd.Timestamp("2025-12-12"))
        self.assertEqual(weekly.date.iloc[-1], pd.Timestamp("2026-11-13"))
        close = etf.set_index("date").close
        self.assertAlmostEqual(weekly.ret13_pct.iloc[-1], (close["2026-11-13"] / close["2026-08-14"] - 1) * 100)
        self.assertAlmostEqual(weekly.ret26_pct.iloc[-1], (close["2026-11-13"] / close["2026-05-15"] - 1) * 100)
        holiday = datetime(2026, 7, 4, 12, tzinfo=ZoneInfo("America/New_York"))
        etf = prices("KBE", .001, start="2025-10-01")
        weekly, latest = research_etf_weekly_history(etf, symbol="KBE", now=holiday)
        self.assertEqual(latest, "2026-07-02")
        self.assertEqual(weekly.date.iloc[-1], pd.Timestamp("2026-07-03"))
        self.assertEqual(weekly.close.iloc[-1], etf.set_index("date").at["2026-07-02", "close"])

    def test_weekly_history_rejects_stale_short_or_invalid_data(self):
        etf = prices("KIE", .001)
        invalid = [
            None, etf.iloc[:-1], etf.iloc[-100:], etf.drop(etf.index[20]),
            etf.assign(symbol="KBE"), pd.concat([etf, etf.iloc[[-1]]]),
            etf.assign(volume=-1),
        ]
        for frame in invalid:
            with self.subTest(frame=None if frame is None else frame.shape):
                self.assertIsNone(research_etf_weekly_history(frame, symbol="KIE", now=NOW))


if __name__ == "__main__":
    unittest.main()
