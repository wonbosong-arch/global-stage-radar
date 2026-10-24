# Pending-candidate activation gate

Status: policy checklist. This document does not approve any candidate and does not replace live provider or price-quality checks.

## Non-negotiable rule

A candidate stays `pending_review` until a human-reviewed record shows that every applicable gate below is satisfied. A stored price history, a completed report, or a low blocker count is not activation approval.

## Gate 1 — instrument identity

- Confirm exact ticker, instrument class, primary/listed exchange, trading currency, and issuer name from an official issuer or exchange source.
- Record the source URL and review date in `identity_evidence_url` and `identity_reviewed_at`.
- Treat issuer domicile separately from trading market and market benchmark.
- For ADR/ADS instruments, confirm depositary ratio from the issuer/depositary source and ensure the price/share-count basis is consistent.
- Resolve special statuses such as `issuer_proxy_review_required` and `issuer_country_review_required`; do not silently convert them to verified.

## Gate 2 — provider support

- Confirm the exact instrument can be requested through the intended KIS endpoint and environment.
- Record the actual response outcome and timestamp in a durable status artifact.
- Distinguish a successful historical response from current endpoint support; a cached CSV alone is not proof.
- A provider status of `not_checked`, blank, or any value other than an explicitly approved supported state remains blocked.

## Gate 3 — usable price history

- Require at least 150 unique daily bars after duplicate removal.
- Confirm dates parse correctly and that OHLCV data has already passed the shared validation rules.
- Check that the latest candidate bar is not more than seven calendar days behind the latest date in the combined snapshot; account for exchange holidays when interpreting warnings.
- Confirm the assigned market and sector benchmarks have usable history and sufficiently recent dates.

## Gate 4 — market-cap provenance (stocks only)

- Keep the value in USD billions and record its source URL and as-of date.
- Reconcile price, shares outstanding, currency, and instrument/share-class basis. For ADRs, explicitly account for the depositary ratio.
- A secondary-source number or plausible arithmetic match is provisional, not independently verified.
- Do not apply this gate to ETFs or commodity proxies.

## Gate 5 — benchmark mapping

- Confirm the market benchmark represents the intended trading-market context.
- Confirm the sector benchmark is consistent with the dashboard's documented sector taxonomy.
- Document intentional exceptions instead of forcing them to match a default mapping.

## Gate 6 — final review and activation

Only after all applicable gates are satisfied:
1. Review the candidate's full report row and evidence links.
2. Resolve every blocker and evidence gap; explain any explicitly accepted exception.
3. Change `activation_status` only through a deliberate, documented review.
4. Add the instrument to the active monitoring universe in a separate change.
5. Preserve a review record so activation can be traced and reversed.

## Current conservative disposition

All candidates in `data/stock_universe_candidates.csv` remain `pending_review` unless a later, explicit human-reviewed change says otherwise. The automated coverage report must continue to emit `activation_recommendation=keep_pending_review`; it is a triage aid, not an approval engine.

## Interpretation of report fields

- `provider_observed_data_returned=true`: at least one row for the symbol exists in the combined saved snapshot. It does not mean a live request was just made.
- `provider_status`: separately recorded provider-review state; this must not be inferred from snapshot rows.
- `evidence_fields_complete=true`: the report's listed provenance fields are populated, not that their contents are correct.
- `metadata_and_snapshot_checks_clear`: no blocker encoded by the current audit was found; this is not an activation recommendation.

## Machine-readable report guard

The coverage report emits `activation_gate_status=blocked_pending_manual_review` and an explanatory `activation_gate_reason` for every candidate. This is deliberately conservative and remains true even when the encoded snapshot checks show no blockers. It prevents a report row from being mistaken for an approval decision.

## Latest refresh attempt fields

The generated coverage report also records the latest status-file timestamp and per-symbol outcome:

- `refresh_attempt_at_utc`: timestamp of the last recorded attempt, not necessarily the current run.
- `refresh_attempt_outcome=fresh_data_returned`: the latest status artifact explicitly lists a successful non-empty fetch for that symbol.
- `refresh_attempt_outcome=request_failed`: the latest status artifact records a failure for that symbol.
- `refresh_attempt_outcome=not_confirmed_in_latest_attempt`: no fresh success or symbol-specific failure is recorded; do not interpret this as success.
- `refresh_attempt_error_count`, `refresh_attempt_requested_symbols`, and `refresh_attempt_fresh_data_symbol_count` provide run-level context.

The refresh script now records the symbols that returned fresh data separately from retained historical rows. This improves traceability but does not independently validate OHLCV quality or approve activation.

