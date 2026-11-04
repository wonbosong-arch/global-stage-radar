# 미국 후보 Stage readiness 오프라인 감사

기준은 `data-validation-mvp`의 `d8d4590d67fa3c4401285cc6e3d08b73bc8a19d7`
(2026-11-04 13:41:22 KST 후보 자동 갱신)다. #208의 병합 SHA
`ddd249c94de24573c14ce5d32a589b1e1bd52e1d`의 바로 다음 커밋이다.
분석 날짜를 2026-11-04로 고정했다. 미국은 발행사 국적이 아니라
registry의 NAS/NYS/AMS 상장 venue를 뜻한다. ADR/외국 발행사도 포함하며
stock 적격성·신원 확인을 마쳤다는 뜻이 아니다.

## 재현과 원본 시각

```powershell
python audit_us_stage_readiness.py --as-of 2026-11-04
python -m pytest -q tests/test_us_stage_readiness_audit.py
```

첫 명령은 로컬 입력을 읽고 JSON을 stdout으로만 출력한다. 네트워크,
API 자격증명, 수집, 데이터 저장, 승인 상태 변경은 없다. 명시적 날짜가
필수다. 입력 11개 파일의 SHA256/바이트 크기와 원본 상태 파일의 시각을
JSON에 기록한다. 원본 가격/응답은 새로 공개하지 않는다.
집계 산출물은 `docs/evidence/us-stage-readiness-20261104.json`이다.
재현에는 이 문서의 기준 커밋 데이터가 필요하다. 이후 자동 갱신된
데이터로 실행하면 fingerprint와 결과가 달라질 수 있다.

- registry 갱신 완료: 2026-11-04 04:41:21 UTC / 13:41:21 KST.
- candidate 가격 갱신 완료: 2026-11-03 23:04:51 UTC / 11-04 08:04:51 KST.
  전체 CSV 날짜 범위 2024-10-04~2026-11-03. 개별 종목 마지막 날짜는 다르다.
- active 가격 갱신: 2026-11-04 01:19:21 UTC / 10:19:21 KST.
  전체 CSV 날짜 범위 2022-09-16~2026-11-03.
- 보고서 CSV에는 독립 생성 시각이 없다. 기준 commit과 파일 hash로
  버전을 고정한다. 디스크 mtime을 관측 시각으로 사용하지 않는다.

## 고유 종목과 조건별 교집합

미국 고유 심볼 **1,897**: NAS 745 / NYS 1,139 / AMS 13.
공백/중복 심볼, 저장 보고서의 미국 심볼 집합 불일치는 실패시킨다.
원본 가격의 중복·비유한 값·OHLC 구조·미래 날짜도 검사하며, 문제 있는
종목은 주봉 가용성 집계에서 제외한다. 이번 입력은 1,897개 모두 이
기초 검사를 통과했다. 거래일 누락/제공자 지원의 완전한 증명은 아니다.

| 차원 | 고유 종목 수 |
|---|---:|
| registry의 bridge 시총 추정값 존재 / $1B 이상 | 1,869 / 1,869 |
| 위 값 없음 | 28 |
| registry 시총 출처 URL + as-of 날짜 모두 존재 | 31 |
| 시총 verified | 0 |
| 고유 일봉 150개 이상 | 1,847 |
| 완료 주봉 30개 이상 / MA30 유한 | 1,850 |
| 완료 주봉 34개 이상 / 4주 MA 기울기 유한 | 1,846 |
| 완료 주봉 35개 이상 | 1,845 |
| 35주 미달 | 52 |
| registry 매핑 필수 필드 모두 존재 | 106 |
| 배정 벤치마크의 날짜 정렬 RS와 35주/신선도 입력 확보 | 105 |
| 예비 sector/market benchmark/sector benchmark 제안 모두 존재 | 271 |
| identity verified / provider supported / active | 0 / 0 / 0 |
| 현행 bridge가 실제 추가한 미국 종목 | 0 |

30주면 MA30 한 점을 계산할 수 있지만 4주 전 MA30과 비교하는 기울기는
34주가 필요하다. 현행 `weekly_bars` 기본/운영 앱은 35주를 요구한다.
이는 이전 주까지의 기울기와 신규 진입 비교 여유도 포함한 현행 정책이며,
30주 MA 존재와 운영 Stage readiness를 동일시하지 않는다. 신규 Stage2
비교에는 인접 주가 정확히 7일 차이인지도 검사한다.

| 교집합 | 고유 종목 수 |
|---|---:|
| 시총 규모 심사값 + 30주 이상 | 1,823 |
| 시총 규모 심사값 + 35주 이상 | 1,818 |
| 30주 이상 + registry 매핑 필드 | 105 |
| 시총 규모 심사값 + 35주 이상 + registry 매핑 필드 | 105 |
| 시총 URL/as-of + 규모 심사값 + 35주 이상 + registry 매핑 필드 | 31 |
| 위 어느 교집합이든 active 추가 | 0 |

106개의 필드 존재는 매핑 승인 106개를 의미하지 않는다. 심볼별로
실제 배정된 두 벤치마크의 35주 가용성과 날짜 정렬된 26주 상대수익률,
현행 freshness helper도 재사용해 별도 집계한다(JSON 참조).
예비 제안은 승인된 필드에 복사하지 않는다.

## 겹치지 않는 blocker 분해

모든 1,897개는 identity 미승인, provider not_checked, pending_review가
동시에 남아 있다. 따라서 '승인되지 않음 1,897'만으로는 병목을 알 수 없다.
다음은 **시총 → 30주 → 35주 → 매핑 필드 → 신원 → 제공자 → active**
순서에서 처음 누락된 차원에만 배정한 분석용 waterfall이다.
이 순서는 실제 승인 처리 순서나 자동 승인 제안이 아니다.

| 처음 누락된 차원 | 고유 종목 수 |
|---|---:|
| registry 규모 심사값 | 28 |
| 앞 조건 통과, 30주 미달 | 46 |
| 앞 조건 통과, 30~34주 | 5 |
| 앞 조건 통과, registry 매핑 필드 부족 | 1,713 |
| 위 데이터 차원 통과, 신원 미승인 | 105 |
| 합계 | 1,897 |

순서에 의존하지 않는 전체 교집합 분해도 제공한다. 아래 각 행은 공통
신원/제공자/활성화 blocker 외에 추가로 부족한 차원이며 서로 배타적이다.

| 추가 누락 차원 | 고유 종목 수 |
|---|---:|
| 없음 | 105 |
| 매핑 필드 | 1,713 |
| 35주 | 1 |
| 35주 + 매핑 필드 | 50 |
| 규모 심사값 + 매핑 필드 | 27 |
| 규모 심사값 + 35주 + 매핑 필드 | 1 |
| 합계 | 1,897 |

## 기존 보고서의 차이와 provenance

예비 Stage 보고서는 Stage2 98 / Stage2A 21 / 중립 116 / 하락 32 /
매핑 보류 1,578 / 짧은 이력 52다. 35주 미달 분류가 매핑 누락 분류를
덮어쓴다. `data_status=benchmark_mapping_missing`은 1,626개이고,
예비 매핑이 있는 271개와 합쳐 1,897개다. 실제 registry 필드 부족은
1,791개(1,897-106)다. 세 숫자는 서로 다른 의미다.

시총도 서로 다른 경로가 있다.

- bridge는 verified USD 값을 우선하고, 그렇지 않으면 registry 보조 USD B,
  이어 discovery USD 추정값을 사용한다. 이 감사의 1,869개는 이 경로의
  값 존재/규모 심사 가능 수다. verified 0은 그대로다.
- 저장 coverage의 size screen은 보조 관측 파일/상태를 별도로 읽어
  pass_estimate 197 / needs_observation 1,700으로 표시한다.
- 저장 review queue의 별도 `size_screen_result`는 pass_estimate 1,897이다.
  동일 행의 coverage-derived field는 여전히 197/1,700이다. 추가 관측값과
  registry 값의 연결 범위가 달라 발생하는 차이다. 이 PR은 이를 고치거나
  28개를 자동 보완하지 않고 그대로 드러낸다.
- registry 유입은 Yahoo queue 1,700 / KIS ranking 166 / 기타 기존 31이다.
  Yahoo review 파일과 현재 registry의 심볼 교집합은 1,707개(유입 출처
  1,700개와 다른 집합)다. 1,707개 모두 URL과 fetched_at이 있지만 시총
  as-of는 비어 있고 `not_provided_by_yahoo`다. 관측 범위는
  2026-10-26 11:28:47~11-02 22:33:09 UTC다. fetched_at을 cap as-of로
  대체하지 않는다. registry URL+as-of 존재 31개도 verified가 아니다.

적격성 역시 미확정이다. instrument_type은 common_stock_candidate 29,
common_stock_candidate_unverified 1,702, equity_candidate_unverified 138,
adr_candidate 28이다. ADR 예탁비율/발행사 국가 처리와 실제 증권 유형은
기존 review gate에 남긴다. 가격 응답이 저장되어 있다는 사실은
provider_status=supported 또는 identity=verified와 다르다.

## 구현 경로 확인과 다음 최소 작업

`approved_stock_universe.py`는 active, identity verified, provider supported,
시총, 필수 매핑, 종목과 벤치마크별 일봉 150개/7일 신선도를 검사한다.
`candidate_stage_integration.py`는 종목별 실패를 격리한다. `app.py`는
daily+candidate 가격으로 이 bridge를 호출하고 기존 Stage engine으로
35주/정렬된 벤치마크 RS/신선도를 검사한다. sector 후보 가격 파일을
예비 분석에 사용하는 경로와 운영 bridge 경로는 같지 않다.
예비 보고서/다운로드/차트와 승인 bridge UI가 이미 있으므로 UI·엔진·수집기를
재구현하지 않았다. 호스팅 UI의 현재 동작은 이번에 검증하지 않았다.

1. 다음 작은 개발은 시총 read-only 보고서에서 registry/coverage/queue
   추정값 선택과 provenance를 일관되게 설명하는 작업이다. 기존 queue
   관측을 활용하되 verified/as-of/activation을 올리지 않아야 한다.
2. 기존 매핑과 35주가 있는 105개 중 URL/as-of도 있는 31개를 작은
   신원·증권 유형·매핑 검토 묶음으로 준비한다. 31개는 승인 추천 목록이
   아니라 기존 증거가 상대적으로 모인 후보 집합이다.
3. 매핑이 비어 있는 1,626개의 예비 분류를 검토하되 약한 업종 proxy를
   강제하지 않는다. 승인 필드가 비어 있는 전체 1,791개와 구분한다.

운영 Stage 반영 **미적용**. 병합·배포·active 변경은 별도 승인 대상이다.
main, #205/중국 코드, 가격/후보 data 파일, workflow/cron/queue,
S3/Streamlit/비용 설정, 11월 5일 10:30 KST 검증 자동화는 변경하지 않았다.
KIS/가격 API 호출, Actions dispatch/rerun은 하지 않았다.

## 검증

신규 합성 테스트 4개: 30/34/35주 및 MA/기울기 경계, pending/보조 시총
분리, 원본 hash 불변, 중복/집합 불일치, 비유한 가격 거부.
bridge/Stage/예비 분석 포함 집중 테스트 31개 통과.
전체 Windows baseline 비교 및 최종 원격 SHA CI 결과는 PR에 기록한다.
