"""Verify the published report distinguishes unattempted work from provider failures."""
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import pandas as pd
import pytest

import candidate_coverage_audit as audit


@pytest.mark.parametrize("schema", [1, 2])
def test_partial_refresh_report_keeps_deferrals_distinct_from_failures_and_fresh_data(schema):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'data').mkdir()
        symbols = ['FRESH', 'FAILED', 'DEFERRED', 'UNKNOWN', 'ADDED', 'SKIPPED']
        pd.DataFrame({'symbol': symbols, 'discovered_at': [
            '2026-10-27T00:00:00Z'] * 4 + ['2026-10-28T12:00:00Z', '2026-10-27T00:00:00Z']
        }).to_csv(root / 'candidates.csv', index=False)
        pd.DataFrame({'symbol': ['SPY']}).to_csv(root / 'universe.csv', index=False)
        status = {
            'status_schema_version': schema,
            'error_count': 2 if schema == 1 else 1,
            'updated_at_utc': '2026-10-28T10:00:00Z',
            'fresh_data_symbols': ['FRESH'],
            'failed_symbols': ['FAILED', 'DEFERRED'] if schema == 1 else ['FAILED'],
            'deferred_symbols': ['DEFERRED'],
            'skipped_symbols': ['SKIPPED'],
            'errors': [{'symbol': 'FAILED', 'error': 'timeout'},
                       *([{'symbol': 'DEFERRED', 'error': 'refresh_deferred_time_budget'}] if schema == 1 else [])],
        }
        (root / 'data/candidate_daily_prices_status.json').write_text(json.dumps(status))
        output = root / 'report.csv'
        argv = ['audit', '--candidates', str(root / 'candidates.csv'),
                '--universe', str(root / 'universe.csv'), '--output', str(output),
                '--adr-ratio-registry', str(root / 'absent.csv'),
                '--yahoo-market-cap-observations', str(root / 'absent.csv')]
        # Isolate report construction; execute the actual CLI's status attachment
        # and CSV publication, including precedence and discovered-after handling.
        report = pd.DataFrame({'symbol': symbols, 'snapshot_coverage_status': ['missing'] * len(symbols)})
        with patch.object(audit, 'ROOT', root), patch('sys.argv', argv), \
                patch.object(audit, 'load_price_snapshots', return_value=pd.DataFrame()), \
                patch.object(audit, 'build_candidate_coverage_report', return_value=report), \
                patch('builtins.print'):
            assert audit.main() == 0
        result = pd.read_csv(output).set_index('symbol')
        assert result['refresh_attempt_outcome'].to_dict() == {
            'FRESH': 'fresh_data_returned', 'FAILED': 'request_failed',
            'DEFERRED': 'deferred_time_budget', 'UNKNOWN': 'not_confirmed_in_latest_attempt',
            'ADDED': 'not_confirmed_in_latest_attempt',
            'SKIPPED': 'unsupported_retry_cooldown',
        }
        assert result['refresh_attempt_error_count'].eq(1).all()
        assert result['refresh_attempt_deferred_count'].eq(1).all()
        assert result.loc['ADDED', 'refresh_attempt_outcome_detail'] == 'candidate_added_after_latest_attempt'
        assert result.loc['DEFERRED', 'refresh_attempt_outcome_detail'] == 'deferred_time_budget'
        assert result.index[result['latest_attempt_kis_response_observed']].tolist() == ['FRESH']
