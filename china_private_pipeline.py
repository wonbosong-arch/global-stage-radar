"""Opt-in private KIS refresh. Immutable generations; no public price writes."""
import json
import os
from datetime import datetime
from pathlib import Path
import uuid
from zoneinfo import ZoneInfo

import pandas as pd

from china_kis_stage import private_root, prepare, load_kis_stage, PRICE_FILE
from china_stage import validated_daily
from market_data import completed_bar_cutoff_date

ROOT = Path(__file__).resolve().parent
FLAG = 'CHINA_KIS_PRIVATE_REFRESH'


def current_snapshot(root):
    root = private_root(root)
    pointer = root / 'current.json'
    if not pointer.exists():
        return root  # Existing explicit private snapshots remain supported.
    generation = json.loads(pointer.read_text(encoding='utf-8'))['generation']
    if not isinstance(generation, str) or len(generation) != 32 or any(c not in '0123456789abcdef' for c in generation):
        raise ValueError('Invalid private snapshot generation')
    path = private_root(root / 'generations' / generation)
    if path.parent != (root / 'generations').resolve() or path.parent.parent != root:
        raise PermissionError('Private snapshot escaped storage root')
    return path


def refresh_private(root, *, provider, source_commit, now=None):
    """All 12 must return valid completed bars before publishing the pointer.

    Provider is shared across symbols to retain its global request throttle.
    Never merges adjusted histories from different snapshots or prints exceptions.
    """
    root = private_root(root)
    if not source_commit:
        raise ValueError('Collector commit required')
    generations = private_root(root / 'generations')
    if generations.parent != root:
        raise PermissionError('Private snapshot escaped storage root')
    metadata = json.loads((ROOT / 'china_sector_metadata.json').read_text(encoding='utf-8'))
    symbols = sorted(item['symbol'] for item in metadata)
    routes = pd.read_csv(ROOT / 'data/china_candidate_observation_manifest.csv', dtype=str)
    selected = routes[routes.symbol.isin(symbols)]
    if (len(symbols) != 12 or len(set(symbols)) != 12 or len(selected) != 12
            or selected.symbol.nunique() != 12 or not selected.exchange.eq('SHS').all()):
        raise ValueError('Invalid representative routes')
    now = now or datetime.now(ZoneInfo('Asia/Seoul'))
    cutoff = completed_bar_cutoff_date('SHS', now_kst=now)
    frames = []
    for symbol in symbols:
        bars = provider.fetch_daily(symbol, market='China', asset_type='sector_etf',
                                    exchange='SHS', max_pages=3)
        if bars.empty or 'symbol' not in bars or not bars.symbol.eq(symbol).all():
            raise ValueError('Missing or mismatched KIS symbol')
        bars = bars.copy()
        bars['date'] = pd.to_datetime(bars.date, errors='raise')
        bars = bars[bars.date.dt.strftime('%Y-%m-%d').le(cutoff)]
        frames.append(validated_daily(bars, as_of_date=now.date()))
    generation = uuid.uuid4().hex
    destination = private_root(root / 'generations' / generation)
    if destination.parent.parent != root:
        raise PermissionError('Private snapshot escaped storage root')
    destination.mkdir(parents=True, exist_ok=False)
    pd.concat(frames, ignore_index=True).to_csv(destination / PRICE_FILE, index=False)
    prepare(destination, source_commit=source_commit, observed_symbols=symbols)
    rows, _, _ = load_kis_stage(destination, as_of_date=now.date())
    # Stale/short/bad inputs must not replace the last usable generation.
    if not rows.stage_ready.all():
        raise ValueError('Private KIS snapshot not ready; previous snapshot retained')
    rows.to_csv(destination / 'china_kis_stage_report.csv', index=False)
    temporary = root / (generation + '.tmp')
    temporary.write_text(json.dumps({'generation': generation}), encoding='utf-8')
    os.replace(temporary, root / 'current.json')
    return {'symbols': len(rows), 'stage_ready': int(rows.stage_ready.sum()),
            'operational_eligible': False}


def configured_refresh():
    """Called by existing scheduled entry point only on explicit research opt-in."""
    if os.environ.get(FLAG) != 'research':
        raise PermissionError('Private refresh is disabled')
    root = os.environ.get('CHINA_PRIVATE_SNAPSHOT_DIR')
    commit = os.environ.get('GITHUB_SHA') or os.environ.get('CHINA_COLLECTOR_COMMIT')
    if not root or not commit:
        raise ValueError('Private storage and collector commit are required')
    private_root(root)  # Reject unsafe destinations before authentication/network.
    from kis_provider import KISOverseasPrices
    from data_providers import KISUSProvider
    result = refresh_private(root, provider=KISUSProvider(KISOverseasPrices()), source_commit=commit)
    if os.environ.get('CHINA_PRIVATE_OBJECT_TRANSFER') == 'publish':
        from china_private_delivery import configured_transfer
        configured_transfer(root, 'publish')
    return result
