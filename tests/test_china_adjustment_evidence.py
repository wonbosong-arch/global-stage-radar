"""Synthetic evidence only; tests run under both unittest and pytest."""
import copy
import hashlib
import json
import unittest
from urllib.parse import urlencode

from china_adjustment_evidence import document_content_check, evidence_gate, notice_coverage
from china_stage import stage_readiness
from tests.test_china_readiness_validation import history
from tests import test_china_corporate_action_audit as event_fixtures


class AdjustmentEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.payload = dict(result=[dict(SECURITY_CODE='512800', SSEDATE='2026-07-01',
                                       TITLE='Synthetic annual report',
                                       URL='/disclosure/fund/announcement/synthetic.pdf')],
                            pageHelp=dict(total=1, pageNo=1, pageSize=100))
        self.query = dict(sqlId='COMMON_PL_JJXX_JJGG_NEW_L', SECURITY_CODE='512800',
                          START_DATE='2025-07-30', END_DATE='2026-11-03',
                          BULLETIN_TYPE='fund05', isPagination='true',
                          **{'pageHelp.pageNo': '1', 'pageHelp.pageSize': '100'})

    def coverage(self, *, start='2025-07-30', end='2026-10-27', bad_hash=False):
        body = json.dumps(self.payload).encode()
        receipt = dict(url='https://query.sse.com.cn/commonQuery.do?' + urlencode(self.query),
                       status=200, sha256='bad' if bad_hash else hashlib.sha256(body).hexdigest())
        return notice_coverage(body, receipt, symbol='512800', interval_start=start, interval_end=end)

    def test_complete_filtered_negative_never_proves_no_events(self):
        before = copy.deepcopy(self.payload)
        result = self.coverage()
        self.assertTrue(result['pagination_complete'])
        self.assertTrue(result['bounded_negative'])
        self.assertFalse(result['event_inventory_complete'])
        self.assertFalse(result['adjusted_history_verified'])
        self.assertFalse(result['stage_ready'])
        self.assertEqual(self.payload, before)

    def test_incomplete_page_and_interval_do_not_support_negative(self):
        self.payload['pageHelp']['total'] = 2
        self.assertFalse(self.coverage()['bounded_negative'])
        self.assertFalse(self.coverage()['pagination_complete'])
        self.payload['pageHelp']['total'] = 1
        for start, end in [('2025-07-29', '2026-10-27'), ('2025-07-30', '2026-11-04')]:
            with self.subTest(start=start, end=end):
                self.assertFalse(self.coverage(start=start, end=end)['bounded_negative'])

    def test_empty_page_requires_zero_total_and_still_not_inventory(self):
        self.payload['result'] = []
        self.assertFalse(self.coverage()['bounded_negative'])
        self.payload['pageHelp']['total'] = 0
        result = self.coverage()
        self.assertTrue(result['bounded_negative'])
        self.assertFalse(result['event_inventory_complete'])

    def test_event_keywords_including_conversion_and_merger_cancel_negative(self):
        for word in ('分红', '收益分配', '拆分', '折算', '合并'):
            with self.subTest(word=word):
                self.payload['result'][0]['TITLE'] = 'Synthetic ' + word
                self.assertEqual(self.coverage()['event_title_matches'], 1)
                self.assertFalse(self.coverage()['bounded_negative'])

    def test_hash_identity_date_duplicate_and_page_errors_rejected(self):
        with self.assertRaises(ValueError):
            self.coverage(bad_hash=True)
        original = copy.deepcopy(self.payload)
        for field, value in [('SECURITY_CODE', '512400'), ('SSEDATE', '2025-01-01'),
                             ('TITLE', ''), ('URL', 'https://example.com/test')]:
            self.payload = copy.deepcopy(original)
            self.payload['result'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.coverage()
        self.payload = copy.deepcopy(original)
        self.payload['result'] *= 2
        self.payload['pageHelp']['total'] = 2
        with self.assertRaises(ValueError):
            self.coverage()
        for value in (-1, True, '1'):
            self.payload = copy.deepcopy(original)
            self.payload['pageHelp']['total'] = value
            with self.subTest(total=value), self.assertRaises(ValueError):
                self.coverage()

    def test_wrong_query_or_error_payload_rejected(self):
        self.query['SECURITY_CODE'] = '512400'
        with self.assertRaises(ValueError):
            self.coverage()
        self.query['SECURITY_CODE'] = '512800'
        self.payload['actionErrors'] = ['synthetic service error']
        with self.assertRaises(ValueError):
            self.coverage()

    def test_http_200_error_redirect_and_parameter_text_are_not_algorithm(self):
        result = document_content_check(b'<meta http-equiv="refresh" content="0;url=/error2.jsp">')
        self.assertTrue(result['error_redirect'])
        self.assertFalse(result['modp_mentioned'])
        self.assertFalse(result['provider_algorithm_confirmed'])
        result = document_content_check(b'MODP 0/1 zdiv precision')
        self.assertTrue(result['modp_mentioned'])
        self.assertFalse(result['provider_algorithm_confirmed'])

    def test_34_35_week_length_and_forged_flags_never_clear_adjustment_gate(self):
        for count in (34, 35, 63):
            with self.subTest(count=count):
                readiness = stage_readiness(history(count), as_of_date='2025-12-27')
                raw = dict(symbol='512800', reconciliation_valid=True,
                           **{k: readiness[k] for k in ('completed_weeks', 'prior_comparison_ready')},
                           adjusted_history_verified=True, provider_algorithm_confirmed=True,
                           event_inventory_complete=True, stage_ready=True)
                result = evidence_gate(raw)
                self.assertEqual(result['raw_35_week_prerequisite'], count >= 35)
                self.assertFalse(result['adjustment_evidence_gate'])
                self.assertFalse(result['stage_ready'])
                self.assertFalse(result['operational_eligible'])
                raw['symbol'] = '512400'
                self.assertTrue(evidence_gate(raw)['review_blocked'])
                raw['reconciliation_valid'] = False
                self.assertFalse(evidence_gate(raw)['raw_35_week_prerequisite'])

    def test_split_ties_report_both_directions_without_selecting_a_rule(self):
        fixture = event_fixtures.CorporateActionAuditTests()
        fixture.setUp()
        fixture.payload['kline'][0][1] = 10.001
        fixture.payload['kline'][1][1] = 10.001
        fixture.daily.loc[:1, ['open', 'high', 'low', 'close']] = ['5', '6', '4', '5']
        fixture.daily.loc[1, 'open'] = '5.001'
        result = fixture.run_audit()
        self.assertEqual(result['affected_half_tick_ties'], 2)
        self.assertEqual(result['affected_ties_lower'], 1)
        self.assertEqual(result['affected_ties_upper'], 1)
        self.assertEqual(result['affected_outside_half_tick'], 0)
        self.assertFalse(result['provider_algorithm_confirmed'])
        fixture.daily.loc[0, 'open'] = '5.0001'
        self.assertEqual(fixture.run_audit()['affected_off_mill_grid'], 1)
        fixture.daily.loc[0, 'open'] = '4.999'
        self.assertEqual(fixture.run_audit()['affected_outside_half_tick'], 1)


if __name__ == '__main__':
    unittest.main()
