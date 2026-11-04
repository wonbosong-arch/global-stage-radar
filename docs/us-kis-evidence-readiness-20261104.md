# KIS 기반 미국 후보 오프라인 readiness

기준: `43bec1f4dc24a181138f01b1a4eb0b7865a7f03e` (#209 병합),
명시적 평가일 `2026-11-04`. main은 `997628e`, 변경하지 않았다.
착수 시 미국 후속 open PR은 없었으며 #205 head `7c9580e`의 파일은
CODEX_PROGRESS.md 외에는 겹치지 않는다. 공유 진행 파일에는 추가만 한다.
기존 작업 checkout은 수정하지 않고 독립 브랜치를 만들었다.

## 정책과 재사용

`audit_us_stage_readiness.build_audit(include_rows=True)`의 기존 OHLCV 검증,
완료 35주, 시장/업종 benchmark, 상대강도, 신선도 조건을 그대로 사용한다.
`kis_universe.normalize_market_cap_candidates`의 마스터 유형 및
ETF/우선주/워런트/권리/ADR 이상 징후 분류를 재사용한다.
새 수집기, 업종 proxy, Stage 계산 또는 운영 gate 우회는 없다.

증거 우선순위는 저장 `unranked_us_stock_master.csv`의 symbol/거래소/유형,
다음으로 `collect_stock_candidates`가 저장한 KIS ranking 출처와 정규화된
`discovery_security_type`이다. 후자는 기존 `master_instrument_type`에서
파생된다. Yahoo 출처나 가격만으로 신원을 추론하지 않는다.
partial unranked master에 없는 종목은 상장폐지로 판단하지 않는다.
파일 SHA256과 크기, 평가일, 후보별 사용 source와 판정을 JSON에 남긴다.
마스터 관측일이 없는 경우 날짜를 만들어 기록하지 않는다.

정상 KIS 근거는 `kis_master_consistent`라는 **오프라인 근거 상태**다.
`identity_status=verified`로 기록하지 않는다. 유효 가격은
`stored_valid_prices`이며 `provider_status=supported`와 별개다.
가격이 있어도 증권 유형은 별도로 판정한다. 가격 미확인/비정상은
`untested_or_invalid_prices`다. KIS 정보 충돌, 비일반주 징후, 중복 티커,
ADR 비율 미확인은 `review_needed`로 분리하며 검토가 곧 외부 조회를
뜻하지는 않는다. 일반 종목의 외부 신원 검증은 요구하지 않는다.

`offline_review_eligible`은 KIS 근거와 기존 데이터 조건을 갖춘
검토 준비 대상이며, 승인 추천이나 운영 편입 허가가 아니다.
시총 confirmed/estimate/missing, $1B threshold, 매핑 필드/제안/기록 상태,
pending/active 기록을 각각 출력한다. 제안 매핑을 assigned 필드로 복사하지
않으며 필수 benchmark 입력이 없으면 준비 대상이 될 수 없다.

## 고정 snapshot 집계

| 조건 | 수 |
|---|---:|
| US NAS/NYS/AMS 후보 | 1,897 |
| 정상 KIS 근거 / 근거 부족 / 추가 검토 | 1,848 / 31 / 18 |
| 저장 유효 OHLCV | 1,897 |
| 완료 주봉 35개 이상 | 1,845 |
| 시총 추정값 / 미상 / confirmed | 1,869 / 28 / 0 |
| 제안 업종 매핑 있음 | 271 |
| 기존 시총·가격·assigned benchmark 입력 조건 충족 | 105 |
| 위 조건과 정상 KIS 근거 교집합(검토 준비) | 72 |
| pending / 실제 bridge 편입 | 1,897 / 0 |

추가 검토 사유: 비일반주/펀드 이름 신호 15, ADR 비율 미확인 1,
ADR 마스터·비율 근거 부족 2. 이름 휴리스틱은 제외 확정이 아니라
검토 신호다. 31개 근거 부족 후보를 개별 외부 검증하지 않았다.
105개 중 72개 외의 후보는 근거 부족 30개와 검토 필요 3개다.

재현 명령:

```sh
python us_kis_evidence_readiness.py --as-of 2026-11-04 --data-dir data > report.json
python -m pytest -q tests/test_us_kis_evidence_readiness.py tests/test_us_stage_readiness_audit.py tests/test_approved_stock_universe.py tests/test_candidate_stage_integration.py
```

집중 회귀 35개 통과. 전체 Windows pytest는 동일한 깨끗한 base와
비교하고 최종 PR head의 자동 CI 결과는 PR에 기록한다.

## 다음 작업 및 승인 경계

우선 31개에 대해 기존 보존 KIS 마스터 근거를 연결하고 18개 이상 신호를
확인한다. 72개는 제안/할당 매핑의 근거와 시총 provenance/as-of, provider
지원 근거를 검토한다. 추정값의 관측 시각을 시총 기준일로 승격하지 않는다.
상태 전이는 현재 **없음**이다. 향후 상태 변경에는 source/hash, 이전/이후
상태, 근거/정책 버전, 검토자와 승인 기록이 필요한 별도 변경안을 준비한다.
기존 최종 approved_stock_universe gate와 candidate_stage_integration의
실패 격리는 유지한다. 운영 전 ADR 최종 gate 보완도 별도 검토가 필요하다.

이 PR 병합, 후보 승인/active, 운영 Stage 반영은 별도 승인 대상이다.
가격/후보 data, workflow/cron/queue, main/통합 branch, 배포/AWS/S3/Secrets/
비용은 변경하지 않는다. KIS live 호출, Actions dispatch/rerun 및
11월 5일 예약 검증 자동화 생성/수정도 수행하지 않는다.
