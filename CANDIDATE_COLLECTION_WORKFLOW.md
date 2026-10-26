# Candidate stock discovery workflow

## Purpose

The candidate discovery job periodically requests KIS market-cap rankings and appends newly discovered instruments to data/stock_universe_candidates.csv. It is a discovery queue, not a recommendation engine and not an approval process.

## Schedule

- 07:30 KST Tuesday-Saturday: KIS ranking discovery, before the daily price snapshot.
- 08:00 KST Tuesday-Saturday: active-universe daily closing-price snapshot.
- 08:05 KST Tuesday-Saturday: pending-candidate price-history review.
- 09:00 KST Monday-Saturday: offline candidate coverage and review reports.
- Sunday KST is intentionally skipped for price refreshes and discovery.

GitHub scheduled workflows run only from the repository's default branch. The new workflow will not run on schedule while it exists only on the GPT migration branch. Do not change the repository default branch or touch the unrelated main app as a workaround; the final workflow/deployment branch must be decided deliberately.

## Discovery and filtering rules

- Uses KIS market-cap rankings for NAS, NYS, AMS, and KRX; it also downloads the KIS US security master and KRX security masters for basic instrument classification.
- A verified market cap below USD 1 billion excludes a stock from this candidate queue.
- Missing or unverified market cap does not count as a pass or a failure: the candidate stays pending review.
- ETFs, index instruments, warrants, and likely non-common securities are not added to the stock candidate queue. ETFs used as market/sector proxies remain governed by the separate monitoring universe and are not subject to the stock market-cap filter.
- US ranking market cap is only used for discovery when the ranking value reconciles with price times shares outstanding. ADRs remain flagged for identity/depositary-ratio review.
- KRX ranking market caps are retained as unknown in USD unless the optional USD_KRW_RATE repository variable is set to a positive, current KRW-per-USD rate. Without it, Korean stock candidates remain pending on USD market-cap review.
- The ranking endpoints are bounded (up to 50 pages per US exchange and 10 KRX pages), so this is not proof that every listed security was enumerated.

## Safety controls

- Existing candidate rows are never overwritten by discovery. Human-entered identity, market-cap, provider, sector, and activation review fields remain intact.
- Active-universe symbols are not re-added to the pending queue.
- New rows have activation_status=pending_review, provider_status=not_checked, and market_cap_status=not_verified.
- The script never writes to data/monitoring_universe.csv; candidate activation remains a separate human-reviewed change.
- data/candidate_collection_status.json records the latest attempt, ranking page counts, number of additions, and any run-level failure.
- KIS requests and live API responses are not validated by unit tests; no live collection has been run as part of this code change.

## Configuration

The workflow uses repository secrets KIS_APP_KEY and KIS_APP_SECRET in the existing live KIS environment. USD_KRW_RATE is optional; if absent, KRX market-cap conversion is deliberately left unresolved rather than guessing an FX rate.
