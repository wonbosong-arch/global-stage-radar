"""Offline configuration inspection only; never resolves credentials or transfers data."""
import argparse
import json
import os
import re

from china_kis_stage import private_root
from china_private_delivery import S3Store


def inspect_configuration(role, environ=None):
    """Return fixed diagnostics, never environment values or exception messages.

    Passing checks is not evidence of IAM, app privacy, rights, or live readiness.
    Even when enabled this function performs no network or filesystem writes.
    """
    if role not in ('writer', 'reader'):
        raise ValueError('Invalid preflight role')
    env = os.environ if environ is None else environ
    mode = 'publish' if role == 'writer' else 'sync'
    enabled = env.get('CHINA_PRIVATE_OBJECT_TRANSFER') == mode
    result = dict(role=role, enabled=enabled, configuration_valid=False,
                  deployment_verified=False, operational_eligible=False, issues=[])
    if not enabled:
        result['issues'].append('transfer_disabled_or_role_mismatch')
        return result
    issues = result['issues']
    root = env.get('CHINA_PRIVATE_SNAPSHOT_DIR')
    try:
        if not root:
            raise ValueError()
        private_root(root)
    except (OSError, ValueError, PermissionError, RuntimeError):
        issues.append('private_root_missing_or_unsafe')
    region = env.get('CHINA_PRIVATE_S3_REGION', '')
    if not re.fullmatch(r'(us|eu|ap|ca|sa|me|af|il|mx)-(?:[a-z]+-)+[0-9]', region):
        issues.append('s3_region_missing_or_invalid')
    try:
        # Constructor validates syntax only; no boto3 import or client is created.
        S3Store(None, env.get('CHINA_PRIVATE_S3_BUCKET', ''),
                env.get('CHINA_PRIVATE_S3_PREFIX', ''), env.get('CHINA_PRIVATE_S3_OWNER', ''))
    except ValueError:
        issues.append('s3_destination_missing_or_invalid')
    if role == 'writer':
        if env.get('CHINA_KIS_PRIVATE_REFRESH') != 'research':
            issues.append('private_refresh_disabled')
        if not (env.get('GITHUB_SHA') or env.get('CHINA_COLLECTOR_COMMIT')):
            issues.append('collector_commit_missing')
        if not all(env.get(key) for key in ('KIS_APP_KEY', 'KIS_APP_SECRET')):
            issues.append('kis_credentials_not_in_process_environment')
    result['configuration_valid'] = not issues
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role', required=True, choices=('writer', 'reader'))
    args = parser.parse_args(argv)
    result = inspect_configuration(args.role)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['configuration_valid'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
