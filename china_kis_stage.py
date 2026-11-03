"""Private KIS-adjusted ETF analysis; no collection, activation or publication."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from china_stage import stage_readiness, validated_daily

ROOT = Path(__file__).resolve().parent
PRICE_FILE = 'china_candidate_prices.csv'
MANIFEST_FILE = 'kis_stage_manifest.json'


def private_root(root):
    path = Path(root).expanduser().resolve()
    # Worktrees and nested paths are public-checkout boundaries too.
    if any((p / '.git').exists() for p in (path, *path.parents)):
        raise PermissionError('가격 경로는 공개 저장소 밖이어야 합니다.')
    return path


def prepare(root, *, source_commit, observed_symbols):
    """Record known collector provenance, not an independent price attestation.

    Caller must have checked the source collector used KIS SHS MODP=1 and
    observed successful responses for these symbols. Never calls a provider.
    """
    path = private_root(root)
    manifest = dict(price_basis='KIS_ADJUSTED', exchange='SHS', modp='1',
                    research_commit=source_commit,
                    observed_symbols=sorted(set(observed_symbols)),
                    price_sha256=hashlib.sha256((path / PRICE_FILE).read_bytes()).hexdigest(),
                    operational_eligible=False)
    (path / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


def load_kis_stage(root, *, as_of_date=None):
    path = private_root(root)
    manifest = json.loads((path / MANIFEST_FILE).read_text(encoding='utf-8'))
    if (manifest.get('price_basis') != 'KIS_ADJUSTED' or manifest.get('exchange') != 'SHS'
            or manifest.get('modp') != '1' or not manifest.get('research_commit')):
        raise ValueError('KIS 조정주가 출처 설정 오류')
    payload = (path / PRICE_FILE).read_bytes()
    if hashlib.sha256(payload).hexdigest() != manifest.get('price_sha256'):
        raise ValueError('개인 KIS 스냅샷 무결성 불일치')
    prices = pd.read_csv(path / PRICE_FILE, dtype={'symbol': str})
    if 'symbol' not in prices:
        raise ValueError('KIS 종목 열 부족')
    metadata = json.loads((ROOT / 'china_sector_metadata.json').read_text(encoding='utf-8'))
    if len(metadata) != 12 or len({r['symbol'] for r in metadata}) != 12:
        raise ValueError('대표 ETF 12종 식별 오류')
    routes = pd.read_csv(ROOT / 'data/china_candidate_observation_manifest.csv', dtype=str)
    rows, valid = [], []
    for item in metadata:
        symbol = item['symbol']
        frame = prices[prices.symbol.eq(symbol)].copy()
        result = dict(stage_label='판정 보류', stage_ready=False, input_valid=False,
                      stage2_new_entry=None, operational_eligible=False,
                      stage_reason='KIS 지원 관측 또는 ETF 식별 근거 부족')
        route = routes[routes.symbol.eq(symbol)]
        identity_ok = all(item.get(k) for k in ('name_en', 'tracked_index_code',
                                                'tracked_index_name', 'benchmark_source_url',
                                                'index_source_url'))
        if (identity_ok and len(route) == 1 and route.iloc[0].exchange == 'SHS'
                and symbol in manifest.get('observed_symbols', [])):
            result = stage_readiness(frame, as_of_date=as_of_date, price_basis='KIS_ADJUSTED')
            if result['input_valid']:
                valid.append(validated_daily(frame, as_of_date=as_of_date))
        rows.append(dict(item, **result, preview_status=result['stage_reason']))
    preview = pd.concat(valid, ignore_index=True) if valid else prices.iloc[:0].copy()
    return pd.DataFrame(rows), preview, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--as-of')
    parser.add_argument('--prepare-source-commit')
    parser.add_argument('--observed-symbols', nargs='+')
    args = parser.parse_args()
    if args.prepare_source_commit:
        if not args.observed_symbols:
            parser.error('--observed-symbols is required for provenance preparation')
        prepare(args.root, source_commit=args.prepare_source_commit,
                observed_symbols=args.observed_symbols)
    candidates, _, _ = load_kis_stage(args.root, as_of_date=args.as_of)
    output = private_root(args.root) / 'china_kis_stage_report.csv'
    candidates.to_csv(output, index=False)
    # No prices or individual indicators in console/public logs.
    print(json.dumps(dict(candidates=len(candidates),
                          stage_ready=int(candidates.stage_ready.sum()),
                          stage2=int(candidates.stage_label.eq('Stage 2 후보').sum()),
                          operational_eligible=0)))


if __name__ == '__main__':
    main()
