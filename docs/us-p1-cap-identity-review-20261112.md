# P1 USD 1B / class / listing review — 2026-11-12 KST

## Verified starting state

Latest integration inspected: `00617551cef24211d2d213915eb07c54df714163`.
PRs #252/#253 are merged. Their postmerge Python runs succeeded, including
[#253 run 42983591750](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/42983591750)
at exact merge SHA `eb471d2d26fa46f4fd7539bce4bc4e4587af9ff1`.
Subsequent integration commits are scheduled data/report refreshes; open PRs
include unrelated EXAONE/Japan/China/UI research. Those branches and another
worker's dirty China checkout were left alone. New development uses a fresh,
independent branch targeting `data-validation-mvp`.

## Actual live evidence and the missing ticker mapping

The complete logs of jobs `130394201569` and `130399468400` were inspected:

| Live KIS run | Cohort slots | Attempted | History pass | Short | Anomaly |
| --- | --- | ---: | ---: | ---: | ---: |
| [42981962117](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/42981962117) | 0–1 | 2 | 1 | 1 | 0 |
| [42983591682](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/42983591682) | 2–15 | 14 | 12 | 1 | 1 |
| Total | 0–15 | 16 | 13 | 2 | 1 |

Both have the same source/candidate/master/price hashes, all 16 eligible,
no systemic stop and no saved prices, intake or operating additions. The first
version predates `selected_start_index`; its workflow and default CLI establish
offset zero. The checked-in evidence JSON preserves only the already published
aggregate JSON and run links, excluding raw logs, secrets, prices and ticker rows.

**Neither run used `--preview`. No per-ticker live result was retained in the
logs, and neither workflow uploaded an artifact. The identities of the 13
passes, two short histories and one anomaly cannot be recovered from these
aggregates.** A recent IPO, a class note or a plausible price pattern cannot be
used to assign any ticker to those outcomes. `identified_history_pass_tickers=0`
means unknown identities, not zero live passes.

## Reusing existing cap and SEC evidence

The approved source is still `d09ca465bb8ac1677f596708618b89a4fd407996`,
CSV SHA256 `77827787da2dbc1b0877b5b1e124da92c7e556e2fc0b579aa28494cd991395bc`.
The historical and current gap audits independently reproduce the same 16 P1
members. Since the 13 cannot be identified, review covers **all 16 P1 metadata
rows**, without presenting them as the passing subset.

Read-only replay at the fresh base, using `yahoo_unranked_master_market_caps.csv`
and the saved SEC registry:

| Evidence | Result | Interpretation |
| --- | --- | --- |
| Saved Yahoo cap observation | 14 below USD 1B; 2 missing/unusable | Secondary observations only; no current exclusion or eligibility decision |
| Source-provided cap effective date | Missing for all 16 | `fetched_at_utc` and quote timestamps cannot substitute |
| Saved SEC security class | 14 common stock; 1 common shares; 1 Class A common stock | Filing-level reference corroboration; no class-specific cap verification |
| Saved SEC/KIS venue strings | 16 agree | Stored-string agreement only; no proof of exact price-series identity |
| SEC records retaining review notes | 6 | Preserve individual notes for the next primary-source review |
| Verified security-level USD 1B cap | 0 | No candidate intake or operation justified |

Yahoo observations were fetched on 2026-10-26/27 and 2026-11-05. These are
fetch dates, **not cap effective dates**. Nasdaq's later issuer-cap screen and
Yahoo's older observations lack aligned dates and security-class bases; do not
calculate a same-date discrepancy or call either source definitively wrong.
Yahoo `EQUITY` is insufficient to establish a common-share class or whether a
market cap aggregates multiple classes. The existing cap reconciliation module
uses the same explicit `source_provided_market_cap_date` rule.

Retained SEC notes distinguish AGLT's recent trading start; CNL's Canadian
incorporation and NYSE American→Nasdaq transfer; RHLD's Nasdaq→NYSE transfer;
LGIH/SBSI's Texas listing references; and WEST listed common shares versus its
issuer's preferred shares. MSM's Class A label is retained explicitly. These
are **previously stored SEC findings**, not newly fetched filings, and none
identifies the live-history anomaly. Full source links, filing dates and notes
remain in the existing SEC registry and optional local report.

Current input hashes are recorded separately from historical probe hashes.
An exact-byte mismatch sets `current_metadata_hashes_match_probe=false`; this
can include Windows checkout line-ending differences as well as refreshed
master data. It must not silently bind historical live counts to current rows.
Even a matching hash would not recover the missing ticker/result mapping.

## Minimal implementation and reproduction

`nasdaq_p1_cap_identity_review.py` reuses `audit_gap`, its receipt validation,
P1 classification and SEC-reference validation. It joins only saved Yahoo
observations, retains exact class/filing/venue notes and uses Decimal for the
USD-billion boundary. Duplicate Yahoo matches fail instead of choosing one.
Aggregate replay rejects overlapping, incomplete, stopped or hash-incompatible
batches. Every ticker's live status remains `unknown_aggregate_only`.

```text
python nasdaq_p1_cap_identity_review.py --nasdaq-csv /local/latest.csv --receipt /local/latest.json
```

Default stdout is aggregate-only. `--preview 16` is for local review only;
do not commit its real ticker-level output. No network, output file, workflow
dispatch, price save, real CSV change, Stage calculation or activation occurs.

Focused tests: 35 passed, 82 subtests passed (new cap/aggregate/privacy tests
plus the existing P1 probe, price inventory and gap-audit regressions). Final
PR CI and postmerge CI are recorded on the PR after checking their actual runs.
Local replay is evidence inspection, not a successful operational expansion.

## Next unresolved work

1. Obtain dated, security/class-specific USD cap evidence; current saved
   observations establish no USD 1B pass. Reuse SEC filings and existing
   reconciliation logic rather than substituting dates or issuer totals.
2. If a dated eligible candidate emerges, a bounded private read-only probe
   must retain a ticker/venue/result mapping and input hashes. The old run
   cannot be reconstructed retrospectively. Do not publish per-symbol KIS
   responses or repeat a whole batch merely to guess a mapping.
3. Review concrete listing transitions/class distinctions, and investigate
   the actual anomaly once its identity is observed. KIS provider trust policy
   remains unchanged; no new independent price-reconciliation requirement.
4. Real CSV intake and operational activation require a separate explicit
   approval. `main`, deployment settings and paid services remain untouched.

This completes the available saved-evidence review and its reproducible code.
It does **not** complete the requested 13-symbol eligibility clearance: their
individual history mapping and dated security-level caps remain unresolved.
