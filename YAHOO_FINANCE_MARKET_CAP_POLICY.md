# Yahoo Finance market-cap supplement (MVP policy)

## Purpose
Yahoo Finance is a secondary market-cap source only. KIS remains the primary discovery/provider path. Yahoo must not replace KIS price history, daily refreshes, stage calculations, sector benchmarks, or instrument identity checks.

## Initial scope
- Query US-listed common-stock candidates only (NAS/NYS/AMS).
- Do not query ADR candidates in this first pass because ADR share-class and depositary-ratio reconciliation remains a separate review gate.
- Do not query ETFs or commodity/market proxies for market-cap filtering.
- Do not convert non-USD quote currencies in the initial implementation. A non-USD market cap is recorded as a native-currency observation but its USD field remains blank.
- Store observations in a separate report; do not overwrite the candidate universe or mark a candidate verified.
- Record source URL, fetch time, quote currency, Yahoo's market timestamp when supplied, and request errors.

## Decision rules
- market_cap_usd_b_secondary is populated only when Yahoo reports a positive market cap and quote currency is USD.
- Every Yahoo observation remains not_verified; a secondary value alone does not prove identity, share-class convention, effective-date alignment, or the $1B threshold.
- Missing, stale, failed, or non-USD observations remain pending. They must not cause automatic exclusion or activation.
- The $1B rule continues to exclude only stocks whose market cap has been verified below $1B. ETFs/proxies remain exempt.

## Operational note
Yahoo Finance data endpoints are not a substitute for a licensed, guaranteed API. Use bounded request volume and treat missing fields, rate limits, schema changes, and outages as normal outcomes. Do not add automatic retries that can amplify rate limiting. The script imports yfinance lazily so non-Yahoo workflows remain usable if that optional source is unavailable.
