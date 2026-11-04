# 미국 Stage 재생 72개 가격 갱신 조사 (2026-11-04 KST)

기준: `data-validation-mvp` / `1839e63a537a9edc1973827958280848acc79bcc`.
시작 시 열린 PR 13개 확인: 미국 가격 갱신 중복 PR 없음. #205/#206 등 중국
작업은 제외. 앱의 최근 작업 목록에서 본 작업 외 실행 중 미국 작업 없음.
기존 중국 연구 checkout의 미커밋 변경을 보존하고 별도 worktree/브랜치 사용.

## 확인된 원인과 실제 경로

72개는 필터에서 빠진 것이 아니라 **900초 제한 회전수집의 미처리 대기열**에 있다.
API 실패라고 볼 근거는 없다. 11/2~11/4 KST 후보 가격 job 5개 모두 성공,
각 job의 오류 0개, 72개 응답 0개/이월 72개를 로그에서 확인했다.
성공은 부분 snapshot의 정상 저장을 의미하며 전체 갱신 완료를 의미하지 않는다.

| 실행일 KST | run / trigger | 요청 | 처리/응답 | 이월 | 실행 후 72개 순번 |
|---|---|---:|---:|---:|---|
| 11/02 | 41358104060 / schedule | 1426 | 362 | 1064 | 707~781 |
| 11/03 | 41537678032 / dispatch | 1676 | 189 | 1487 | 768~842 |
| 11/03 | 41539591042 / schedule | 1676 | 329 | 1347 | 439~513 |
| 11/04 | 41731232136 / dispatch | 1926 | 195 | 1731 | 494~568 |
| 11/04 | 41733324359 / schedule | 1926 | 368 | 1558 | 126~200 |

각 실행의 시작/종료 UTC, run/job URL, snapshot SHA256은
`docs/evidence/us-price-refresh-runs-20261104.json`에 보존했다.
순번은 각 결과 커밋 `7442fab`, `9dfcc10`, `f939610`, `7d6183d`, `e386e56`의
registry/universe/CSV/status를 `git show`로 읽고 기존 `collection_plan`을 재생했다.
현재 결과는 후보별 `docs/evidence/us-price-refresh-queue-20261104.json`에 있다.

- `candidate_collection.yml`: 후보 발견과 bounded intake. 가격 수집 자체가 아니다.
  신규 후보가 있으면 기존 후보 가격 workflow를 dispatch한다. 관측된 dispatch는
  이 기존 경로와 일치하며 이번 작업이 실행한 dispatch가 아니다.
- 후보 수 1426→1676→1926: 하루 250개 추가가 두 차례 있었다. 최초 무가격·미시도
  후보가 우선되어 기존 72개의 대기 순번이 밀리는 효과가 실제 관측됐다.
- `candidate_prices_manual.yml`: 이름에 Manual이 있지만 schedule도 있다.
  07:05 KST 월~토 cron과 discovery 후 dispatch가 같은 updater를 사용한다.
  updater는 pending_review이며 monitoring universe 밖인 후보만 처리한다.
- `collection_plan`: 최초 무가격·미시도 → 이전 pending/deferred 순서 → 나머지의
  last_attempt/last_success 순. 기존 가격 latest_date는 후순위 tie-break fallback이다.
  Stage 72개 전용 우선권/일일 갱신 보장은 없다. 실제 이월 tail은 줄고 있다.
- 현재 1926개 요청은 미국 1897개와 다른 후보 29개를 포함한다. 72개 전부 eligible,
  cooldown 제외 0, 직전 이월 72, last_attempt `2026-10-29T23:55:07.744550+00:00`.
  72개 모두 저장 latest_session `2026-10-29`, 운영 active 0 그대로다.
- `daily_prices.yml`: monitoring universe 92개 경로이며 이 72개 후보를 갱신하지 않는다.
  11/3~11/4 KST 예약 run 41537809892/41731268126은 취소. 11/4 push run
  41752574430은 성공. 이 사실을 후보 가격 실패와 혼동하면 안 된다.
- 기존 900초는 다음 종목 시작을 중단하는 예산이다. in-flight 요청은 bounded retry
  후 끝날 수 있다. US HTTP timeout20초, 페이지별 최대4회 시도/backoff,
  token 제한 재시도 경로가 있어 종목당 처리 시간은 고정이 아니다. 기존
  `history_pages_for_candidate`는 저장150행 이상이면1페이지, 짧은 이력5페이지,
  신규3페이지를 사용한다. 이번에 호출량/재시도/선택 정책을 바꾸지 않았다.

## 저장 시각과 거래일

최신 후보 status 시작 11/04 07:49:50 KST, 종료/updated 08:04:51 KST.
CSV/status 게시 커밋 e386e56의 author 시각은 11/04 08:04:56 KST.
이는 72개가 그 시각에 갱신됐다는 뜻이 아니다. 72개는 이전 이력을 보존했고
마지막 거래일은 모두10/29다. status의 fresh_data_symbols도 최신 거래일 보증이
아닌 유효한 비어 있지 않은 응답 목록이다. daily snapshot status는 별도로
11/04 10:19:21 KST이며 해당 커밋0b3d0e1 author 시각10:19:27 KST다.

현재 위치126~200과 관측 처리량189~368개/실행을 단순 적용하면 72개 전체
시도에는 **1~2회 성공 실행**이 필요하다(195개 처리라면 5개는 다음 회차).
새 후보 유입/큐 순서/오류/지연/취소가 없다는 조건부 추정이다. 예약1회/일만
고려하면 대략1~2 수집일이지만, discovery 추가 dispatch 횟수는 확정되지 않는다.
전체1926개 순환은 같은 가정에서 ceil(1926/368)~ceil(1926/189)=6~11회다.
이는 관측 범위 extrapolation이며 완료 날짜나 최신 봉 반환을 약속하지 않는다.
가격7일 gate는11/05까지 유효,11/06부터 만료된다. 성공 응답이 와도 저장 session을
다시 검사해야 한다. 현재 근거만으로72개 일일 신선도를 보장할 수 없다.

#207 queue:max는 이미 병합되어 있지만 관측한 해당 예약 실행들은 병합 전이다.
다음 예약 실행 전 정상 운영 효과는 실증 불가다. 기존11/05 10:30 KST 검증
자동화를 그대로 두었다. cron/shared concurrency/rate-limit/workflow diff 없음.

## 최소 변경과 재현

정상 회전수집을 변경할 근거가 부족하므로 collector/스케줄 대신 명시적 cohort용
오프라인 진단 CLI `candidate_refresh_queue_audit.py`를 추가했다. 기존
`us_stage_connection_plan.py` 출력/packet의 후보 목록과 `collection_plan`을 재사용해
현재 순번, 이월, cooldown/제외, 최종 저장 session,7일 gate 만료 경고를 출력한다.
명시적 cohort는 만료 후에도 남아 있어 Stage 준비 목록에서 사라진 후보를 놓치지 않는다.
명령은 JSON stdout만 쓰며 데이터/상태/네트워크를 변경하지 않는다. 자동 경고 발송이나
Actions 연결은 없다. 시총/매핑/KIS 신뢰/승인·active 정책을 변경하지 않는다.

```powershell
python candidate_refresh_queue_audit.py --cohort docs/evidence/us-stage-connection-20261104.json --as-of 2026-11-04 --observed-batch-size 189 --observed-batch-size 368
```

입력4개와 cohort SHA256을 출력한다. snapshot/status digest가 일치하지 않으면 중단한다.
Windows git autocrlf checkout에서는 CSV가 CRLF로 바뀌어 digest가 다를 수 있으므로,
증거 파일은 임시 디렉터리에 `git show 1839e63:data/<name>`의 원본 바이트를 저장하고
`--data-dir`로 지정하여 생성했다. 운영 무결성 검사를 완화하지 않았다.
cohort는 #211의72개 packet이며 새 cohort가 필요하면 기존 Stage generator로 별도
생성한다. 진단 출력은 운영 승인 payload가 아니다.

검증: 새 테스트3개는 대기 순서, cooldown, 운영 제외, 이월/응답 구분, gate 만료,
조건부 처리회수, 잘못된 처리량, CLI 무변경, digest 불일치 거부를 검증한다.
이력 보존/US Stage·KIS readiness와 함께23개 및6 subtests 통과.
로컬 UTF8 전체 pytest는 변경452통과/28실패/7skip, 정확한 기준 커밋은449통과/28실패/7skip.
FAILED/SUBFAILED 목록이 완전히 같고 새3개만 통과 수에 추가됐다. 양쪽162 subtests통과.
기존 Windows fsync 등의 실패는 이번 변경 범위 밖이며 최종 Linux Python/Unit CI는
Draft PR #212의 최종 SHA에서 별도 확인한다. CODEX_PROGRESS.md에도 결과를 보존했다.

다음 최소 승인: 이 진단 전용 Draft PR을 검토 후 통합할지 결정. 우선 기존 예약
실행 결과에서72개 실제 session 갱신을 확인한다. 일일 보장이 필요하면 이후 bounded
예약 quota와 기존 tail 공정성의 tradeoff를 별도 설계/승인해야 한다. workflow 변경,
live KIS 호출/dispatch/rerun, 운영 활성화·배포, main, AWS/S3/Secrets/권한/비용,
보호 브랜치 병합은 이번 작업에 포함하지 않았다.
