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


## Official-source facts checked in the latest review pass

These entries record only the fields explicitly supported by the linked issuer material. They do not automatically complete the broader identity review, validate issuer domicile, verify market capitalization, or approve KIS/provider support.

| Symbol | Fact confirmed from issuer source | Evidence | Remaining caveat |
|---|---|---|---|
| ORCL | Oracle FAQ identifies NYSE and ticker ORCL | [Oracle Investor Relations FAQ](https://investor.oracle.com/faq/default.aspx) | Legal issuer domicile and market-cap reconciliation still need separate evidence |
| KO | Coca-Cola says its stock trades on NYSE under KO | [Coca-Cola Shareowner FAQ](https://investors.coca-colacompany.com/shareowners/faqs) | Domicile, market cap and provider review remain open |
| TSM | TSMC identifies NYSE: TSM and Taiwan Stock Exchange: 2330 | [TSMC Stock Quotes](https://investor.tsmc.com/english/shareholder-services/stock-quotes) | ADS ratio is recorded separately; ADS-basis market cap and provider mapping remain open |
| BABA | Alibaba says NYSE ADS ticker BABA; each ADS represents eight ordinary shares; Hong Kong ordinary-share codes 9988/89988 | [Alibaba Investor FAQ](https://www.alibabagroup.com/en-US/faqs-investor-information) | ADS-basis market cap and provider mapping remain open |
| TMUS | T-Mobile identifies common stock ticker TMUS on Nasdaq and incorporation in Delaware | [T-Mobile Investor FAQ](https://investor.t-mobile.com/resources/investor-faqs/default.aspx) | This supports U.S. incorporation; finish remaining identity fields and cap/provider checks |
| CSCO | Cisco IR displays NASDAQ: CSCO | [Cisco Investor Relations](https://investor.cisco.com/overview/) | Separate issuer-domicile and market-cap review remains open |
| IBM | IBM FAQ says common stock is listed on NYSE and NYSE Texas under IBM | [IBM Investor FAQ](https://www.ibm.com/investor/help/general-faqs) | Dashboard's single exchange code represents the primary listing; domicile/cap/provider checks remain open |
| ANET | Arista IR displays NYSE: ANET and states it went public as ANET in 2014 | [Arista Investor Relations](https://investors.arista.com/Home/default.aspx) | Domicile, cap and provider checks remain open |
| DIS | Disney says common stock trades on NYSE under DIS | [Disney Investor FAQ](https://investors.thewaltdisneycompany.com/resources/investor-faqs/default.aspx) | Domicile, cap and provider checks remain open |
| SBUX | Starbucks IR displays NASDAQ: SBUX | [Starbucks Investor Relations](https://investor.starbucks.com/ir-home/default.aspx) | Domicile, cap and provider checks remain open |
| ETN | Eaton IR states it has been listed on NYSE for more than a century | [Eaton Investor Relations](https://www.eaton.com/us/en-us/company/investor-relations.html) | Keep Irish issuer domicile separate from U.S. listing venue; legal-domicile evidence and cap/provider checks remain open |
| LIN | Linde IR explicitly identifies Nasdaq ticker LIN | [Linde Investors](https://www.linde.com/investors) | Keep Irish issuer domicile separate from U.S. listing venue; cap/provider checks remain open |
| CEG | Constellation says CEG trades on Nasdaq | [Constellation Investor FAQ](https://constellationenergy.gcs-web.com/shareholder-services/investor-faqs) | Domicile, cap and provider checks remain open |
| AEP | AEP says its shares trade on Nasdaq under AEP | [AEP Stock FAQ](https://aep-q.aep.com/investors/stock/faq/) | Domicile, cap and provider checks remain open |

### Review interpretation

- Evidence above is a focused check of ticker/exchange statements, not a complete legal-identity audit for every symbol.
- Some issuer pages show delayed/current stock quotes; quote timestamps are not used as evidence of market-cap correctness.
- Candidate CSV statuses remain unchanged in this pass: all 31 remain `pending_review`, `market_cap_status=not_verified`, and `provider_status=not_checked` until all required evidence fields are reconciled.


## Official-source facts checked — follow-up pass (2026-10-24)

The following source results were directly inspected in this pass. They confirm only the stated listing/ticker or corporate facts; they do not complete every candidate's legal-identity review.

| Symbol | Confirmed fact | Official evidence | Still open |
|---|---|---|---|
| CRM | Salesforce investor-relations page displays NYSE: CRM | [Salesforce IR overview](https://investor.salesforce.com/overview/default.aspx) | Legal issuer/domicile field evidence, market-cap reconciliation, and provider mapping |
| PLTR | FY2025 Form 10-K says Class A common stock trades on Nasdaq Global Market Select under PLTR; Class B and Class F are not listed | [Palantir FY2025 Form 10-K](https://investors.palantir.com/files/2025%20FY%20PLTR%2010-K.pdf?mod=article_inline) | Ensure candidate specifically represents listed Class A; domicile/cap/provider checks |
| NFLX | Netflix's official release identifies Netflix, Inc. as Nasdaq: NFLX | [Netflix IR release](https://ir.netflix.net/investor-news-and-events/financial-releases/press-release-details/2026/Netflix-to-Announce-Third-Quarter-2026-Financial-Results/default.aspx) | Legal issuer/domicile evidence, cap/provider checks |
| COST | Costco identifies itself as a Washington corporation publicly traded on Nasdaq as COST | [Costco company profile](https://investor.costco.com/company-profile/) | Cap/provider checks; domicile evidence is now explicit for this field |
| PG | P&G IR displays NYSE: PG | [P&G IR overview](https://www.pginvestor.com/overview/) | Separate legal domicile evidence, cap/provider checks |
| BAC | Bank of America states common shares trade on NYSE under BAC; its 2025 Form 10-K identifies Delaware as jurisdiction of incorporation | [Shareholder information](https://investor.bankofamerica.com/shareholder-information/shareholder-and-contact-info) · [2025 Form 10-K](https://investor.bankofamerica.com/regulatory-and-other-filings/select-sec-filings/content/0000070858-26-000157/bac-20251231.htm) | Cap/provider checks |
| CAT | Caterpillar stock page displays NYSE: CAT | [Caterpillar stock information](https://investors.caterpillar.com/stock-info/default.aspx) | Legal domicile evidence, cap/provider checks |
| NOW | ServiceNow stock information displays NYSE: NOW | [ServiceNow stock information](https://investor.servicenow.com/stock-info/default.aspx) | Legal domicile evidence, cap/provider checks |

### Status handling

- Do not convert `identity_status` to verified based only on the limited facts above; remaining fields still matter.
- Candidate rows remain pending and market cap remains `not_verified`; provider support remains `not_checked` even when a historical price snapshot exists.
- A stock ticker page's delayed quote is not a market-cap reconciliation source. Share count, effective date, currency, and listing/share-class basis must match before verification.


## Official-source facts checked — follow-up pass 2 (2026-10-24)

| Symbol | Confirmed fact | Official evidence | Still open |
|---|---|---|---|
| HD | Home Depot says common stock trades on NYSE under HD and identifies Delaware incorporation | [Home Depot investor FAQ](https://ir.homedepot.com/investor-resources/faqs) | Market-cap reconciliation and provider mapping |
| MCD | McDonald's IR identifies NYSE:MCD; its 2025 annual report lists common stock MCD on NYSE and Delaware as jurisdiction of incorporation | [McDonald's IR](https://corporate.mcdonalds.com/corpmcd/investors.html) · [2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/63908/000006390826000035/mcd-20251231.htm) | Market-cap reconciliation and provider mapping |
| DE | Deere's official stock page identifies NYSE: DE | [Deere stock page](https://investor.deere.com/stock/) | Legal domicile, market-cap reconciliation and provider mapping |
| CVX | Chevron says common stock ticker CVX is listed on NYSE | [Chevron stock and dividend information](https://www.chevron.com/investors/stock-and-dividend) | Legal domicile, market-cap reconciliation and provider mapping |
| LIN | Linde says Linde plc is listed on Nasdaq under LIN and provides ISIN IE000S9YS762 | [Linde stock information](https://www.linde.com/investors/stock-and-dividend-information) | Irish issuer-domicile treatment already flagged; market-cap reconciliation and provider mapping |
| PG | SEC filing lists common stock PG on NYSE and identifies Ohio as state of incorporation | [P&G SEC filing](https://www.sec.gov/Archives/edgar/data/80424/000008042426000094/pg-20260729.htm) | Market-cap reconciliation and provider mapping |

These are field-level evidence additions only. They do not automatically change the candidate CSV's overall `identity_status`, `market_cap_status`, `provider_status`, or `activation_status`. All candidates remain pending until the complete evidence checklist is satisfied.


## Official-source facts checked — follow-up pass 3 (2026-10-24)

| Symbol | Confirmed fact | Official evidence | Still open |
|---|---|---|---|
| ADBE | Adobe FY2024 Form 10-K identifies Adobe Inc.; common stock ticker ADBE is registered on Nasdaq; state of incorporation is Delaware | [Adobe FY2024 Form 10-K](https://www.adobe.com/content/dam/cc/en/investor-relations/pdfs/ADBE-10K-FY24-FINAL.pdf) | Listing and domicile fields have direct evidence; market-cap reconciliation and provider/instrument mapping remain open |
| TJX | FY2026 Form 10-K identifies The TJX Companies, Inc.; common stock ticker TJX is listed on NYSE; Delaware is jurisdiction of incorporation | [TJX FY2026 Form 10-K](https://investor.tjx.com/node/21241/html) | Market-cap reconciliation and provider/instrument mapping remain open |
| AEP | AEP stock page identifies Nasdaq ticker AEP; company proxy material states AEP is incorporated in New York | [AEP stock information](https://www.aep.com/investors/stock/) · [AEP corporate/shareholder information](https://pr.aep.com/assets/docs/investors/AnnualReportsProxies/docs/23annrep/2024ProxyAppendixA.pdf) | Incorporation state is New York (not Ohio); market-cap reconciliation and provider/instrument mapping remain open |

These facts are recorded at field level only. Candidate activation and overall status remain unchanged until all required checks are complete.


## Official-source facts checked — follow-up pass 4 (2026-10-24)

| Symbol | Confirmed fact | Official evidence | Still open |
|---|---|---|---|
| AMGN | Amgen FY2025 Form 10-K identifies Amgen Inc.; common stock trades on Nasdaq Global Select Market under AMGN; incorporation is Delaware | [Amgen FY2025 Form 10-K](https://investors.amgen.com/static-files/43d5c346-88b9-44b3-9201-79514b22087a) | Market-cap reconciliation and provider/instrument mapping remain open |
| WELL | Welltower's official Q2 2026 release identifies Welltower Inc. as NYSE: WELL | [Welltower Q2 2026 results](https://welltower.com/investors/press-release-details/?id=808) | Legal incorporation/domicile evidence, market-cap reconciliation and provider/instrument mapping remain open |

The source records confirm only the listed fields. They do not complete the remaining identity or activation gates.


## Sixth batch: official filings checked (2026-10-24)

- **BAC — Bank of America Corporation:** the issuer's FY2025 Form 10-K identifies the registrant as Bank of America Corporation, lists common stock ticker BAC on the New York Stock Exchange, and identifies Delaware as its jurisdiction of incorporation. Source: [2025 Form 10-K, Items 1 and 5 / securities table](https://investor.bankofamerica.com/regulatory-and-other-filings/select-sec-filings/content/0000070858-26-000157/bac-20251231.htm). This supports issuer name, primary common-stock ticker/exchange and legal incorporation state; it does not independently verify KIS mapping or current market capitalization.
- **PLTR — Palantir Technologies Inc.:** the issuer's FY2025 Form 10-K names Palantir Technologies Inc. and Delaware as its jurisdiction of incorporation. Source: [FY2025 Form 10-K](https://investors.palantir.com/files/2025%20FY%20PLTR%2010-K.pdf). The filing source is recorded as evidence for issuer name/domicile; the listing ticker/exchange should be recorded only after the relevant securities-registration table is checked, and KIS support remains unverified.

These are partial field-level reviews only. Do not change overall identity status to verified from these facts alone.
