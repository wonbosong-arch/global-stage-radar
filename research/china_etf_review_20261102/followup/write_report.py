"""Regenerate the Korean follow-up report from the frozen research tables."""
import json
from analyze_followup import HERE,read_csv,D

methods=read_csv(HERE/'methodology_versions_30.csv')
coverage=read_csv(HERE/'holdings_coverage.csv')
liquidity=read_csv(HERE/'official_liquidity_60d.csv')
market=read_csv(HERE/'official_market_reconciliation.csv')
summary=json.loads((HERE/'analysis_summary.json').read_text(encoding='utf8'))

method_table='\n'.join(f"| {r['symbol']} | {r['index_code']} | {r['document_month']+' '+r['document_version'] if r['document_version'] else '본문 미확보'} | {'공식 PDF 버전·코드 확인' if r['source_path'] else 'factsheet만 확인'} |" for r in methods)
liq_table='\n'.join(f"| {r['symbol']} | {D(r['official_avg_volume_shares']):,.2f} | {D(r['official_avg_turnover_cny']):,.2f} | {D(r['official_min_daily_turnover_cny']):,.0f} | {r['ohlc_matched_days']}/60 |" for r in liquidity[:12])
gap_table='\n'.join(f"| {r['symbol']} | {r['disclosed_rows']} | {D(r['equity_table_minus_reported_total_cny']):+,.2f} | {'일치' if r['total_reconciliation_status']=='matched' else '원인 미검증'} |" for r in coverage if r['as_of']=='2026-06-30')
examples=[]
for symbol in ['512400','512700']:
    r=next(r for r in market if r['symbol']==symbol and r['ohlc_matches']=='false')
    examples.append(f"- {symbol}, {r['date']}: 저장 종가 {r['baseline_close']} / 거래소 종가 {r['official_close']} CNY. 거래량 {int(r['baseline_volume']):,}좌는 일치한다.")

report=f'''# 중국 본토 ETF 공식 근거 후속 검증

검토일: 2026-11-02 KST. 연구 브랜치: `research/antigravity-china-etf`. 기존 Work 보고서와 정정 커밋을 재사용했다. 고정 입력은 `fda15a07fedefcb16506339d8600627ba581ac08`이다. 작업 시작 때 이미 있던 가격·상태·OHLCV 감사표의 미커밋 변경은 사용하거나 수정하지 않았다. **운영 편입 승인 보고서가 아니다.**

## 판정과 검증 완료 범위

| 항목 | 완료한 확인 | 미검증 / 해석 제한 |
|---|---|---|
| 30종 방법론 | 30행 출처·확인수준 등록. 24 ETF / 23개 지수에서 공식 PDF 본문의 버전·개정월·지수 코드를 확인하고 파일·SHA256 보존 | **30종 모두 최신성·해당 버전 시행일 미확정**. 나머지 6종은 상세 방법론 본문 미확보 |
| 대표 12종 보유내역 | 12종 모두 2026-06-30 반기 / 2026-09-30 3분기 공식 공시 확보. 총 {summary['holdings_rows']:,}개 공시 행, 기준일별 66쌍 / 합계132쌍 계산 | 반기 11종은 개별표 금액 합계와 보고서 주식투자 요약금액 차이 미해소. 3분기는 상위10 및 공시된 적극투자 일부여서 전체 포트폴리오 아님 |
| 거래량·거래대금 | 대표12 + 비교2의 60일, **840건 모두 수량 일치**. 단위 좌수(份). 같은 날짜의 공식 거래대금(CNY) 확보 | 가격 2종 일부 불일치. 호가 스프레드·시장 깊이·슬리피지·유동성 최우수 판정 미검증 |

이 보고서에서 “확인”은 해당 필드만 뜻한다. 파일 다운로드 성공, 문서 표지 버전, 지수 코드 일치, 현재 최신 방법론 확정, ETF 보유중복 확정은 서로 다른 판정이다. 테스트 통과도 외부 자료의 최신성을 입증하지 않는다.

## 1. 방법론 문서 버전 30종

아래 버전은 **이번에 실제 확보한 사본 중 가장 최근 표지 개정월·버전**이다. 2026-11-02 현재 최신본이라는 뜻이 아니다. 시행일은 30행 모두 빈 값이며 `unverified_no_dated_change_notice_retained`로 기록했다. 지수 기준일·최초 발표일·정기 조정일·URL의 숫자·검색 게시일을 문서 시행일로 대체하지 않았다.

| ETF | 지수 | 확보 사본 개정월 / 버전 | 확인 수준 |
|---|---|---|---|
{method_table}

공식 문서 URL·사본 경로·해시·지수 코드가 나오는 페이지는 [methodology_versions_30.csv](methodology_versions_30.csv)에 있다. 주 문서의 버전·코드 확인이며, 인용된 계산·유지 세칙 전체와 모든 예외 규정까지 확인했다는 뜻은 아니다. 기존 등록부·게이트의 최신 버전 상태를 일괄 상향하지 않았다.

**구체적으로 확인한 버전 위험:**

- 000949의 일반 경로 사본은 2023-02 V1.3, 기존 타임스탬프 경로 사본은 2023-12 V1.4였다. 930726도 일반 경로는 2021-09 V1.2, 다른 공식 경로는 2023-12 V1.3이다. 따라서 일반형 URL을 열었다고 최신본으로 채택하지 않았다. 두 버전과 원문을 모두 보존했다.
- 000932는 확보한 CSI800 업종 방법론 2022-04 V1.3 부록 p3에서 단일 종목 상한 **10%**를 확인했다. 이는 확보 버전의 규칙이고 현재 규칙의 시행일 승인은 아니다.
- 399986 은행 / 399975 증권은 통합 업종 방법론 2023-10 V1.7 부록 p3 / p5에서 각각 **15%**를 확인했다. 931775 부동산은 p3의 **10%**다. 공통 문서 파일명 H30199 자체를 각 ETF의 추종 지수 코드로 취급하지 않았다.
- 000827·931151은 공식 도메인 검색색인에서 2023-12 V1.2를 발견했으나 직접 다운로드는 HTTP403이었다. 본문 확보로 계산하지 않았다. 399967·399971·399808은 시도한 상세 PDF 경로에서 본문을 확보하지 못했다.
- CES990001 직접 사이트는 HTTP200이지만 정상 지수 본문 대신 접근 확인용 응답이었다. 공식 저장소의 2020-05-29 명칭 변경 공지는 검색색인에 2020-06-15 장 종료 후 시행으로 나오지만 직접 PDF는403이다. 이 **명칭 변경 시행일을 전체 방법론의 최신 시행일로 전용하지 않았다**. 색인 근거는 [search_index_evidence.json](search_index_evidence.json)에 분리했다.
- CSI 동적 상세 API 탐색은 오류 응답으로 끝났다. 파라미터 오류일 수 있으므로 문서가 존재하지 않는다고 단정하지 않는다. 최신 첨부파일과 이후 개정 공지 전체를 확인하지 못한 상태다.

## 2. 실제 ETF 구성종목·가중치 중복

지수 factsheet를 ETF 실제 보유내역으로 대체하지 않았다. 11종은 SSE에 게시된 운용사 공식 반기·3분기 보고서, 515650은 운용사 Fullgoal의 [반기 보고서](https://www.fullgoal.com.cn/wbs-file/fund_report/20260831/CN_50100000_515650_FB020010_20260009.pdf)와 [3분기 보고서](https://www.fullgoal.com.cn/wbs-file/fund_report/20261027/CN_50100000_515650_FB030030_20260010.pdf)를 사용했다. 공시일은 모두 각각 2026-08-31 / 2026-10-27이며 보유 기준일과 구분한다.

계산은 동일 기준일의 동일 주식 코드별 **min(A의 공시 NAV비중, B의 공시 NAV비중)의 합**이다. 반기에는 지수투자·적극투자(IPO 등)의 공시 행을 포함했다. 현금·채권·선물·경제적 룩스루 노출은 포함하지 않았다. 공시 비중은 소수점 둘째자리 %NAV이며 재정규화·미공시 비중 추정은 하지 않았다. 0.00% 행도 보유 행으로 보존했으므로 공유 종목 수와 유의미한 비중 중복은 다르다.

| 조합 | 기준일 | 공시 비중 기준 관측 중복 | 판단 |
|---|---|---:|---|
| 512600 필수소비 / 515650 소비50 | 2026-06-30 | 49.53%p NAV | 공시 전체 주식표 기준. 512600 요약금액 대사 차이 미해소 |
| 같은 조합 | 2026-09-30 | 40.70%p NAV | 상위10·공시 적극투자 부분에서 관측. 전체 확정률 아님 |
| 512400 비철 / 516160 신에너지 | 2026-06-30 | 11.56%p NAV | 공시 전체 주식표 기준. 양쪽 요약금액 대사 차이 미해소 |
| 같은 조합 | 2026-09-30 | 2.43%p NAV | 부분 공시에서 관측. 전분기 대비 전체중복 감소를 뜻하지 않음 |

**“12종 비중복” 주장은 지지되지 않는다.** 두 소비 ETF 및 비철·신에너지는 명확히 공유 주식과 비중이 있다. 다른 조합에서 관측 중복이 0이어도 현재 전체 포트폴리오가 비중복이라고 승인하지 않는다. 9월 데이터의 lower-bound 표시는 공시 반올림 값으로 계산한 부분 관측치라는 뜻이며, 반올림 오차까지 제거한 수학적 보장치는 아니다.

실제 행은 [official_etf_holdings.csv](official_etf_holdings.csv), 기준일·공시범위·합계는 [holdings_coverage.csv](holdings_coverage.csv), 132쌍과 공유 코드는 [official_etf_overlap_pairs.csv](official_etf_overlap_pairs.csv)에 있다. 각 행에 원문 페이지·URL·SHA256을 붙였다. 줄바꿈으로 숫자가 나뉜 512880·515220 3분기 표는 PDF 셀 경계를 이용해 복구했고 해당 페이지를 렌더링해 대조했다.

### 반기 공시표 합계 대사에서 남은 차이

아래는 추출한 7.3 전체 주식표 금액 합계에서 보고서의 주식투자 요약금액을 뺀 값(CNY)이다. 515650만 일치한다. 다른 11종은 두 텍스트 추출기에서도 같은 합계가 나왔지만 원인 규명이나 전체 합계 승인은 하지 않았다. 숫자를 맞추려고 보유행·비중을 임의 보정하지 않았다. 때문에 “12종 전체 보유중복 완전 검증 완료”로 표시하지 않는다.

| ETF | 반기 공시 행 수 | 표 합계 - 요약금액 CNY | 판정 |
|---|---:|---:|---|
{gap_table}

## 3. 평균 거래량 단위·공식 거래대금

기간은 기존 선정표와 같은 **2026-07-28~2026-10-27, 60개 관측 거래일**이다. 고정 커밋의 가격 파일 SHA256은 `{summary['baseline_price_sha256']}`다. 거래소 일봉은 더 최근 날짜와 11월2일 장중 행도 반환했지만 비교에 섞지 않았다.

공식 출처는 SSE ETF 사이트가 사용하는 `yunhq.sse.com.cn:32042/v1/sh1/dayk/{{ETF}}`이며 `date,open,high,low,close,volume,amount` 필드를 명시해 저장했다. [공식 화면 스크립트](https://etf.sse.com.cn/xhtml/js/funddetail_new.js?v=V3.1.1)는 `volume/100`을 手, `amount/10000`을 万元로 표시한다. [거래소 ETF 안내](https://etf.sse.com.cn/fund/quertion/)도 1手=100份을 명시한다. 공식 수량과 저장 수량이 840/840개 그대로 일치하고, 각 일자의 거래대금/좌수가 공식 저가~고가 안에 들어간다. 따라서 이 스냅샷의 `volume`은 手나 금액이 아니라 **份(ETF 좌수)**로 대사됐다.

평균 거래대금은 공식 일별 `amount`의 산술평균이다. 종가×거래량으로 추정하지 않았다. 아래 표는 표시만 소수 둘째자리로 반올림했다.

| 대표 ETF | 평균 거래량 좌/일 | 평균 거래대금 CNY/일 | 최소 일 거래대금 CNY | OHLC 일치일 |
|---|---:|---:|---:|---:|
{liq_table}

비교 후보 512700과512760도 각각60일 거래량이 일치했다. 전체 14종·840행은 [official_market_reconciliation.csv](official_market_reconciliation.csv), 평균과 원문URL은 [official_liquidity_60d.csv](official_liquidity_60d.csv)에 있다.

**가격 차이는 별도 미검증:** 512400은31일, 512700은25일에서 OHLC 중 하나 이상이 다르다. 거래량 일치와 분리했다. 배당·수정주가·공급자 정밀도 등이 원인이라고 추정하지 않는다.

{chr(10).join(examples)}

구형 SSE `queryAllQuatAbelNew.do`는 요청일2026-10-27에 일·월·연0값과2022-02-25 누적행을 반환했다. 이 응답은 자료 없음/구형 자료로 처리했고, 실제 거래량0이나 최신 유동성 근거로 사용하지 않았다.

공식 거래대금 확보는 과거 체결 규모의 확인이다. 역사적 스프레드·호가 깊이·주문규모별 체결 가능성·추적오차·매매 자격까지 보장하지 않는다. 12종 중 “최고 유동성”이나 투자 적격 결론을 내리지 않았다.

## 4. 실행·재현과 변경 범위

- `collect_official_documents.py`, `collect_fund_reports.py`, `collect_official_market.py`, `fetch_source.py`: 수동 실행 연구용 자료 확보. 기존 예약수집 코드에서 호출하지 않는다. TLS 검증을 끄지 않고 Windows 신뢰 인증서를 사용했다.
- `analyze_followup.py`: 보존한 공식 사본·고정 git 입력에서 CSV 재생성. API를 호출하지 않는다. `write_report.py`: 이 보고서 재생성.
- `retained_source_catalog.json`: 최종 보존 원문 경로·URL·응답 해시·열람시각. 각 acquisition manifest에는 실패 시도도 포함한다. 초기512980 공시의 안내문과 본보고서가 같은 저장 경로를 거친 이력이 있어, 보존 원문의 증거는 최종 catalog의 실제 일치 해시를 기준으로 한다. 향후 수집은 안내문을 제외한다.
- **집중 테스트 57개 및 하위 검사195개 통과**. 신규19개 + 기존 중국 ETF 검사38개. 실제 PDF의 버전·지수 코드, 24공시의 범위, 줄바꿈 숫자 복구, 부분 중복의 승격 방지, 840일 수량·거래대금·가격 차이 분리, 원문 해시를 검사했다. [test_results.json](test_results.json)에 명령과 결과를 기록했다.
- 전체 테스트는 재실행하지 않았다. 이번 변경은 연구 데이터·연구 도구·집중 테스트·진행 기록만이다. 기존 전체 테스트의 Windows 오류 결과는 상위 Work 보고서에 보존돼 있으며 이번 통과로 재인증하지 않는다.
- `main`, `data-validation-mvp`, PR#192, 운영 대시보드, 기존 가격 파일, 승격 게이트, GitHub Actions 워크플로 및 수집 스케줄을 수정하지 않는다. PR생성·병합·운영활성화·수동 Actions 실행을 수행하지 않는다. 커밋·푸시 결과는 최종 사용자 보고의 실제 SHA를 따른다.

## 5. 다음 우선순위

1. **최신 방법론/시행일:** 상세 본문이 없는 512580·512660·512760·512980·515790·516160부터 정상 공식 상세 링크·문서를 확보한다. 이어 30종의 현재 첨부파일과 개정 공지/발효 이력을 대조한다. 오늘 확보한 표지 버전을 최신으로 승격하지 않는다.
2. **보유표 완전성:** 11종 반기 전체 주식표 합계 차이를 운용사 원자료/정정공시와 대사한다. 9월말 전량 자료가 공개된 경우에만 같은 날짜의 전체중복을 재계산한다. 상위10을100%로 재가중하지 않는다.
3. **가격 기준:** 512400·512700의 공식 원시 가격과 공급자 조정 기준을 대사한다. 기존 가격파일을 이번 근거만으로 고치지 않는다.
4. **유동성 잔여:** 같은 기간의 공식 호가/스프레드·시장깊이·추적오차 자료를 확보한다. 현재 주문가능성·조정주가·거래일 완전성·이용권은 별도 운영 전 게이트로 남긴다.

다음 작업은 보존 자료와 미검증 목록에서 이어가면 된다. 사용자 파일 전달이나 GitHub Actions 신규 구축은 필요하지 않다.
'''
(HERE/'followup_report_ko.md').write_text(report,encoding='utf8')
print('Written followup_report_ko.md')
