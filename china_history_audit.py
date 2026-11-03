"""Offline evidence inventory. Never returns prices or authorizes Stage/display."""
import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd

from china_dashboard import load_metadata
from china_stage import stage_readiness, validated_daily

FIELDS = ['open', 'high', 'low', 'close', 'volume']


def official_daily(payload, symbol):
    """Decode the retained SSE yunhq kline format, rejecting ambiguous evidence."""
    if not isinstance(payload, dict) or payload.get('code') != symbol or not payload.get('kline'):
        raise ValueError('SSE identity or observations missing')
    records = []
    for row in payload['kline']:
        if not isinstance(row, (list, tuple)) or len(row) != 7:
            raise ValueError('SSE row shape')
        date = pd.to_datetime(str(row[0]), format='%Y%m%d', errors='raise')
        values = [Decimal(str(v)) for v in row[1:]]
        if not all(v.is_finite() for v in values):
            raise ValueError('SSE nonfinite value')
        op, high, low, close, volume, amount = values
        if volume <= 0 or amount <= 0 or not low <= amount / volume <= high:
            raise ValueError('SSE turnover/volume inconsistency')
        records.append(dict(date=date, symbol=symbol, **dict(zip(FIELDS, values[:5]))))
    return pd.DataFrame(records)


def audit_symbol(daily, payload, symbol, *, as_of_date):
    """Compare every overlapping session; never bridge a mismatch or missing day.

    The comparable suffix must end at the latest supplied KIS observation.
    Counts and prerequisite flags describe evidence only, not adjustment quality.
    """
    result = dict(symbol=symbol, stage_ready=False, stage_label='판정 보류',
                  operational_eligible=False, adjusted_history_verified=False,
                  previous_stage_verified=False, reconciliation_valid=False,
                  reconciled_sessions=0, matched_sessions=0, mismatch_sessions=0,
                  price_mismatch_sessions=0, volume_mismatch_sessions=0,
                  missing_official_sessions=0, completed_weeks=0,
                  ma30_ready=False, slope4_ready=False, prior_comparison_ready=False,
                  ret26_history_ready=False, review_blocked=symbol == '512400')
    try:
        if daily.empty or not daily.symbol.astype(str).eq(symbol).all():
            raise ValueError('KIS identity or observations missing')
        frame = validated_daily(daily, as_of_date=as_of_date)
        official = official_daily(payload, symbol)
        validated_daily(official, as_of_date=as_of_date)
        result['observed_sessions'] = len(frame)
        result['observed_start'] = frame.date.min().strftime('%Y-%m-%d')
        result['observed_end'] = frame.date.max().strftime('%Y-%m-%d')
        result['observed_completed_weeks'] = stage_readiness(
            frame, as_of_date=as_of_date)['completed_weeks']
        reference = official.set_index('date')
        matches = []
        for row in frame.itertuples(index=False):
            if row.date not in reference.index:
                result['missing_official_sessions'] += 1
                matches.append(False)
                continue
            day = reference.loc[row.date]
            price_match = all(Decimal(str(getattr(row, key))) == Decimal(str(day[key]))
                              for key in FIELDS[:4])
            volume_match = Decimal(str(row.volume)) == Decimal(str(day.volume))
            match = price_match and volume_match
            result['price_mismatch_sessions'] += int(not price_match)
            result['volume_mismatch_sessions'] += int(not volume_match)
            matches.append(match)
            result['matched_sessions'] += int(match)
            result['mismatch_sessions'] += int(not match)
        # Only the uninterrupted suffix is usable for current-bar prerequisites.
        start = len(matches)
        while start and matches[start - 1]:
            start -= 1
        suffix = frame.iloc[start:]
        if not suffix.empty:
            ready = stage_readiness(suffix, as_of_date=as_of_date)
            for key in ('completed_weeks', 'ma30_ready', 'slope4_ready', 'prior_comparison_ready'):
                result[key] = ready[key]
            result.update(reconciled_sessions=len(suffix),
                          reconciled_start=suffix.date.min().strftime('%Y-%m-%d'),
                          reconciled_end=suffix.date.max().strftime('%Y-%m-%d'),
                          ret26_history_ready=ready['completed_weeks'] >= 27)
        result['reconciliation_valid'] = True
        result['reason'] = 'Raw OHLCV agreement only; adjustment/corporate actions and previous Stage unverified'
        if symbol == '512400':
            result['reason'] += '; existing 512400 review block remains'
    except (ValueError, TypeError, KeyError, OverflowError, ArithmeticError):
        # Do not echo source rows or exceptions containing private values.
        result['reason'] = 'Invalid or incomplete input evidence'
    return result


def external_path(path):
    resolved = Path(path).expanduser().resolve()
    if any((parent / '.git').exists() for parent in (resolved, *resolved.parents)):
        raise ValueError('Private evidence must be outside every Git checkout')
    return resolved


def audit_snapshot(root, *, as_of_date):
    root = external_path(root)
    price_path = external_path(root / 'china_candidate_prices.csv')
    raw = price_path.read_bytes()
    prices = pd.read_csv(price_path, dtype=str)
    manifest_path = external_path(root / 'market_manifest.json')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.is_file() else []
    reports = []
    for item in load_metadata():
        symbol = item['symbol']
        path = external_path(root / 'sources' / f'{symbol}_sse_daily.json')
        if not path.is_file():
            report = audit_symbol(pd.DataFrame(), {}, symbol, as_of_date=as_of_date)
        else:
            source = path.read_bytes()
            try:
                entries = [entry for entry in manifest if entry.get('symbol') == symbol]
                if len(entries) != 1:
                    raise ValueError('Missing or ambiguous source receipt')
                entry = entries[0]
                url = urlparse(entry.get('requested_url', ''))
                query = parse_qs(url.query)
                if (entry.get('http_status') != 200
                        or entry.get('sha256') != hashlib.sha256(source).hexdigest()
                        or entry.get('local_path') != f'sources/{symbol}_sse_daily.json'
                        or url.scheme != 'https' or url.netloc != 'yunhq.sse.com.cn:32042'
                        or url.path != f'/v1/sh1/dayk/{symbol}'
                        or query.get('period') != ['day']
                        or query.get('select') != ['date,open,high,low,close,volume,amount']):
                    raise ValueError('Source receipt mismatch')
                payload = json.loads(source)
            except (ValueError, UnicodeError):
                payload = {}
            report = audit_symbol(prices[prices.symbol.eq(symbol)].copy(), payload,
                                  symbol, as_of_date=as_of_date)
            report['sse_sha256'] = hashlib.sha256(source).hexdigest()
        reports.append(report)
    return dict(as_of_date=as_of_date, kis_sha256=hashlib.sha256(raw).hexdigest(),
                note='Hashes identify local bytes, not authenticity or adjustment verification',
                stage_possible=0, stage_withheld=len(reports), symbols=reports)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of-date', required=True)
    args = parser.parse_args()
    root = os.environ.get('CHINA_PRIVATE_SNAPSHOT_DIR')
    if not root:
        parser.error('CHINA_PRIVATE_SNAPSHOT_DIR is required; no repository fallback')
    print(json.dumps(audit_snapshot(root, as_of_date=args.as_of_date), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
