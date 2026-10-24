# Candidate identity review queue

Updated: 2026-10-24

Purpose: turn the 31 pending candidates into an evidence-based review queue. This is a worklist, not a claim that each link or listing has been independently verified. Every candidate remains `pending_review`; do not activate from a successful price fetch alone.

## Completion rules

- Record the official source section/document and the exact fact it supports: ticker, exchange, legal issuer name, issuer domicile, instrument type, and (for ADR/ADS) depositary ratio.
- A source URL alone is not evidence that every field on the row has been checked.
- Keep market capitalization `not_verified` until share count/date/currency and price basis reconcile to an authoritative or clearly documented source.
- Keep provider support `not_checked` until the provider mapping and expected instrument are confirmed; a successful fetch is only run-scoped response evidence.
- Preserve ETF exemption from stock market-cap screening; this queue covers stock candidates only.

## A. 일반 상장 종목 식별 검토 (27개)

공식 IR/거래소 자료에서 티커, 거래소, 법인명, 발행사 소재지를 확인하고 근거 문구 또는 자료 제목을 기록. IR 링크가 있다는 사실만으로 확인 완료 처리하지 않음.

| Symbol | Issuer | Exchange | Issuer country | Official source currently recorded | Review status |
|---|---|---|---|---|---|
| ORCL | Oracle Corporation | NYS | United States | [IR/source](https://investor.oracle.com/faq/default.aspx) | review_required |
| CRM | Salesforce Inc. | NYS | United States | [IR/source](https://investor.salesforce.com/) | review_required |
| PLTR | Palantir Technologies Inc. | NAS | United States | [IR/source](https://investors.palantir.com/) | review_required |
| NFLX | Netflix Inc. | NAS | United States | [IR/source](https://ir.netflix.net/) | review_required |
| COST | Costco Wholesale Corporation | NAS | United States | [IR/source](https://investor.costco.com/stock-info/) | review_required |
| HD | Home Depot Inc. | NYS | United States | [IR/source](https://ir.homedepot.com/investor-resources/faqs) | review_required |
| PG | Procter & Gamble Company | NYS | United States | [IR/source](https://www.pginvestor.com/overview/) | review_required |
| KO | Coca-Cola Company | NYS | United States | [IR/source](https://investors.coca-colacompany.com/shareowners/faqs) | review_required |
| BAC | Bank of America Corporation | NYS | United States | [IR/source](https://investor.bankofamerica.com/) | review_required |
| CAT | Caterpillar Inc. | NYS | United States | [IR/source](https://investors.caterpillar.com/stock-info/default.aspx) | review_required |
| ADBE | Adobe Inc. | NAS | United States | [IR/source](https://www.adobe.com/investor-relations.html) | review_required |
| CSCO | Cisco Systems Inc. | NAS | United States | [IR/source](https://investor.cisco.com/overview/) | review_required |
| IBM | International Business Machines Corporation | NYS | United States | [IR/source](https://www.ibm.com/investor/) | review_required |
| NOW | ServiceNow Inc. | NYS | United States | [IR/source](https://investor.servicenow.com/stock-info/default.aspx) | review_required |
| ANET | Arista Networks Inc. | NYS | United States | [IR/source](https://investors.arista.com/Home/default.aspx) | review_required |
| TMUS | T-Mobile US Inc. | NAS | United States | [IR/source](https://investor.t-mobile.com/resources/investor-faqs/default.aspx) | review_required |
| DIS | Walt Disney Company | NYS | United States | [IR/source](https://investors.thewaltdisneycompany.com/resources/investor-faqs/default.aspx) | review_required |
| SBUX | Starbucks Corporation | NAS | United States | [IR/source](https://investor.starbucks.com/ir-home/default.aspx) | review_required |
| MCD | McDonald's Corporation | NYS | United States | [IR/source](https://corporate.mcdonalds.com/corpmcd/investors.html) | review_required |
| TJX | TJX Companies Inc. | NYS | United States | [IR/source](https://investor.tjx.com/) | review_required |
| AMGN | Amgen Inc. | NAS | United States | [IR/source](https://investors.amgen.com/) | review_required |
| CVX | Chevron Corporation | NYS | United States | [IR/source](https://www.chevron.com/investors) | review_required |
| COP | ConocoPhillips | NYS | United States | [IR/source](https://ir.conocophillips.com/) | review_required |
| DE | Deere & Company | NYS | United States | [IR/source](https://investor.deere.com/) | review_required |
| WELL | Welltower Inc. | NYS | United States | [IR/source](https://welltower.com/investors/) | review_required |
| CEG | Constellation Energy Corporation | NAS | United States | [IR/source](https://investor.constellationenergy.com/) | review_required |
| AEP | American Electric Power Company Inc. | NAS | United States | [IR/source](https://www.aep.com/investors/) | review_required |

## B. ADR/ADS 및 예탁비율 검토 (2개)

ADS가 대표하는 보통주 수, 미국 상장 티커/거래소, 시가총액 계산의 주식 수 기준을 별도로 확인. ADS 가격과 보통주 수를 혼합하지 않음.

| Symbol | Issuer | Exchange | Issuer country | Official source currently recorded | Review status |
|---|---|---|---|---|---|
| TSM | Taiwan Semiconductor Manufacturing ADR | NYS | Taiwan | [IR/source](https://investor.tsmc.com/english/faq) | issuer_proxy_review_required |
| BABA | Alibaba Group Holding ADR | NYS | China | [IR/source](https://www.alibabagroup.com/en-US/faqs-investor-information) | issuer_proxy_review_required |

## C. 발행사 소재지와 거래시장 구분 (2개)

법적 발행사 소재지와 미국 상장 거래소를 별도 필드로 근거 확인. 소재지 분류와 거래시장 벤치마크를 혼동하지 않음.

| Symbol | Issuer | Exchange | Issuer country | Official source currently recorded | Review status |
|---|---|---|---|---|---|
| ETN | Eaton Corporation plc | NYS | Ireland | [IR/source](https://www.eaton.com/us/en-us/company/investor-relations.html) | issuer_country_review_required |
| LIN | Linde plc | NAS | Ireland | [IR/source](https://www.linde.com/investors/stock-and-dividend-information) | issuer_country_review_required |

## Current blockers

- 27 ordinary identity reviews; 2 ADR/ADS reviews (TSM, BABA); 2 issuer-domicile reviews (ETN, LIN).
- All 31 candidates still require market-cap reconciliation and provider/instrument support review.
- No candidate is activated by this document or by the candidate coverage report.
