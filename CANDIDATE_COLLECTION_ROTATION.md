# Candidate price collection

Entry point: `refresh_candidate_prices.py`; publisher:
`.github/workflows/candidate_prices_manual.yml`. Only pending-review candidates
outside the monitoring universe are requested. Collection never activates them.
China/Japan ETF review snapshots and the active daily snapshot remain separate.

## Rotation and request budget

Scheduling state lives in the existing `candidate_daily_prices_status.json`:
`collection_state` records each symbol's last attempt, last success, outcome and
listing route. `pending_symbols` records a checkpoint's unfinished tail;
`deferred_symbols` records symbols unattempted when the time budget expires.
Legacy deferrals recorded only inside `errors` are also understood.

1. Missing histories that have never been attempted enter first.
2. The previous unfinished/deferred tail resumes in its saved order.
3. Remaining symbols follow oldest attempt, then oldest successful refresh (or
   latest stored bar when migrating legacy metadata).

A missing symbol that fails loses its first-attempt priority. Repeated failures
therefore cannot block the rest of the tail. Explicit unsupported-route errors
wait 30 days, with immediate retry eligibility when the route changes. Empty
responses, authentication, throttling and transient failures are not permanent
unsupported classifications. Existing provider throttles, page counts and bounded
retries are retained; collection does not add concurrency or API retries.

The 900-second budget stops **starting** new symbols. An in-flight request can
finish its bounded provider retries before final publication. Every 25 attempted
symbols a checkpoint is saved locally. Actions commits the completed/failed
snapshot at the existing publication step. Abrupt runner loss before that step
can lose local progress; the previously committed snapshot remains available.

## Snapshot and status contract (v2)

All previous valid rows are merged with validated completed response bars;
new rows win the same symbol/date. Wrong-symbol, malformed, non-finite and invalid
OHLCV responses are failures and cannot overwrite existing good rows. Invalid,
future and incomplete-session rows remain excluded under the existing cutoff.

Both files are staged before replacement. Serialization/write/rename failures
restore the previous pair; an additional rollback failure retains its `.bak`
recovery copy and raises its location. Each status contains a CSV SHA-256 and
validated per-symbol coverage. A hard kill between the two atomic renames may
leave stale metadata: the collector, dashboard diagnostics and coverage report
reject mismatched metadata while preserving independently readable prices.

`error_count`/`errors` and `failed_symbols` now contain actual failures only.
`deferred_symbol_count`, `skipped_symbol_count`, `preserved_symbol_count` and
`missing_symbol_count` are separate. Attempted = succeeded + failed during a
normal run; requested = attempted + deferred + skipped. Preserved is available
previous history for symbols without fresh success, and can overlap other states.
`refresh_complete` requires every requested candidate to succeed in that run.
The dashboard and report support legacy inclusive error counts as well as v2.

`started_at_utc` is collection start; `finished_at_utc` is set only for the final
collection save. `updated_at_utc`/`updated_at_kst` identify the save/checkpoint;
they are not a market bar date. A workflow-level failure has unknown attempted
count and does not claim checkpoint data as a fresh success.

## Schedule and remaining operational validation

Daily KIS collection: `0 22 * * 0-5` UTC = Monday–Saturday 07:00 KST.
Candidate follow-up: `5 22 * * 0-5` = 07:05 KST. Korea has no daylight saving
time; GitHub scheduling/serialization may delay actual starts. Crypto has a
separate workflow. No cron or provider credentials were changed by this fix.

After review/merge, observe consecutive scheduled candidate runs: verify their
attempted sets rotate, deferred counts remain separate from provider failures,
snapshot commits succeed, and missing/short-history coverage improves. CI and
mocked API tests do not establish live KIS collection success.
