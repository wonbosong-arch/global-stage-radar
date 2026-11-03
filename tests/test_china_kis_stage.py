"""Synthetic inputs only. KIS trust does not bypass basic quality guards."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
from china_kis_stage import load_kis_stage, prepare
from china_stage import stage_readiness
from stage_engine import classify_stage, weekly_bars
from tests.test_china_readiness_validation import history


class KISStageTests(unittest.TestCase):
    def test_real_engine_indicators_and_previous_stage(self):
        frame = history(45)
        result = stage_readiness(frame, as_of_date='2025-12-27', price_basis='KIS_ADJUSTED')
        weekly = weekly_bars(frame, as_of_date='2025-12-27', calendar_name='XSHG')
        self.assertTrue(result['stage_ready'])
        self.assertEqual(result['stage_label'], 'Stage 2 후보')
        self.assertEqual(result['previous_stage_label'], 'Stage 2 후보')
        self.assertFalse(result['stage2_new_entry'])
        self.assertAlmostEqual(result['ret26_pct'], weekly.iloc[-1].ret26_pct)
        self.assertAlmostEqual(result['ma30'], weekly.iloc[-1].ma30)
        self.assertFalse(result['operational_eligible'])
        self.assertFalse(result['adjusted_history_verified'])

    def test_new_stage2_uses_previous_completed_week(self):
        frame = history(45)
        frame[['open', 'high', 'low', 'close']] = [10., 11., 9., 10.]
        last_week = frame.date >= '2025-12-22'
        frame.loc[last_week, ['open', 'high', 'low', 'close']] = [12., 13., 11., 12.]
        result = stage_readiness(frame, as_of_date='2025-12-27', price_basis='KIS_ADJUSTED')
        self.assertEqual(result['stage_label'], 'Stage 2 후보')
        self.assertEqual(result['previous_stage_label'], '중립 / 추가 확인')
        self.assertTrue(result['stage2_new_entry'])

    def test_short_stale_and_anomalous_prices_are_guarded(self):
        for count in (29, 30, 33, 34):
            result = stage_readiness(history(count), as_of_date='2025-12-27', price_basis='KIS_ADJUSTED')
            self.assertFalse(result['stage_ready'])
            self.assertIsNone(result['stage2_new_entry'])
        result = stage_readiness(history(45), as_of_date='2026-01-20', price_basis='KIS_ADJUSTED')
        self.assertFalse(result['stage_ready'])
        self.assertIn('오래됨', result['stage_label'])
        frame = history(45)
        frame.loc[frame.index[-1], ['open', 'high', 'low', 'close']] *= 2
        result = stage_readiness(frame, as_of_date='2025-12-27', price_basis='KIS_ADJUSTED')
        self.assertFalse(result['input_valid'])
        self.assertIn('이상치', result['stage_reason'])

    def test_all_twelve_including_512400_and_manifest_integrity(self):
        metadata = json.loads(Path('china_sector_metadata.json').read_text(encoding='utf-8'))
        symbols = [r['symbol'] for r in metadata]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frames = [history(45).assign(symbol=s) for s in symbols]
            pd.concat(frames).to_csv(root / 'china_candidate_prices.csv', index=False)
            prepare(root, source_commit='synthetic', observed_symbols=symbols)
            rows, preview, _ = load_kis_stage(root, as_of_date='2025-12-27')
            self.assertEqual(len(rows), 12)
            self.assertTrue(rows.stage_ready.all())
            self.assertIn('512400', set(preview.symbol))
            self.assertFalse(rows.operational_eligible.any())
            # Same symbol's actual KIS quality failure still blocks it.
            frames[0].loc[0, 'close'] = -1
            pd.concat(frames).to_csv(root / 'china_candidate_prices.csv', index=False)
            with self.assertRaisesRegex(ValueError, '무결성'):
                load_kis_stage(root, as_of_date='2025-12-27')
            prepare(root, source_commit='synthetic', observed_symbols=symbols)
            rows, preview, _ = load_kis_stage(root, as_of_date='2025-12-27')
            self.assertFalse(rows.set_index('symbol').loc[symbols[0], 'stage_ready'])
            self.assertNotIn(symbols[0], set(preview.symbol))
            self.assertEqual(int(rows.stage_ready.sum()), 11)
            prepare(root, source_commit='synthetic', observed_symbols=[])
            rows, _, _ = load_kis_stage(root, as_of_date='2025-12-27')
            self.assertFalse(rows.stage_ready.any())

    def test_shared_classifier_existing_types_unchanged(self):
        self.assertEqual(classify_stage(12, 10, 1, 2, 3, 'stock'), 'Stage 2 후보')
        self.assertEqual(classify_stage(12, 10, 1, -2, 3, 'sector_etf'), '중립 / 추가 확인')
        self.assertEqual(classify_stage(12, 10, 1, np.nan, np.nan, 'market_etf'), 'Stage 2 후보')


if __name__ == '__main__':
    unittest.main()
