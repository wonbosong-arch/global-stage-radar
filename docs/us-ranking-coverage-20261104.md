# 미국 ranking 수집 상태 보완 (2026-11-04)

기준: `data-validation-mvp` `20bfde2df49ae644cabebfcc2d4d14d74d3d004a`.
독립 브랜치 `fix/us-ranking-coverage-20261104`. main 및 통합 브랜치 직접 수정 없음.

## 원인과 불확실성

저장된 01:20 UTC 수집 상태에서 NAS/NYS/AMS 모두 100행씩 두 번 반환한다.
각 둘째 페이지의 신규 symbol은 0이며 두 응답 모두 tr_cont=F다.
KEYB는 두 요청에서 공란이고 저장된 response_structure.cursor_fields도 공란이다.
reported total은 5249/2832/4781이다. 이것은 정확한 반환 가능 종목 수로 검증되지 않았다.
따라서 누락 종목 수나 전수 커버리지 비율을 이 값에서 계산하지 않는다.

기존 #144/#160/#164는 CURR_GB=0, F/M 연속 조회, 반복 페이지 중단,
민감값 없는 응답 구조 진단을 제공한다. 현재 요청을 바꾸거나 상한을 늘릴 근거는 없다.
KEYB를 어떤 응답 필드에서 어떻게 만드는지, ranking 자체의 최대 반환 범위,
F의 해당 API별 의미는 미확정이다. daily price의 BYMD 날짜 커서(kis_provider.py)는
다른 endpoint의 계약이므로 ranking으로 옮기지 않는다. kis_provider.py는 변경하지 않는다.

확인한 결함: 수집 경고가 reported total > 중복 포함 반환 행 수에 의존했다.
반복/상한 중단이어도 total이 없거나 작으면 성공으로 표시될 수 있었다.
이제 종료 사유(no_new_symbols/page_limit/unconfirmed_header/terminal_header),
고유 symbol 및 중복 행 집계를 전달한다. 불확실한 종료는 total과 무관하게 경고한다.
D/E는 기존 코드에서 종료로 취급하던 transport 상태다. terminal_header도
거래소 전수 발견을 뜻하지 않는다. 과거 diagnostics에 new_symbols가 없으면 고유 수는 null이다.
반환 symbol의 공백·대소문자를 정규화하여 반복 감지와 최종 중복 제거 기준도 맞췄다.

## 저장 데이터 집계와 대체 경로

미국은 registry market=United States 기준이며 미국 상장 외국 발행사/ADR을 포함한다.
cap known은 discovery_market_cap_usd 또는 보조 USD B 값 존재 여부다.
검증된 시총이나 승인 상태를 뜻하지 않는다.

| 거래소 | 등록 후보 | cap known | cap unknown | pending | approved/운영 Stage ready |
|---|---:|---:|---:|---:|---:|
| NAS | 745 | 738 | 7 | 745 | 0 |
| NYS | 1139 | 1118 | 21 | 1139 | 0 |
| AMS | 13 | 13 | 0 | 13 | 0 |
| 미국 합계 | 1897 | 1869 | 28 | 1897 | 0 |

전체 US/KR registry는 1926개다. 알려진 미국 cap 1869개는 모두 >=1B 추정값이다.
미국 출처는 Yahoo queue 1700, KIS ranking 166, 초기 공란 31이다.
저장 coverage는 pass_estimate 197 / needs_observation 1700이며 모두 manual review 차단이다.
시총 값 존재만으로 coverage의 관측 증거 요구를 우회하지 않는다.
저장 provisional report에서 35주 이상 1845개, 매핑 보류 1578개, 35주 미달 52개,
검토용 Stage2 98 / Stage2A 21 / 중립 116 / 하락 32다. 운영 승인이나 신규 진입 수가 아니다.

ranking 미포함 master 6484개(NAS 3850/NYS 2351/AMS 283) 중 1707개가
이미 미국 registry에 있다. master 숫자는 적격 주식 모집단이 아니다.
Yahoo master 보완은 6444행, cap 관측 5369 / 미상 1075, >=1B 추정 2291개다.
후속 review queue는 2270개(NAS 947/NYS 1301/AMS 22), registry 교집합은
1707개(NAS 655/NYS 1042/AMS 10)다. 미등록 563개 모두가 intake 적격은 아니다.
기존 build_review_only_candidates를 메모리에서 max_add/max_total=10000으로 실행한 결과,
현행 일반주/시총/검토 상태/active 제외 규칙을 통과하는 미등록 후보는 436개
(NAS 246/NYS 178/AMS 12)였다. 파일 저장 및 실제 intake는 하지 않았다.
기존 정책은 run당 250개/총 2500개 및 72시간 freshness 제한이다.
11/04 저장 intake 상태는 250개 추가, 총 1926개, pending review다.

따라서 ranking은 독립 발견 경로의 실제 병목이나, 전체 미국 후보가 300개에 갇힌 것은 아니다.
master와 Yahoo가 상당 부분 우회한다. 미국 전체 적격 종목 수는 여전히 모른다.

## 재사용, 검증 및 후속 기준

#58의 수집 후 보고서, #79 approved_stock_universe/candidate_stage_integration bridge,
#75/#100 Yahoo 보완과 bounded review-only intake를 재사용한다. #12/#13은 main에
병합됐으나 현재 integration의 승인/pending 보호는 현행 코드와 테스트로 확인했다.
새 수집기·Stage 엔진·활성화 경로는 만들지 않았다.
작업 전 open PR/최근 CI/다른 채팅 및 로컬 worktree를 확인했다.
#205 head 7c9580e, #206 및 중국 연구 PR을 변경하지 않았다.
최신 기존 Python CI 성공은 f6bda62이며 데이터 HEAD 전체 CI 성공과 구분한다.

신규 회귀 4개는 수정 전 기준에서 실패(하위 사례 포함), 수정 후 집중 suite
68 passed / 17 subtests passed. 일반 F/M 연속 페이지, 한국 수집, retry,
민감값 비노출, intake 및 승인 bridge 보호도 포함한다.
로컬 전체 unittest는 353 tests, 기존 Windows fsync 오류 26개/skip 1개다.
전체 pytest는 428 passed / 28 failed / 7 skipped / 156 subtests passed다.
실패한 4개 모듈을 수정 전 20bfde2에서 재실행해 동일 28개 실패와 동일 실패 ID 집합을
확인했다(Windows fsync 26건, POSIX shell 1건, 기존 캐시 결측값 검사 1건).
원격 자동 Python/Unit CI의 최종 결과는 PR에 기록한다.

효과 기준: 현재 snapshot 재생 시 각 거래소 raw 200 / unique 100 / 중복 100,
no_new_symbols와 partial 상태가 total 유무에 관계없이 유지돼야 한다.
이번 변경만으로 신규 종목 수 증가를 주장하지 않는다. 후속 자연 예약 결과에서
거래소별 unique 수, 종료 사유, 등록 후보/시총 미상/미등록 intake 적격 수를 비교한다.
전수 비율은 제공자 모집단 정의를 확인한 뒤에만 계산한다.

live KIS, Actions 수동 dispatch/rerun, cron/concurrency, 데이터/활성화,
AWS/S3/Streamlit, main, 병합·배포 및 11/05 자동화는 변경/실행하지 않았다.
다음 최소 개발 후보는 Yahoo provenance의 보고서 연결이다. 먼저 기존 관측 일자와
조회 일자의 차이를 보존해야 하며 registry 시총만으로 verified로 승격하면 안 된다.
ranking 요청 수정은 공식 continuation 계약 확인 또는 승인된 제한적 live 검증 후 별도 작업이다.
