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


## Third batch: IBM, NOW, TMUS, MCD, TJX, SBUX (2026-10-24)

The overview pages below report the October 23, 2026 close. The displayed share counts are rounded, so implied market caps are approximate.

| Symbol | Close (USD) | Shares out (million) | Implied cap ($B) | Source-reported cap ($B) | Approx. difference | Status |
|---|---:|---:|---:|---:|---:|---|
| IBM | 253.56 | 942.13 | 238.88 | 238.89 | -0.00% | Arithmetic broadly consistent |
| NOW | 158.96 | 1,030.00 | 163.73 | 164.34 | -0.37% | Small difference; rounded share count/source timing may explain |
| TMUS | 146.54 | 1,070.00 | 156.80 | 157.19 | -0.25% | Small difference; rounded share count/source timing may explain |
| MCD | 248.46 | 707.64 | 175.83 | 175.82 | +0.01% | Arithmetic broadly consistent |
| TJX | 145.06 | 1,100.00 | 159.57 | 159.56 | +0.01% | Arithmetic broadly consistent; shares rounded |
| SBUX | 100.80 | 1,140.00 | 114.91 | 114.89 | +0.02% | Arithmetic broadly consistent; shares rounded |

Sources (overview and shares data):
- IBM: https://stockanalysis.com/stocks/ibm/ and https://stockanalysis.com/stocks/ibm/statistics/
- NOW: https://stockanalysis.com/stocks/now/ and https://stockanalysis.com/stocks/now/statistics/
- TMUS: https://stockanalysis.com/stocks/tmus/ and https://stockanalysis.com/stocks/tmus/statistics/
- MCD: https://stockanalysis.com/stocks/mcd/ and https://stockanalysis.com/stocks/mcd/statistics/
- TJX: https://stockanalysis.com/stocks/tjx/
- SBUX: https://stockanalysis.com/stocks/sbux/ and https://stockanalysis.com/stocks/sbux/statistics/

The small differences for NOW and TMUS do not by themselves imply an error: the displayed share counts are rounded to two significant digits in the overview. These checks remain arithmetic plausibility checks only, not source-methodology or eligibility verification.


## Fourth batch: PLTR, NFLX, COST, HD, PG, KO, BAC, CAT (2026-10-24)

The prices, share counts and reported caps below are the values recorded from secondary-source pages for the October 23, 2026 reference date. Share counts are displayed rounded, and the calculations are approximate.

| Symbol | Close (USD) | Shares out (million) | Implied cap ($B) | Source-reported cap ($B) | Approx. difference | Status |
|---|---:|---:|---:|---:|---:|---|
| PLTR | 184.68 | 2,560 | 472.78 | 472.80 | -0.00% | Arithmetic broadly consistent; shares rounded |
| NFLX | 116.00 | 2,330 | 270.28 | 270.40 | -0.04% | Arithmetic broadly consistent; shares rounded |
| COST | 991.00 | 448.60 | 444.56 | 444.60 | -0.01% | Arithmetic broadly consistent |
| HD | 328.10 | 972.50 | 319.09 | 319.09 | 0.00% | Arithmetic broadly consistent |
| PG | 158.80 | 2,355.00 | 374.27 | 374.00 | +0.07% | Arithmetic broadly consistent; rounded shares/source timing |
| KO | 92.10 | 4,330.00 | 398.79 | 398.89 | -0.03% | Arithmetic broadly consistent; shares rounded |
| BAC | 48.10 | 7,277.00 | 350.03 | 350.01 | +0.01% | Arithmetic broadly consistent |
| CAT | 653.00 | 483.60 | 315.79 | 315.80 | -0.00% | Arithmetic broadly consistent |

Sources (overview and statistics pages):
- PLTR: https://stockanalysis.com/stocks/pltr/ and https://stockanalysis.com/stocks/pltr/statistics/
- NFLX: https://stockanalysis.com/stocks/nflx/ and https://stockanalysis.com/stocks/nflx/statistics/
- COST: https://stockanalysis.com/stocks/cost/ and https://stockanalysis.com/stocks/cost/statistics/
- HD: https://stockanalysis.com/stocks/hd/ and https://stockanalysis.com/stocks/hd/statistics/
- PG: https://stockanalysis.com/stocks/pg/ and https://stockanalysis.com/stocks/pg/statistics/
- KO: https://stockanalysis.com/stocks/ko/ and https://stockanalysis.com/stocks/ko/statistics/
- BAC: https://stockanalysis.com/stocks/bac/ and https://stockanalysis.com/stocks/bac/statistics/
- CAT: https://stockanalysis.com/stocks/cat/ and https://stockanalysis.com/stocks/cat/statistics/

These checks only show rough arithmetic consistency between a displayed price, rounded shares outstanding and a secondary market-cap figure. They do not independently confirm share-count definitions, float versus total shares, source timing or market-cap eligibility. All eight remain unverified.
