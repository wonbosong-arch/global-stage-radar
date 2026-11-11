# US Nasdaq high-cap gap: read-only intake audit (2026-11-11)

**Status:** exploratory coverage reconciliation; **zero operational additions**. Not an approval to activate, redistribute a second derived issuer file, or trigger new KIS queries.

## Exact inputs used for the first review

- Official Nasdaq Screener CSV saved by explicit user publication consent in branch `data/nasdaq-manual-screener`, commit `d09ca465bb8ac1677f596708618b89a4fd407996`. The hash-bound `latest.json` records download date 2026-11-09 and CSV SHA-256 `77827787da2dbc1b0877b5b1e124da92c7e556e2fc0b579aa28494cd991395bc`.
- Integration snapshot `data-validation-mvp` at `756c21420206abc6afc8aed66f15f894870c64a7` for `unranked_us_stock_master.csv`, `candidate_identity_evidence_coverage.csv`, and `monitoring_universe.csv`. The identity report is an existing derived view of the candidate registry, not a new KIS fetch.
- The source file has **no Exchange column**; overlap is ticker-only, not evidence of identical exchange, issuer, class, ADS ratio, market-cap basis, or KIS orderability.

## Observed coverage at the snapshot

| Measure | Count |
|---|---:|
| Nasdaq CSV rows / unique tickers | 7,062 / 7,062 |
| Nasdaq-reported market cap >= USD 1 billion | 2,673 |
| Above threshold and in existing US candidate identity inventory | 2,265 |
| **Above threshold but not in existing US candidate ticker inventory** | **408** |
| Of these 408, ticker in unranked KIS US master | 354 |
| Of these 408, ticker absent from unranked KIS US master | 54 |
| Existing total candidate identity rows (US + KRX) | 2,367 |
| Existing US candidate identity rows | 2,335 |

All 354 master-matched missing rows are marked `unranked_master_symbol_cap_unknown` in the retained KIS master. That **does not validate** their market cap or ordinary-common-share eligibility. Examples include issuer-associated preferred/depositary shares and foreign ADRs; the Nasdaq cap can reflect issuer size rather than the particular tradable security.

The existing review intake (`intake_large_cap_review_candidates.py`) caps candidates at **2,500** total, so no bulk import of the 408 without independent classification, available room, and an approved workflow is appropriate.

## Implemented audit

`nasdaq_coverage_gap_audit.py` takes an *already available local copy* of the saved CSV and its matching JSON receipt; checks the receipt hash and existing official-CSV quality gates; then compares US ticker sets with the existing candidate registry and KIS master. It separates already reviewed tickers from unregistered high-cap tickers; provides source-name risk **signals**, not eligibility verdicts.

Run in an isolated checkout with the authorized input files already available:

`python nasdaq_coverage_gap_audit.py --nasdaq-csv /local/latest.csv --receipt /local/latest.json`

By default only **aggregate JSON** is printed. Optional `--preview N` prints up to 100 explicitly unapproved rows in the user's own local console. No API calls, output files, approval status updates, operational changes, scheduled uploads, or new CSV distribution are made.

## Next bounded decision

Investigate the 408 ticker gaps by instrument type (exclude clearly non-common securities, separately review ADR/ADS share ratios, corroborate KIS listing venue and issuer, confirm USD market cap basis) before considering *review-only* candidate intake. Do not infer that 408 valid companies were omitted, do not override the 2,500-candidate limit, and do not edit `data/monitoring_universe.csv` without explicit approval.
