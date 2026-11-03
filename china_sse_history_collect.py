"""Cache-first, bounded SSE history acquisition; evidence only, never activation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import time
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

import pandas as pd

from china_dashboard import load_metadata
from china_history_audit import audit_snapshot, audit_symbol, external_path, official_daily
from china_stage import validated_daily

SELECT = 'date,open,high,low,close,volume,amount'
MAX_BYTES = 2_000_000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect rejected')


def request_url(symbol, sessions):
    if symbol not in {item['symbol'] for item in load_metadata()}:
        raise ValueError('Unknown representative symbol')
    if not 200 <= sessions <= 1000:
        raise ValueError('sessions must be between 200 and 1000')
    return (f'https://yunhq.sse.com.cn:32042/v1/sh1/dayk/{symbol}?'
            + urlencode(dict(begin=-sessions, end=-1, period='day', select=SELECT)))


def download(url):
    request = Request(url, headers={'User-Agent': 'GlobalStageRadar-private-history-audit/1.0',
                                   'Referer': 'https://www.sse.com.cn/'})
    with build_opener(NoRedirect).open(request, timeout=15) as response:
        raw = response.read(MAX_BYTES + 1)
        if response.status != 200 or len(raw) > MAX_BYTES:
            raise ValueError('Invalid or oversized response')
        return raw


def checked_payload(raw, symbol, as_of_date):
    payload = json.loads(raw)
    # Reuse #197 parser and existing calendar validation, never a second parser.
    validated_daily(official_daily(payload, symbol), as_of_date=as_of_date)
    return payload


def collection(root, *, as_of_date, sessions=500, symbols=None, fetch=False,
               max_requests=1, interval=2.0, transport=download, sleeper=time.sleep):
    root = external_path(root)
    if not 1 <= max_requests <= 12 or interval < 2:
        raise ValueError('Request budget 1..12 and interval >=2 seconds required')
    baseline = audit_snapshot(root, as_of_date=as_of_date)
    known = [item['symbol'] for item in load_metadata()]
    symbols = known if symbols is None else symbols
    if not symbols or len(set(symbols)) != len(symbols) or any(s not in known for s in symbols):
        raise ValueError('Unique representative symbols required')
    prices = pd.read_csv(external_path(root / 'china_candidate_prices.csv'), dtype=str)
    results, calls, network_blocked = [], 0, False
    for symbol in symbols:
        url = request_url(symbol, sessions)
        # Exact request cache; preserve every attempt and original baseline bytes.
        key = hashlib.sha256(url.encode()).hexdigest()
        directory = external_path(root / 'sse_history' / key)
        receipt_path = external_path(directory / 'receipt.json')
        payload = None
        status = 'cache_missing'
        if receipt_path.exists():
            try:
                receipt = json.loads(receipt_path.read_bytes())
                if (receipt['requested_url'] != url or receipt['symbol'] != symbol
                        or receipt['http_status'] != 200
                        or receipt['local_path'] != f'sse_history/{key}/response.json'):
                    raise ValueError('Receipt identity mismatch')
                raw = external_path(directory / 'response.json').read_bytes()
                if len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != receipt['sha256']:
                    raise ValueError('Receipt hash mismatch')
                payload = checked_payload(raw, symbol, as_of_date)
                status = 'cache_reused'
            except (ValueError, KeyError, TypeError, OSError, ArithmeticError):
                status = 'cache_invalid'  # Never repair or overwrite suspect evidence automatically.
        elif fetch and calls < max_requests and not network_blocked:
            directory.mkdir(parents=True, exist_ok=True)
            # An interrupted/failed attempt remains immutable; request a different window to retry.
            attempt_path = external_path(directory / 'attempt.json')
            if attempt_path.exists() or external_path(directory / 'response.json').exists():
                status = 'attempt_retained'
            else:
                if calls:
                    sleeper(interval)
                calls += 1
                attempt = dict(symbol=symbol, requested_url=url,
                               retrieved_at_utc=datetime.now(timezone.utc).isoformat())
                with attempt_path.open('x', encoding='utf-8') as output:
                    json.dump(attempt, output)
                try:
                    raw = transport(url)
                    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
                        raise ValueError('Invalid response bytes')
                    with external_path(directory / 'response.json').open('xb') as output:
                        output.write(raw)
                    payload = checked_payload(raw, symbol, as_of_date)
                    receipt = dict(attempt, http_status=200, sha256=hashlib.sha256(raw).hexdigest(),
                                   local_path=f'sse_history/{key}/response.json', bytes=len(raw))
                    with receipt_path.open('x', encoding='utf-8') as output:
                        json.dump(receipt, output, indent=2)
                    status = 'collected'
                except (OSError, ValueError, TypeError, KeyError, ArithmeticError):
                    # No exception text/HTTP bodies on stdout; stop futile calls after first failure.
                    payload = None
                    status = 'collection_failed'
                    network_blocked = True
                    with external_path(directory / 'failure.json').open('x', encoding='utf-8') as output:
                        json.dump(dict(attempt, status=status), output)
        candidate = (audit_symbol(prices[prices.symbol.eq(symbol)].copy(), payload, symbol,
                                  as_of_date=as_of_date) if payload is not None else None)
        if candidate is not None:
            official = official_daily(payload, symbol)
            candidate.update(sse_sha256=hashlib.sha256(raw).hexdigest(),
                             official_sessions=len(official),
                             official_start=official.date.min().strftime('%Y-%m-%d'),
                             official_end=official.date.max().strftime('%Y-%m-%d'))
        prior = next(r for r in baseline['symbols'] if r['symbol'] == symbol)
        # Independently audited snapshots only: no splicing or silent revised-price overwrite.
        best = max([r for r in (prior, candidate) if r is not None],
                   key=lambda r: r['reconciled_sessions'] if r['reconciliation_valid'] else -1)
        results.append(dict(symbol=symbol, acquisition=status, requested_url=url,
                            baseline=prior, candidate=candidate,
                            best_reconciled_sessions=best['reconciled_sessions'],
                            best_completed_weeks=best['completed_weeks'],
                            target_35_raw_weeks_met=best['completed_weeks'] >= 35))
    return dict(as_of_date=as_of_date, kis_sha256=baseline['kis_sha256'],
                requested_sessions=sessions, network_requests=calls,
                stage_possible=0, stage_withheld=len(known), operational_eligible=False,
                kis_modp='1 (provider setting; adjustment semantics unverified)',
                corporate_actions_verified=False, adjusted_history_verified=False,
                note='Raw agreement only; hashes do not prove authenticity. 512400 remains blocked.',
                symbols=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of-date', required=True)
    parser.add_argument('--sessions', type=int, default=500)
    parser.add_argument('--symbols', nargs='+')
    parser.add_argument('--fetch', action='store_true', help='Opt in to bounded official SSE calls')
    parser.add_argument('--max-requests', type=int, default=1)
    args = parser.parse_args()
    root = os.environ.get('CHINA_PRIVATE_SNAPSHOT_DIR')
    if not root:
        parser.error('CHINA_PRIVATE_SNAPSHOT_DIR required; no repository fallback')
    print(json.dumps(collection(root, as_of_date=args.as_of_date, sessions=args.sessions,
                                symbols=args.symbols, fetch=args.fetch,
                                max_requests=args.max_requests), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
