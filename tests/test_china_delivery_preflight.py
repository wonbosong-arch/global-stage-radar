import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from china_delivery_preflight import inspect_configuration


class PreflightTests(unittest.TestCase):
    def config(self, root, role='writer'):
        return dict(CHINA_PRIVATE_OBJECT_TRANSFER='publish' if role == 'writer' else 'sync',
                    CHINA_PRIVATE_SNAPSHOT_DIR=str(root), CHINA_PRIVATE_S3_REGION='ap-northeast-2',
                    CHINA_PRIVATE_S3_BUCKET='example-private', CHINA_PRIVATE_S3_PREFIX='china/research',
                    CHINA_PRIVATE_S3_OWNER='123456789012', CHINA_KIS_PRIVATE_REFRESH='research',
                    GITHUB_SHA='test-commit', KIS_APP_KEY='sensitive-key', KIS_APP_SECRET='sensitive-secret')

    def test_default_off_does_not_inspect_root(self):
        with patch('china_delivery_preflight.private_root', side_effect=AssertionError):
            result = inspect_configuration('writer', {})
        self.assertFalse(result['enabled'])
        self.assertFalse(result['configuration_valid'])

    def test_valid_both_roles_no_client_or_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'not-created'
            with patch('china_private_delivery.configured_store', side_effect=AssertionError):
                for role in ('writer', 'reader'):
                    env = self.config(root, role)
                    if role == 'reader':
                        del env['KIS_APP_KEY'], env['KIS_APP_SECRET']
                    result = inspect_configuration(role, env)
                    self.assertTrue(result['configuration_valid'])
                    self.assertFalse(result['deployment_verified'])
                    self.assertFalse(result['operational_eligible'])
            self.assertFalse(root.exists())

    def test_checkout_and_invalid_settings_are_redacted(self):
        env = self.config(Path(__file__).resolve().parents[1])
        env.update(CHINA_PRIVATE_S3_REGION='secret-region', CHINA_PRIVATE_S3_OWNER='secret-owner',
                   CHINA_KIS_PRIVATE_REFRESH='', GITHUB_SHA='', KIS_APP_KEY='')
        result = inspect_configuration('writer', env)
        self.assertEqual(len(result['issues']), 6)
        output = json.dumps(result)
        for value in ('secret-region', 'secret-owner', 'sensitive-secret', str(Path(__file__))):
            self.assertNotIn(value, output)

    def test_mode_mismatch_and_bad_role(self):
        self.assertFalse(inspect_configuration('reader', {'CHINA_PRIVATE_OBJECT_TRANSFER': 'publish'})['enabled'])
        with self.assertRaises(ValueError):
            inspect_configuration('other', {})
