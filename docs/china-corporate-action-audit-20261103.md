# 중국 ETF 기업행사 독립 대사 (2026-11-03)

기준 통합 `dceea1877ede390b6b953689e749d89c1ca04145`, 선행 Draft #197
`8e490d0`, #198 `11c61034`. 시작 시 원격 ref와 두 PR의 Python/Unit 자동 CI
성공, 다른 활성 Codex 작업 없음 확인. 별도 `feat/china-corporate-action-audit-20261103`
작업이며 기존 PR/감사/수집 코드는 수정하지 않았다. 통합 대상은 data-validation-mvp,
리뷰 순서는 #197 → #198 → 본 후속 변경이다. 선행 PR을 중복 병합하지 않는다.

## 확인한 기업행사와 공식 근거

| 종목 | 확인된 행사 | 공식 문서 / 위치 |
|---|---|---|
| 515220 | 등록 2025-12-23, 배당락 12-24, 10좌당 0.400 CNY = 좌당 0.040 | [운용사 공시/SSE](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2025-12-19/515220_20251219_B5T8.pdf), p1 금액/p2 일자 |
| 512480 | 등록·분할 처리 2026-07-02, 거래 권리락 07-03, 1좌→2좌 | [6/29 시행 공시](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-06-29/512480_20260629_CA4B.pdf) p1, [7/3 결과](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-07-03/512480_20260703_WPHJ.pdf) p1 |
| 512400 | 등록 2025-09-12, 배당락 09-15, 10좌당 0.1500 = 좌당 0.015 | [운용사](https://www.nffund.com/main/files/2025/09/09/076473619639.pdf) p2, [동일 공시/SSE](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2025-09-10/512400_20250910_RUGH.pdf) |
| 512400 | 등록 2026-09-08, 배당락 09-09, 10좌당 0.8000 = 좌당 0.080 | [운용사 공시/SSE](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-09-04/512400_20260904_MAOK.pdf) p2 |

512480의 7/2 등록/분할 처리와 7/3 거래 권리락을 구분한다. 결과 공시의 1:2
실행은 확인했지만 공시의 NAV 반올림 4자리 규칙을 KIS OHLC 반올림 규칙으로
전용하지 않는다. [SSE 모의 옵션 공지](https://www.sse.com.cn/assortment/options/mnjyzxxx/c/c_20260703_10824231.shtml)는
거래 권리락일과 모의 계약단위 2배/행사가 절반을 보조 확인한다. 실제 옵션 거래
공시로 해석하지 않는다. 512400 운용사 URL 디렉터리는 9/9지만 문서 서명과 SSE
게시일은 2025-09-10이다. URL 날짜를 행사일로 사용하지 않았다.

## 수치 검증 수준

기존 외부 `CHINA_PRIVATE_SNAPSHOT_DIR`의 KIS CSV와 #198의 499일 SSE 캐시만
재사용했다. 신규 시세 요청 0, KIS 호출 0. 기존 #198의 영수증/해시 검증을 먼저
오프라인 실행하고 #197 파서와 달력/원시 OHLCV 감사를 재사용한다.
계수는 관측 가격비율에 맞춰 추정하지 않는다. 현금분배 가설은
`1 - 좌당 공시금액 / 배당락 직전 SSE 원시 종가`, 분할 가설은 `1 / 공시 분할배수`.
각 행보다 뒤의 행사 계수만 곱하고 마지막에 소수 셋째 자리 반올림한다.
배당락 당일에는 해당 행사 계수를 적용하지 않는다. 여러 분배는 계수를 순차 곱한다.
이는 **명시한 연구 가설**이며 KIS가 이 공식을 쓴다는 공식 확인이 아니다.

| 종목 | 전체 원시 불일치 일수 | 행사 전 OHLC 비교 | HALF_UP 정확 일치 | 반올림 전 최대 잔차 |
|---|---:|---:|---:|---:|
| 515220 | 98 | 392 | 392/392 | 0.000496769 미만 |
| 512480 | 222 | 888 | 696/888 | 0.0005 |
| 512400 | 271 | 1084 | 1084/1084 | 0.000499211 미만 |

515220 가설 계수 0.9630655586334256694367497692.
512400은 2025 행사 0.9903969270166453265044814341과 2026 행사
0.9579168858495528669121514992를 곱한다. 2025 행사 전 행에도 두 계수를 적용하여
271일 전체를 비교했으며 짧은 최신 구간의 2026 분배만으로 전체 이력을 설명하지 않는다.

512480의 공식 분할 계수는 0.5. 888개 모두 이론값과 차이 ≤0.0005이나,
HALF_UP 기준 192필드/114거래일은 정확 일치하지 않는다. HALF_EVEN도
685/888만 정확 일치(138일 잔여). 두 규칙을 별도 보고하며 더 잘 맞는 값을 골라
가격을 생성하지 않는다. 이론적 분할과 호가 정밀도 범위의 수치 부합까지만 확인했다.
공급자의 이진 부동소수점 처리·반올림 순서·정밀도는 **미확인**이다.

세 종목의 행사 후 원시 일치 시작일은 각각 2025-12-24, 2026-07-03,
2026-09-09로 공식 권리락/배당락일과 일치한다. 거래량은 각각 전체 299/299,
299/299, 300/300일 일치한다. 가설 일치는 원시 감사의 불일치 개수나 연속 일치
길이를 변경하지 않으며 조정가격을 출력·저장하지 않는다.

## 나머지 9종과 검색의 한계

SSE 공식 `commonQuery.do`, `sqlId=COMMON_PL_JJXX_JJGG_NEW_L`,
`BULLETIN_TYPE=fund05`(基金运作), `SECURITY_CODE=<종목>`,
`START_DATE=2025-07-30`, `END_DATE=2026-11-03`, pageNo=1/pageSize=100을
12종에 순차 조회했다. 각 응답의 total=반환건수(최대10)로 이 필터의 페이지
잘림은 없었다. 전체76건 중 행사 공시는 위 4행사/5공시와 일치했다.

| 원시 일치 63주 종목 | fund05 반환건수 | 분배/분할/병합 제목 발견 |
|---|---:|---:|
| 512800 | 6 | 0 |
| 512880 | 7 | 0 |
| 512600 | 4 | 0 |
| 515650 | 4 | 0 |
| 512010 | 10 | 0 |
| 512720 | 7 | 0 |
| 512980 | 7 | 0 |
| 512200 | 4 | 0 |
| 516160 | 6 | 0 |

이 9종의 55건은 조회된 운용 공시 목록의 제한적 검토다. 제목 검색과 단일 분류
필터는 연차보고서·임시보고·전체 운용사 공시 목록의 완전성 증명이 아니다.
63주 원시 OHLCV 일치와 이 검색에서 행사 미발견은 기록하되, **전 구간에 기업행사가
없었다거나 조정주가가 검증됐다고 판정하지 않는다**. 공시 분류 누락/정정 공시,
2025-07-30 이전 및 2026-10-27 이후 시세 대사는 미확인이다.

## KIS MODP와 보존·재현

[KIS 공식 API 상세](https://apiportal.koreainvestment.com/api/apis/public/detail?accessUrl=/uapi/overseas-price/v1/quotations/dailyprice),
[공식 property](https://apiportal.koreainvestment.com/api/apis/guide/property/0e9fb2ba-bbac-4735-925a-a35e08c9a790),
[공식 샘플](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/dailyprice/dailyprice.py):
MODP 수정주가 반영 여부 0/1 설명은 조정 산식·분배·분할의 처리 순서·반올림
방법·ETF별 적용 정확성의 설명이 아니다. 과거 각 행의 원요청/응답과 같은 시점의
MODP=0/1 쌍 대사는 없다. 현재 요청 코드의 MODP=1로 이를 대체하지 않는다.

공시5개 PDF와 KIS 상세 JSON, SSE 목록 응답12개는 외부
`CHINA_PRIVATE_SNAPSHOT_DIR/corporate_action_evidence/`에만 보존한다.
URL·UTC·상태·SHA256·조회건수만 `research/china_corporate_action_provenance.json`에
기록했다. 해시는 로컬 바이트 식별이며 공식 진위 또는 완전성 인증이 아니다.
최초 목록 요청은 로컬 CA 신뢰 오류로 중단됐고, OS 신뢰 루트를 포함한 CA 묶음으로
TLS 검증을 유지해 재실행했다. 인증서 검증 비활성화는 하지 않았다.

```powershell
$env:CHINA_PRIVATE_SNAPSHOT_DIR = '<기존 외부 스냅샷 경로>'
$env:PYTHONUTF8 = '1'
python china_corporate_action_audit.py --as-of-date 2026-11-03
python -m pytest -q tests/test_china_corporate_action_audit.py tests/test_china_sse_history_collect.py tests/test_china_history_audit.py tests/test_china_readiness_validation.py tests/test_china_stage_guard.py
```

## 게이트와 다음 우선순위

Stage 판정 가능 **0종 / 보류12종**, 512400 기존 차단 유지. 9종63주/515220 42주/
512480 16주/512400 6주의 기존 원시 연속 일치 길이를 승격하지 않는다.
30/34/35 완료주봉, 26주 절대수익률용 이력, 조정 기준, 이전 Stage 및 벤치마크
정책 검증 전 Stage1~4·수익률 출력·신규 Stage2 자동편입은 계속 보류한다.
운영/차트 로더 연결·가격 활성화·배포·Actions 수정/수동 실행·병합 없음.

다음은 KIS 공식 조정 산식/반올림 및 과거 요청 근거 확보, 512480의 0.0005 경계
잔차 규칙 확인, 9종의 연차·중간보고서와 전체 공시 분류를 통한 행사 목록 보강,
그 뒤 이전 Stage/벤치마크 정책 검증이다. 본 결과만으로 가격을 보정하지 않는다.
