import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from china_private_delivery import publish, sync, S3Store, configured_transfer
from china_private_pipeline import refresh_private, current_snapshot
from tests.test_china_private_pipeline import Provider, NOW


class Store:
    def __init__(self):
        self.objects = {}
        self.writes = []
        self.fail = None

    def get(self, key, *, missing_ok=False):
        if missing_ok and key not in self.objects:
            return None, None
        data = self.objects[key]
        return data, hashlib.sha256(data).hexdigest()

    def put(self, key, payload, *, previous=None):
        if key == self.fail:
            raise RuntimeError('synthetic failure')
        current = self.get(key)[1] if key in self.objects else None
        if current != previous:
            raise RuntimeError('CAS conflict')
        self.objects[key] = payload
        self.writes.append(key)


class DeliveryTests(unittest.TestCase):
    def seed(self, root):
        refresh_private(root, provider=Provider(), source_commit='synthetic', now=NOW)

    def test_separate_volumes_roundtrip_actual_dashboard_and_cache(self):
        from china_kis_stage import load_kis_stage
        from china_dashboard import load_research
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as cache:
            self.seed(source)
            store = Store()
            publish(source, store, as_of_date=NOW.date())
            self.assertEqual(store.writes[-1], 'current.json')
            first = sync(cache, store, as_of_date=NOW.date())
            self.assertNotEqual(first, current_snapshot(source))
            with patch('china_kis_stage.load_kis_stage', side_effect=lambda path: load_kis_stage(path, as_of_date=NOW.date())):
                rows, prices, _ = load_research(cache)
            self.assertTrue(rows.stage_ready.all())
            self.assertEqual(prices.symbol.nunique(), 12)
            self.assertFalse(rows.operational_eligible.any())
            self.assertEqual(sync(cache, store, as_of_date=NOW.date()), first)
            publish(source, store, as_of_date=NOW.date())  # Safe retry after partial upload.

    def test_partial_upload_does_not_advance_remote_pointer(self):
        with tempfile.TemporaryDirectory() as source:
            self.seed(source)
            store = Store()
            publish(source, store, as_of_date=NOW.date())
            previous = store.objects['current.json']
            self.seed(source)
            generation = current_snapshot(source).name
            store.fail = 'generations/' + generation + '/kis_stage_manifest.json'
            with self.assertRaises(RuntimeError):
                publish(source, store, as_of_date=NOW.date())
            self.assertEqual(previous, store.objects['current.json'])
            store.fail = None
            publish(source, store, as_of_date=NOW.date())
            self.assertNotEqual(previous, store.objects['current.json'])

    def test_tamper_missing_file_and_bad_pointer_preserve_local(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as cache:
            self.seed(source)
            store = Store()
            publish(source, store, as_of_date=NOW.date())
            sync(cache, store, as_of_date=NOW.date())
            previous = (Path(cache) / 'current.json').read_bytes()
            refresh_private(source, provider=Provider(), source_commit='synthetic-next', now=NOW)
            publish(source, store, as_of_date=NOW.date())
            original = dict(store.objects)
            key = 'generations/' + current_snapshot(source).name + '/china_candidate_prices.csv'
            for kind in ('tamper', 'missing', 'traversal', 'stale'):
                with self.subTest(kind=kind):
                    store.objects = dict(original)
                    if kind == 'tamper':
                        store.objects[key] = b'corrupt'
                    elif kind == 'missing':
                        del store.objects[key]
                    elif kind == 'traversal':
                        store.objects['current.json'] = json.dumps({'generation': '../escape'}).encode()
                    with self.assertRaises((ValueError, KeyError)):
                        sync(cache, store, as_of_date='2026-03-01' if kind == 'stale' else NOW.date())
                    self.assertEqual(previous, (Path(cache) / 'current.json').read_bytes())

    def test_checkout_rejected_before_any_store_access(self):
        store = Mock()
        with self.assertRaises(PermissionError):
            sync(Path(__file__).parent, store)
        store.get.assert_not_called()

    def test_concurrent_pointer_change_rejected(self):
        with tempfile.TemporaryDirectory() as source:
            self.seed(source)
            store = Store()
            publish(source, store, as_of_date=NOW.date())
            original_put = store.put

            def concurrent_put(key, payload, **kwargs):
                if key == 'current.json':
                    store.objects[key] = b'another writer'
                return original_put(key, payload, **kwargs)

            store.put = concurrent_put
            with self.assertRaisesRegex(RuntimeError, 'CAS conflict'):
                publish(source, store, as_of_date=NOW.date())
            self.assertEqual(store.objects['current.json'], b'another writer')

    def test_collector_publishes_only_after_local_collection(self):
        from china_private_pipeline import configured_refresh
        with tempfile.TemporaryDirectory() as root, patch.dict('os.environ', {
                'CHINA_PRIVATE_SNAPSHOT_DIR': root, 'CHINA_KIS_PRIVATE_REFRESH': 'research',
                'CHINA_COLLECTOR_COMMIT': 'synthetic', 'CHINA_PRIVATE_OBJECT_TRANSFER': 'publish'}), patch(
                'kis_provider.KISOverseasPrices'), patch('data_providers.KISUSProvider'), patch(
                'china_private_pipeline.refresh_private', return_value={'stage_ready': 12}) as refresh, patch(
                'china_private_delivery.configured_transfer') as transfer:
            self.assertEqual(configured_refresh(), {'stage_ready': 12})
            transfer.assert_called_once_with(root, 'publish')
            transfer.reset_mock()
            refresh.side_effect = ValueError('bad input')
            with self.assertRaises(ValueError):
                configured_refresh()
            transfer.assert_not_called()

    def test_s3_contract_encryption_owner_cas_bounded_reads_and_redaction(self):
        client = Mock()
        store = S3Store(client, 'private-test-bucket', 'china/research', '123456789012')
        store.put('current.json', b'{}', previous='etag')
        kw = client.put_object.call_args.kwargs
        self.assertEqual(kw['IfMatch'], 'etag')
        self.assertEqual(kw['ServerSideEncryption'], 'AES256')
        self.assertEqual(kw['ExpectedBucketOwner'], '123456789012')
        self.assertNotIn('ACL', kw)
        store.put('immutable', b'{}')
        self.assertEqual(client.put_object.call_args.kwargs['IfNoneMatch'], '*')
        body = BytesIO(b'payload')
        client.get_object.return_value = {'Body': body, 'ETag': 'etag'}
        self.assertEqual(store.get('current.json'), (b'payload', 'etag'))
        self.assertTrue(body.closed)
        client.get_object.side_effect = RuntimeError('secret credentials')
        with self.assertRaisesRegex(RuntimeError, '^Private object read failed$'):
            store.get('current.json', missing_ok=True)

    def test_disabled_transfer_and_errors_are_redacted(self):
        with tempfile.TemporaryDirectory() as cache, patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, '^Private transfer failed; previous snapshot retained$'):
                configured_transfer(cache, 'sync')

    def test_optional_real_sdk_serializes_conditional_put_without_network(self):
        try:
            import boto3
            from botocore.stub import Stubber
        except ImportError:
            self.skipTest('Optional private deployment SDK not installed')
        client = boto3.client('s3', region_name='ap-northeast-2',
                              aws_access_key_id='synthetic', aws_secret_access_key='synthetic')
        store = S3Store(client, 'private-test-bucket', 'china/research', '123456789012')
        with Stubber(client) as stub:
            stub.add_response('put_object', {}, {
                'Bucket': 'private-test-bucket', 'Key': 'china/research/current.json',
                'ExpectedBucketOwner': '123456789012', 'Body': b'{}',
                'ServerSideEncryption': 'AES256', 'IfMatch': 'etag'})
            store.put('current.json', b'{}', previous='etag')
            stub.assert_no_pending_responses()

    def test_dashboard_sync_only_for_explicit_environment_mode(self):
        from china_dashboard import load_research
        with tempfile.TemporaryDirectory() as cache, patch.dict('os.environ', {
                'CHINA_PRIVATE_SNAPSHOT_DIR': cache, 'CHINA_PRIVATE_OBJECT_TRANSFER': 'sync'}), patch(
                'china_private_delivery.configured_transfer', side_effect=RuntimeError('fixed failure')) as transfer:
            with self.assertRaisesRegex(RuntimeError, 'fixed failure'):
                load_research()
            transfer.assert_called_once_with(cache, 'sync')
            transfer.reset_mock()
            with self.assertRaises(FileNotFoundError):
                load_research(cache)
            transfer.assert_not_called()


if __name__ == '__main__':
    unittest.main()
