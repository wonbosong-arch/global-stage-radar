# Candidate market-cap reconciliation guide

Status: procedure only; this file does not certify any candidate value.

## Current candidate fields

- `market_cap_usd_b_secondary`: provisional value copied from a secondary reference source, in USD billions.
- `market_cap_source_url`: per-symbol reference page.
- `market_cap_asof`: stated reference date (currently 2026-10-23 for the candidate batch).
- `market_cap_status`: must remain `not_verified` until evidence is reconciled.

Do not use the secondary field as an eligibility decision or display it as a verified market cap. A recorded value and URL are provenance breadcrumbs, not validation.

## Reconciliation method

For each symbol, record a same-date or nearest-date reference price and the applicable shares outstanding:

`implied_market_cap_usd_b = price_usd * shares_outstanding_millions / 1000`

Compare the implied result with the secondary reported market cap. A difference is a review flag, not automatic proof of error: dates, share classes, diluted versus basic shares, treasury shares, and data vendor definitions may differ. Record the reference URLs and as-of dates for both price and shares before drawing a conclusion.

Suggested comparison bands:
- Absolute difference <= 3%: arithmetic broadly consistent; source definitions still need review.
- > 3% and <= 10%: investigate date mismatch, share-count basis, and corporate actions.
- > 10%: material mismatch; do not promote the value to verified.

These bands are triage thresholds, not accounting standards.

## ADR handling

For an ADR/ADS, determine whether the market-cap source reports the U.S. depositary receipt class or underlying ordinary shares. Verify the ordinary-shares-per-ADS ratio from issuer or depositary documentation. Do not multiply or divide the market cap by the ratio unless the source's share-count convention proves that adjustment is required. The ratio being verified does not by itself verify market cap.

## Verification gates

A candidate can only be marked market-cap verified after all of the following are documented:
1. Correct listed instrument and exchange.
2. Source value, currency, timestamp/as-of date, and source URL.
3. Share-count definition and source URL/date.
4. Price × shares arithmetic comparison and explanation for any variance.
5. FX rate and source/date if conversion is required.
6. ADR/share-class treatment where applicable.
7. A reviewer/date and a clear status change from `not_verified`.

Keep candidate activation status at `pending_review` until all separate identity, benchmark, provider, price-history, and market-cap gates have been resolved. Price rows returned for a ticker are not proof of instrument identity or confirmed KIS support.

## Automated candidate triage report (added 2026-10-24)

The scheduled candidate report workflow also runs `candidate_market_cap_reconciliation.py` and publishes `data/candidate_market_cap_reconciliation.csv`. This is deliberately a triage report, not a verification source.

- It uses the latest available candidate close and the recorded secondary market-cap snapshot to calculate an implied share count.
- Only a small subset with a dated share count explicitly recorded from issuer filings is compared against that implied count.
- The report flags large arithmetic differences for follow-up; differences can arise from mismatched effective dates, issuance/buybacks, or source conventions.
- ADR candidates are routed to share-class/ADS-ratio review rather than treated as ordinary common shares.
- No result changes `market_cap_status`, `provider_status`, or `activation_status`. All candidates remain pending until a human-reviewed, date-aligned evidence basis is recorded.

- The report now carries the per-symbol secondary source URL into each output row, alongside its as-of date and value, so a review finding can be traced back to its input rather than relying on the CSV value alone.

The current scripted reference set contains dated share-count evidence for ORCL, CRM, COST, WELL, CAT, PG, HD, BAC, NFLX, AMGN, SBUX, CSCO, CEG, CVX, TMUS, AEP, KO, ANET, ADBE, MCD, ETN, IBM, NOW, PLTR, COP, TJX, DIS, DE, and LIN. The dates span different reporting periods, so these remain independent triage inputs—not a uniform current-share-count dataset. The report retains each source URL and effective date for follow-up. Newly added filing references: CSCO as of 2026-08-27, CEG as of 2026-07-31, CVX as of 2026-06-30, and TMUS as of 2026-07-17, and AEP as of 2026-07-30, and KO as of 2026-07-27, ANET as of 2026-07-30, ADBE as of 2026-09-18, MCD as of 2026-06-30, and ETN as of 2026-06-30, IBM as of 2026-06-30, NOW as of 2026-06-30, and PLTR as of 2026-07-27, COP as of 2026-06-30, and TJX as of 2026-08-21. PLTR uses the combined Class A, Class B, and Class F share count from its filing, which is explicitly noted in the output.


Additional filing references added 2026-10-24: DIS (1,726.686902 million common shares as of 2026-07-29), DE (269.937425 million common shares as of 2026-05-03), and LIN (460.980163 million ordinary shares outstanding, net of treasury shares, as of 2026-06-30). LIN's issuer domicile and US listing context are distinct; do not infer issuer country from its trading venue. These additions are still triage inputs and do not verify secondary market-cap methodology or date alignment.


## ADS-equivalent share-count handling (2026-10-24)

- TSM: the 2026-06-30 TSMC report gives 25,932.370 million ordinary shares (capital stock, after shares awaiting retirement) and states that 1 ADS represents 5 ordinary shares. The reconciliation script records approximately 5,186.474 million ADS-equivalent shares for comparison with a US-listed ADS price, not the number of ADSs actually deposited or held by investors. Source: https://www.sec.gov/Archives/edgar/data/1046179/000104617926000541/a2026q2consolidatedreport-.htm
- BABA: a 2026-09-22 AGM filing reports 19,892.488918 million ordinary shares in issue; the issuer states each ADS represents 8 ordinary shares. The script records approximately 2,486.561 million ADS-equivalent shares. This is a derived conversion and still needs confirmation that the secondary market-cap source uses compatible share-count conventions. Source: https://www.stocktitan.net/sec-filings/BABA/6-k-alibaba-group-holding-ltd-current-report-foreign-issuer-c260c31c0da9.html; ratio: https://www.alibabagroup.com/en-US/faqs-investor-information

Both symbols remain `adr_share_class_review_required` regardless of the added count. Their market-cap status remains `not_verified`; ADS-equivalent arithmetic must not be treated as independent confirmation of vendor market capitalization.
