"""Exercise the complete review refresh with isolated files and mocked providers."""
from contextlib import ExitStack
from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pandas as pd

import refresh_candidate_prices as refresh


def bars(symbol, dates, base=100):
    return pd.DataFrame([
        dict(date=date, symbol=symbol, open=base+i, high=base+i+2,
             low=base+i-1, close=base+i+1, volume=1000)
        for i, date in enumerate(dates)
    ])


class CandidateCompletedSessionTests(unittest.TestCase):
    def run_refresh(self, responses, previous=None, hour=10):
        now = datetime(2026, 10, 28, hour, 0, tzinfo=ZoneInfo('Asia/Seoul'))
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root = Path(tmp)
            paths = {name: root / f'{name}.csv' for name in ('CANDIDATES', 'UNIVERSE', 'PRICES')}
            paths['STATUS'] = root / 'status.json'
            candidates = pd.DataFrame([
                dict(symbol=s, exchange='KRX' if s.isdigit() else 'NAS',
                     market='South Korea' if s.isdigit() else 'United States',
                     asset_type='stock', activation_status='pending_review')
                for s in responses
            ])
            candidates.to_csv(paths['CANDIDATES'], index=False)
            pd.DataFrame(columns=['symbol']).to_csv(paths['UNIVERSE'], index=False)
            if previous is not None:
                previous.to_csv(paths['PRICES'], index=False)
            original_candidates = paths['CANDIDATES'].read_bytes()
            original_universe = paths['UNIVERSE'].read_bytes()
            for name, path in paths.items():
                stack.enter_context(patch.object(refresh, name, path))
            stack.enter_context(patch.dict('os.environ', KIS_APP_KEY='test', KIS_APP_SECRET='test'))
            stack.enter_context(patch.object(refresh, 'KISOverseasPrices'))
            stack.enter_context(patch.object(refresh, 'KISDomesticPrices'))
            def fetch(symbol, **kwargs):
                result = responses[symbol]
                if isinstance(result, Exception):
                    raise result
                return result.copy()
            for name in ('KISUSProvider', 'KISKoreaProvider'):
                stack.enter_context(patch.object(refresh, name, return_value=Mock(fetch_daily=fetch)))
            clock = stack.enter_context(patch.object(refresh, 'datetime'))
            clock.now.return_value = now
            stack.enter_context(patch.object(refresh.time, 'sleep'))
            stack.enter_context(patch('builtins.print'))
            self.assertEqual(refresh.main(), 0)
            result = pd.read_csv(paths['PRICES'], dtype={'symbol': str})
            status = json.loads(paths['STATUS'].read_text())
            self.assertEqual(paths['CANDIDATES'].read_bytes(), original_candidates)
            self.assertEqual(paths['UNIVERSE'].read_bytes(), original_universe)
            return result, status

    def test_partial_korean_bar_is_not_saved_or_counted_as_fresh(self):
        previous = bars('005930', ['2026-10-27'])
        result, status = self.run_refresh({'005930': bars('005930', ['2026-10-28'])}, previous)
        self.assertEqual(result['date'].tolist(), ['2026-10-27'])
        self.assertEqual(status['fresh_data_symbol_count'], 0)
        self.assertEqual(status['symbols_preserved_from_previous_snapshot'], ['005930'])
        self.assertEqual(status['failed_symbols'], ['005930'])
        self.assertEqual(status['provider_observations'], [])

    def test_mixed_response_keeps_completed_rows_and_reports_filtered_coverage(self):
        result, status = self.run_refresh({'005930': bars('005930', ['2026-10-27', '2026-10-28'])})
        self.assertEqual(result['date'].tolist(), ['2026-10-27'])
        self.assertEqual(status['fresh_data_symbols'], ['005930'])
        self.assertEqual(status['error_count'], 0)
        observation = status['provider_observations'][0]
        self.assertEqual(observation['response_rows'], 1)
        self.assertEqual(observation['latest_response_date'], '2026-10-27')

    def test_after_close_keeps_today_korean_bar_but_not_future(self):
        result, status = self.run_refresh({'005930': bars('005930', ['2026-10-28', '2026-10-29'])}, hour=16)
        self.assertEqual(result['date'].tolist(), ['2026-10-28'])
        self.assertEqual(status['fresh_data_symbol_count'], 1)

    def test_us_listing_keeps_today_without_asian_cutoff_and_removes_future(self):
        result, status = self.run_refresh({'AAPL': bars('AAPL', ['2026-10-28', '2026-10-29'])})
        self.assertEqual(result['date'].tolist(), ['2026-10-28'])
        self.assertEqual(status['fresh_data_symbols'], ['AAPL'])

    def test_cleanup_also_applies_to_preserved_history_on_provider_failure(self):
        previous = bars('005930', ['2026-10-27', '2026-10-28', '2026-10-29'])
        result, status = self.run_refresh({'005930': RuntimeError('provider unavailable')}, previous)
        self.assertEqual(result['date'].tolist(), ['2026-10-27'])
        self.assertEqual(status['fresh_data_symbol_count'], 0)
        self.assertEqual(status['per_symbol_coverage'][0]['latest_date'], '2026-10-27')

    def test_successful_incremental_merge_preserves_history_and_fresh_duplicate_wins(self):
        previous = bars('AAPL', ['2026-10-26', '2026-10-27'])
        result, status = self.run_refresh({'AAPL': bars('AAPL', ['2026-10-27', '2026-10-28'], base=200)}, previous)
        self.assertEqual(result['date'].tolist(), ['2026-10-26', '2026-10-27', '2026-10-28'])
        self.assertEqual(result['close'].tolist(), [101, 201, 202])
        self.assertEqual(status['error_count'], 0)
        self.assertEqual(status['symbols_preserved_from_previous_snapshot'], [])

    def test_only_future_rows_without_history_leave_empty_snapshot_and_failure(self):
        result, status = self.run_refresh({'AAPL': bars('AAPL', ['2026-10-29'])})
        self.assertTrue(result.empty)
        self.assertEqual(status['symbols_with_data'], 0)
        self.assertEqual(status['fresh_data_symbol_count'], 0)
        self.assertEqual(status['failed_symbols'], ['AAPL'])

    def test_invalid_preserved_history_is_not_reported_as_available(self):
        previous = bars('005930', ['2026-10-28', '2026-10-29'])
        result, status = self.run_refresh({'005930': RuntimeError('timeout')}, previous)
        self.assertTrue(result.empty)
        self.assertEqual(status['symbols_with_data'], 0)
        self.assertEqual(status['symbols_preserved_from_previous_snapshot'], [])

    def test_empty_provider_response_keeps_existing_error_and_valid_history(self):
        previous = bars('AAPL', ['2026-10-27'])
        result, status = self.run_refresh({'AAPL': pd.DataFrame()}, previous)
        self.assertEqual(result['date'].tolist(), ['2026-10-27'])
        self.assertEqual(status['errors'][0]['error'], 'empty_response')
        self.assertEqual(status['symbols_preserved_from_previous_snapshot'], ['AAPL'])

    def test_invalid_response_date_cannot_count_as_fresh_data(self):
        result, status = self.run_refresh({'AAPL': bars('AAPL', ['invalid'])})
        self.assertTrue(result.empty)
        self.assertEqual(status['fresh_data_symbol_count'], 0)
        self.assertEqual(status['errors'][0]['error'], 'no_completed_daily_bars')
