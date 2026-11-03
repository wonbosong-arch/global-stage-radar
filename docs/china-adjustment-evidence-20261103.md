# KIS adjustment evidence sufficiency — 2026-11-03

## Scope
Independent branch from #199 d1ae87ea3fe188fc7ccc807e2a637968ccaf9e4c.
Integration is data-validation-mvp dceea1877ede390b6b953689e749d89c1ca04145.
Dependency order: #197 → #198 → #199 → this Draft. Existing PRs unchanged.
Before edits, checked GitHub integration/head metadata, open PRs, related chat
activity and #199 exact-head CI (Unit and Python both success). No overlapping
active development was found. Local fetch failed at Windows schannel
SEC_E_NO_CREDENTIALS; the connected GitHub API confirmed the remote state.
This adds offline diagnostics, tests and integer residual counters, reusing
existing event/history/readiness validators. No application/UI/price changes.

## Official evidence and correction
Official samples pinned at commit 3a9be59a3ed8745720dc3aa9d584bdf3b7830362:

- [dailyprice](https://github.com/koreainvestment/open-trading-api/blob/3a9be59a3ed8745720dc3aa9d584bdf3b7830362/examples_llm/overseas_stock/dailyprice/dailyprice.py), lines 22/86/90–97: endpoint, HHDFS76240000 and MODP propagation.
- [check sample](https://github.com/koreainvestment/open-trading-api/blob/3a9be59a3ed8745720dc3aa9d584bdf3b7830362/examples_llm/overseas_stock/dailyprice/chk_dailyprice.py), line 52: MODP 0 unadjusted, 1 adjusted; line 22: zdiv decimal places.

The check sample rounds some columns for printed display (103/117); that is
client presentation code, not a server historical rounding specification.
Neither reviewed sample defines the server dividend/split formula, internal
precision, rounding sequence or tie rule. zdiv does not establish those rules.

Correction to #199's description: the retained API detail response is NOT usable
specification JSON. HTTP 200 carries only an 86-byte HTML meta refresh to
truefriend's error2.jsp. The property endpoint has the identical body/hash.
Both were inspected; neither contains MODP. Current web retrieval of these
portal endpoints also failed. The pinned official GitHub sample supports the
0/1 meaning; the error pages do not. document_content_check and regression tests
ensure HTTP success/hash retention cannot be mistaken for algorithm evidence.

Inventoried the configured external snapshot (sources, sse_history,
corporate_action_evidence): SSE responses and normalized KIS CSV are retained,
but no original historical same-snapshot MODP=0/1 request/response pairs or KIS
zdiv metadata were found there. Current kis_provider.py requests MODP=1 and
normalizes numeric OHLCV; it does not retain original responses/zdiv. Current
code cannot prove past-row request provenance. This negative finding is scoped
to the inspected snapshot, not all possible archives elsewhere. No new KIS calls.

Official sample bodies and portal responses/receipts remain only in external
CHINA_PRIVATE_SNAPSHOT_DIR/corporate_action_evidence. Public metadata in
research/china_kis_document_checks.json contains URLs, hashes and retrieval
metadata. Hashes identify bytes; they do not certify the server algorithm.

## 512480 residuals
Reused the #199 formulas and both rounding hypotheses. Added only affected-field
counts, without exporting or changing prices:

| Check | Count |
|---|---:|
| Affected OHLC | 888 |
| HALF_UP exact | 696 |
| HALF_EVEN exact | 685 |
| Exact theoretical half-tick ties | 428 |
| Lower mill outcomes at ties | 192 |
| Upper mill outcomes at ties | 236 |
| Off .001 grid | 0 |
| Greater than .0005 residual | 0 |

All 192 HALF_UP differences are lower outcomes at ties; the other 460 non-tie
fields match. These Decimal diagnostics use retained parsed raw values and the
disclosed 0.5 factor; they do not prove the provider uses decimal arithmetic.
Mixed tie directions have multiple possible causes. No floating-point rule was
fitted or promoted. Tests cover both directions, off-grid and out-of-tolerance
values. 515220/512400 remain 392/392 and 1084/1084 exact hypothesis matches.

## Negative coverage for the other nine
notice_coverage replays retained fund05 queries, validating body hash against
receipt and public provenance, official HTTPS host/path, query symbol/date/
category/page, totals, per-notice symbol/date, unique paths and nonempty titles.
Incomplete pages or an interval shorter than the price history cannot support
a bounded negative. Hash/identity/date/duplicate/service errors fail validation.

The retained queries cover 2025-07-30–2026-11-03, spanning the KIS overlap ending
2026-10-27. All 12 totals equal returned counts: 76 notices. Nine raw-matching
symbols 512800/512880/512600/515650/512010/512720/512980/512200/516160 return 55
notices and zero distribution/dividend/split/conversion/merger title matches.
The other three return five matching titles, consistent with prior reviewed
events; a notice count is not an event count.

This is bounded negative evidence in ONE category, not a complete no-action
inventory. Other SSE categories, issuer archives, annual/interim reports,
corrections and out-of-interval events remain unverified. No broader coverage or
new notice collection is claimed. Tests cover truncated/empty-but-incomplete
pages, interval gaps and conversion/merger titles. Even a complete filtered
negative always leaves event_inventory_complete and adjustment verification false.

## Gates and reproduction
The diagnostic evidence_gate separates the existing raw reconciliation/35-week/
prior-comparison prerequisite from adjustment evidence. No caller verification
flag can clear the missing server algorithm/rounding, historical paired response,
whole-interval action inventory or previous Stage/benchmark policy requirements.
Tests use actual XSHG synthetic histories at 34/35/63 weeks and retain 512400's
explicit review block. This gate reports deficiencies; it authorizes no outputs.

Raw length only: 10/12 pass 35 weeks (nine 63; 515220 42). 512480 remains 16,
512400 6. Adjustment gate 0/12. Stage possible 0 / withheld 12. Stage1–4,
26-week returns, new Stage2 entries and operational eligibility remain withheld.

```powershell
$env:PYTHONUTF8 = '1'
$env:CHINA_PRIVATE_SNAPSHOT_DIR = '<external retained snapshot>'
python china_adjustment_evidence.py --as-of-date 2026-11-03
python china_corporate_action_audit.py --as-of-date 2026-11-03
python -m unittest tests.test_china_adjustment_evidence -q
python -m pytest -q tests/test_china_adjustment_evidence.py tests/test_china_corporate_action_audit.py tests/test_china_sse_history_collect.py tests/test_china_history_audit.py tests/test_china_readiness_validation.py tests/test_china_stage_guard.py
```

Offline replay passed with zero network calls; focused 54 passed / 48 subtests;
new unittest 9 passed; py_compile passed. Full Windows and exact remote-head CI
results are recorded in CODEX_PROGRESS.md / Draft PR after completion.

Next: official server formula/precision/tie policy and historical paired original
requests/responses with zdiv, then issuer/report/all-category coverage for nine
symbols, then previous Stage/benchmark policy. Never reconstruct old receipts
from current code or rewrite prices to fit a hypothesis. No protected-branch
edits, merge, deployment, data activation, workflow/schedule changes or manual runs.
