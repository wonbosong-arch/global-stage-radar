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
- Market cap is a minimum-size screen, not a full accounting verification exercise.
- Use a reputable source's positive USD market-cap estimate for the $1B size screen; do not require issuer share-count arithmetic for every stock.
- A source-backed secondary estimate at or above $1B can satisfy the size-screen gate while the candidate's formal `market_cap_status` remains `not_verified`. This is not a claim that the value is officially verified.
- A source-backed estimate below $1B fails the minimum-size screen. Near-threshold or conflicting observations are flagged for review rather than automatically excluded.
- Missing, stale, failed, or non-USD observations stay pending; missing data alone must never cause automatic exclusion.
- If a company is obviously well above the threshold but one field is missing, use an independent reputable source as a screening estimate instead of requiring manual share-count reconciliation.
- ADR share-class and depositary-ratio research is reserved for cases where it could materially affect the $1B decision or instrument identity.
- ETFs/proxies are exempt from the stock market-cap filter.
- The screening result must not set `market_cap_status=verified`, alter identity/provider evidence, or automatically activate a candidate.

## Operational note
Yahoo Finance data endpoints are not a substitute for a licensed, guaranteed API. Use bounded request volume and treat missing fields, rate limits, schema changes, and outages as normal outcomes. Do not add automatic retries that can amplify rate limiting. The script imports yfinance lazily so non-Yahoo workflows remain usable if that optional source is unavailable.
