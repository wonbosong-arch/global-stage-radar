"""Offline event hypothesis tests. Never exports or modifies adjusted prices."""
import argparse
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN
import hashlib
import json
import os
from pathlib import Path

import pandas as pd

from china_history_audit import audit_symbol, external_path, official_daily
from china_sse_history_collect import collection, request_url
from china_stage import validated_daily


def event_audit(daily, payload, symbol, events, *, as_of_date, rounding=ROUND_HALF_UP):
    """Test disclosed factors, never fit a ratio to observed KIS prices.

    Cash hypothesis: 1-D/previous raw close; split hypothesis: 1/new shares.
    Multiply all later factors in full precision, then round to .001.
    This is an explicit research convention, not a confirmed KIS algorithm.
    """
    if rounding not in (ROUND_HALF_UP, ROUND_HALF_EVEN):
        raise ValueError('Unsupported rounding hypothesis')
    raw_audit = audit_symbol(daily, payload, symbol, as_of_date=as_of_date)
    if not raw_audit['reconciliation_valid']:
        raise ValueError('Invalid evidence')
    frame = validated_daily(daily, as_of_date=as_of_date).set_index('date')
    official = validated_daily(official_daily(payload, symbol),
                               as_of_date=as_of_date).set_index('date')
    factors = []
    seen = set()
    for event in sorted(events, key=lambda e: e['ex_date']):
        date = pd.Timestamp(event['ex_date'])
        if (event['symbol'] != symbol or date in seen or date not in official.index
                or not event.get('source_url', '').startswith('https://')
                or not event.get('evidence_level')):
            raise ValueError('Ambiguous event evidence')
        seen.add(date)
        before = official.loc[official.index < date]
        if before.empty:
            raise ValueError('Previous official session missing')
        amount = Decimal(event['value'])
        if not amount.is_finite() or amount <= 0:
            raise ValueError('Invalid event value')
        if event['kind'] == 'cash':
            factor = 1 - amount / Decimal(str(before.iloc[-1].close))
        elif event['kind'] == 'split':
            factor = 1 / amount
        else:
            raise ValueError('Unsupported event kind')
        if factor <= 0:
            raise ValueError('Invalid theoretical factor')
        factors.append((date, factor))
    total = matched = affected = affected_matched = volume_matched = within_half_tick = 0
    raw_mismatch_explained = raw_mismatch_unexplained = 0
    max_residual = Decimal(0)
    for date, row in frame.iterrows():
        if date not in official.index:
            continue
        source = official.loc[date]
        factor = Decimal(1)
        for ex_date, value in factors:
            if date < ex_date:  # ex-date itself must remain unadjusted by that event
                factor *= value
        day_match = True
        raw_match = True
        for key in ('open', 'high', 'low', 'close'):
            original = Decimal(str(source[key]))
            observed = Decimal(str(row[key]))
            theoretical = original * factor
            equal = theoretical.quantize(Decimal('.001'), rounding=rounding) == observed
            total += 1
            matched += int(equal)
            if factor != 1:
                affected += 1
                affected_matched += int(equal)
            max_residual = max(max_residual, abs(theoretical - observed))
            within_half_tick += int(abs(theoretical - observed) <= Decimal('.0005'))
            day_match &= equal
            raw_match &= original == observed
        if not raw_match:
            raw_mismatch_explained += int(day_match)
            raw_mismatch_unexplained += int(not day_match)
        volume_matched += int(Decimal(str(row.volume)) == Decimal(str(source.volume)))
    return dict(symbol=symbol, raw_audit=raw_audit, disclosed_events=len(events), rounding=rounding,
                tested_fields=total, hypothesis_matching_fields=matched,
                fields_within_half_tick=within_half_tick,
                affected_fields=affected, affected_matching_fields=affected_matched,
                raw_mismatch_hypothesis_matching_days=raw_mismatch_explained,
                raw_mismatch_unexplained_days=raw_mismatch_unexplained,
                volume_matching_days=volume_matched,
                max_unrounded_residual=str(max_residual),
                event_factors=[dict(ex_date=d.strftime('%Y-%m-%d'), factor=str(f))
                               for d, f in factors],
                conclusion='hypothesis_only' if events else 'raw_agreement_only_no_event_inventory',
                provider_algorithm_confirmed=False, event_inventory_complete=False,
                adjusted_history_verified=False, stage_ready=False,
                operational_eligible=False, review_blocked=symbol == '512400')


def audit_private(root, *, as_of_date):
    root = external_path(root)
    # Reuse #198's immutable receipt/hash checks, offline only; no new collection.
    retained = collection(root, as_of_date=as_of_date)
    price_path = external_path(root / 'china_candidate_prices.csv')
    price_bytes = price_path.read_bytes()
    if hashlib.sha256(price_bytes).hexdigest() != retained['kis_sha256']:
        raise ValueError('KIS input changed after validation')
    from io import BytesIO
    prices = pd.read_csv(BytesIO(price_bytes), dtype=str)
    events = json.loads((Path(__file__).parent / 'research/china_corporate_actions.json').read_text())
    results = []
    for item in retained['symbols']:
        symbol = item['symbol']
        if item['acquisition'] != 'cache_reused' or item['candidate'] is None:
            raise ValueError('Validated long cache required')
        key = hashlib.sha256(request_url(symbol, 500).encode()).hexdigest()
        raw = external_path(root / 'sse_history' / key / 'response.json').read_bytes()
        if hashlib.sha256(raw).hexdigest() != item['candidate']['sse_sha256']:
            raise ValueError('Cache changed after validation')
        result = event_audit(prices[prices.symbol.eq(symbol)].copy(), json.loads(raw),
                             symbol, [e for e in events if e['symbol'] == symbol],
                             as_of_date=as_of_date)
        result['sse_sha256'] = item['candidate']['sse_sha256']
        result['alternative_half_even'] = event_audit(
            prices[prices.symbol.eq(symbol)].copy(), json.loads(raw), symbol,
            [e for e in events if e['symbol'] == symbol], as_of_date=as_of_date,
            rounding=ROUND_HALF_EVEN)
        results.append(result)
    return dict(as_of_date=as_of_date, kis_sha256=retained['kis_sha256'], network_requests=0,
                stage_possible=0, stage_withheld=len(results), symbols=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of-date', required=True)
    args = parser.parse_args()
    root = os.environ.get('CHINA_PRIVATE_SNAPSHOT_DIR')
    if not root:
        parser.error('CHINA_PRIVATE_SNAPSHOT_DIR required; no repository fallback')
    print(json.dumps(audit_private(root, as_of_date=args.as_of_date), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
