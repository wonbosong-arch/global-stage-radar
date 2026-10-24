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

## Official-source facts checked — follow-up pass 5 (2026-10-24)

| Symbol | Confirmed fact | Official evidence | Still open |
|---|---|---|---|
| CEG | Constellation Energy Corporation's FY2025 Form 10-K identifies it as a Pennsylvania corporation and lists common stock CEG on Nasdaq | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/1868275/000186827526000032/ceg-20251231.htm) | Market-cap reconciliation and provider mapping |
| COP | ConocoPhillips FY2025 Form 10-K identifies the issuer and lists common stock COP on NYSE | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/1163165/000116316526000009/cop-20251231.htm) | Issuer domicile, market-cap reconciliation and provider mapping |
| IBM | IBM FY2025 Form 10-K identifies International Business Machines Corporation, New York incorporation, and ticker IBM on NYSE (also NYSE Texas) | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/51143/000005114326000010/ibm-20251231.htm) | Market-cap reconciliation and provider mapping |
| ETN | Eaton FY2025 Form 10-K identifies Eaton Corporation plc as incorporated in Ireland and its ordinary shares ETN as NYSE-listed | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/1551182/000155118226000007/etn-20251231.htm) | Preserve issuer-country review flag; market-cap reconciliation and provider mapping |

These are limited field-level findings, not an activation approval. All four candidates remain pending and their market caps/provider support remain unverified.

### COP field clarification (2026-10-24)

The FY2025 Form 10-K identifies ConocoPhillips as incorporated in Delaware and lists common stock COP on the New York Stock Exchange. Official SEC filing: [ConocoPhillips FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/1163165/000116316526000009/cop-20251231.htm). This closes the issuer-domicile evidence gap at the document level, but does not verify market capitalization or KIS/provider mapping.

## Official-source facts checked — follow-up pass 6 (2026-10-24)

| Symbol | Confirmed fact | Official evidence | Still open |
|---|---|---|---|
| PG | P&G FY2026 Form 10-K confirms Ohio incorporation and common stock PG on NYSE | [FY2026 Form 10-K](https://www.sec.gov/Archives/edgar/data/80424/000008042426000103/pg-20260630.htm) | Market-cap reconciliation and provider mapping |
| CAT | Caterpillar FY2025 Form 10-K confirms Delaware incorporation and NYSE: CAT | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/18230/000001823026000008/cat-20251231.htm) | Market-cap reconciliation and provider mapping |
| NOW | ServiceNow FY2025 Form 10-K confirms Delaware incorporation and NYSE: NOW | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/1373715/000137371526000007/now-20251231.htm) | Market-cap reconciliation and provider mapping |
| CSCO | Cisco FY2026 Form 10-K confirms Delaware incorporation and Nasdaq: CSCO | [FY2026 Form 10-K](https://www.sec.gov/Archives/edgar/data/858877/000085887726000132/csco-20260725.htm) | Market-cap reconciliation and provider mapping |
| SBUX | Starbucks FY2025 Form 10-K confirms Washington incorporation and Nasdaq Global Select Market: SBUX | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/829224/000082922425000114/sbux-20250928.htm) | Market-cap reconciliation and provider mapping |
| TMUS | T-Mobile US FY2025 Form 10-K identifies T-Mobile US, Inc. and common stock TMUS on Nasdaq; its incorporation is Delaware | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/1283699/000128369926000010/tmus-20251231.htm) | Market-cap reconciliation and provider mapping |
| DIS | Disney FY2025 annual report confirms issuer identity and Delaware incorporation; ticker/exchange listing is separately stated in issuer investor materials | [FY2025 annual report](https://www.sec.gov/Archives/edgar/data/0001744489/000174448926000012/ars_2025.pdf) | Market-cap reconciliation and provider mapping |

These are field-level evidence updates only. Candidate statuses remain pending until market capitalization and provider/instrument checks are completed.

## Official-source facts checked — follow-up pass 7 (2026-10-24)

| Symbol | Confirmed fact | Official evidence | Still open |
|---|---|---|---|
| ORCL | Oracle FY2026 Form 10-K confirms Delaware incorporation and NYSE: ORCL; 2.880 billion shares outstanding as of 2026-06-12 | [FY2026 Form 10-K](https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm) | Reconcile shares and price date to the secondary market-cap figure; provider mapping |
| CRM | Salesforce FY2026 Form 10-K confirms Delaware incorporation and NYSE: CRM; about 923 million shares outstanding as of 2026-02-25 | [FY2026 Form 10-K](https://www.sec.gov/Archives/edgar/data/1108524/000110852426000060/crm-20260131.htm) | Reconcile shares and price date to the secondary market-cap figure; provider mapping |
| NFLX | Netflix FY2025 Form 10-K confirms Delaware incorporation and Nasdaq: NFLX | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/1065280/000106528026000034/nflx-20251231.htm) | Reconcile shares and price date to the secondary market-cap figure; provider mapping |
| COST | Costco FY2026 Form 10-K confirms Washington incorporation and Nasdaq: COST; 443,129,349 shares outstanding as of 2026-09-29 | [FY2026 Form 10-K](https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/cost-20260830.htm) | Reconcile shares and price date to the secondary market-cap figure; provider mapping |
| HD | Home Depot FY2025 Form 10-K confirms Delaware incorporation and NYSE: HD | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/354950/000035495025000085/hd-20250202.htm) | Market-cap reconciliation and provider mapping |
| KO | Coca-Cola Company FY2025 Form 10-K confirms Delaware incorporation and NYSE: KO | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/21344/000162828026010047/ko-20251231.htm) | Market-cap reconciliation and provider mapping |

The reported share counts are retained as dated reference evidence only; they are not treated as a verified 2026-10-23 market-cap calculation without a matching price basis and effective date.

## Official-source facts checked — follow-up pass 8 (2026-10-24)

| Symbol | Confirmed fact | Official evidence | Still open |
|---|---|---|---|
| ANET | Arista Networks FY2025 Form 10-K confirms Delaware incorporation and NYSE: ANET | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/1596532/000159653226000013/anet-20251231.htm) | Market-cap reconciliation and provider mapping |
| CVX | Chevron FY2025 Form 10-K confirms Delaware incorporation and NYSE: CVX | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/93410/000009341026000078/cvx-20251231.htm) | Market-cap reconciliation and provider mapping |
| DE | Deere & Company FY2025 Form 10-K confirms Delaware incorporation and NYSE: DE | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/315189/000110465925122321/de-20251102x10k.htm) | Market-cap reconciliation and provider mapping |
| WELL | Welltower FY2025 Form 10-K confirms Delaware incorporation and NYSE: WELL; 697,752,530 shares outstanding as of 2026-02-06 | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/766704/000076670426000010/well-20251231.htm) | Reconcile shares and price date to the secondary market-cap figure; provider mapping |
| AEP | American Electric Power FY2025 Form 10-K identifies the parent company as incorporated in New York; issuer materials identify Nasdaq: AEP | [FY2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/4904/000000490426000013/aep-20251231.htm) | Market-cap reconciliation and provider mapping |

These field-level records do not constitute market-cap verification or provider approval.
