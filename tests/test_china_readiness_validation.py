"""Synthetic calendar-correct prices only; no provider prices in fixtures."""
import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import numpy as np
import pandas as pd
import exchange_calendars as xcals
from china_stage import stage_readiness, validated_daily


def history(weeks):
    # End on a Friday before as_of; include every XSHG session, including holidays.
    end = pd.Timestamp('2025-12-26')
    start = end - pd.Timedelta(weeks=weeks - 1, days=4)
    dates = xcals.get_calendar('XSHG').sessions_in_range(start, end).tz_localize(None)
    close = np.linspace(10, 20, len(dates))
    return pd.DataFrame(dict(date=dates, open=close, high=close + 1,
                             low=close - 1, close=close, volume=100.))


class ChinaReadinessTests(unittest.TestCase):
    def test_manifest_cannot_omit_consumed_files_without_private_inputs(self):
        from china_dashboard import _load_reconciled_research
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'manifest.json').write_text(json.dumps({'files': {}}))
            with self.assertRaisesRegex(ValueError, '필수 무결성'):
                _load_reconciled_research(root)

    def test_exact_indicator_boundaries_and_hold_even_when_long(self):
        for count in (29, 30, 33, 34, 35, 45):
            with self.subTest(weeks=count):
                result = stage_readiness(history(count), as_of_date='2025-12-27')
                self.assertTrue(result['input_valid'])
                self.assertEqual(result['completed_weeks'], count)
                self.assertEqual(result['ma30_ready'], count >= 30)
                self.assertEqual(result['slope4_ready'], count >= 34)
                self.assertEqual(result['prior_comparison_ready'], count >= 35)
                for key in ('adjusted_history_verified', 'previous_stage_verified', 'stage_ready', 'operational_eligible'):
                    self.assertFalse(result[key])
                for key in ('ma30', 'slope4_pct', 'ret26_pct', 'stage2_new_entry'):
                    self.assertIsNone(result[key])
                self.assertIn('조정 기준 미검증', result['stage_reason'])

    def test_current_friday_is_not_a_completed_week(self):
        frame = history(35)
        during = stage_readiness(frame, as_of_date='2025-12-26')
        after = stage_readiness(frame, as_of_date='2025-12-27')
        self.assertEqual(during['completed_weeks'], 34)
        self.assertFalse(during['prior_comparison_ready'])
        self.assertEqual(after['completed_weeks'], 35)

    def test_unreviewed_adjustment_flag_cannot_authorize_outputs(self):
        frame = history(45).assign(adjusted=True, adjustment_verified=True)
        frame.attrs['adjusted_history_verified'] = True
        result = stage_readiness(frame, as_of_date='2025-12-27')
        self.assertFalse(result['adjusted_history_verified'])
        self.assertFalse(result['stage_ready'])
        self.assertIsNone(result['ret26_pct'])
        self.assertIsNone(result['stage2_new_entry'])

    def test_invalid_input_never_outputs_indicators(self):
        valid = history(35)
        cases = [pd.DataFrame(), valid.drop(columns='close'),
                 pd.concat([valid, valid.iloc[:1]]), valid.drop(index=5)]
        for column, value in [('date', 'bad'), ('date', '2030-01-01'),
                              ('date', '2025-12-28'), ('close', np.nan),
                              ('close', np.inf), ('volume', -1), ('high', 1), ('low', 50)]:
            frame = valid.copy()
            if column == 'date':
                frame[column] = frame[column].astype(object)
            frame.loc[frame.index[-1], column] = value
            cases.append(frame)
        mixed = valid.assign(symbol='512800')
        mixed.loc[0, 'symbol'] = '512400'
        cases.append(mixed)
        for frame in cases:
            with self.subTest(case=len(frame), columns=list(frame.columns)):
                result = stage_readiness(frame, as_of_date='2025-12-29')
                self.assertFalse(result['input_valid'])
                self.assertFalse(result['stage_ready'])
                self.assertIsNone(result['ret26_pct'])
                self.assertIsNone(result['stage2_new_entry'])
                self.assertIn('검증 실패', result['stage_reason'])

    def test_calendar_failure_is_closed(self):
        frame = history(35)
        with patch('exchange_calendars.get_calendar', side_effect=RuntimeError('unavailable')):
            result = stage_readiness(frame, as_of_date='2025-12-27')
        self.assertFalse(result['input_valid'])
        self.assertIn('달력 검증 실패', result['stage_reason'])

    def test_leading_partial_week_cannot_satisfy_35_week_requirement(self):
        frame = history(35).iloc[1:]
        result = stage_readiness(frame, as_of_date='2025-12-27')
        self.assertTrue(result['input_valid'])
        self.assertEqual(result['completed_weeks'], 34)
        self.assertFalse(result['prior_comparison_ready'])

    def test_older_partial_week_excluded_and_sorting_preserves_input(self):
        frame = history(35)
        partial = frame[frame.date < '2025-12-26']
        self.assertEqual(stage_readiness(partial, as_of_date='2025-12-29')['completed_weeks'], 34)
        shuffled = frame.sample(frac=1, random_state=1)
        original = shuffled.copy(deep=True)
        pd.testing.assert_frame_equal(validated_daily(shuffled, as_of_date='2025-12-27').reset_index(drop=True), frame)
        pd.testing.assert_frame_equal(shuffled, original)
