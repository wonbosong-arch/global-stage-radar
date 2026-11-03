"""Disabled-by-default private S3 delivery; never creates infrastructure or ACLs."""
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from china_kis_stage import private_root, load_kis_stage, PRICE_FILE, MANIFEST_FILE
from china_private_pipeline import current_snapshot

FILES = (PRICE_FILE, MANIFEST_FILE)
MAX_BYTES = 16 * 1024 * 1024


def generation_id(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{32}', value):
        raise ValueError('Invalid private generation')
    return value


class S3Store:
    """Uses existing approved AWS credentials; no endpoint override/public URLs."""
    def __init__(self, client, bucket, prefix, owner):
        if (not bucket or not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', bucket)
                or not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*', prefix)
                or not re.fullmatch(r'[0-9]{12}', owner)):
            raise ValueError('Invalid private object storage configuration')
        self.client, self.bucket, self.prefix, self.owner = client, bucket, prefix, owner

    def get(self, key, *, missing_ok=False):
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self.prefix + '/' + key,
                                              ExpectedBucketOwner=self.owner)
        except Exception as error:
            if missing_ok and getattr(error, 'response', {}).get('Error', {}).get('Code') == 'NoSuchKey':
                return None, None
            raise RuntimeError('Private object read failed') from None
        body = response['Body']
        try:
            payload = body.read(MAX_BYTES + 1)
        finally:
            body.close()
        if len(payload) > MAX_BYTES:
            raise ValueError('Private object exceeds size limit')
        return payload, response['ETag']

    def put(self, key, payload, *, previous=None):
        if len(payload) > MAX_BYTES:
            raise ValueError('Private object exceeds size limit')
        condition = {'IfMatch': previous} if previous else {'IfNoneMatch': '*'}
        try:
            self.client.put_object(Bucket=self.bucket, Key=self.prefix + '/' + key,
                                   ExpectedBucketOwner=self.owner, Body=payload,
                                   ServerSideEncryption='AES256', **condition)
        except Exception:
            raise RuntimeError('Private object write failed; pointer not advanced') from None


def publish(root, store, *, as_of_date=None):
    """All immutable files first, remote pointer CAS last. Caller serializes writers."""
    path = current_snapshot(root)
    generation = generation_id(path.name)
    rows, _, _ = load_kis_stage(path, as_of_date=as_of_date)
    if not rows.stage_ready.all():
        raise ValueError('Private generation not ready')
    _, previous = store.get('current.json', missing_ok=True)
    hashes = {}
    for name in FILES:
        payload = (path / name).read_bytes()
        hashes[name] = hashlib.sha256(payload).hexdigest()
        key = 'generations/' + generation + '/' + name
        existing, _ = store.get(key, missing_ok=True)
        if existing is None:
            store.put(key, payload)
        elif existing != payload:
            raise ValueError('Immutable private generation collision')
    pointer = json.dumps({'generation': generation, 'sha256': hashes}).encode()
    store.put('current.json', pointer, previous=previous)
    return generation


def sync(root, store, *, as_of_date=None):
    """Download one pinned generation, verify/Stage-check, atomically expose locally.

    Unique local generations prevent concurrent readers from seeing partial writes.
    Failure preserves prior local pointer but is raised, never presented as fresh.
    """
    root = private_root(root)
    payload, _ = store.get('current.json')
    pointer = json.loads(payload)
    generation = generation_id(pointer['generation'])
    hashes = pointer.get('sha256', {})
    if set(hashes) != set(FILES) or any(not isinstance(v, str) or not re.fullmatch('[0-9a-f]{64}', v) for v in hashes.values()):
        raise ValueError('Invalid private object manifest')
    cached = current_snapshot(root)
    if all((cached / name).is_file() and hashlib.sha256((cached / name).read_bytes()).hexdigest() == hashes[name] for name in FILES):
        rows, _, _ = load_kis_stage(cached, as_of_date=as_of_date)
        if not rows.stage_ready.all():
            raise ValueError('Private generation not ready')
        return cached
    destination = private_root(root / 'generations' / uuid.uuid4().hex)
    if destination.parent != (root / 'generations').resolve() or destination.parent.parent != root:
        raise PermissionError('Private cache escaped storage root')
    destination.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        data, _ = store.get('generations/' + generation + '/' + name)
        if hashlib.sha256(data).hexdigest() != hashes[name]:
            raise ValueError('Private object integrity mismatch')
        (destination / name).write_bytes(data)
    rows, _, _ = load_kis_stage(destination, as_of_date=as_of_date)
    if not rows.stage_ready.all():
        raise ValueError('Private generation not ready')
    temporary = root / (uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps({'generation': destination.name}), encoding='utf-8')
    os.replace(temporary, root / 'current.json')
    return destination


def configured_store(mode):
    if mode not in ('publish', 'sync') or os.environ.get('CHINA_PRIVATE_OBJECT_TRANSFER') != mode:
        raise PermissionError('Private object transfer disabled')
    # Deliberately optional: no new dependency or credential lookup on default paths.
    import boto3
    from botocore.config import Config
    region = os.environ['CHINA_PRIVATE_S3_REGION']
    # Force official regional HTTPS; ignore AWS_ENDPOINT_URL environment overrides.
    if not re.fullmatch(r'(us|eu|ap|ca|sa|me|af|il|mx)-(?:[a-z]+-)+[0-9]', region):
        raise ValueError('Invalid private S3 region')
    client = boto3.client('s3', region_name=region,
                          endpoint_url='https://s3.' + region + '.amazonaws.com',
                          config=Config(connect_timeout=5, read_timeout=15,
                                        retries={'total_max_attempts': 2}))
    return S3Store(client, os.environ['CHINA_PRIVATE_S3_BUCKET'],
                   os.environ['CHINA_PRIVATE_S3_PREFIX'], os.environ['CHINA_PRIVATE_S3_OWNER'])


def configured_transfer(root, mode):
    private_root(root)  # Reject checkout paths before credential resolution/network.
    try:
        store = configured_store(mode)
        return publish(root, store) if mode == 'publish' else sync(root, store)
    except Exception:
        raise RuntimeError('Private transfer failed; previous snapshot retained') from None
