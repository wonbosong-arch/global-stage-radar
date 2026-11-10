# Chromium ticker alignment browser check — 2026-11-11

- Fresh integration base e72793c7403c4395ce76720766bf11aba3593f5f.
- Reproduced the exact PR #235 failure with Chromium 158.0.8127.18.
  Computed justify-content is flow-start for authored flex-start, while ticker
  text-align is left and glyph offset remains exactly 10px. Chromium 157
  returns flex-start. This is a browser serialization change.
- Accept both computed values and inspect the visible ticker button. Retain
  the actual glyph-position, numeric/header alignment, click, sorting,
  navigation, favorites, scrolling, and 3x3 chart regression checks.
- The full local navigation run then reached a separate transient grid-footer
  failure. Its captured DOM contains data-stale=true elements from the previous
  list inside the new pager. Wait for these elements to clear before measuring
  footer alignment, retaining the same geometric assertions.
- CI also captured the table resizing from the previous 33% width to the
  requested 45% between geometry reads. Wait for the active sidebar rerun to
  finish before beginning the table measurements. Local Chromium 158 full
  navigation and synthetic Nasdaq approval/recovery checks passed.
- Local before-fix Chromium 158 run fails at the original assertion. Full
  updated browser workflow and exact-head Python CI are pending this checkpoint.
- Next: pass focused PR CI, merge into data-validation-mvp, update #235 to
  latest integration, verify synthetic Nasdaq upload and all CI before merging.
  Hosted revision and original production store failure remain unverified.

# Nasdaq monthly official-CSV pilot — 2026-11-06

- Fresh base7fdd875; main997628e unchanged. Default branch is currently
  data-validation-mvp; no setting changed. #219 Draft7a245cf separate; #216/217
  and #206 unchanged. Related other Codex tasks idle. Isolated feature checkout.
- Live official page/Download CSV browser automation succeeded once: 6,952 rows,
  11 fields, unique6952, native complete6300. Supplied /mnt/data path absent;
  accessible Downloads copy hash matches prior c339fd6 (6,925 rows). Separate
  hash-bound private replays both completed: KIS matches2319/2334; eligible1341,
  Stage2 401/Stage2A106. Source effective date unknown; no live KIS or activation.
- Implemented official-button collector, max2 timeout-only attempts, denial stop,
  schema/row/coverage/numeric/alias gates, private hash-verified immutable generations,
  atomic current pointer, nonzero failure with last-good fallback, existing offline
  KIS/Stage pipeline. Manual and automated provenance remain distinct.
- Manual-only false-input workflow; no schedule, data upload/commit/cache/artifacts,
  secrets or persistent runner storage. Monthly cron is an unapplied doc proposal.
  Cross-run GitHub persistence/publication needs a later approved private delivery
  connection. Existing 07:00 KIS workflows and #219 UI are untouched.
- Final focused40 passed/55 subtests; compile and all15 workflow YAMLs pass.
  Full Windows checkpoint509 passed/27 failed/6 skipped/276 subtests. Unchanged
  base reproduces all27 failures in three modules; failure identifiers exactly
  match. Two later retry/CLI tests and final provenance metadata are covered by
  final focused checks and will be included in exact-head full Linux CI.
  New Python collector headless/GitHub live acquisition not executed; successful
  live evidence is the browser tool's actual official-button download.
- Next: finish final-code actual replay, preserve source on remote
  feature branch, create focused Draft PR to data-validation-mvp and inspect final
  head automatic CI. No merge/deploy/schedule/data activation is authorized.

# 미국 ranking 수집 상태 보완 — 2026-11-04

- 기준 20bfde2, 독립 브랜치 fix/us-ranking-coverage-20261104. main/통합 직접 수정 없음.
- 완료: 기존 PR/채팅/CI/구현과 저장 데이터 확인; 종료 사유·고유/중복 수 진단,
  total과 독립적인 partial 경고, symbol 정규화 및 회귀 4개 추가.
- 신규 회귀는 수정 전 기준에서 실패, 수정 후 집중 68 passed / 17 subtests passed.
- 로컬 전체 unittest 353 tests: Windows fsync 오류 26개/skip 1개. 전체 pytest는
  428 passed / 28 failed / 7 skipped / 156 subtests passed. 실패 4개 모듈을 수정 전
  20bfde2에서 재실행해 동일 28개 실패 및 동일 실패 ID 집합을 확인했다.
- 원격 구현 커밋 2fe167d, Draft PR #208, 대상 data-validation-mvp. 로컬 4b9511a와
  원격 트리 SHA 1d46fb9 일치. GitHub 연결 API로 보존(HTTPS schannel 자격증명 오류).
- 다음: 최종 문서 커밋의 자동 Python/Unit CI 확인. live KIS/dispatch/rerun 없이 자연 실행 결과로
  unique 수를 비교. KEYB 계약 및 정확한 제공자 모집단은 미확정.
- 운영 반영/데이터 변경/활성화/설정 변경/병합 없음. 11/05 자동화 재생성 없음.
- 상세 수치·원인·효과 기준: docs/us-ranking-coverage-20261104.md.

# UI/UX 개편 작업 보존 기록

기록일: 2026-10-29 (UTC)
저장 브랜치: `feat/analysis-convenience-state`
보존 커밋: `5c1db00930d8c6d65812fcb27ea75f126a35d6b7` (원격 푸시 성공)
보존 Draft PR: [#176](https://github.com/wonbosong-arch/global-stage-radar/pull/176), 대상 `data-validation-mvp`, 미병합
기준 통합 커밋: `ab807f3` (`data-validation-mvp`, PR #175 병합 결과)

## 작업 원칙

- `AGENTS.md`, `CODEX_PROJECT_HANDOFF.md`를 읽고 단계별 기능 브랜치/PR로 진행했다.
- `main` 및 `data-validation-mvp`에 직접 기능 커밋하지 않았다. 아래 완료 단계는 PR을 통해서만 통합했다.
- 수집 스케줄, KIS API 및 Stage 판정 로직은 변경하지 않았다.
- 사용자의 작업물 보존 지시에 따라 추가 개발을 중단하고 현재 4단계 변경을 보존한다.
- `AGENTS.md` 원칙 보완은 다음 작업으로 남겼으며 이번에는 수정하지 않았다.

## 완료 및 통합된 단계

1. [PR #173](https://github.com/wonbosong-arch/global-stage-radar/pull/173): 고정 제목, Stage 2 기본 진입의 4개 탭, 독립적인 탭 상태 복원, 한 줄 데이터 상태, 접힌 데이터 관리 패널. 긴 경고/누락/검토/개발 정보는 삭제하지 않고 이동했다. 큰 app.py 변경은 주로 컨테이너 내부로 기존 코드를 들여쓴 것이다. 최종 CI 4개 통과 후 병합. 로컬 pytest 369개 및 하위 검사 98개, unittest 284개 통과. 데스크톱/모바일과 고정 헤더 실제 브라우저 검증을 수행했다.
2. [PR #174](https://github.com/wonbosong-arch/global-stage-radar/pull/174): 업종·종목·Stage 2의 간결한 클릭 목록과 큰 차트, 후보 목록 상위 25개 제한 제거, 반복 설명/큰 지표 축소. 새 표 모드는 추가하지 않았다. 최종 CI 4개와 로컬 pytest 370개/하위 검사 98개 통과 후 병합. 1440/800/390px 검증. 현재 활성 데이터에 승인된 개별 종목이 없어 종목 배치는 명시적 가상 데모로 검증했다.
3. [PR #175](https://github.com/wonbosong-arch/global-stage-radar/pull/175): 신규 Stage 2 필터(이전 주 가드 유지), 30주선 거리 정렬, 후보 기본 절대 수익률 정렬, 필터 밖 선택 보존, 국가→업종→종목 경로와 복귀. 최종 CI 4개 통과 후 병합. 관련 6개 테스트 및 실제 브라우저의 빈 검색 결과 선택 유지·국가/업종/종목 왕복 검증 통과. 이전 전체 로컬 실행의 정렬 옵션 고정 단언 1개를 새 옵션에 맞게 수정했고, 수정 후 관련 검사 및 최종 CI가 통과했다.

## 이번에 보존하는 4단계 변경 (미병합 / 검증 진행 중)

- `analysis_preferences.py`: 허용된 UI 필드만 URL에 저장/복원하는 코드. 탭, 데이터 모드, 종목, 보기 모드, 일봉/주봉, 그리드 페이지, 목록 너비를 대상으로 한다. 인증 상태는 허용하지 않는다. KIS 모드는 새 연결에서 기존 인증이 필요하다. CSV 파일은 새로고침 후 재업로드가 필요할 수 있다.
- `list_keyboard.js`: 목록 클릭/포커스 후 ↑/↓로 항목을 바꾸는 브라우저 처리. 입력 필드의 방향키는 가로채지 않는다.
- `app.py`: 별표 관심 추가/해제, 목록의 별표, 관심 목록 필터, 사이드바 임시 관심 목록, 30~45% 목록 너비 조절, UI 설정 저장/복원 연결, 데이터 모드에 맞는 상태 요약.
- `ui_shell.py`: 관심 버튼 상태를 위젯 복원 대상에서 제외, 키보드 컴포넌트 연결, 상단 선택기를 탭처럼 표시하는 스타일.
- `chart_interactions.js`: 선형/로그 선호를 브라우저 sessionStorage에 저장하는 코드.
- `.github/workflows/chart-browser.yml`: 새 UI 파일 변경에도 브라우저 검사를 실행하도록 경로 추가. 수집 워크플로는 수정하지 않았다.
- `tests/test_analysis_preferences.py`, `browser_checks/check_dashboard_navigation.py`: URL 입력 제한, 관심 목록, 탭/새로고침 복원, 키보드/로그 복원 등의 검사 추가.

위 기능은 코드가 작성된 상태이며 모두 완료/검증된 것으로 간주하면 안 된다. 현재 브랜치는 Draft PR로 보존하고 최종 검증 전 병합하지 않는다.

## 4단계 테스트 상태 및 알려진 실패

- 관련 pytest 실행: 5개 통과 (`/tmp/prefs-focused.log`, 약 40초). 관심 목록, 탭 상태, URL 복원과 입력 제한을 포함한다. 이후 추가된 너비 URL 복원 및 일부 배치/브라우저 검사 변경은 이 실행에 포함되지 않았다.
- 최신 전체 pytest는 보존 시점에 실행 중이다 (`/tmp/prefs-full.log`). 완료 통과로 보고하지 않는다. 세션이 끝나면 결과가 사라질 수 있으므로 다음 작업에서 다시 실행할 것.
- 최신 실제 브라우저 검사는 실패했다 (`/tmp/preferences-browser.log`). 국가 히트맵 데스크톱 검사에서 첫 두 타일이 같은 열에 나타나 `second.x > first.x + 10` 단언이 실패했다. 관측된 타일 폭은 230px였다. 목록 너비 설정 도입 이후 기본값/컨테이너 실제 폭 및 CSS 최소 타일 폭을 확인해야 한다. 원인은 아직 확정하지 않았다.
- 위 실패는 키보드·관심 목록·실제 새로고침 복원 검사보다 앞에서 발생했다. 따라서 해당 최신 브라우저 시나리오들이 통과한 것으로 보고하면 안 된다.
- `git diff --check`는 보존 시점에 통과했다. 마지막 변경 뒤 전체 CI/브라우저 검증은 완료되지 않았다.
- pandas/Streamlit 기존 경고가 있다. 경고 수를 통과 여부와 혼동하지 말 것.

## 다음 작업

1. 브랜치와 원격 PR 상태를 확인하고 이 기록 및 `AGENTS.md`, `CODEX_PROJECT_HANDOFF.md`를 다시 읽는다.
2. 목록 너비의 초기 값(의도 33%)과 실제 브라우저 폭을 확인해 히트맵 회귀를 해결한다. 다른 너비에서 한 열이 타당한 경우에도 테스트를 무조건 완화하지 말고 요구한 데스크톱/모바일 배치를 실제로 확인한다.
3. 키보드 반복 이동 시 스크롤 유지, 관심 추가/해제·필터·전역 관심 목록 이동, 탭 왕복, 너비 조절, 실제 페이지 새로고침과 선형/로그 복원을 브라우저에서 끝까지 검증한다.
4. URL 복원은 인증/임의 세션 키를 허용하지 않도록 유지한다. 관심 목록은 현재 Streamlit 세션 내 임시 저장이며 서버 세션 종료/새 연결에서 유지된다고 보장하지 않는다.
5. 관련 pytest, 전체 pytest/unittest, 기존 4종 차트 검사, 대시보드 브라우저 검사를 실행한다. 최신 PR head SHA에서 모든 CI 통과 및 전체 diff 확인 후에만 data-validation-mvp에 PR로 통합한다.
6. 전체 개편 완료 후 단계별 PR·검증·미완료 사항을 한국어로 보고한다. `AGENTS.md` 보완은 별도 다음 작업이다.

## 배포 및 보존 범위

- 운영 Streamlit의 실제 소스 브랜치/배포 화면 반영은 확인하지 않았다. 로컬/CI 성공이나 통합 브랜치 병합을 운영 배포 확인으로 표현하지 말 것.
- 커밋 대상으로 소스, 회귀 검사, 이 문서를 명시적으로 지정했다. `__pycache__` 등 생성물과 로컬 scratch 스크린샷/로그는 GitHub 저장 대상이 아니다.
- 이전 작업의 `validated-handoff-draft` stash는 그대로 보존하며 이번 기능 커밋에 섞지 않았다.
- 4단계 소스/검사/이 문서는 원격 브랜치에 푸시됐고 Draft PR #176 생성에 성공했다. 후속 작업은 해당 브랜치와 Draft PR을 기준으로 시작한다. 이 원격 보존 결과를 기록하는 추가 문서 커밋도 함께 푸시한다.

## 개발 지침 및 진행 기록 체계 보완 (2026-10-29)

- 작업 브랜치: `docs/long-running-work-principles`, 기준 `data-validation-mvp`.
- 완료: 기존 `AGENTS.md`를 읽고 원문을 그대로 유지한 채 '장시간 작업 및 사용량 한도 대응 원칙' 10개 항목을 추가했다. 기능 분할, 독립 커밋, 중간 원격 푸시, 진행 기록, 재개 전 확인, 중복 작업 방지, 저장 실패 보고, 보호 브랜치 및 PR 절차를 명시했다.
- 완료: Draft PR #176에 보존한 기존 `CODEX_PROGRESS.md`를 문서 전용 브랜치로 가져와 이전 진행 기록과 미완료 UI 작업을 보존했다. 위의 UI 작업/테스트 상태는 당시 보존 시점의 기록이며 이번에 앱 개발을 재개한 것이 아니다.
- 테스트/검증: 기존 통합 브랜치의 `AGENTS.md` 전체 원문이 수정본의 접두부로 그대로 유지되는지, 새 항목이 1~10까지 순서대로 존재하는지, 변경 파일이 두 Markdown 문서뿐인지, 공백 오류가 없는지 확인한다. 앱 코드·수집·KIS 로직을 수정하지 않아 앱 테스트는 새로 실행하지 않는다.
- 미완료: 문서 PR의 검토/통합. UI 4단계의 기존 미완료 기능과 브라우저 실패는 위 기록 및 Draft PR #176에 남아 있다.
- 다음 실행: 문서 PR을 확인한다. UI 작업을 재개할 때는 원격 브랜치/커밋과 이 기록을 먼저 읽고, 문서 PR이 먼저 병합되었다면 최신 통합 문서를 보존하며 #176을 갱신한다. 이미 완료된 1~3단계를 반복하지 않는다.
- 이번 변경은 개발 지침과 진행 기록에만 한정하며 `main`에는 변경하지 않는다.
- 원격 보존 결과: 문서 변경 커밋 `abc83de` 푸시 성공. [문서 PR #177](https://github.com/wonbosong-arch/global-stage-radar/pull/177)을 `data-validation-mvp` 대상으로 생성했다. 원문 유지/10개 항목/문서 전용 변경/공백 검증을 모두 통과했고 PR은 미병합 상태다.

## 재개 (2026-10-29)

- 기존 커밋/PR/기록을 확인했다. 완료된 1~3단계는 반복하지 않는다.
- #177은 기존 원문을 보존하는 원칙 보완이며 CI 통과 확인 후 통합했다. #176에 최신 지침과 진행 기록을 포함하면서 문서 충돌은 기존 기록의 상위 집합을 보존해 해결했다.
- 보존 당시 전체 테스트의 실제 종료 결과는 374개 및 하위 검사 98개 통과였다. 브라우저 실패는 여전히 미해결 상태에서 재개하며 최종 결과와 혼동하지 않는다.
- 공식 표시 이름을 Global Stage Radar로 변경 중이다. 저장소/배포 URL/데이터 경로/설정 식별자는 변경하지 않는다.
- 재개 후 전체 로컬 pytest 374개/하위 검사 98개, unittest 284개, 일봉/주봉/compact/review 실제 차트 4종 검사가 통과했다.
- 기본 목록 너비를 명시적 33%로 설정했다. 이전 히트맵 열 배치 실패는 이 변경 후 재발하지 않았고, 실제 방향키 선택 검사까지 도달해 통과했다. 관심 필터 검사는 숨겨진 input 대신 사용자가 누르는 레이블을 사용하도록 갱신했다.
- 표시 이름과 브라우저 제목 회귀 검사를 추가했다. 현재 브라우저 전체 검사는 접힌 화면 설정 패널을 열어 너비 조절까지 포함하는 시나리오로 재실행 중이며, 최신 전체 CI 완료 전까지 #176을 완료로 간주하지 않는다.

## 재개 후 4단계 검증 결과

- 실제 Chromium 전체 시나리오 통과: 1440/800/390px 배치, 고정 헤더/가로 스크롤 탭, 목록 너비 33→45% 조작, 히트맵, 국가→업종→종목 왕복, 필터 밖 선택 보존, 방향키 선택, 별표 관심 필터, 실제 reload 후 탭·종목·일봉·로그 복원. 그리드 페이지 이동의 main scroll 차이는 0px였다.
- 보존 시점의 히트맵 실패는 기본 목록 너비 33% 명시 후 해결했다. React/네이티브 입력을 직접 누르는 검사 방식은 레이블/접근성 역할로 변경했다. 이 후 전체 브라우저 검사가 통과했다.
- 로컬 전체 pytest 374개/하위 검사 98개 및 unittest 284개, 기존 차트 4종 검사 통과. 최종 PR head의 CI는 원격 중간 푸시 후 확인한다.
- 완료한 1~3단계 및 개발 원칙은 재작성하지 않았다. 기존 #176을 검증 완료 PR로 갱신하며, main·수집·KIS·데이터 경로는 변경하지 않는다.
- 남은 운영 확인: hosted Streamlit의 실제 배포/소스 브랜치/화면 반영. 로컬·CI 통과를 배포 확인으로 간주하지 않는다. KIS 재인증, CSV 재업로드 가능성, 관심 목록의 세션 한정 저장은 의도된 제한이다.

## 헤더·차트 UI 통합 수정 (진행 중)

- #176 통합 결과를 기존 작업 브랜치에 포함했고 완료 기능을 재작성하지 않는다.
- Streamlit 기본 헤더 높이로 고정 오프셋과 본문 예약 공간을 계산하고, 실제 React Aria 표시 원형만 숨기는 폴더 탭 스타일을 적용했다. 제목/탭 경계 검사를 추가해 간격을 보완 중이다.
- Linear/Log 설정을 Plotly 캔버스 밖의 반응형 상단 영역으로 옮겼다. 주기 명칭은 '차트 주기', 선택 버튼 스타일은 공통 CSS로 통일했다.
- 표시용 일봉은 SMA50, 주봉은 기존 SMA30이다. 검토 차트도 적용하며 Stage 엔진은 바꾸지 않았다. 범례를 아래로 옮겨 오른쪽 가격 영역을 확보했다.
- SMA 수치 회귀 3개/하위 검사 8개 및 외부 설정 적용 후 차트 4종 브라우저 검사 통과. 새 제목 경계/외부 도구 모음 위치 검사와 전체 회귀/CI는 진행 중이다.
- 데이터 수집/KIS/스케줄/main 변경 없음. 다음 작업: 최신 데스크톱·모바일 브라우저 전체 검증, 전체 테스트 및 정확한 PR head CI 확인 후 통합.
- 추가 검증: 외부 가격 축 설정이 Plotly 캔버스 위에 위치하고 오른쪽 여백이 35px 미만인 검사, 실제 SMA 범례 검사를 포함한 차트 4종이 통과했다. 첫 화면의 JS 초기화 전에도 제목이 기본 헤더 아래에서 시작하도록 CSS 기본 padding도 확보했다. 최종 헤더/탭 경계 및 전체 CI 결과 확인은 계속 진행한다.
- 전체 로컬 pytest 375개/하위 검사 98개 통과. 대시보드 브라우저 흐름은 마지막 가로 스크롤 단언까지 도달했으며, 원형 제거 후 탭이 390px에 모두 들어가 기존 '반드시 overflow' 단언이 더 이상 맞지 않았다. 390px에서는 잘림 없이 맞고, 더 좁은 320px에서 실제 가로 스크롤을 검증하도록 검사 폭을 변경했다. 기능을 완화하거나 숨긴 것이 아니다.
- 최신 전체 대시보드 Chromium 시나리오 통과: 초기/스크롤 후 제목 경계, 원형 없는 폴더 탭, 1440/800/390px 배치와 320px 가로 탭 스크롤, 기존 목록/그리드/탭/국가 왕복/새로고침 및 0px 그리드 스크롤 유지.
- 3×3 차트에도 하단의 정확한 이동평균 범례를 표시했다. 최종 커밋의 원격 CI를 확인한 뒤에만 PR #178을 통합한다. 운영 Streamlit 배포/실제 소스 브랜치는 미확인이다.
- 원격 브라우저 CI가 탭 클릭 직후 서버가 URL 상태를 저장하기 전에 reload하던 경합을 검출했다. 새로고침 검사는 실제 URL에 종목 탭/일봉 저장이 완료된 것을 먼저 확인하도록 강화했다. 상태 보존 검증을 생략하지 않으며, 최종 CI를 다시 확인한다.

## 차트 사용성 3건 수정 (진행 중)

- 별도 브랜치 fix/chart-padding-period-scales, 최신 통합 기준으로 작업. 수집/KIS/스케줄/Stage 판정/main 변경 없음.
- 공통 가격·거래량 축 기본 끝에 4봉 간격 여백을 추가하고 왼쪽 150봉 시작은 유지했다. 브라우저는 최신 봉이 보이는 경우 부족한 여백만 보완하며 과거 구간을 강제로 이동하지 않는다.
- 주봉 기본 로그/일봉 기본 선형, 위젯+주기별 sessionStorage로 수동 선택을 분리했다. 기존의 주기 공통 저장 키는 새 주기 기본값에 덮어씌우지 않는다.
- Stage 2와 모든 자산 그리드의 기존 페이지 키/콜백을 유지해 9개 차트 아래 중앙으로 이동했다. 페이지 전환 동안 그리드 높이/스크롤을 유지하는 브라우저 처리를 추가했다.
- 관련 Python 5개 및 하위 검사 8개 통과. 전체 및 실제 브라우저 검증은 진행 중. 브라우저 검사는 일봉 실제 렌더 완료 후 수동 축을 변경하도록 동기화를 보완했고, 과거 이동은 실제 마우스 드래그로 검사한다.
- 다음: 주기별 설정 왕복/최신 봉·거래량 여백/하단 페이지 스크롤·주기 유지, 전체 CI 확인 후 PR 통합. 운영 배포 미확인.
- 검증 결과: 전체 로컬 pytest 376개/하위 검사 98개 통과. 갱신된 그리드 AppTest는 일봉 선택→다음/이전 페이지 왕복 보존과 첫/마지막 페이지 비활성화를 포함해 통과했다.
- 실제 차트 4종 + 동일 위젯 주기 왕복/수동 설정/실제 과거 드래그 검사가 통과했다. 하단 페이지 실제 브라우저 이동은 main scroll 0px로 기존 탐색/모바일/상태 복원까지 통과했다.
- 모바일의 그리드 하단 영역 폭과 버튼 비활성화 검사도 추가했다. 정확한 최신 head에서 전체 CI를 확인한 뒤에만 PR #179를 data-validation-mvp에 통합한다. 운영 배포는 미확인이다.

## 후보 가격 순환 수집 안정화 (2026-10-30)

- 브랜치: `fix/candidate-collection-rotation-20261030`, 최신 `data-validation-mvp` 기준 `4608a45`. 원격 접근/열린 PR을 확인했고 #181(중국 식별), #182(활성 스냅샷 상태 JSON 격리)의 변경은 복제하지 않았다. main/통합 브랜치에 직접 변경하지 않는다.
- 완료: 기존 후보 상태 JSON에 종목별 시도/성공/경로/실패 상태를 저장하고, 최초 미수집→미처리 꼬리→오래된 시도 순으로 순환한다. 반복 실패가 최초 미수집 우선순위를 계속 차지하지 않는다. 명확한 미지원 경로만 30일 대기하며 경로 수정/기간 만료 시 재시도한다.
- 완료: v2 상태에서 실제 오류와 시간 제한 보류를 분리하고 dashboard/report는 기존 상태도 해석한다. Requested/Attempted/Succeeded/Deferred/Failed/Preserved/Missing/Skipped, 수집 시작/종료, 체크포인트 상태를 구분한다.
- 완료: 기존 모든 정상 이력 병합, 응답 OHLCV/심볼/유한값 검증, 중복 제거, 25종목 체크포인트, CSV·상태 사전 검증/임시 저장/교체 실패 복구, CSV SHA 검증을 추가했다. Actions 실패 기록은 순환 상태와 저장 커버리지를 보존한다. 자세한 계약/복구 한계는 `CANDIDATE_COLLECTION_ROTATION.md`에 기록했다.
- 운영 데이터 재확인: 1,426개 대상, 이력 없음 250개/150봉 미만 24개/150봉 이상 1,152개. 실제 CSV 347,904행을 임시 복사해 API 실패+시간 제한을 모의 실행했고 347,904행·1,176종목·중복 없음·기존 이력 보존을 확인했다. 원본 데이터 변경/실제 KIS 호출 없음.
- 검증 중간 결과: 관련 pytest 36개/하위 검사 15개 통과, 전체 unittest 296개 통과, 전체 pytest 중간 코드 386개/하위 검사 113개 통과, 차트 4종 Chromium 통과. 최종 코드 전체 검사와 원격 CI는 이후 결과를 별도 기록한다.
- 브라우저 초기 헤더 위치 검사가 렌더 준비 전 측정으로 실패했다. 기준 브랜치에서는 통과했고 현재 변경에서는 같은 레이아웃이 안정화된 뒤 정상인 것을 확인했다. 기존 위치 단언을 유지하면서 헤더 컴포넌트의 첫 레이아웃을 기다리도록 검사만 보완했다. 전체 탐색 재검증 중이다.
- 기존 UTC cron은 일일 KIS `0 22 * * 0-5`, 후보 후속 `5 22 * * 0-5`로 한국시간 월~토 07:00/07:05에 맞다. 일정·API 요청 제한·Stage 판정·수동 검토/중국 비활성 정책을 변경하지 않았다.
- 남은 작업: 최종 전체 테스트/탐색, #182와의 임시 통합 호환성, Draft PR 및 정확한 head CI 확인. 병합/운영 수집 성공은 확인하지 않았다. 하드 runner 종료 시 로컬 체크포인트가 원격 커밋 전에 소실될 수 있으나 이전 원격 스냅샷은 유지된다.
- 원격 보존: 구현 커밋 `ee6f1f7` 푸시 및 Draft PR [#183](https://github.com/wonbosong-arch/global-stage-radar/pull/183) 생성 완료, 대상은 data-validation-mvp이며 미병합이다.
- PR #182의 최신 `97f77b4` 변경을 임시 별도 worktree에만 적용해 상태 JSON 격리/순환/상태 화면 검사를 함께 실행했고 18개/하위 검사 15개 통과했다. 이번 브랜치에는 #182 코드를 복제하지 않았다.
- 최종 구현 전체 unittest 298개 통과. 전체 pytest와 원격 CI는 진행 중이다. 탐색 검사가 실제 reload 후 차트 도구의 비동기 생성을 5초 안에 찾지 못한 경우도 확인해 값 보존 단언은 유지하고 대기만 30초로 맞췄다. 소스 UI/차트 동작은 변경하지 않았다. 최종 결과는 PR 설명 및 작업 최종 보고에 기록한다.
- 후속 확인: 전체 Chromium 탐색(데스크톱/모바일, 탭·관심·방향키·새로고침 복원) 및 그리드 스크롤 0px 검증 통과. #182가 `47612ef`로 갱신되어 다시 임시 적용했고 동일한 18개/하위 검사 15개 통과했다.
- CI에서 unittest 전용 작업이 보고서 회귀 검사의 pytest import 때문에 실패했다. pytest 의존성을 새로 요구하지 않도록 표준 unittest+subTest로 변경해 두 상태 스키마를 모두 검사한다. 이 수정 이후 정확한 PR head의 CI 완료를 확인한다.

## UI 통합 및 관심 목록 개발 (2026-10-30)

- 브랜치 `feat/unified-chart-watchlist-20261030`, 최신 통합 `4608a45`에서 새로 시작했다. #182(`47612ef`)·#183(`875c3ed`)는 별도 Draft이며 소스 변경을 덮어쓰지 않는다. KIS/수집 일정/Stage/시총/승인 정책/운영 데이터는 수정하지 않는다.
- 완료: `chart_ui.py` 공통 카드로 Stage 2/국가·원자재/업종/종목의 목록·3×3 제목·별표·주기·차트 구조를 공유한다. 이름·티커의 차트 내부 중복을 제거하고, 구성 업종/종목 이동은 카드 아래로 옮겼다. 내부 주기/표시 상태 값과 기존 위젯 키는 보존하며 화면에서만 일/주, 목록으로 줄인다.
- 완료: 목록 한 줄 압축/순위/26주 절대 수익률/이름 툴팁/약 6행 내부 스크롤/부드러운 선택 배경을 적용했다. 기존 정렬·필터·독립 모드·선택·페이지 콜백을 유지한다.
- 완료: 공통 hover 처리에 일봉 50일/완료 주봉 10주 거래량 단순평균을 추가했다. 기존 주봉 합계/부분 주간 제외/크로스헤어/150봉/잠긴 세로축/휠 확대는 유지한다. 기간 부족·누락·0 거래량에 임의 평균을 표시하지 않는다.
- 완료: 거래소+티커 ID의 관심 목록과 전용 탭, 자산군 필터·26주 수익률/이름/등록순 정렬·목록/3×3를 구현했다. 기존 티커 관심 목록을 보존하여 이관하며 Stage 또는 데이터 부재로 등록을 삭제하지 않는다. 동일 티커의 복수 거래소 가격을 현재 스냅샷에서 구분할 수 없으면 다른 거래소 가격을 대신 보여주지 않는다.
- 저장 범위: 서버/URL/다른 사용자 공용 파일이 아닌 현재 브라우저 탭의 sessionStorage. 새로고침과 서버 재연결 시 복원하며 다른 탭/기기와 공유하지 않는다. 브라우저 저장 불가 시 기존 현재 연결의 목록을 유지하고 제한을 알린다.
- 검증 중간 결과: 기존 UI 상태·탐색 테스트 15개, 신규 관심/거래량 테스트 9개(하위 검사 2개), 전체 unittest 293개 및 차트 4종 실제 Chromium 통과. 전체 pytest와 공통 카드·반응형·관심 탭 새로고침 브라우저 검증을 진행 중이다. 기존 검사도 새 카드 경계/컨트롤 위치에 맞춰 검증하며 핵심 단언은 유지한다.
- 유지할 UI 동작: 이름 클릭 선택, 선택/모드/주기/목록·페이지 위치 보존, 국가→업종→종목 왕복, 필터 밖 선택 유지, 별표의 화면 간 공유/새로고침 복원, 독립 관심 목록, 모바일 내부 스크롤·겹침 없음, 150봉·크로스헤어·축 잠금.
- 남은 작업: 전체/브라우저 검증 실패 수정, #182·#183 임시 조합 검사, 최종 Diff/원격 Draft PR/정확한 head CI 확인. 운영 배포/병합은 진행하지 않는다.
- 원격 Draft PR [#184](https://github.com/wonbosong-arch/global-stage-radar/pull/184) 생성, 구현 커밋 `5bc6603` 보존 완료. 전체 pytest 385개/하위 검사 100개 및 #182·#183를 함께 적용한 임시 작업 디렉터리의 검사 20개/하위 검사 15개가 통과했다. 조합 검증에서 각 PR의 CODEX_PROGRESS 추가 기록과 브라우저 준비 대기 패치는 UI 브랜치의 새 검사와 별개로 유지하고 수집/상태 소스를 함께 검사했다.
- 실제 브라우저에서 키보드 Space로 별표 등록→탭 저장소→관심 탭 3×3→새로고침 후 등록/모드 복원과 390px 가로 넘침 없음 확인. 긴 제목의 말줄임/별표 인접 배치를 보완했다. 도움말의 숨김 측정 버튼을 제외해 실제 보이는 버튼을 검사하며, Plotly 위젯 재사용 시 제목을 확실히 비우도록 명시적인 빈 제목을 전송한다.
- 기존 candidate_watchlist_symbols도 관심 등록 이관 대상으로 포함했다. 기존 다중 선택/CSV 기능은 후보 비교 선택으로 명확히 구분하며 기존 키와 선택값을 삭제하지 않는다. 현재 전체 브라우저의 최종 관심 목록 흐름과 수정 후 전체 검사/정확한 PR head CI를 마무리 중이다.
- 추가 보존 가드: 유니버스 메타데이터만 있고 현재 가격이 없는 실행에서도 관심 자산의 마지막 관측일·수익률·등록 시각을 지우지 않도록 갱신을 분리하고 회귀 검사를 추가했다. 커서 툴팁에서 해당 날짜의 실제 거래량 평균값을 대조하는 차트 4종 브라우저 검사도 통과했다.
- 최종 로컬 전체 Chromium 탐색 통과: 1440/800/390px 목록/카드 배치, 320px 탭·3×3 하단 페이지 UI, 목록 내부/페이지 스크롤 분리, 그리드 페이지 이동 0px, 국가→업종→종목 왕복, 필터 밖 선택·방향키·관심 공유·실제 reload 선형/로그 복원. 신규 관심 탭의 필터 키보드 조작·3×3·등록 해제·새로고침 복원·별도 브라우저 컨텍스트 격리도 통과했다.
- 현재 운영 배포/병합은 하지 않았고 마지막 로컬 전체 pytest와 정확한 최종 커밋의 CI 결과를 PR #184 설명 및 최종 보고에 기록한다. 기능 코드는 ccd541d에 보존했고 후속 커밋은 필터 브라우저 조작과 이 검증 기록이다.

## 3×3 기본 가격 축 및 간결한 페이지 UI (2026-10-29, 진행 중)

- 최신 통합 커밋 6508eb7 기준 별도 브랜치 `fix/grid-scale-defaults-pager`에서 작업. 기존 PR #179는 이미 통합되었고, 열린 기능 PR은 없음을 GitHub API로 확인했다. main/수집/KIS/스케줄/Stage 판정 변경 없음.
- 새 세션의 9개 주봉 차트는 기존 코드에서도 로그로 표시되었다. 다만 같은 X 구간/주기로 재렌더링 후 실제 축이 선택값과 달라지면 브라우저 갱신이 이를 놓치는 경로를 확인했다. 공통 차트가 주봉 Log/일봉 Linear 기본값을 최초 figure부터 전달하고, 브라우저가 실제 축과 저장된 선택값의 불일치도 복구하도록 보완했다.
- 기존 위젯+주기별 수동 설정 키를 유지했다. 모든 그리드가 기존 페이지 콜백/키를 공유하는 `‹ 현재 / 전체 ›` 하단 중앙 UI를 사용한다. 페이지 수 계산/끝점 비활성화/스크롤 보존은 유지하며 모바일에서도 한 줄로 배치한다.
- 완료 검증: 가격/내비게이션 Python 11개 및 하위 검사 13개 통과. 기존 AppTest의 페이지/주기/선택 유지 검사도 통과했으며, 공통 pager 추출에 맞춰 낡은 소스 문자열 검사를 갱신했다. 차트 4종 실제 브라우저 회귀 통과. 9개 각각의 주봉 Log/일봉 Linear, 독립 수동 설정, 페이지 왕복 및 1440/390px 하단 배치 검사 통과.
- 남은 작업: 전체 pytest, 다른 탭의 실제 그리드 및 동일 구간 축 덮어쓰기 복구 회귀 검사, 정확한 최종 커밋의 원격 전체 CI 확인과 PR 생성. 운영 Streamlit 배포는 미확인.
- 다음 실행: 테스트 로그 `/tmp/grid-full.log`, `/tmp/grid-scales-fixed2.log` 확인 후 최종 브라우저 재실행. 실패를 수정하고 이 브랜치를 푸시해 `data-validation-mvp` 대상 PR로 보존한다.
- 최종 Python 전체 검사: 377개 + 하위 검사 102개 통과(205.80초). 기존 pandas 경고는 남아 있으며 데이터 로직은 이번 범위에서 바꾸지 않았다.
- 재렌더 축 덮어쓰기 회귀는 수정한 JS에서 통과했고, 별도 임시 사본에서 실제 축 불일치 복구 조건만 제거하자 compact 로그 복구 대기에서 실패하여 회귀 검사의 유효성을 확인했다.
- 네 탭 실제 그리드 기본값/공통 footer 검증을 확장했다(Stage 2/국가/업종 9개, 가상 데모 종목 3개). 전체 로컬 시나리오 통과. 첫 CI 브라우저 검사는 업종 그리드→목록→탭 전환의 비동기 렌더 경합에서 실패했고, UI 체크 상태만 보던 검사를 서버 저장 모드/탭과 실제 차트 준비까지 기다리도록 보완했다. 최종 head CI 재확인이 필요하다.
- 중간 커밋 b31f116 원격 저장 및 Draft PR #180 생성 완료: https://github.com/wonbosong-arch/global-stage-radar/pull/180
- 최종 인계: 기능 구현과 로컬 검증은 완료했다. 전체 탭 재실행 `/tmp/grid-all-tabs-final2.log` 및 가격/축 덮어쓰기 복구 `/tmp/grid-axis-replay.log` 통과, 9개 차트 페이지 왕복 스크롤 0px. 일봉 SMA50/주봉 SMA30, 거래량 독립 축, 기존 호버·줌·선택·탭·모바일 회귀 포함.
- 남은 작업은 최종 head의 원격 CI 4개 확인과 PR을 리뷰 가능 상태로 전환하는 것이다. 이번 요청은 PR 생성까지이며 통합/운영 배포는 별도 상태로 보고한다. 다음 재개 시 PR #180의 최신 head/checks부터 확인하고 완료된 UI 작업은 반복하지 않는다.

## 실제 대시보드 사용을 위한 릴리스 통합 (2026-10-30)

- 새 작업 브랜치 `release/dashboard-integration-20261030`를 최신 `data-validation-mvp` (`4608a45`)에서 생성했다. #182, #183, #184 및 기존 그리드 보완 #180, 시간 문서 #185, 스냅샷 상태 원자 저장 #186의 실제 브랜치를 merge commit으로 통합했다. main 및 미검증 중국 ETF #181은 변경하지 않았다.
- 진행 문서는 모든 작업 기록을 합쳤고, 브라우저 검사/공통 차트 JS/공통 pager/새 관심 탭의 충돌은 두 기능을 모두 보존해 해결했다. 공통 pager를 관심 목록에도 적용했고, 실제 가격 축이 선택값과 달라지는 재렌더링도 복구한다.
- 중간 검증: 통합 unittest 316개 통과, 가격/거래량 차트 4종 실제 Chromium 통과. 모든 탭 9개 그리드의 일/주·선형/로그·페이지 왕복과 관심 목록을 포함한 통합 브라우저/전체 pytest를 검증 중이다.
- 배포 준비: `release_info.json`의 공개 릴리스 ID를 브라우저 DOM에 기록한다. `hosted_dashboard.yml`은 PR에서 현재 운영 화면을 읽기 전용 관찰하고 통합 브랜치 반영 후 실제 운영 URL의 릴리스 ID·데모 탐색·관심 목록 reload·모바일을 검증한다. 이 검증은 운영 소스 변경/권한 변경/실제 KIS 호출을 하지 않는다.
- 운영 주소는 인계 문서의 기존 Streamlit URL을 유지한다. 저장소의 GitHub 배포·환경 메타데이터에는 실제 Streamlit 연결 브랜치가 없다. 관리 설정 변경이 필요할 때 사용할 인증된 브라우저 접근은 아직 연결되지 않았다. TinyFish 연결과 무관한 통합/검증/배포 준비를 계속 진행한다.
- 다음: 최종 통합 오류 수정, 통합 PR CI 및 운영 기준 화면 확인, 검증된 변경을 통합 브랜치에 반영한 뒤 운영 버전을 직접 확인한다. 운영 설정 접근이 막히면 정확한 남은 접근 단계만 사용자에게 요청한다. PR 생성만으로 완료 처리하지 않는다.
- 통합 전체 pytest 408개/하위 검사 121개 통과. 운영 URL 기준 화면을 실제 CI Chromium으로 확보했고 기존 4개 탭 UI가 열리는 것을 확인했다. Community Cloud의 외부 프레임과 내부 앱 프레임을 구분하도록 운영 검증을 보완했다. PR의 기준 화면 관찰 성공은 새 버전 배포 확인과 구분한다.
- 배포 재현성을 위해 CI/로컬에서 검증한 Streamlit 1.66.1, Plotly 7.1.0을 고정했다. 운영 캐시에서도 해당 UI 버전으로 설치되도록 하며 KIS/API/판정 정책은 바꾸지 않는다. 그리드 장시간 검증 뒤 필터를 화면으로 가져와 선택하고 실제 combobox 값을 확인하도록 브라우저 동기화를 보완했다.
- 통합 PR #187은 정확한 head `f4a7d0a`의 CI 5개가 모두 통과한 뒤 병합했다(통합 커밋 `93c888a`). #180·#182·#183·#184·#185·#186도 병합 처리됐고 main은 `c5c3380`으로 유지됐다. 로컬 전체 pytest 408개/하위 검사 121개, unittest 316개, 전체 탭/관심/모바일/축 브라우저 검사 통과. 병합 후 Python tests·Candidate coverage report·Daily closing-price snapshot도 성공했다.
- 운영 검증에서 새 5개 탭과 관심 등록을 실제로 확인했지만 외부 호스팅 프레임 전체 reload 시 내부 URL 설정이 유실되어 관심 탭의 3×3 표시가 목록으로 초기화되는 문제가 드러났다. 운영 검증을 성공으로 보고하지 않고 별도 수정 브랜치 `fix/hosted-preference-reload-20261030`에서 보완한다.
- 수정: 기존 허용 목록의 화면 설정만 브라우저 탭 sessionStorage에 보관/복원하며 명시적인 URL 설정이 우선한다. 인증/비밀번호/관심 자산은 이 설정에 포함하지 않는다. 실제 프레임을 감싼 새 브라우저 회귀 검사로 수정 전 reload 실패를 재현했고 수정 후 관심 등록·3×3 복원·모바일이 통과했다. 단위 검사 4개도 통과했다.
- 다음: 수정 릴리스 2의 전체 CI를 확인해 통합한 뒤 같은 운영 URL의 엄격한 브라우저 검증을 다시 완료한다. 운영 소유자 설정 변경이나 추가 API 호출은 필요하지 않았다.
- 수정 PR #188은 정확한 head `48b8dc9`의 CI 5개(전체 pytest 410개/하위 검사 121개, unittest 316개, 기존 차트/전체 탐색/호스팅 프레임 회귀)를 확인한 뒤 `8c03c40`으로 통합됐다. 운영 DOM의 릴리스 2와 실제 3×3 화면도 확인했다.
- 운영 검사는 그리드가 실제로 표시된 상태에서도 내부 iframe의 URL 변경을 기다리다 시간 초과됐다. 화면과 저장소 및 전체 reload라는 사용자 동작을 직접 확인하도록 URL에 대한 부수 조건을 실제 그리드 표시 단언으로 바꾸고, 안전한 표시 방식/브리지 진단을 추가한다. 관심 등록·저장 완료·reload·모바일 단언은 유지한다. 다음은 같은 운영 릴리스에 이 검사를 실행해 실제 기능과 검증기의 가정을 분리하는 것이다.
- 실제 운영 최종 기능 검증 성공: 2026-10-30 14:38:12 KST, `2026-10-30-dashboard-integration-2` 일치·5개 탭·Space 관심 등록·탭 저장 완료·실제 3×3 표시·바깥 페이지 전체 reload 후 관심/3×3 복원·1440/390px 가로 넘침 없음·앱 예외 없음. 엄격한 운영 실행: https://github.com/wonbosong-arch/global-stage-radar/actions/runs/41009381308 (success). KIS를 추가 호출하지 않은 가상 데모 검증이며 실제 일일 KIS 스냅샷 92개/오류 0개 성공은 별도로 확인했다.
- 검증기 PR #189에서 내부 URL 부수 조건 대신 실제 그리드 표시를 확인한 뒤 동일한 저장·reload 단언이 모두 통과했다. 초기 화면 진단과 최종 화면 진단을 구분해 보고하도록 정리한다. 다음: 정확한 최종 검증기 head의 전체 CI를 확인해 통합하고 통합 브랜치 운영 검증도 성공 상태로 남긴다. 운영 관리자 접근/새 플러그인/추가 사용자 승인은 필요하지 않다.

## 티커 압축 테이블 및 차트 버튼 통일 (2026-10-30)

- 최신 통합 `eb2b84d`에서 `feat/unified-ticker-table-controls-20261030` 생성. 관련 열린 UI PR 없음. main/수집/판정/가격/스케줄은 변경하지 않는다. 기존 예약 변경 #190과 실제 실행 자동 확인은 별도 작업이다.
- 공통 `asset_table.py`/CSS로 티커·26주 수익률·계산된 신규 진입·독립 관심 별표와 추가 지표를 렌더링한다. 기존 선택 키/콜백/필터와 자산 식별을 유지한다. 숫자 우측/티커 좌측·34px 행·허용된 열 정렬·고정 티커/헤더·내부 양방향 스크롤을 구현하고 실제 브라우저를 보며 Streamlit wrapper의 크기와 overflow를 보정 중이다. 이름은 툴팁에서만 확인하며 30주선 거리는 표에 표시하지 않는다. 신규 비교 근거가 없으면 신규 열/표시를 만들지 않는다.
- 차트 공통 헤더는 티커/별표, 왼쪽 설정 행은 일봉·주봉 및 선형·로그 버튼으로 통일한다. 기존 브라우저 탭/차트/주기별 축 저장키와 자동 축 복구·150봉·마우스 기능은 유지한다.
- 검증: 핵심 선택/필터/왕복 AppTest 6개, 신규 테이블 5개 통과. 실제 Chromium 차트 4종은 150봉·툴팁·거래량 평균·확대·축 잠금·축 덮어쓰기 복구·주기별 수동 값 복원을 통과했다. unittest 320개 중 공통 렌더러 이동에 따른 옛 소스 위치 단언 1개만 실패해 현재 공통 호출/동일 키 검사로 갱신했고 해당 6개 재검사 통과.
- 다음: 전체 pytest/다섯 영역 테이블/모바일/기존 3×3 전체 탐색 회귀를 마무리하고 실패를 수정한다. 안정화된 커밋을 원격 보존, 통합 PR의 정확한 CI 확인 후 통합 및 실제 운영 릴리스 검증까지 이어간다. 운영 반영 전에는 개발/운영 성공을 구분한다.
- 전체 로컬 pytest 415개/하위 검사 121개 및 unittest 320개 통과. 다섯 영역의 실제 테이블/열 정렬/34px/고정 헤더·티커/행 클릭/독립 별표/그리드 기본축·수동축·페이지·왕복·reload 브라우저 흐름이 통과했다. 문자 자체의 좌측/우측 정렬과 설정 그룹의 실제 버튼 기준선도 추가 검증한다.
- 구현 `615d07a` 원격 보존 및 Draft PR #191 생성: https://github.com/wonbosong-arch/global-stage-radar/pull/191 . 해당 head의 Python CI 3개는 성공했지만 브라우저 CI가 관심 그리드 전환 중 빈 화면으로 실패해 병합하지 않았다.
- 빠른 필터 해제/즉시 탭 전환 재현에서 Streamlit `Cached ForwardMsg MISS` 및 fatal WebSocket 오류를 수집했다(5회 내 실패). 설치된 1.66.1의 메시지 참조 캐시 경합이며 https://github.com/streamlit/streamlit/issues/17265#issuecomment-6000613061 의 공식 우회 설정 `.streamlit/config.toml`을 적용했다. 화면 전송 캐시만 우회해 큰 화면 메시지의 전송량은 늘 수 있으나 분석/API 캐시·가격·인증/저장 정책은 바꾸지 않는다. 동일 재현 12회 모두 통과했고 전체 회귀에 해당 겹침 조작 및 fatal console 오류 검사를 추가했다.
- 마지막 행이 화면 하단 밖에 조금 걸쳐 있을 때 Playwright가 클릭 전 페이지를 7px 이동하는 경우를 확인했다. 클릭 대상을 보이게 한 뒤 측정하도록 준비만 보완하고 이동 허용값 3px는 유지한다. 실제 스크롤 복원은 서버의 선택·정렬·별표 갱신 때 한 번만 적용해 후속 사용자 스크롤과 싸우지 않게 했다. 렌더러 재실행 사이에도 복원 상태는 같은 브라우저 문서 안에서 유지한다.
- 다음: 우회/스크롤 보완을 포함한 전체 로컬 브라우저 및 정확한 최종 head의 CI를 확인하고, 검증된 UI만 통합한다. 운영 검사는 다섯 영역의 새 테이블·버튼 및 실제 프레임 reload·모바일까지 확인한다. main/운영 예약/수집/Stage 로직은 변경하지 않는다.
- 메시지 캐시 우회 후 같은 데모 필터/탭 겹침 조작 12회가 오류 없이 완료됐다. 이 과정에서 Streamlit v2 renderer가 갱신될 때 반환 cleanup은 unmount 시에만 보장되어 전역 차트 컨트롤러가 중복될 수 있음을 확인했다. 실제 실패 DOM은 카드 1개·Plotly 1개·축 그룹 2개였다. 새 renderer 실행 시 이전 document-wide 컨트롤러를 idempotent cleanup하고 새로 연결하도록 차트/테이블 JS를 보완했다. 기존 저장키와 Plotly 이벤트 계약은 유지한다.
- 보완 후 차트 4종 Chromium 검사 재통과. 최신 전체 브라우저는 넓은/좁은 화면의 설정 기준선·고정 표·3×3 왕복 및 빠른 전환 12회를 함께 확인 중이다. 어떤 JS 오류나 fatal 메시지 캐시 오류도 검사에서 실패로 기록한다. 다음은 이 최종 보완 head의 CI 확인과 승인 가능한 통합/배포 준비다.
- 최종 로컬 검증: 최신 컨트롤러에서 전체 대시보드 Chromium이 성공했고, 빠른 필터/탭 왕복 12회·전체 5개 영역·축·0px 페이지 이동·모바일/reload를 확인했다. 호스팅 프레임의 전체 5개 영역→관심 3×3→외부 페이지 reload도 성공했다.
- 최종 육안 확인에서 Streamlit 버튼 내부 flex 정렬 때문에 CSS text-align만으로는 티커 글자 자체가 가운데에 남는 것을 발견했다. 내부 label wrapper도 좌측 정렬했고 실제 텍스트 Range 좌표가 셀 왼쪽+10px인 것을 검증한다. 기본 열 제목 잘림과 숫자 정렬은 유지한다.
- 원격 브라우저에서 테이블 정렬 직후 Plotly DOM은 있으나 layout 초기화가 끝나기 전 값을 읽는 경합을 확인했다. 동일 선택 보존 단언은 유지하고 실제 차트 준비/예상 심볼을 기다리는 조건을 추가했다. 다음은 이 정확한 최종 head의 전체 CI 확인이며 운영은 아직 이전 릴리스다.

## 2026-11-03 private China analysis development
- Fresh base 45558d7; reused #193 chart/UI/reconciliation code and #194 identity metadata only. Existing PRs untouched; no workflow, schedule, data, universe or deployment changes.
- Private snapshot copied locally outside checkout to /workspace/china-private-snapshot; never staged. Explicit external-path loader; default metadata only. 11 reconciled previews, 512400 blocked; 12/12 Stage withheld, no generated new-entry flag.
- Eight focused tests passed with private input. Full Python and actual Chromium regressions started; see final PR validation for results.
- Remaining: trusted adjusted long history, benchmark and full Stage classification; real operational deployment intentionally prohibited. Resume using docs/china-private-analysis.md and this branch; never commit raw research inputs.

- Local Chromium China journey PASS: 11 reconciled previews, ETF-name selection, daily/weekly, 9+3 paging and tab-return page retention; common chart four cases PASS with 150 visible bars and no errors. Full existing-area browser regression and Python CI pending.
- Development preserved in Draft PR #195. No merge/deployment.

## 중국 ETF Stage prerequisites 후속 보완 (2026-11-03)

- 시작 시 GitHub PR #195 head `0a43e8d`, 통합 `45558d7`, 정확한 head 자동 CI 3종 성공을 확인했다. 관련 Codex 채팅은 유휴 상태였다. #192/#193/#194는 읽기 확인만 했다. 기존 연구 worktree의 미커밋 가격 파일은 건드리지 않았다.
- 별도 `feat/china-stage-readiness-20261103`에서 #195를 이어갔다. 통합 최신 커밋이 이미 조상으로 포함돼 있다. 기존 차트 구현을 반복하지 않았다.
- 완료: readiness에 MA30(30주), 4주 기울기(34주), 이전 주의 유효 기울기 비교(35주)를 각각 계산 가능한지 검사하는 진단을 추가했다. 첫/끝 부분 주봉 제외, XSHG 실제 거래일의 중복/누락/비거래일/미래일/혼합종목 및 OHLC/NaN/무한대/거래량 검증을 구현했다. 달력 검증 실패는 차단한다.
- 완료: 소비하는 CSV의 manifest 해시 항목 누락/외부 경로 차단. 512400은 일치 플래그 변경만으로 해제되지 않도록 명시 차단. 조정 기준·이전 Stage는 미검증이며 35주 이상이어도 Stage/MA/기울기/26주 수익률/신규 Stage2 출력은 null, 운영 승격은 false다. 진단 flag는 활성화 권한이 아니다.
- 기존 장기 자료 8,905행/30종/2025-07-30~2026-10-27을 검토했지만 공식 대사는 60거래일뿐이고 KIS MODP=1은 조정 기준 검증이 아니다. 새로운 검증 조정주가 이력은 확보하지 못했으며 미검증 과거 자료를 분석에 연결하지 않았다. 원본 가격은 추가 커밋하지 않는다. 외부 CHINA_PRIVATE_SNAPSHOT_DIR 정책 유지.
- 중간 검증: 집중 29개/하위23개 통과(최종 manifest 무입력 회귀 1개 추가 후 재검사 예정). 실제 Chromium 중국 개인모드 선택/일주봉/9+3/복귀 통과(11종 차트, 12종 Stage 보류). 공통 차트4종 150봉/오류 없음. 호스팅 프레임 five-area/관심/reload/mobile 통과. 전체 navigation은 Windows stocks footer 정렬에서 실패하여 동일 원본 #195와 비교 중이다. unittest 325개 중 기존 Windows fsync 오류26건, 전체 pytest 집계 중.
- 다음: 최종 집중/전체 집계와 원본 비교, 이 head 자동 CI 확인 후 기록. Stage 판정 가능0/보류12, 512400 불일치 미해결. 다음 개발은 전 계산 구간의 독립 대사·조정 방법/배당/분할 이력·벤치마크 및 Stage1~4/이전단계 정책 검증을 확보하는 일이다. 병합/운영활성화/배포/Actions 수정·예약변경·수동실행 없음.
- 최종 로컬 결과: 집중30개/하위23개 통과, 신규 readiness8개/하위19개 포함. 최종 전체 pytest409통과/28실패/하위136통과(208.42초). 실패한 네 모듈을 수정 전 #195에서도 재실행하여 동일28실패를 재현했다(기존 Windows fsync26/POSIX shell1/캐시 결측값1). 전체 unittest의 신규 readiness는 모두 통과했으며 Windows fsync26건은 동일하다.
- 실제 Chromium 최종: 중국9+3 이동 스크롤0px, 512400 실제 Plotly 차트 없음, 오류 메시지, 일주봉/선택/탭복귀 모두 통과. 공통 차트4종150봉 및 호스팅 프레임5영역/관심/reload/mobile 통과. 전체 dashboard 탐색은 stocks footer 좌표 (y484.109375, y569.109375) 불일치로 중단되며 수정 전 #195도 좌표까지 동일하게 실패했다. 전체 로컬 탐색 성공으로 보고하지 않는다.
- 구현 커밋 f3a55622db8fb6927ea6e273e905e5bf50752b77 원격 보존 완료. 통합 대상 Draft PR #196: https://github.com/wonbosong-arch/global-stage-radar/pull/196 . f3a5562의 자동 Python CI41559903484 및 Unit CI41559903398 성공, browser41559903465 진행 중에 이 후속 기록/개인 브라우저 단언을 추가했다. 최종 head의 자동 CI 결과는 PR Checks/최종 보고를 참조한다. 수동 워크플로 실행 없음.
- 다음 인계: 통합/운영은 미반영이며 검증 조정주가·이전 Stage 및 벤치마크 정책 확보 전 Stage0가능/12보류를 유지한다. 기존28개 Windows 실패와 stocks footer 로컬 재현은 별도 환경/레이아웃 과제다. #195/#193/#194/#192는 변경·병합하지 않았다.

## 단일 통합 후보 재확인 (2026-11-03)

- 단일 최종 Draft 후보는 #196, 대상 data-validation-mvp(45558d733cb51b9402f1a7963a05dcfbda153ca3). GitHub compare에서 #195 최종 0a43e8dfdd5ed56d200cd4dc744aefb05dc751f2가 #196 d41f36f703ebe07303a5f84f73c73e878360efea의 merge-base이며 ahead 2/behind 0임을 확인했다. #195 별도 병합/체리픽은 필요 없다. #192~#195는 그대로 보존한다. 최신 열린 PR 목록에서 이 이후의 별도 중국 구현은 없었다.
- GitHub는 #196 mergeable=true/draft=true로 응답했다. 12종 메타데이터, 외부 개인 스냅샷 차트와 강화된 readiness를 모두 포함한다. 전체 diff 11개 파일에 가격/워크플로 변경 없음. 이번 재개는 기능 코드 수정 없이 이 인계 문서와 #196 설명만 정리한다.
- 정확한 기능 head d41f36f의 자동 CI 3종 성공을 API로 재확인: Python 41560435049, unit/syntax 41560435039, browser 41560435023. 기존 결과 Python427통과/6개 개인입력 skip/140 subtests, unittest328통과. 기존 Windows28실패 및 로컬 stocks footer 재현 한계는 위 기록 유지. 코드 무변경이므로 로컬 전체 검사를 반복하지 않았다. 후속 문서 커밋 CI는 PR Checks에서 별도로 확인한다.
- Stage 가능0/보류12, 개인 차트11/512400차단. CHINA_PRIVATE_SNAPSHOT_DIR 외부 경로와 기본 메타데이터 모드 유지. 미검증 데이터 신규 업로드/활성화/삭제/이력재작성/Actions 변경 또는 수동실행/병합/배포 없음.
- 다음 주 첫 작업: #196 최신 head/CI 및 통합 기준 이동 여부부터 확인하고, 전 계산 구간의 독립 대사된 장기 조정주가·배당/분할 및 조정방법 증거, 이전 Stage/벤치마크 정책, 512400 가격 불일치 해결 자료를 확보한다. 완료된 차트/메타데이터를 재구현하지 않는다.
# 2026-11-03 KIS trust / China private Stage implementation

- User's latest decision supersedes old independent-price/adjustment gates. Policy
  recorded in AGENTS.md, README and docs/provider-trust-policy.md for all markets.
- Before edits: GitHub integration dceea187, main 997628e, #200 head 0ddf281;
  #197→#200 remain Draft/unmerged and #200 automatic CI both success. Open PRs,
  remote branches, local worktrees and recent Codex chats inspected. Other recent
  related chats idle. Existing research worktree has private price modifications;
  left untouched. Fresh independent feat/china-kis-stage-20261103 from integration.
- No research PR imported or changed. New explicit KIS private manifest path skips
  external reconciliation and 512400-only block; legacy diagnostics preserved.
  Validates metadata/routes, successful-response symbol observations, price-byte
  integrity, sessions, missing/duplicate/nonfinite/OHLC/volume data, >50% daily
  adjusted-close anomalies, completed weeks and existing ten-day freshness guard.
- Reuses shared weekly_bars and classify_stage thresholds, with explicitly labelled
  absolute 26-week momentum (not market RS). Existing US/KR/JP benchmark logic is
  unchanged. Prior completed Stage and comparable-week new entry calculated.
- Private replay from source 17c4099, price hash matched retained snapshot; successful
  KIS response observations checked from original commit. All12:63 complete weeks,
  as-of2026-11-03, last daily2026-10-27. Stage2 512800/512010, new entries0.
  512400 passed quality and classified 하락 추세 관찰. No invented indicator values.
  Original prices/response bytes/manifest/report/screenshots remain outside Git.
- Browser private journey passed on Chrome: 512400 chart, daily/weekly, list,
  9+3 grid paging, Stage2 filter2, tab round trip, widths1440/800/390 without overflow.
  Initial harness failures were incorrect header text and expected selected symbol;
  corrected to actual header and preserved512400 selection. Synthetic UI regression
  covers filter persistence and page clamping. Default metadata-only path preserved.
- Local full suite during implementation:408 passed/28 failed/6 skipped/136 subtests.
  Fresh integration baseline:403 passed/28 failed/6 skipped/136 subtests. All24 unique
  failing IDs (28 parameterized failures) exactly equal; no new failing IDs. Known
  Windows fsync/POSIX shell/cached numeric-missing failures remain. Five new calculation
  tests and one synthetic UI journey passed; final focused validation recorded in PR.
- No merge, deployment, operational activation, direct protected-branch modification,
  workflow/schedule change or manual Actions execution. Public price authorization
  remains false. Private Stage2 filter does not change active operational Stage2.
- Final focused suite40 passed/26 subtests. Synthetic UI test is additional to the
  five new calculations in the full-suite implementation run. Shared-market Chrome
  journey failed stock-grid footer alignment at grid_checks.py:56; fresh integration
  reproduces exactly the same coordinates (y484.109375 vs569.109375), unrelated to
  China path. No claim that the general browser journey passed.
- Draft PR #201 preserved targeting data-validation-mvp. Initial remote4b5e48e tree
  cf6ba651 exactly equals local839b830 tree. Ordinary Git push lacked interactive
  credentials; connected GitHub API used instead. Subsequent finalization parses
  the exact hashed private CSV bytes to avoid concurrent-file replacement races.
  Automatic Unit/Syntax, Python and Chart-browser CI started, never manually run.
- Remaining: inspect automatic CI at exact final remote head. Next priority:
  review code, then separately approved deployment/activation and fresh private KIS
  snapshot. Do not resume independent-price or adjustment reverse-engineering gates.
# 2026-11-03 China private automated pipeline (after merged #201)

- Fresh integration/remote head67cff86a4e3ede9130574f2d33fdd86f41111540 checked twice;
  independent feat/china-kis-pipeline-20261103. Existing dirty research worktrees
  untouched. Open #197–#200 remain Draft and conflicting with integration; not
  dependencies and never modified. Other open legacy/research PRs left untouched.
  Merge SHA combined-status endpoint returns no statuses, not a CI success claim.
- Official KIS dailyprice route/TR/SHS mapping/MODP=1 sample inspected. Original
  17c4099 collector/status confirms all12 SHS responses299 rows at2026-10-27.
  Current KIS credentials absent in environment; live calls0, current deployed
  account permissions unverified. No claim of newly acquired/fresh prices.
- New default-disabled research hook in existing07:00 entry point; single shared
  provider, existing throttle/retries, 12 full snapshots, completed bars, existing
  Stage/quality/freshness gates, immutable private generations and atomic pointer.
  Actual dashboard loader resolves pointer; legacy direct private snapshots work.
  Failures retain previous generation and redact provider error text. No price
  merge across adjustment vintages, no active-universe additions or public files.
- Hosting investigation: current workflow commits public research CSVs; new private
  output is outside checkout and cannot use that publication route. Shared private
  persistent volume contract implemented; ephemeral runner→Community Cloud delivery
  needs approved infrastructure/authenticated backend. Not configured or deployed.
  No workflow/schedule/manual Actions execution, secrets/flags or deployment changes.
- Retained real KIS CSV replay through new collector/store/Stage/dashboard loader:
  network0, ready12, Stage2=2, new entries0; research only. Original data and new
  replay output remain outside Git. No independent SSE/adjustment reconstruction.
- Final focused58 tests/29 subtests pass including7 new pipeline tests, real adapter
  request contract, synthetic UI list/grid navigation, newStage2 and US/KR routes.
  Implementation full pytest413 pass/28 fail/6 skip/136 subtests (213.45s).
  Exact fresh67cff86 baseline failing four modules reproduces all28 failures;
  FAILED/SUBFAILED lines compare identically. Existing Windows fsync26/POSIX shell1/
  numeric missing-value1. Final extra adapter/guard tests covered by focused58;
  full run preceded those final tests. Full unittest340 tests/errors26, same known
  fsync platform limitation. Compile/diff checks pass. No full-local-success claim.
- Next: preserve Draft PR, inspect automatic exact-head CI. Current live KIS probe,
  private storage/hosting configuration and operational activation remain gated;
  see docs/china-kis-pipeline-20261103.md. Do not change other PRs or merge/deploy.

## 2026-11-03 Private cross-host delivery follow-up

- Latest integration67cff86, #202 head0181173 still Draft; its Unit41589125198
  and Python41589125409 both success. Other recent related chats idle, existing
  worktrees/dirty inputs untouched. Fresh feat/china-private-delivery-20261103
  from integration; reuse #202 tree8af45b67 exactly via local2f0d29f before edits.
  #197–#202 never modified/merged. New PR is a cumulative alternative to #202,
  not an instruction to merge both overlapping proposals.
- No KIS environment credentials in current session; current authenticated live
  calls0. No secret-value extraction/re-entry request. Connected tool does not
  expose secret administration. Scheduled job124998764400 (run41356890322,
  2026-11-02 KST) shows masked nonempty KIS_APP_KEY/SECRET injection and successful
  collection:30/30, error0, all representative12 SHS300 rows/latest2026-10-30,
  including512800. This is authenticated collector observation evidence, not new
  raw-response acquisition in this session. Nov3 run41537626610 cancelled/jobs0;
  both runs artifacts0. Next unchanged schedule can be read-only checked; no
  workflow dispatch/rerun, new monitor, schedule edit, flags/secrets or activation.
- Added optional private AWS S3 transfer, explicit publish/sync modes only.
  Immutable files + remote CAS pointer, authenticated server-side reads into
  separate private cache, hashes and existing12-ETF Stage/quality/freshness before
  local atomic pointer. Partial uploads retry, failed fetch/tamper/stale/CAS
  conflicts preserve prior relevant pointer. Default local/shared-volume path
  retained, existing Stage/UI reused. No infrastructure created or data uploaded.
  Optional deployment dependency isolated in requirements-private-delivery.txt.
- Focused final48 passed/17 subtests; includes separate-volume actual dashboard
  roundtrip, failure preservation/cache, SDK Stubber serialization (no network),
  collector/dashboard opt-in hooks, Stage2 and US/KR routes. Compile/diff checks
  passed. Full final pytest405 passed/64 failed/6 skipped/127 subtests; exact
  untouched67cff86 under identical newly provisioned Windows dependencies:
  388 passed/64 failed/6 skipped/121 subtests. FAILED/SUBFAILED lines identical.
  Do not reuse earlier28-failure count from a different runtime as this result.
  Full unittest350/errors48; baseline comparison and exact remote CI follow.
- Native Git fetch/push transport fails schannel SEC_E_NO_CREDENTIALS; existing
  authorized GitHub connector used to preserve code. No KIS credential searches.
- Deployment design/least privilege/configuration/rollback and next scheduled
  evidence inspection documented in docs/china-private-delivery.md. Remaining:
  approved private S3/reader hosting/access rights, separate credentials and
  schedule-preserving environment wiring, actual private backend E2E. Automatic
  transfer is implemented but unconfigured; hosted behavior remains unverified.

## 2026-11-04 Latest integration candidate

- Fresh native remote refs and API branch agree on integration285b67ac9dcfb833c8bd287f2768377bf591edaa,
  eight data refresh commits after merged201/67cff86. Fresh independent
  feat/china-integration-20261104 includes all eight without changes to data/.
  Git fetch uses command-scoped openssl because Windows schannel fails; original
  remote refspec only tracks research, so explicit branch refs were fetched.
- Existing202/0181173 and203/f58ee5f remain untouched Drafts. API PR snapshots
  still name old base67cff86 and report mergeable=true/clean, while branch endpoint
  is newer. Actual Git no-commit merge of exact203 into285b67a succeeds without
  conflicts. Earlier mergeable=false is not a reproducible content conflict.
- Reuses exact203 code via ancestry merge, including202. No duplicated feature
  implementation or research197-200 dependency. Shared app/chart, Actions, data
  and provider trust policy unchanged. Related local chats inactive/notLoaded;
  other worktrees and their untracked inputs untouched. No main/integration push.
- Added actual private KIS browser paging scroll assertion and result metric.
  This browser_checks change also qualifies for existing automatic browser CI,
  without editing or manually dispatching workflows. Synthetic memory transport
  replay generated12 ready symbols and passed actual dashboard loader validation;
  no external provider/object-storage calls. Focused35 tests/25 subtests passed,
  including installed optional boto3 Stubber contract (no SDK skip).
- Full Python/unittest and browser verification in progress; final results follow.
  Live KIS calls0; S3 calls0. Prior scheduled success is historical evidence only.
  No secrets, schedule/rate-limit, infrastructure, permissions, deployment or
  operational activation changes. Remaining approvals: merge, hosting/storage
  cost/access configuration, deployment and private data activation.

### Validation and preservation

- Draft204: https://github.com/wonbosong-arch/global-stage-radar/pull/204
  Initial remote9899d730 has parents285b67a and original203/f58ee5f. Its tree
  5039417953f64990c6206fd98f5494962dc6f254 exactly equals tested local84d1856.
  Git push failed at wincredman; connected GitHub API preserved identical Git
  blobs/tree and both parents. Existing202/203 refs never changed.
- Full local pytest426 passed/28 failed/6 skipped/142 subtests. Fresh285b67a
  baseline409 passed/28 failed/6 skipped/136 subtests. All24 FAILED/SUBFAILED
  lines identical (26 Windows fsync errors, POSIX shell and numeric missing-value
  failures). Optional SDK was installed after this full run; final focused35
  includes successful real boto3 Stubber serialization. Private legacy-input
  tests skipped when their external snapshot is unconfigured. No full pass claim.
  Unittest350 vs baseline333, both26 errors; ERROR ID lists identical. Compileall,
  all14 workflow YAML parses and complete diff checks passed.
- Actual Chrome synthetic pipeline→memory object store→separate private cache→
  actual dashboard passed:12 ready, operational false, daily/weekly,512400 chart,
  grid9+3,Stage2 filter2,area roundtrip,1440/800/390px and paging scroll delta0px.
  New-entry and prior completed-week behavior covered by synthetic unit tests.
  Chart browser weekly/daily/compact/review contracts all passed,150 bars each.
  Hosting-frame reload/mobile/preferences/shared list controls also passed.
  Full navigation failed existing stocks pager alignment at grid_checks.py:56;
  exact fresh285b67a reproduces same y484.109375 vs569.109375. Not a new regression
  and not a claim of full local browser success. Initial startup failed because
  this installed Streamlit defaults developmentMode=true; reruns set only local
  STREAMLIT_GLOBAL_DEVELOPMENT_MODE=false. No repository config change.
- Local evidence outside Git: integration-focused-final.log,
  integration-full-pytest.log, integration-baseline-pytest.log,
  integration-unittest.log, integration-baseline-unittest.log,
  integration-private-browser-final.log, integration-browser-final-{0,1,2}.log,
  integration-baseline-navigation.log; screenshots/results in matching folders.
- Initial exact-head automatic CI: Unit/Syntax41741092065 success;
  Python41741092070 unit/YAML/compile success, pytest running;
  browser41741092061 chart contracts success, navigation running at this record.
  https://github.com/wonbosong-arch/global-stage-radar/actions/runs/41741092065
  https://github.com/wonbosong-arch/global-stage-radar/actions/runs/41741092070
  https://github.com/wonbosong-arch/global-stage-radar/actions/runs/41741092061
  Final documentation commit triggers normal automatic checks; final exact-head
  results will be retained in Draft204 description. No manual Actions execution.
- Eleven-file complete diff reviewed; data/, Actions, app.py, chart_ui.py and
  trust policy unchanged. No merge/deployment/backend provisioning/activation.
  Next: review Draft204, separately approve merge and private hosting/storage
  wiring and rights/access before real cross-host operation. Historical scheduled
  KIS success is not a current-session live call. Current KIS/S3 network calls0.
- Additional stored-snapshot Chrome US/SPY, KR/EWY, JP/EWJ roundtrip passed daily/weekly, provider calls0; integration-markets-browser-verified.log. Two preliminary checker selectors failed on duplicate label/overlaid radio; final scoped stRadio label journey passed without app changes.
# US Stage readiness audit — 2026-11-04

- Fresh base d8d4590d67fa3c4401285cc6e3d08b73bc8a19d7, child of merged
  #208 ddd249c. Dedicated audit/us-stage-readiness-20261104 branch; other
  checkouts untouched. PR/chat inventory checked; no active parallel US work
  visible. #205/#206 and China research work remain separate.
- Offline JSON audit reuses weekly/RS/freshness engine and real pending bridge;
  explicit as-of, eleven input hashes, unique US listing identities, independent
  dimensions/intersections and exhaustive disjoint counts. No price export.
- US1897, cap value1869, weeks30=1850/34=1846/35=1845, registry mapping
  fields106 (not approved), assigned Stage data inputs105, all pending/identity
  unverified/provider not_checked; operational bridge additions0. Saved review
  Stage2=98/2A=21 remains review-only. Cap report discrepancies documented.
- New synthetic tests4 and final focused bridge/Stage tests31 passed. Full
  Windows pytest during implementation433 passed/28 failed/7 skipped/156
  subtests; clean d8d4590 baseline429 passed with same28 failures,7 skips,156
  subtests. All24 unique FAILED IDs exactly equal (fsync26, POSIX shell1,
  cached numeric missing value1). Final RS/freshness counters covered by final
  focused31 and successful stored-data audit rerun. Compile/diff checks pass.
  Draft209 preserves remote tree matching local implementation exactly;
  exact final-head automatic CI results to be recorded in PR. See docs/us-stage-readiness-20261104.md and
  docs/evidence/us-stage-readiness-20261104.json for reproduction/fingerprints.
- No data/, app, engine, collectors, workflows, main/integration edits, live KIS
  or price calls, Actions dispatch/rerun, cron/queue/hosting/cost/activation,
  merges or November5 automation changes. Next: reconcile size-screen provenance
  in existing reports; prepare small identity/mapping review batch. Activation,
  protected-branch merge and deployment require separate user approval.

## 2026-11-04 US KIS evidence readiness
- Branch feat/us-kis-evidence-readiness-20261104 from integration 43bec1f (#209).
- Added read-only KIS evidence report and regression tests; reused existing audit/normalizer.
- Focused tests: 35 passed. Full Windows base comparison and final head CI tracked in PR.
- Pending: review missing retained KIS evidence/anomaly signals; no status transitions or operational changes.
- Details: docs/us-kis-evidence-readiness-20261104.md.
- CI follow-up: standard unittest conversion removes pytest import from unittest-only workflow; focused 25 passed, 8 new methods cover 18 cases.

## 2026-11-04 US Stage connection adapter (unmerged)
- Fresh integration base9416654 (#210), isolated feat/us-stage-connection-20261104.
  GitHub open PR/branch/CI, recent chat inventory and local worktrees checked;
  no competing active US work found; China dirty checkout and #205 untouched.
- New offline adapter turns KIS-eligible candidates into per-symbol review
  packets and actual assigned/suggested Stage engine replays without fabricating
  approval statuses. Captures selected cap value+URL linkage, observation/as-of
  separation, mapping drift, benchmark metadata, weekly/RS/freshness and gates.
- Stored snapshot:72 inputs-ready; NAS1/NYS71/AMS0; cap estimates72/confirmed0;
  source-value links72, cap as-of unknown72; mapping inputs/proposals agree72
  but suitability not approved. Engine review labels25 Stage2/5 Stage2A/35 neutral/
  7 declining. Actual original pending registry bridge additions0/errors0.
- All72 last price2026-10-29, none fresh in last attempt. Fresh7 expires after
  2026-11-05 without new data. No live call/refresh triggered.
- Final focused41 passed/56 subtests; new unittest8 passed including six bad
  benchmark scenarios. Full unittest374,26 Windows fsync errors,1 skip.
  Default cp949 full pytest427 passed/64 failed/7 skips; clean exact base420
  passed/same64 failures; complete FAILED/SUBFAILED lines exactly equal.
  UTF8 full implementation448/base441 passed, both28 failed/7 skips; all28
  FAILED/SUBFAILED lines exactly equal. Full run preceded final alignment case
  and freshness deadline; final focused41 validates both. Final-head CI in PR.
- Details/reproduction:docs/us-stage-connection-20261104.md. Full packet input
  hashes in docs/evidence/us-stage-connection-20261104.json.
- No data/, UI, operational bridge, workflow/cron/queue, main/integration direct
  changes, merge, activation, deploy, costs/Secrets or Nov5 automation change.
  Next minimum approval: merge Draft211 to data-validation-mvp; no status write,
  activation or live call included. Mapping suitability remains a separate gate.
- Published implementation4f4d52e via GitHub connector after local Git credential
  persistence failure; fetched remote tree df7af491 exactly equals tested local
  tree087a3a6. Final documentation-only head/CI is recorded in Draft211.
# US candidate price refresh investigation — 2026-11-04

- Base1839e63 (#211 merged); isolated fix/us-price-refresh-fairness-20261104.
- Checked latest GitHub branches/open PRs/recent CI and app tasks before edits.
  No overlapping US price PR/running task; existing China changes untouched.
- Read five Nov2-Nov4 KST candidate job logs:362/189/329/195/368 processed,
  errors0; all72 deferred every run. Candidate growth1426→1676→1926 and
  first-time missing-history priority explain temporary queue displacement.
  Historical next positions707-781→768-842→439-513→494-568→126-200.
- Current72 stored sessions10/29, last attempt10/29 23:55UTC, active0.
  Latest status11/04 08:04:51KST describes partial snapshot, not72 refresh.
  Existing normal rotation retained; conditional1-2 runs for72 attempts,
  no daily freshness/completion promise. Seven-day gate expires after11/05.
- Added offline candidate_refresh_queue_audit.py using existing collection_plan
  and Stage-plan cohort packet. Reports order/defer/cooldown/exclusion/session,
  expiry warning and conditional throughput estimates; rejects digest mismatch.
  No network/data mutation, collector/schedule/workflow/queue/rate-limit change.
- Evidence:docs/evidence/us-price-refresh-{queue,runs}-20261104.json.
  Investigation/reproduction:docs/us-price-refresh-investigation-20261104.md.
- New3 tests + existing history/US Stage/KIS readiness:23 passed,6 subtests.
  Compile passed. Full UTF8 Windows pytest452 passed/28 failed/7 skips; exact
  base449 passed/28 failed/7 skips. Both162 subtests passed; all FAILED/SUBFAILED
  lines exactly equal. Existing Windows fsync/source-encoding failures unchanged.
  Published Draft212 head5c114383; remote tree3860ce61 equals tested local tree.
  Final documentation-only follow-up CI must be checked on its resulting SHA.
- No live KIS/dispatch/rerun, activation, deployment, main/integration direct
  commit, merge, AWS/S3/Secrets/cost/permission or Nov5 automation changes.
  #207 post-change scheduled queue operation cannot yet be demonstrated.
- Draft PR: https://github.com/wonbosong-arch/global-stage-radar/pull/212
  Next:verify final SHA Python/Unit CI; review/merge is separate approval.
  No operational change is included in this diagnostic-only PR.


## 2026-11-05 US intake identity audit
- Base b37bf7b. US registry 2148; eligible unregistered 186. Offline only.
- Fixed pair identity/dedup and venue gate in intake only; regression before 2 failures, after pass.
- Related 71 passed/8 subtests; Windows rotation base comparison identical 10 failures.
- See docs/us-intake-audit-20261105.md and docs/evidence/us-intake-20261105.json.
- Remaining: submit Draft PR targeting data-validation-mvp; verify final head automatic CI. No merge or operational changes.

## 2026-11-05 US review-only Stage mapping expansion
- Fresh base 168ccf14c1a0043d37125a3438179920cb1156fa; independent
  feat/us-stage-mapping-expansion-20261105. Latest branches/open PRs/CI inspected;
  no competing US mapping expansion PR. Implementation b45d279 pushed remotely.
- Added 14 explicit sector/proxy suggestions with official fund holdings/issuer
  sources and retained KIS code corroboration. No general blank/000 code inference.
  New offline adapter reuses existing cap/KIS/weekly/RS/Stage helpers and never
  resamples the saved 72 baseline symbols or changes registry statuses.
- 13 additional names pass cap >=$1B, valid daily150/completed35 weeks, aligned
  SPY/sector ETF RS, freshness and retained KIS identity checks. IDXX has sufficient
  prices but lacks a linked KIS identity row; its label is withheld.
- Exact baseline comparison: export six original inputs from 9416654; all match
  the saved audit SHA256/byte counts after CRLF normalization only. At 2026-11-04:
  coverage72 ->85, Stage2 25 ->28, Stage2A5 ->5. New Stage2 D/NUE/PSA. Baseline
  recalculations0. Latest 2026-11-05 additions also13/Stage2=3/2A=0; the report
  deliberately withholds combined Stage counts for a different input snapshot.
- Related33 tests/84 subtests pass, including9 new regression tests. Full unittest
  386 run, OK/1 private-input skip. Sandbox /tmp/.git caused13 existing China
  private-root errors; creating /dev/shm/us-stage-tests and using it as TMPDIR
  resolves them without changing the guard. Full pytest with the same corrected
  temp setup is in progress; final result belongs in the PR. Compileall and all
  workflow YAML parses pass. Final documentation head automatic Python/Unit CI
  remains to be checked; do not infer success from an earlier implementation SHA.
- Sources, exact-snapshot/current evidence and reproduction commands are in
  docs/us-stage-mapping-expansion-20261105.md and three new docs/evidence JSONs.
- No main, original candidate/price data, active universe, engine thresholds,
  workflow/schedule, live KIS calls, status promotion, activation, merge or deploy.
  Next: submit Draft PR to data-validation-mvp, confirm final SHA Python/Unit CI
  and mergeability, fix any attributable failures. Merge/deploy require separate approval.

## 2026-11-05 — saved US sector evidence batch (independent follow-up)

- Base `38ef245532024073aa89ac84403f7980a40d0ff2`, branch
  `feat/us-bulk-sector-mapping-20261105`. #214 merged; its final Python/Unit CI
  succeeded. Read current branches, 13 open PRs and related Codex work; no open
  overlapping US mapping PR. No other PR imported or modified.
- Implemented a generic offline multi-record source join with exact listing/name,
  source/date, retained KIS-code, existing mapping and ETF metadata conflict gates.
  Reuses stock_mapping proposals, KIS/cap helpers and existing weekly/RS/Stage.
  Does not decode industry codes or write registry/approval/operational inputs.
- Full stored inventory: 2,148 US candidates; preserve 85 without replay. Only 13
  saved fund-membership annotations exist, all already in the 85. One issuer/KIS
  source (IDXX) passes price/benchmarks but lacks retained KIS identity. Therefore
  actual coverage85 ->85, new Stage2/2A0/0. Historical same-snapshot85 labels
  remain28/5; no claim of a current revalidation or mixed-snapshot total.
- 2,062 additional candidates lack explicit saved sector evidence. Overlapping
  blockers: identity55, cap29, valid completed35 weeks71, valid daily150 rows68.
  Of 199 existing curated proposals without a batch source,135 otherwise meet
  inputs/KIS/cap checks; their labels are withheld and they are not counted as
  validated new mappings. Need saved additional fund membership or explicit KIS
  industry metadata; no external full identity audit or API recollection.
- Related34 tests/66 subtests pass, including9 new tests. Full local unittest395
  OK/1 skip with external `/dev/shm` TMPDIR; initial `/tmp/.git` environment caused
  the same13 private-root errors as prior work. No guard modification. Full pytest
  in progress; compileall/14 YAML parses/diff and protected input checks pass.
- Evidence with hashes/exact symbol groups and reproduction/limits are in
  docs/us-sector-mapping-batch-20261105.md and its evidence JSON. Next: preserve
  commit, open independent Draft PR and verify exact final head automatic CI.
- No main/data/engine/active universe/workflow changes, KIS calls, manual Actions,
  approval/activation, merge or deployment. Actual coverage increase is blocked by
  saved evidence availability; do not describe the batch implementation as an
  achieved increase in analysis coverage.
- Follow-up whole-suite finding: local pytest497 passed/1 failed/7 skipped. The
  unmodified base test+CSV reproduced the same failure: Korean candidates grew
  to30 (033780), while a test hard-coded total29. Test-only fix keeps the29
  reviewed proposals and all pending/unassigned/status checks, allows additional
  unmapped discoveries only with sector_mapping_missing/blank proxy, and adds a
  synthetic appended-candidate regression. No Korean product/data changes.
- Related37 tests/66 subtests pass; rerun corrected whole suite and exact new-head
  CI before reporting full success. Original f02a7ed Unit CI succeeded; its Python
  run predates the stale-count test fix. Final result belongs in the PR body.
- Also replayed latest parallel automatic-price snapshot ddfa145 outside checkout:
  new eligible0, same blocker counts and135 conditional proposals. IDXX now has
  prices through11/04/freshness11/11 but still lacks KIS identity. Pinned evidence
  remains the start38ef245 snapshot. No original data was edited or rolled back.

## 2026-11-05 — NASDAQ official CSV access audit and local validation

- Fresh remote integration cac6c70; #215 merged, #216 Draft7d5a1c8 and #217
  Draft258477e unchanged. Their final-head PR Python/Unit CI passed. Open15 PRs
  and related idle chats checked; no duplicate Nasdaq work. Independent branch
  feat/nasdaq-local-csv-validation-20261105; no other checkout edits imported.
- Official screener has Download CSV but retrieved page has unavailable data.
  Full official /legal (updated2026-05-11) Sections2/6/7/8/11 checked. Personal
  use/button is not permission for data capture/analysis-software development,
  storage or redistribution. Project permission not established. Download
  attempts0/success0; fields/rows/venues/missingness/sector/135 matches unmeasured.
  No hidden endpoint, scraping, bypass,403/429 retry or raw CSV upload.
- Minimal stdout-only local validator; user-declared permission/hash/UTC before
  input, Git-external real CSV only. Exact ticker+venue and evidenced same-class
  notation aliases; missing exchange needs documented export filter. Native
  sector observations stay separate from GICS/ETF/Stage. Reuses saved_baseline
  and existing batch cohorts2148/85/135; no current Stage replay or activation.
- New12 synthetic tests plus batch9:21 pass/46 subtests. Full Windows tests and
  final-head automatic CI pending at this checkpoint. No real dataset/coverage
  counted from synthetic validation. Documentation/audit record the access
  limits, null measurements and permission-first manual/offline workflow.
- No original data/UI/engine/workflow/cron/queue changes, main/integration edits,
  KIS live, manual Actions, keys/accounts/Secrets/cost, merge/deploy/approval.
  Next: preserve tested Draft PR and final SHA CI; actual measurement needs
  documented purpose-specific Nasdaq permission and a manually supplied file.
- Full Windows UTF-8 pytest487 passed/28 failed/7 skipped/236 subtests passed.
  Untouched merged-base replay of four failing modules reproduces the exact28
  expanded failure lines; no additional failures. Existing Windows fsync/POSIX
  shell/numeric-path issues remain outside scope. Final focused21/46 pass after
  provenance-hash fields; compile and14 workflow YAML parses/audit JSON valid.
  Final-head automatic CI remains pending and will be recorded in the PR body.
# 2026-11-05 — Nasdaq supplied CSV single-source continuation

- Rechecked GitHub integration `cac6c702603b0e4c967a3cc1cc5eba34564716ed`,
  merged #215, unchanged Draft #216/#217/#218 and related idle chats. No other
  mapper implementation is active. Extend the existing independent #218 branch;
  do not create a duplicate PR or merge another Draft.
- Added `nasdaq_single_source.py`, exact native Sector+Industry -> 11 ETF proxy
  rules, KIS/name/type unique-symbol joins when source Exchange is absent,
  explicit class-alias/collision handling, private supplied-file provenance,
  local Stage replay and separate price-only diagnostics. Reuse #218 parsing
  and #215 identity/cap/replay/engine functions. Keep source dates unknown when
  unknown; no independent exchange lookup or blanket license blocker is added.
- Preserve historical85 and independently re-evaluate their saved mappings on
  the same date/current stored prices as additions. Historical label counts are
  never summed with current results. Unclear industries/conflicts stay held.
- Added synthetic regression tests and `docs/nasdaq-single-source-offline.md`.
  External raw/derived enterprise data and measurements remain private outside
  this source snapshot. Do not commit the private report or original CSV.
- Final focused verification: 74 tests/106 subtests passed, including the new
  guards and neighboring private-path policies. Windows unittest418 ran with
  26 existing errors; the unchanged parent reproduces the known28 pytest
  failures in the same four Windows-specific modules. Private actual replay
  completed; original input hashes preserved. Full-suite final run/remote
  exact-head CI will be recorded in the PR after source publication.
- No integration/main changes, merges, deployment, live KIS, schedule/Actions
  configuration changes or paid/account/secret operations. Next: finish private
  validation, inspect allowed-file diff, publish to existing #218 with head lease,
  verify automatic CI, report private measured exceptions in Korean.

## 2026-11-06 — Resume existing Draft #218 on refreshed integration

- Rechecked open PRs, branch heads, recent Actions and related chats. #216/#217
  remain separate Drafts; no duplicate Nasdaq implementation was active. Pinned
  latest integration `090e58b915a35800259e2bd255b66226155264b4` and existing #218
  head `c90c4247a7317b4ff18f97946a0a588d01056e9e` in an isolated checkout.
- Integrate the latest target as a second parent of the #218 continuation,
  preserving published history. Target delta: ten data-only commits/31 paths;
  automatic merge is clean. Every data file matches the pinned target exactly.
  No feature edits to data, main, integration, UI, engine or workflow settings.
- Policy v2 adds 19 exact narrow Sector/Industry proxy pairs. Broad software,
  EDP, REIT, marine transport and uncertain equipment stay withheld. Native
  labels, the 11-ETF scope, existing-proxy conflicts and identity/price gates
  remain in force; no additional classification source or live request.
- Fix the adjacent validator regression that pinned a historical discovery
  count: a synthetic appended candidate must be counted while saved cohorts
  retain membership. Also cover the case where a refreshed KIS master loses
  a saved baseline member; its historical label cannot enter current totals.
- Focused six-module suite: 59 passed/114 subtests passed. Full Windows suite
  and exact-head automatic CI pending at this source checkpoint. Compare v1/v2
  against identical current inputs and evaluation date in private local output;
  detailed measurements/exceptions and supplied CSV never enter Git or CI.
- No new PR, merge into target, activation/deployment, live KIS, manual Actions,
  cron/workflow, Secrets/account or paid-service operations. Next: finish private
  replay validation, check the final-head CI, and update the existing Draft body
  with actual validation status and any remaining limitations.

# 2026-11-06 — Hosted Nasdaq pilot failure and safe diagnostics

- Revalidated exact #220 head20dee804: 3 successful CI checks, clean/mergeable,
  no reviews/unresolved threads. Actual default data-validation-mvp; main997628e
  unchanged. #219/#216/#217 retained Draft at their prior heads; no competing
  active Nasdaq chat. Ready then authorized merge dfa73ffc; tree equals tested
  source. Post-merge CI42161389296 success: unittest429/skip1, pytest533 pass/
  7 skip/281 subtests; workflow syntax and compilation pass.
- One manual opt-in hosted pilot42162170485, attempt1, exact merge SHA, failed.
  Install succeeded; acquisition step emitted only Error/exit2 after2.3 seconds.
  Download/11fields/rows/native validity/quality unmeasured; no verified hosted
  last-good fallback. No rerun, further download, API substitution or bypass.
- Fresh independent fix branch from merge SHA: allowlisted failure phases and
  numeric observed HTTP status only; failure/fallback aggregate summary file,
  nonzero status retained; always-report after failed refresh. Preserve original
  browser failure if secondary guard body-read fails; denial/challenge and bounded
  timeout retry unchanged. No raw exception/response/URL/path output.
- Synthetic focused59 tests/91 subtests pass. Six new/expanded behavioral
  regressions each fail on untouched #220 source; six new tests and one expanded.
  Exact-head automatic full CI pending at source checkpoint. See hosted-result doc.
- Weekly Sunday07:00 KST / cron0 22 * * 6 confirmed in docs only. Failed hosted
  prerequisite blocks schedule/persistence activation. No new Secrets/store/cost,
  data publication, main/other Draft changes, deployment or operational additions.
  Next: preserve diagnostic Draft and exact-head CI; a second hosted pilot needs
  a later explicit instruction. Do not run it while checking synthetic CI.

# 2026-11-06 — Pilot 3 navigation diagnostic preparation

- Fresh independent branch from integration/default eff2834969478c3c1a1f5cecb0c42124a9e2cfdb.
  Latest post-merge CI successful; other open Draft heads retained. No competing
  active Codex task or running Actions job observed at start.
- Add allowlisted Chromium network codes and exception types; distinguish DNS,
  TCP, TLS, network timeout, closed browser and protocol failures. Observe numeric
  Nasdaq main-frame navigation status even if goto throws. Denial/challenge
  remains terminal. No new network probes, body/URL/log disclosure or bypass.
- Hosted dispatch explicitly uses one attempt with no timeout retry; local
  default retry behavior and existing quality, exit-2/fallback integrity preserved.
- Focused monthly/navigation tests: 21 passed, 32 subtests. New regression run
  against untouched integration collector fails as expected (25 failed assertions
  including subtests); synthetic only. Full Windows UTF-8 run and exact-head
  hosted CI pending at this source checkpoint; initial Windows run encountered
  existing cp949 decoding errors in unrelated chart JS loading.
- Authorized next: Draft PR to data-validation-mvp, exact-head full CI, ready/merge
  without protection changes, post-merge CI, then exactly one opt-in dispatch.
  Stop on failure without retry/rerun. No main/KIS workflow/Draft changes,
  schedule, Secrets/account/cost/default changes, data publication or activation.

# 2026-11-09 — Nasdaq weekly upload flow in Draft #225

- Continue from Draft head `5fc456f` on integration `835769a`. The dashboard
  exposes the opt-in public uploader above Data Management. The existing app
  password unlocks the session. File selection and a blank, explicitly attested
  UTC download date trigger validation. The publication button records one
  explicit approval for the validated bytes and expected GitHub head.
- Show last save time in KST, symbol/classification coverage and weekly upload
  status. Detect identical saved bytes before prompting for a date, retain the
  verified snapshot on failure and reload it on a new authenticated session.
- Synthetic Streamlit tests cover authentication, no write before approval,
  rejected writes, duplicate detection and cold recovery. The browser workflow
  exercises the dashboard with a fake GitHub API and checks chart selection.
- Next: confirm head CI and review Draft #225. Operator setup and deployment
  remain pending, including the dedicated branch and server token.
