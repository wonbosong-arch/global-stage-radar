from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

import pandas as pd

from market_data import completed_bar_cutoff_date, filter_incomplete_daily_bars


class USCompletedDailySessionTests(unittest.TestCase):
    def test_us_close_uses_new_york_date_and_daylight_saving_time(self):
        cases = [
            (datetime(2026, 7, 8, 5, 4), '2026-07-06'),
            (datetime(2026, 7, 8, 5, 5), '2026-07-07'),
            (datetime(2026, 1, 8, 6, 4), '2026-01-06'),
            (datetime(2026, 1, 8, 6, 5), '2026-01-07'),
            (datetime(2026, 10, 28, 20, 30), '2026-10-27'),
        ]
        for exchange in ('NAS', 'NYS', 'AMS'):
            for clock, expected in cases:
                with self.subTest(exchange=exchange, clock=clock):
                    self.assertEqual(completed_bar_cutoff_date(exchange, clock), expected)

    def test_weekend_and_monday_before_close_use_friday(self):
        for clock in (datetime(2026, 10, 31, 20), datetime(2026, 10, 26, 20)):
            self.assertEqual(completed_bar_cutoff_date('NAS', clock),
                             '2026-10-30' if clock.day == 31 else '2026-10-23')

    def test_saved_us_partial_is_removed_while_closed_korea_and_crypto_are_preserved(self):
        frame = pd.DataFrame([
            {'symbol': 'AAPL', 'date': '2026-10-27', 'close': 100},
            {'symbol': 'AAPL', 'date': '2026-10-28', 'close': 999},
            {'symbol': '005930', 'date': '2026-10-28', 'close': 200},
            {'symbol': 'BTC-USD', 'date': '2026-10-28', 'close': 300},
        ])
        filtered = filter_incomplete_daily_bars(frame,
            {'AAPL': 'NAS', '005930': 'KRX', 'BTC-USD': 'CRYPTO'},
            now_kst=datetime(2026, 10, 28, 20, 30, tzinfo=ZoneInfo('Asia/Seoul')))
        self.assertEqual(list(zip(filtered.symbol, filtered.date)), [
            ('AAPL', '2026-10-27'), ('005930', '2026-10-28'), ('BTC-USD', '2026-10-28')])
        self.assertEqual(len(frame), 4)
