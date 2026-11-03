import json
import hashlib
from pathlib import Path
import tempfile
import unittest

import exchange_calendars as xcals
import pandas as pd

from china_history_audit import audit_symbol, audit_snapshot, external_path


class HistoryAuditTests(unittest.TestCase):
    def setUp(self):
        dates = xcals.get_calendar('XSHG').sessions_in_range('2024-01-01', '2024-12-31').tz_localize(None)
        self.daily = pd.DataFrame(dict(date=dates, symbol='512800', open='10',
                                       high='11', low='9', close='10', volume='100'))
        self.payload = dict(code='512800', kline=[
            [int(d.strftime('%Y%m%d')), 10, 11, 9, 10, 100, 1000] for d in dates])

    def audit(self, daily=None, payload=None):
        return audit_symbol(self.daily if daily is None else daily,
                            self.payload if payload is None else payload,
                            '512800', as_of_date='2025-01-05')

    def test_long_match_is_evidence_only(self):
        result = self.audit()
        self.assertTrue(result['reconciliation_valid'])
        self.assertEqual(result['reconciled_sessions'], len(self.daily))
        self.assertTrue(result['ma30_ready'])
        self.assertTrue(result['slope4_ready'])
        self.assertTrue(result['prior_comparison_ready'])
        self.assertTrue(result['ret26_history_ready'])
        self.assertFalse(result['stage_ready'])
        self.assertFalse(result['adjusted_history_verified'])
        self.assertFalse(result['operational_eligible'])

    def test_mismatch_never_bridged(self):
        self.payload['kline'][-40][4] = 10.5
        result = self.audit()
        self.assertEqual(result['mismatch_sessions'], 1)
        self.assertEqual(result['price_mismatch_sessions'], 1)
        self.assertEqual(result['volume_mismatch_sessions'], 0)
        self.assertEqual(result['reconciled_sessions'], 39)
        self.assertFalse(result['ma30_ready'])

    def test_missing_tail_does_not_claim_current_evidence(self):
        self.payload['kline'].pop()
        result = self.audit()
        self.assertEqual(result['missing_official_sessions'], 1)
        self.assertEqual(result['reconciled_sessions'], 0)

    def test_all_overlap_used_instead_of_last_60(self):
        self.payload['kline'] = self.payload['kline'][-110:]
        result = self.audit()
        self.assertEqual(result['reconciled_sessions'], 110)
        self.assertEqual(result['missing_official_sessions'], len(self.daily) - 110)

    def test_malformed_evidence_fails_closed(self):
        variants = []
        for change in ('duplicate', 'identity', 'amount', 'nonfinite', 'missing_session'):
            payload = json.loads(json.dumps(self.payload))
            if change == 'duplicate':
                payload['kline'].append(payload['kline'][-1])
            elif change == 'identity':
                payload['code'] = '512400'
            elif change == 'amount':
                payload['kline'][0][6] = 999999
            elif change == 'nonfinite':
                payload['kline'][0][1] = 'NaN'
            else:
                payload['kline'].pop(50)
            variants.append(payload)
        for payload in variants:
            with self.subTest(payload_type=variants.index(payload)):
                result = self.audit(payload=payload)
                self.assertFalse(result['reconciliation_valid'])
                self.assertFalse(result['stage_ready'])

    def test_kis_duplicate_and_mixed_symbol_rejected(self):
        duplicate = pd.concat([self.daily, self.daily.iloc[-1:]])
        mixed = self.daily.copy()
        mixed.loc[0, 'symbol'] = '512400'
        for daily in (duplicate, mixed):
            self.assertFalse(self.audit(daily=daily)['reconciliation_valid'])

    def test_snapshot_missing_sources_keeps_all_twelve_withheld(self):
        with tempfile.TemporaryDirectory() as directory:
            self.daily.to_csv(Path(directory) / 'china_candidate_prices.csv', index=False)
            result = audit_snapshot(directory, as_of_date='2025-01-05')
            self.assertEqual(result['stage_possible'], 0)
            self.assertEqual(result['stage_withheld'], 12)
            self.assertEqual(len(result['symbols']), 12)
            self.assertNotIn('kline', json.dumps(result))

    def test_git_checkout_paths_rejected(self):
        with self.assertRaises(ValueError):
            external_path(Path(__file__).resolve().parent)

    def test_source_receipt_and_hash_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.daily.to_csv(root / 'china_candidate_prices.csv', index=False)
            (root / 'sources').mkdir()
            source = root / 'sources/512800_sse_daily.json'
            source.write_text(json.dumps(self.payload), encoding='utf-8')
            manifest = [dict(symbol='512800', http_status=200,
                             local_path='sources/512800_sse_daily.json',
                             sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                             requested_url='https://yunhq.sse.com.cn:32042/v1/sh1/dayk/512800?period=day&select=date,open,high,low,close,volume,amount')]
            def check():
                return audit_snapshot(root, as_of_date='2025-01-05')['symbols'][0]
            self.assertFalse(check()['reconciliation_valid'])
            (root / 'market_manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            self.assertTrue(check()['reconciliation_valid'])
            source.write_text(json.dumps(self.payload) + ' ', encoding='utf-8')
            self.assertFalse(check()['reconciliation_valid'])


if __name__ == '__main__':
    unittest.main()
