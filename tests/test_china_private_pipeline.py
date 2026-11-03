import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from china_private_pipeline import refresh_private, current_snapshot, configured_refresh
from china_dashboard import load_research, load_metadata
from tests.test_china_readiness_validation import history


NOW = datetime(2025, 12, 27, 7, tzinfo=ZoneInfo('Asia/Seoul'))


class Provider:
    def __init__(self, failure=None):
        self.calls = []
        self.failure = failure

    def fetch_daily(self, symbol, **kwargs):
        self.calls.append((symbol, kwargs))
        if len(self.calls) == self.failure:
            raise RuntimeError('private provider diagnostic')
        return history(45).assign(symbol=symbol)


class PipelineTests(unittest.TestCase):
    def test_real_adapter_uses_price_route_and_adjustment_without_order_calls(self):
        from kis_provider import KISOverseasPrices, DAILY_PATH, DAILY_TR_ID
        from data_providers import KISUSProvider
        from unittest.mock import Mock
        response = Mock(ok=True, status_code=200, headers={}, text='')
        response.json.return_value = {'rt_cd': '0', 'output2': [
            {'xymd': '20251226', 'open': '10', 'high': '11', 'low': '9', 'clos': '10', 'tvol': '100'}]}
        session = Mock()
        session.get.return_value = response
        client = KISOverseasPrices(app_key='synthetic', app_secret='synthetic', session=session)
        with patch.object(client, '_get_token', return_value='synthetic'):
            bars = KISUSProvider(client).fetch_daily('512800', market='China', asset_type='sector_etf', exchange='SHS', max_pages=3)
        self.assertEqual(len(bars), 1)
        args, kwargs = session.get.call_args
        self.assertTrue(args[0].endswith(DAILY_PATH))
        self.assertEqual(kwargs['headers']['tr_id'], DAILY_TR_ID)
        self.assertEqual(kwargs['params']['EXCD'], 'SHS')
        self.assertEqual(kwargs['params']['MODP'], '1')
        self.assertEqual(kwargs['params']['GUBN'], '0')
        session.post.assert_not_called()

    def test_full_refresh_dashboard_and_previous_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = Provider()
            result = refresh_private(directory, provider=provider, source_commit='synthetic', now=NOW)
            self.assertEqual(result['stage_ready'], 12)
            self.assertFalse(result['operational_eligible'])
            self.assertEqual(len(provider.calls), 12)
            for _, route in provider.calls:
                self.assertEqual(route, dict(market='China', asset_type='sector_etf', exchange='SHS', max_pages=3))
            # Actual dashboard loader, with the same as-of date as collection.
            from china_kis_stage import load_kis_stage
            with patch('china_kis_stage.load_kis_stage', side_effect=lambda path: load_kis_stage(path, as_of_date=NOW.date())):
                rows, prices, _ = load_research(directory)
            self.assertEqual(set(prices.symbol), {r['symbol'] for r in load_metadata()})
            self.assertTrue(rows.stage_ready.all())
            self.assertTrue(rows.previous_stage_label.notna().all())
            self.assertFalse(rows.stage2_new_entry.any())
            first = current_snapshot(directory)
            refresh_private(directory, provider=Provider(), source_commit='synthetic', now=NOW)
            self.assertNotEqual(current_snapshot(directory), first)
            self.assertTrue(first.exists())

    def test_failure_retains_pointer_and_stops_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            refresh_private(root, provider=Provider(), source_commit='synthetic', now=NOW)
            pointer = (root / 'current.json').read_bytes()
            provider = Provider(failure=2)
            with self.assertRaises(RuntimeError):
                refresh_private(root, provider=provider, source_commit='synthetic', now=NOW)
            self.assertEqual(len(provider.calls), 2)
            self.assertEqual((root / 'current.json').read_bytes(), pointer)
            with self.assertRaises(ValueError):
                refresh_private(root, provider=Provider(), source_commit='synthetic', now=datetime(2026, 2, 1, tzinfo=NOW.tzinfo))
            self.assertEqual((root / 'current.json').read_bytes(), pointer)

    def test_disabled_and_checkout_paths_never_construct_client(self):
        with patch.dict('os.environ', {}, clear=True), patch('kis_provider.KISOverseasPrices') as client:
            with self.assertRaises(PermissionError):
                configured_refresh()
            client.assert_not_called()
        with self.assertRaises(PermissionError):
            refresh_private(Path(__file__).parent, provider=Provider(), source_commit='synthetic', now=NOW)

    def test_pointer_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'current.json').write_text(json.dumps({'generation': '../escape'}))
            with self.assertRaises(ValueError):
                current_snapshot(root)

    def test_scheduled_entrypoint_redacts_failure_and_never_falls_through(self):
        from refresh_china_candidate_prices import main
        import io
        from contextlib import redirect_stdout
        with patch.dict('os.environ', {'CHINA_KIS_PRIVATE_REFRESH': 'research'}), patch(
                'china_private_pipeline.configured_refresh', side_effect=RuntimeError('secret-token')):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(), 1)
            self.assertNotIn('secret-token', output.getvalue())
            self.assertIn('previous_snapshot_retained', output.getvalue())

    def test_invalid_symbol_and_ohlc_cannot_publish(self):
        for field, value in [('symbol', 'WRONG'), ('close', -1)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                provider = Provider()
                original = provider.fetch_daily
                provider.fetch_daily = lambda symbol, **kw: original(symbol, **kw).assign(**{field: value})
                with self.assertRaises(ValueError):
                    refresh_private(directory, provider=provider, source_commit='synthetic', now=NOW)
                self.assertFalse((Path(directory) / 'current.json').exists())


if __name__ == '__main__':
    unittest.main()
