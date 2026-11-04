"""Read stored CSVs only; write a reproducible intake audit, never source data."""
import hashlib
import json
from pathlib import Path
import sys
import pandas as pd
from intake_large_cap_review_candidates import build_review_only_candidates
from yahoo_master_cap_batch import build_cap_triage, build_large_cap_candidate_review_queue
root = Path(__file__).resolve().parents[2]
def read(name):
    return pd.read_csv(root/'data'/f'{name}.csv', dtype=str, keep_default_na=False)
c, a, q, m, o, t = map(read, ['stock_universe_candidates','monitoring_universe','yahoo_large_cap_candidate_review','unranked_us_stock_master','yahoo_unranked_master_market_caps','yahoo_master_cap_triage'])
rebuilt = build_large_cap_candidate_review_queue(build_cap_triage(o, m))
keys = lambda d: set(zip(d.symbol.str.strip().str.upper(), d.exchange.str.strip().str.upper()))
us = c[c.exchange.isin(['NAS','NYS','AMS'])]
result, status = build_review_only_candidates(c, a, q, '2026-11-05')
added = result.iloc[len(c):]
again, repeated = build_review_only_candidates(result, a, q, '2026-11-06')
rebuilt_result, rebuilt_status = build_review_only_candidates(c, a, rebuilt, "2026-11-05")
assert len(added) == 186 and len(again) == len(result)
assert result.iloc[:len(c)].equals(c)
assert added.activation_status.eq('pending_review').all()
assert added.identity_status.eq('review_required').all()
assert added.market_cap_status.eq('not_verified').all()
report = dict(base_sha='b37bf7b4d5a4ccd790877678d970dffe717b866d',
    total_registry=len(c), us_registry=len(us), registry_by_exchange=c.exchange.value_counts().to_dict(),
    master_rows=len(m), master_duplicate_pairs=int(m.duplicated(['symbol','listing_exchange']).sum()),
    observations=len(o), triage=t.triage_status.value_counts().to_dict(), queue_rows=len(q),
    queue_instrument_types=q.instrument_type.value_counts().to_dict(),
    queue_duplicate_pairs=int(q.duplicated(['symbol','exchange']).sum()),
    invalid_queue_venues=int((~q.exchange.isin(['NAS','NYS','AMS'])).sum()),
    intake_eligible_queue=int(q.instrument_type.eq('equity_candidate_unverified').sum()),
    eligible_unregistered=len(added), added_by_exchange=added.exchange.value_counts().to_dict(),
    slots_before=2500-len(c), slots_after=2500-len(result), simulated_total=len(result),
    simulated_us_total=len(us)+len(added), second_simulation_added=repeated['large_cap_review_candidates_added'],
    rebuilt_queue_identity_matches=keys(q) == keys(rebuilt), rebuilt_queue_rows=len(rebuilt),
    stored_only_identities=sorted(keys(q)-keys(rebuilt)), rebuilt_only_identities=sorted(keys(rebuilt)-keys(q)),
    rebuilt_eligible_unregistered=len(rebuilt_result)-len(c), added_symbols=sorted(added.symbol),
    status=status,
    input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'data').glob('*') if p.is_file() and p.suffix in ['.csv','.json']})
Path(sys.argv[1]).write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['input_sha256','added_symbols']},indent=2))
