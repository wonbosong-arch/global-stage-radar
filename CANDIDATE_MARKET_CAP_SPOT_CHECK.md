# Candidate market-cap arithmetic spot-check (2026-10-24)

This is a limited arithmetic spot-check, not a verification or approval of candidate market caps. Source pages show October 23, 2026 closing prices and rounded shares-outstanding figures. Because shares are rounded on the overview pages, calculations are approximate. All candidate rows remain `market_cap_status=not_verified` and `activation_status=pending_review`.

Formula: closing price × reported shares outstanding (millions) ÷ 1,000 = implied USD billions.

| Symbol | Close (USD) | Shares out (million) | Implied cap ($B) | Source-reported cap ($B) | Approx. difference | Status |
|---|---:|---:|---:|---:|---:|---|
| ORCL | 126.16 | 3,030 | 382.26 | 382.45 | -0.05% | Arithmetic broadly consistent; shares rounded |
| AMGN | 439.26 | 540.63 | 237.48 | 237.48 | <0.01% | Arithmetic broadly consistent |
| COP | 150.80 | 1,200 | 180.96 | 181.16 | -0.11% | Arithmetic broadly consistent; shares rounded |
| AEP | 129.69 | 544.40 | 70.59 | 70.60 | -0.01% | Arithmetic broadly consistent |

## Source links

- ORCL overview (price, shares, market cap): https://stockanalysis.com/stocks/orcl/
- ORCL market-cap history: https://stockanalysis.com/stocks/orcl/market-cap/
- AMGN overview (price, shares, market cap): https://stockanalysis.com/stocks/amgn/
- COP overview (price, shares, market cap): https://stockanalysis.com/stocks/cop/
- AEP overview (price, shares, market cap): https://stockanalysis.com/stocks/aep/

## Interpretation and next steps

- These four checks support only that the source-reported values are arithmetically plausible using the displayed, rounded share counts.
- They do not independently establish exact shares outstanding, source methodology, diluted/basic share basis, corporate-action treatment, or eligibility under a market-cap threshold.
- Do not change `market_cap_status` to `verified` on this basis.
- Next, extend the same-date price/share cross-check to the remaining 27 candidates. TSM and BABA need explicit ADS-versus-underlying ordinary share conventions; ETN/LIN issuer-country review remains separate.


## Second batch: CRM and ADBE (2026-10-24)

| Symbol | Close (USD) | Shares out (million) | Implied cap ($B) | Source-reported cap ($B) | Approx. difference | Status |
|---|---:|---:|---:|---:|---:|---|
| CRM | 248.57 | 823.00 | 204.57 | 204.57 | <0.01% | Arithmetic broadly consistent; shares rounded |
| ADBE | 263.82 | 389.20 | 102.70 | 102.68 | +0.02% | Arithmetic broadly consistent; shares rounded |

Sources:
- CRM overview and shares: https://stockanalysis.com/stocks/crm/ and https://stockanalysis.com/stocks/crm/statistics/
- CRM market-cap history: https://stockanalysis.com/stocks/crm/market-cap/
- ADBE price and shares: https://stockanalysis.com/stocks/adbe/statistics/
- ADBE market-cap history: https://stockanalysis.com/stocks/adbe/market-cap/

A separate market-cap provider reports ADBE at $103.15B for the same date, versus Stock Analysis at $102.68B. This reinforces that provider definitions/share-count timing can differ; do not treat any one provider's value as verified without defining the chosen source convention.
