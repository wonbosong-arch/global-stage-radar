# Pending candidate provider-mapping review guide

This guide is a manual evidence checklist for the pending candidate queue. It does not verify KIS support, establish listing identity, or authorize activation.

## Current interpretation rules

- A non-empty price response (even hundreds of rows) proves only that the request returned price data for the requested symbol/exchange parameters.
- Matching requested and response exchange fields is useful diagnostic evidence, but is not proof that the symbol maps to the intended legal instrument.
- `price_response_observed_formal_support_unverified` means exactly that: price data was observed; formal provider support remains unverified.
- `no_price_response_observed` means no usable response was captured. It does not by itself prove that KIS does not support the instrument.
- A response error should be inspected before retrying. Preserve the exact error and avoid repeatedly calling KIS in quick succession because of rate limits.
- Do not change `provider_status` to `verified` based only on snapshot rows or an exchange-code match.
- Keep every candidate at `keep_pending_review` until listing identity, country-index benchmark mapping/freshness, provider mapping, and final review are independently resolved.

## Per-symbol review steps

1. Read `data/candidate_review_queue.csv` and locate the symbol. Record `requested_exchange`, `response_exchange`, `exchange_fallback_used`, `response_rows`, `latest_response_date`, and `response_error`.
2. Check the official exchange instrument directory or the issuer's investor-relations listing page for the exact ticker, exchange, share class, and instrument type. For ADR/ADS, record the official depositary ratio and underlying share class.
3. Compare the official listing identity with the intended candidate row. If the ticker is reused across markets or the legal issuer country differs from the economic market, document both rather than silently substituting one for the other.
4. Check KIS's official product/instrument mapping or an explicit KIS response/documentation that identifies the same instrument. Do not infer formal support from successful price retrieval alone.
5. Verify the country representative index used by Stage RS is active and has current price history. Sector benchmarks are informational only while sector RS is disabled; the US country representative index is S&P 500 (SPY).
6. Update evidence fields only when supported by the cited source, then regenerate the review reports. Never activate a candidate as a side effect of report generation.

## Required evidence to close provider mapping

- Exact KIS instrument/symbol mapping or official support evidence.
- Requested exchange and response exchange reconciled to the intended listing.
- Any fallback behavior explained and documented.
- Latest response date and error state recorded.
- Separate identity and benchmark gates passed; market-cap reconciliation remains a coarse optional screen, not proof of identity.

## Current queue context

The latest generated summary at 2026-10-25 11:04:50 UTC shows 31 candidates held for manual review: 27 at provider mapping and 4 at issuer-country/ADR classification. These are queue counts, not verified support results. The latest available candidate price snapshot is dated 2026-10-23; do not run a Sunday market-data refresh.
