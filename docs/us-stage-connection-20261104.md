# 미국 72개 Stage 연결 준비 — 2026-11-04

기준: data-validation-mvp `9416654f90de2b01e2141050a5c6b246f8404222` (#210 병합).
독립 브랜치 `feat/us-stage-connection-20261104`. 사전 GitHub branch/열린 PR,
최근 채팅, worktree/dirty 파일 확인. 중국 작업 checkout의 미커밋 가격 파일과
#205/#206 등 별도 작업은 변경하지 않았다. 통합 merge HEAD의 자동 Python CI는
사전 확인 당시 실행 중이었다. main은 읽기/쓰기 대상이 아니다.

## 실질적인 변경

기존 감사는 `assigned_stage_data_inputs_available` 등 boolean까지만 제공했다.
새 `us_stage_connection_plan.py`는 그 감사와 KIS 판정을 재사용하여 72개를 선택하고,
실제 registry 입력 및 현재 `stock_mapping.proposed_stock_mapping` 입력을 각각
기존 weekly/RS/classify_stage 엔진으로 실행한다. 주봉을 symbol별로 캐시하고
품질/150일/완료35주/MA30/4주기울기/동일 주봉 RS/7일 freshness를 검증한다.
중복·미래값·비정상 OHLCV·자기 benchmark·누락 benchmark는 label을 보류한다.
active/verified/supported 상태를 흉내 내는 데이터는 만들지 않는다.

원본 registry와 승인 bridge는 수정하지 않았다. 결과는 종목별 검토 packet이며
운영 universe로 로드하는 경로나 승인 적용 명령이 없다. 기존 `app.py`의 종목
후보/운영 분리와 `candidate_stage_integration.py`/`approved_stock_universe.py`의
명시적 active·identity·provider gate를 유지한다. 현재 pending 원본을 실제
bridge에 전달한 결과 추가 0, 오류 0이다.

## 결과와 남은 조건

| 근거 | 72개 분류 |
|---|---|
| 보존 KIS 마스터/가격 | KIS 정상 근거 72; 명백한 유형/중복/venue 이상 0 |
| venue | NAS 1 (IBKR), NYS 71, AMS 0 |
| 선택 시총 | 추정 72, confirmed 0; $1B threshold 통과 72 |
| 시총 provenance | 선택값과 URL이 저장 Yahoo review 행에 유일하게 일치 72 |
| 시총 기준일 | as-of 없음 72 (`not_provided_by_yahoo`); 관측 UTC 10/26–10/27 |
| 매핑 | assigned/현재 suggestion의 업종·유형·benchmark 일치 72, 차이 0 |
| 저장 proposal | 현재 suggestion과 차이 0; 전부 first_pass_review_required |
| benchmark 데이터 | SPY 및 10개 업종 ETF에 저장 가격/완료35주/정렬 RS/신선도 충족 |
| 가격/엔진 | 전부 완료30/35주 통과; 종목 완료41–62주; 두 매핑 재생 모두 72 성공 |
| 운영 편입 | 0; 상태 승격/운영 반영 없음 |

시총 `fetched_at_utc`는 **관측 시각**이며 as-of로 사용하지 않는다. 선택된 secondary
USD billions → discovery USD fallback 순서는 기존 bridge와 같다. 값/URL이 다른
관측 자료에서 시간을 가져오지 않으며 중복 일치는 ambiguous로 남긴다. 기존
verified 표시도 recorded로만 표현하고 도구가 formal verification을 부여하지 않는다.
후속 Yahoo supplement/batch status는 입력 hash로 보존한다. 선택된 72개의 직접
연결 근거는 별도의 `yahoo_large_cap_candidate_review.csv`이며 최신 batch 완료가
이들 선택값을 갱신했다는 뜻은 아니다. 시총 기준일 부재는 추정 screen의 한계이며,
현 정책에서 confirmed cap으로 재조사해야만 screen을 통과하는 추가 gate는 아니다.

업종별: Industrials19, Financials18, Energy11, Information Technology5,
Materials5, Consumer Discretionary5, Health Care4, Real Estate2, Utilities2,
Consumer Staples1. 제안 출처는 repo의 수동 curated ticker/sector/proxy 규칙이다.
assigned 필드의 원래 승인 근거는 인증되지 않았으며, 같은 코드에서 나온 제안과
일치하는 것은 독립적인 적절성 검증이 아니다. SPY는 US-listed-market fallback이다.
국외 발행사 보통주도 포함될 수 있으므로 발행국/상장시장 proxy 정책의 적절성은
**매핑 검토**에서 판단한다. KIS 정상 신원에 대한 종목별 외부 재조사는 요구하지 않는다.
benchmark metadata는 `monitoring_universe.csv`: SPY/XLB/XLE/XLF/XLI/XLK/XLP/
XLRE/XLU/XLV/XLY, 모두 기존 active KIS ETF이나 sector_source는 비어 있다.
이들의 기존 active 표시는 이번 후보에 대한 mapping approval을 증명하지 않는다.

종목 최신 저장 session은 모두 **2026-10-29**, 최신 수집 시도(11/03 23:04 UTC)의
fresh_data_symbols에는 이 72개가 없다. 저장 데이터는 11/04 기준 6일 경과하여 현재
7일 gate를 통과하지만, 추가 수집 없이는 **11/05까지만** 해당 gate를 통과한다.
전체 완료 주봉 수만으로 현재 신선도를 보증하지 않는다. 새로운 live KIS 호출은 0.
이전 수집 성공/저장 가격과 현재 계정 live 지원 검증을 구분한다.

오프라인 heuristic 재생 결과: Stage2 후보25, Stage2A5, 중립35, 하락관찰7.
이는 적절성이 미승인인 매핑을 사용한 검토용 출력이며 운영 Stage/신호가 아니다.

실질적 미완료 gate는 (1) 업종 및 SPY/업종 ETF proxy 적절성 검토/승인 기록,
(2) KIS 보존 근거에 따른 identity/provider 명시적 상태 결정과 별도 activation 승인,
(3) 실제 사용 시점의 가격 freshness 재확인이다. 시총 추정값이나 필드 존재만으로
verified/approved를 부여하지 않는다. 다음 단일 최소 승인 권고는 **Draft PR #211을
data-validation-mvp에 병합하는 것**이다. 활성화나 live 호출을 그 승인에 포함시키지
않는다. 이후 이72개의 매핑 적절성 검토 결과/근거는 별도 변경안으로 남겨야 한다.

## 재현과 검증

`python us_stage_connection_plan.py --as-of 2026-11-04`

기본 동작은 저장 파일 읽기와 JSON stdout뿐이다. 평가일은 필수이며 원본 출력/수정,
네트워크 요청, wall-clock 기반 자동 승인, dispatch/rerun, workflow/queue 변경이 없다.
`docs/evidence/us-stage-connection-20261104.json`은 후보별 선택 cap 값/출처/관측일/
as-of, 매핑 분류, 완료주봉/날짜, 요약 gate 및 입력14개 SHA256을 포함한다.
전체 packet은 CLI로 재생성하며 full_replay_sha256으로 비교한다. 상세 출력은
checkout 밖 `us-stage-connection-final-replay.json`에도 보존했다. 이 hash와 평가일이
같은 snapshot에서 재현해야 한다.

집중 테스트 및 Windows clean baseline, 최종 remote HEAD 자동 CI 결과는
CODEX_PROGRESS.md와 Draft PR에 기록한다. 11/05 10:30 자동화 변경/중복 생성 없음.
data 원본·main·통합 브랜치 직접 변경·병합·운영 배포·비용/Secrets 변경 없음.
