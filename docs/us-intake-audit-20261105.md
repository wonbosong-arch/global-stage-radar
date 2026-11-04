# 미국 review-only intake 진단 — 2026-11-05 KST

기준: data-validation-mvp b37bf7b4d5a4ccd790877678d970dffe717b866d. 최신 PR #212 병합 후 신규 PR 없음(시작 시 확인). 별도 매핑 작업 01a1a553-715c-7ae3-af09-ed8076600a99는 분석 종료·제품 변경 없음. stock_mapping.py 및 매핑 경로는 수정하지 않음.

## 저장 데이터 결과

- 전체 registry 2,177; 미국 2,148 (NAS 887 / NYS 1,243 / AMS 18); KRX 29.
- 미국 unranked KIS master 6,485; symbol+venue 중복 0. 저장 Yahoo 관측 6,444.
- 저장 review queue 2,270; 일반 주식 후보 2,156, ADR 의심 별도 검토 114. 중복 pair/잘못된 venue 0.
- 현행 적격 미등록 미국 후보 186 (NAS 104 / NYS 75 / AMS 7). 오늘 250개가 이미 추가되어 과거 436에서 186으로 감소.
- 186개 오프라인 intake 재생 후 전체 2,363 / 미국 2,334; 2,500 상한까지 137자리. 두 번째 재생 신규 0. 기존 행 불변, 신규 모두 review_required / not_verified / pending_review.
- 오늘 once-per-KST-day marker가 있어 실제 추가 대기는 정상. 250/run 및 2,500 전체 제한은 현재 병목 아님.
- Yahoo 상태 2026-11-04 22:40:12 UTC (11/05 07:40 KST), 72시간 gate 유지. 성공·no-cap checkpoint, 실패 뒤로 배치 및 가격 수집 FIFO/회전은 변경하지 않음.
- 저장 triage와 최신 master 재조합 queue는 완전히 같은 스냅샷이 아님: 기존만 CCEP/NEM/TRI, 재조합만 HONA. 기존 2,270 vs 재조합 2,268이나 미등록 적격 후보는 양쪽 모두 186. 소스 시점 차이를 숨기거나 관측 완료 상태로 최신 master 전체가 재검증됐다고 해석하지 않음. Yahoo status의 6,411 eligible/100%는 해당 생성 시점 집계임.

## 확인된 intake 버그와 최소 변경

기존 intake는 symbol만으로 등록 여부와 최종 dedup을 판단. 다른 시장의 같은 symbol을 신규 미국 상장과 혼동하며, append 뒤 기존 행을 삭제할 수 있음. 중복 queue 행이 head(slots)를 차지하여 실제 추가보다 추가 수를 크게 기록하고 다음 후보를 지연시킴. venue/빈 symbol gate도 없었음.

intake_large_cap_review_candidates.py만 변경: 정규화 symbol+exchange로 등록 비교, NAS/NYS/AMS 및 비어 있지 않은 symbol만 허용, 슬롯 선택 전에 pair 중복 제거. 기존 registry 행을 정규화하거나 삭제하지 않음. 현재 저장 데이터 중복은 0이므로 186이라는 현행 수치를 늘리는 수정은 아님.

회귀 fixture는 KRX 동일 symbol, 미국 이중 venue, active pair, 중복 큐, 빈 symbol/OTC, 정확한 추가/잔여 수, 연속 재생, 250/run·2,500 상한, 72시간 및 미래 시각/명시적 review-only gate를 검사. 수정 전 신규 회귀 2개 실패, 수정 후 통과.

## 검증 및 운영 경계

관련 테스트 71 passed / 8 subtests. 별도 discovery/reconciliation 및 rotation 실행: 30 passed / 11 subtests, Windows 파일 descriptor 오류 10 failures. 정확한 base에서 rotation만 재실행해 동일 10 failures / 6 passed / 11 subtests 재현. 최종 Linux 자동 CI는 PR에서 확인.

재현: PYTHONPATH=. python docs/evidence/reproduce_us_intake_20261105.py docs/evidence/us-intake-20261105.json
입력 해시와 후보 목록은 evidence JSON. 원본 CSV/JSON에는 쓰지 않음.

실제 후보/가격/승인/active 변경 없음. live KIS 호출·dispatch·rerun·workflow/cron/concurrency 변경·병합·main/통합 직접 변경·배포/비용/Secrets 변경 없음. 기존 10:30 KST 자동화 유지.

다음 고가치 작업: 정상 예약 intake 후 186개 잔여 감소를 저장 산출물로 확인. 독립 매핑 작업의 master 업종 코드 보존 제안은 별도 범위로 유지. 현재 후보 추가 한도를 늘릴 이유 없음.
