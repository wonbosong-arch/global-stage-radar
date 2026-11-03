import json
from pathlib import Path
import tempfile
import unittest

import exchange_calendars as xcals
import pandas as pd

from china_sse_history_collect import collection, request_url


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        dates = xcals.get_calendar('XSHG').sessions_in_range('2024-01-01', '2024-12-31').tz_localize(None)
        pd.DataFrame(dict(date=dates, symbol='512800', open='10', high='11', low='9',
                          close='10', volume='100')).to_csv(self.root / 'china_candidate_prices.csv', index=False)
        self.payload = dict(code='512800', kline=[
            [int(d.strftime('%Y%m%d')), 10, 11, 9, 10, 100, 1000] for d in dates])
        self.calls = []

    def transport(self, url):
        self.calls.append(url)
        return json.dumps(self.payload).encode()

    def run_collection(self, **kwargs):
        return collection(self.root, as_of_date='2025-01-05', symbols=['512800'],
                          transport=self.transport, **kwargs)

    def test_offline_default_never_calls_network(self):
        result = self.run_collection()
        self.assertEqual(self.calls, [])
        self.assertEqual(result['symbols'][0]['acquisition'], 'cache_missing')
        self.assertEqual(result['stage_possible'], 0)

    def test_long_snapshot_reuses_parser_and_remains_evidence_only(self):
        result = self.run_collection(fetch=True)
        item = result['symbols'][0]
        self.assertGreaterEqual(item['best_completed_weeks'], 35)
        self.assertTrue(item['target_35_raw_weeks_met'])
        self.assertFalse(item['candidate']['stage_ready'])
        self.assertFalse(result['adjusted_history_verified'])
        self.assertFalse(result['corporate_actions_verified'])
        self.assertFalse(result['operational_eligible'])
        self.assertEqual(result['stage_withheld'], 12)

    def test_cache_reused_without_second_call_or_write(self):
        self.run_collection(fetch=True)
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.run_collection(fetch=True)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result['symbols'][0]['acquisition'], 'cache_reused')
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_invalid_cache_fails_closed_without_refetch(self):
        self.run_collection(fetch=True)
        path = next(self.root.rglob('response.json'))
        path.write_bytes(b'{}')
        item = self.run_collection(fetch=True)['symbols'][0]
        self.assertEqual(item['acquisition'], 'cache_invalid')
        self.assertIsNone(item['candidate'])
        self.assertEqual(len(self.calls), 1)

    def test_receipt_identity_tamper_rejected(self):
        self.run_collection(fetch=True)
        path = next(self.root.rglob('receipt.json'))
        receipt = json.loads(path.read_bytes())
        receipt['requested_url'] = 'https://example.com/'
        path.write_text(json.dumps(receipt), encoding='utf-8')
        self.assertEqual(self.run_collection()['symbols'][0]['acquisition'], 'cache_invalid')

    def test_one_failure_stops_further_calls_and_is_retained(self):
        def failure(url):
            self.calls.append(url)
            raise OSError('private error must not be emitted')
        result = collection(self.root, as_of_date='2025-01-05', fetch=True,
                            max_requests=12, transport=failure)
        self.assertEqual(result['network_requests'], 1)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result['symbols'][0]['acquisition'], 'collection_failed')
        self.assertNotIn('private error', json.dumps(result))
        self.assertEqual(self.run_collection(fetch=True)['symbols'][0]['acquisition'], 'attempt_retained')

    def test_request_budget_and_throttle(self):
        waits = []
        def response(url):
            self.calls.append(url)
            payload = dict(self.payload, code=url.split('/dayk/')[1].split('?')[0])
            return json.dumps(payload).encode()
        result = collection(self.root, as_of_date='2025-01-05', fetch=True,
                            max_requests=2, transport=response, sleeper=waits.append)
        self.assertEqual(result['network_requests'], 2)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(waits, [2.0])

    def test_mismatch_and_missing_days_not_bridged(self):
        self.payload['kline'][-40][4] = 10.5
        item = self.run_collection(fetch=True)['symbols'][0]
        self.assertEqual(item['candidate']['reconciled_sessions'], 39)
        self.assertEqual(item['candidate']['price_mismatch_sessions'], 1)
        self.assertFalse(item['target_35_raw_weeks_met'])

    def test_short_server_response_never_claims_requested_length(self):
        self.payload['kline'] = self.payload['kline'][-110:]
        item = self.run_collection(fetch=True)['symbols'][0]
        self.assertEqual(item['candidate']['reconciled_sessions'], 110)
        self.assertFalse(item['target_35_raw_weeks_met'])

    def test_missing_session_rejected_without_filling(self):
        self.payload['kline'].pop(50)
        item = self.run_collection(fetch=True)['symbols'][0]
        self.assertEqual(item['acquisition'], 'collection_failed')
        self.assertIsNone(item['candidate'])

    def test_512400_block_survives_long_agreement(self):
        path = self.root / 'china_candidate_prices.csv'
        prices = pd.read_csv(path, dtype=str)
        prices['symbol'] = '512400'
        prices.to_csv(path, index=False)
        self.payload['code'] = '512400'
        result = collection(self.root, as_of_date='2025-01-05', symbols=['512400'],
                            fetch=True, transport=self.transport)
        item = result['symbols'][0]
        self.assertTrue(item['target_35_raw_weeks_met'])
        self.assertTrue(item['candidate']['review_blocked'])
        self.assertFalse(item['candidate']['stage_ready'])
        for key in ('open', 'high', 'low', 'close', 'volume', 'kline'):
            self.assertNotIn('"' + key + '"', json.dumps(result))

    def test_invalid_parameters(self):
        for symbol, sessions in [('512800', 199), ('512800', 1001), ('999999', 500)]:
            with self.assertRaises(ValueError):
                request_url(symbol, sessions)
        for kwargs in [dict(max_requests=0), dict(max_requests=13), dict(interval=0)]:
            with self.assertRaises(ValueError):
                self.run_collection(**kwargs)

    def test_repository_input_rejected(self):
        (self.root / '.git').mkdir()
        with self.assertRaises(ValueError):
            self.run_collection(fetch=True)
        self.assertEqual(self.calls, [])

    def test_invalid_payload_saved_privately_without_receipt(self):
        self.payload['code'] = '512400'
        item = self.run_collection(fetch=True)['symbols'][0]
        self.assertEqual(item['acquisition'], 'collection_failed')
        self.assertEqual(len(list(self.root.rglob('response.json'))), 1)
        self.assertEqual(list(self.root.rglob('receipt.json')), [])


if __name__ == '__main__':
    unittest.main()
