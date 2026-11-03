import copy
import unittest
from decimal import ROUND_HALF_EVEN

import pandas as pd

from china_corporate_action_audit import event_audit


class CorporateActionAuditTests(unittest.TestCase):
    def setUp(self):
        self.dates = pd.to_datetime(['2026-07-01', '2026-07-02', '2026-07-03', '2026-07-06'])
        self.payload = dict(code='512480', kline=[
            [int(d.strftime('%Y%m%d')), 10, 12, 8, 10, 100, 1000] for d in self.dates])
        self.daily = pd.DataFrame(dict(date=self.dates, symbol='512480', open='10',
                                       high='12', low='8', close='10', volume='100'))
        self.event = dict(symbol='512480', kind='split', ex_date='2026-07-03',
                          value='2', source_url='https://www.sse.com.cn/test',
                          evidence_level='synthetic_test_only')

    def run_audit(self, events=None):
        return event_audit(self.daily, self.payload, '512480',
                           [self.event] if events is None else events, as_of_date='2026-07-07')

    def test_split_boundary_and_no_mutation_or_promotion(self):
        self.daily.loc[:1, ['open', 'high', 'low', 'close']] = ['5', '6', '4', '5']
        before = self.daily.copy(deep=True)
        payload = copy.deepcopy(self.payload)
        result = self.run_audit()
        self.assertEqual(result['hypothesis_matching_fields'], 16)
        self.assertEqual(result['affected_matching_fields'], 8)
        self.assertEqual(result['raw_mismatch_hypothesis_matching_days'], 2)
        self.assertEqual(result['raw_audit']['reconciled_sessions'], 2)
        self.assertFalse(result['adjusted_history_verified'])
        self.assertFalse(result['stage_ready'])
        self.assertFalse(result['operational_eligible'])
        pd.testing.assert_frame_equal(self.daily, before)
        self.assertEqual(self.payload, payload)

    def test_cash_per_unit_and_half_up(self):
        self.event.update(kind='cash', value='0.005')
        self.daily.loc[:1, ['open', 'high', 'low', 'close']] = ['9.995', '11.994', '7.996', '9.995']
        self.assertEqual(self.run_audit()['hypothesis_matching_fields'], 16)

    def test_multiple_events_compose_only_for_earlier_rows(self):
        cash = dict(self.event, kind='cash', ex_date='2026-07-06', value='1')
        self.daily.loc[:1, ['open', 'high', 'low', 'close']] = ['4.5', '5.4', '3.6', '4.5']
        self.daily.loc[2, ['open', 'high', 'low', 'close']] = ['9', '10.8', '7.2', '9']
        self.assertEqual(self.run_audit([cash, self.event])['hypothesis_matching_fields'], 16)

    def test_wrong_factor_does_not_get_fitted(self):
        self.daily.loc[:1, ['open', 'high', 'low', 'close']] = ['4', '4.8', '3.2', '4']
        result = self.run_audit()
        self.assertEqual(result['raw_mismatch_unexplained_days'], 2)
        self.assertEqual(result['affected_matching_fields'], 0)
        self.assertEqual(result['event_factors'][0]['factor'], '0.5')

    def test_invalid_events_rejected(self):
        for override in (dict(value='NaN'), dict(value='0'), dict(symbol='512400'),
                         dict(kind='merger'), dict(ex_date='2026-07-04'),
                         dict(source_url=''), dict(evidence_level='')):
            with self.subTest(override=override), self.assertRaises(ValueError):
                self.run_audit([dict(self.event, **override)])
        with self.assertRaises(ValueError):
            self.run_audit([self.event, self.event])

    def test_missing_previous_session_rejected(self):
        self.event['ex_date'] = '2026-07-01'
        with self.assertRaises(ValueError):
            self.run_audit()

    def test_half_tick_ambiguity_is_separate_from_exact_match(self):
        self.payload['kline'][0][1] = 10.001
        self.daily.loc[:1, ['open', 'high', 'low', 'close']] = ['5', '6', '4', '5']
        result = self.run_audit()
        self.assertEqual(result['hypothesis_matching_fields'], 15)
        self.assertEqual(result['fields_within_half_tick'], 16)
        alternative = event_audit(self.daily, self.payload, '512480', [self.event],
                                  as_of_date='2026-07-07', rounding=ROUND_HALF_EVEN)
        self.assertEqual(alternative['hypothesis_matching_fields'], 16)
        self.assertFalse(alternative['provider_algorithm_confirmed'])

    def test_no_events_is_not_proof_of_no_actions(self):
        result = self.run_audit([])
        self.assertEqual(result['hypothesis_matching_fields'], 16)
        self.assertFalse(result['event_inventory_complete'])
        self.assertFalse(result['provider_algorithm_confirmed'])

    def test_512400_remains_blocked_even_with_exact_hypothesis(self):
        self.daily['symbol'] = '512400'
        self.payload['code'] = '512400'
        result = event_audit(self.daily, self.payload, '512400', [], as_of_date='2026-07-07')
        self.assertTrue(result['review_blocked'])
        self.assertFalse(result['stage_ready'])
        self.assertFalse(result['adjusted_history_verified'])

    def test_missing_official_session_fails_closed(self):
        self.payload['kline'].pop(1)
        with self.assertRaises(ValueError):
            self.run_audit()


if __name__ == '__main__':
    unittest.main()
