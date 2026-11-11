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
## Follow-up: security-type and KIS identity signal triage (2026-11-11)

The audit now adds **independent, review-only signals** without changing the original 408 ticker-gap definition or the source/receipt validation. Source names containing notes/debentures/bonds/ZONES, preferred securities, warrants/rights, funds/trusts, ADR/ADS/depositary receipts, units, or share classes receive distinct signals. This closes misleading 'no obvious warning' cases such as Comcast ZONES, long-dated notes and tangible equity units. A name lacking these terms is **not** classified as an ordinary common share.

The read-only KIS master join also provides saved `master_dr_flag`, master security-type codes and ticker collision warnings. DR flag `Y` is a **review requirement**, not independently confirmed ADR ratio, while `N` and security-type code `2` do not certify common shares. Multiple venue rows are retained and identified; no guess at the listing venue is made. The Nasdaq export itself does not include an Exchange column.

New aggregations: `gap_security_name_signals`, `gap_identity_review_flags`. Per-row `security_name_signal`, `kis_master_dr_flags`, `kis_master_security_type_codes_unverified` and `identity_review_flags` stay local and marked `research_only_not_approved`. No candidate intake or operational universe update is introduced. Synthetic regression tests cover each risk type, ADR code, ambiguous KIS master ticker, missing KIS ticker and unchanged source data.

**Next:** inspect apparent ordinary-share cases against authenticated KIS venue/issuer evidence and any required ADR ratios; do not automatically treat the new unflagged subgroup as an approval-ready universe.
## Follow-up: KIS issuer-name corroboration and SEC listing evidence (2026-11-11)

Using the same approved Nasdaq snapshot and existing KIS unranked master, the review-only audit now independently classifies all 408 gaps by source-name security type, **KIS English master-name risk**, issuer-name token coherence, KIS type/DR/venue ambiguity and Nasdaq issuer country. This cannot approve a candidate, establish public redistribution rights, verify 1B security-level cap, verify KIS prices or assign an operational sector.

Independent read-only cross-check of 408 gaps against the revised cohort rules (full live CLI replay not claimed):

| Review cohort | Ticker count |
|---|---:|
| KIS issuer-name coherent / primary evidence still required (P1) | 16 |
| Common-share class name needs review (P2) | 12 |
| Issuer name mismatch/missing (P2) | 4 |
| Common-share label missing (P2) | 1 |
| Depositary/ADR ratio review (P3) | 163 |
| Non-common or structured security risk (P3) | 153 |
| Foreign issuer/listing structure review (P3) | 5 |
| KIS master ticker not present (P4) | 54 |
| **Total** | **408** |

The earlier 36 source-name-quiet KIS DR=N tickers shrink when KIS long names and additional source labels are inspected. A KIS DR=N flag is *not* evidence that Rio Tinto/FEMSA/etc. are not ADRs. KIS master-name variants such as SPON ADR, DEP SHS, PRF, STRATS are treated as risk signals. Positive name coherence is only a queue priority. For example, very recent AGLT needs adequate trading history and corporate-action/issuer continuity review even with SEC evidence.

**Official source evidence added:** `docs/evidence/us-nasdaq-issuer-listing-sec-20261111.json` contains 22 SEC filing links corroborating security class, US-listed ticker and exchange (including MRX corporate restructuring and AGLT recent listing). Only the filing class/symbol/venue is documented; the source records are **not approval tokens** and do not imply price-history readiness, correct issuer-level market cap, or KIS trade support. Unreferenced tickers remain without the required primary filing evidence.

Follow-up after safe code integration: (1) cross-check each P1 with the official evidence register, (2) investigate P2 false-negative issuer abbreviations without weakening matching globally, (3) assess 150-bar history and listing/ADR corporate actions in an offline, human-reviewed candidate workflow. Do not write the stock candidate CSV or activate instruments automatically.

**Source-country discrepancy confirmed:** CNL is incorporated in Canada although the Nasdaq CSV `Country` field says United States; SEC 6-K confirms its common shares transferred from NYSE American to Nasdaq on 2026-08-11. The screen's country column is not proof of legal domicile; issuer-country and KIS venue history need independent review even for P1 issuer-name coherent rows. SEC source: https://www.sec.gov/Archives/edgar/data/1953575/000121390026087988/ea030148801ex99-1.htm .

## Follow-up: SEC reference-to-P1 linkage (2026-11-11)

The offline gap audit now reads the already committed SEC reference registry and reports whether each ticker has a **registered SEC filing link** and whether that link's saved venue matches the unique saved KIS master venue. It separately summarizes the P1 name-coherent subgroup and all 408 high-cap gaps.

- The CLI uses `--sec-registry` (default: `docs/evidence/us-nasdaq-issuer-listing-sec-20261111.json`), and requires a reference registry that declares zero operational additions, unique symbols, valid saved US venue identifiers and `pending_review` statuses. Malformed reference inventories fail closed.
- The status `sec_reference_same_saved_kis_venue_review_only` confirms **only that two stored strings agree**. It is not proof that the linked filing was independently fetched in the current run, that its terms match the exact trading instrument today, or that KIS price/volume/market-cap evidence and 30-week Stage readiness exist.
- A missing link, venue mismatch or ambiguous KIS master is made explicit. Synthetic tests cover the above states, malformed registry rejection, zero network calls and unchanged input frames.
- The generated output remains aggregate-only unless the user explicitly supplies `--preview N`; it never writes a review queue, changes operational universe data or calls SEC/KIS automatically.

Next: manually investigate P1 rows with nonmatching or absent SEC references and KIS venue/issuer discrepancy; then assess saved price history, appropriate cap basis and sector benchmarks before considering a separate review-only intake proposal.

## Follow-up: P1 saved-price inventory after merged #248

Fresh integration base `913eb18381a059c87147a03e4f8357dfb1edbe37` already includes
#242 and #245–#248; its postmerge Python CI succeeded. The 16 P1 rows already
have stored SEC links agreeing with saved KIS venues. Repeating that identity
linkage does not resolve their next blocker: price-history availability.

`nasdaq_gap_price_readiness.py` reuses the receipt-bound gap audit, the existing
`OfflineStageReplay` quality checks/weekly engine and the shared US completed-bar
cutoff. It inventories **only P1**, separating absent, invalid, short, stale and
threshold-meeting stored histories. It rejects duplicate, future, malformed,
weekend and invalid OHLCV rows, excludes unclosed US sessions/current weekly
bars, and flags close moves over 50% for concrete anomaly review. KIS prices are
trusted under the existing provider policy; external exchange matching and
adjustment-formula reconstruction are not introduced as prerequisites.

Local usage with already authorized inputs (timezone-aware clock required):

```text
python nasdaq_gap_price_readiness.py --nasdaq-csv /local/latest.csv --receipt /local/latest.json --evaluated-at 2026-11-11T15:30:00+09:00
```

Default stdout contains **aggregates and input hashes only**. `--preview N`
explicitly exposes at most 100 unapproved P1 rows in the local console. No output
file, request, workflow dispatch, candidate intake, CSV write or Stage label is
produced. Price file hashes identify the exact bytes inspected. The optional
per-row diagnostic suggests manual inspection or a bounded KIS-history request
review; it neither constructs an executable collection queue nor bypasses the
2,500-candidate intake limit.

**Read-only real snapshot replay:** at `2026-11-11T15:30:00+09:00`, source data
branch `d09ca465bb8ac1677f596708618b89a4fd407996`, CSV hash
`77827787da2dbc1b0877b5b1e124da92c7e556e2fc0b579aa28494cd991395bc`, integration
data at `913eb183`: **P1 16 / saved prices missing 16 / live KIS calls 0 /
operational additions 0**. Neither `daily_prices.csv` nor
`candidate_daily_prices.csv` contains any of those 16 tickers. This is absence
from these saved files, not evidence of KIS non-support, a failed live query, or
an exchange-wide history search. No real per-symbol result file is committed.

Saved prices lack venue, provider and adjustment-provenance columns. Even a
150-row/35-week/freshness pass cannot establish exact security identity, full
exchange-session continuity, security-level cap basis/date, sector/market RS or
activation readiness. Holidays and listing changes retain a continuity review
gate; the shared weekly policy is unchanged.

**Next:** prepare a separately reviewed, bounded KIS history check for the 16
missing P1 symbols with unique saved venues, retaining recent-listing/venue
transition notes; inspect cap basis/date and benchmark mapping before any
candidate intake. Actual CSV updates and operational activation remain outside
this change. Synthetic tests cover the CLI receipt/cohort join, hashes,
aggregate-only output, immutable inputs, zero network, invalid bars and
unclosed-session/weekly exclusion.
