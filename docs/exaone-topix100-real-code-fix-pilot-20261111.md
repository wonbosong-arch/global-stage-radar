# K-EXAONE TOPIX100 실제 코드 수정 파일럿 — 2026-11-11

## 목표 및 기존 자산

- 대상: 공식 JPX 월말 명부 기반 **TOPIX Core30 30종목 + Large70 70종목**의 비공개 업종 분류 검증. 추가 시가총액 기준 없음.
- 기존 GPT 작성 [연구용 검증 도구 PR #234](https://github.com/wonbosong-arch/global-stage-radar/pull/234), 최종 확인 원본 SHA `377c3e4f48a824882ff9d0325fa48cc6653fdd3c`를 **수정 대상으로 재사용**한다. PR #234는 Draft이고 미병합. 이번 파일럿은 기존 전체 검증 도구를 재구현하지 않는다.
- 확인된 결함: 원본 파일은 리포지터리 루트에 있지만 `REPO = Path(__file__).resolve().parents[1]`로 정의해 **저장소 상위 디렉터리까지 보호 경계로 인식**한다. 정상적인 개인 연구 폴더(같은 상위 폴더의 형제 디렉터리)를 잘못 차단할 수 있다. 기존 테스트는 이 잘못된 전제를 답습한다.
- **EXAONE이 작성할 실제 코드:** 모듈의 REPO 정의와 `safe_outside_repo` 함수만 고치는 최소 교체안. GPT가 정답 패치를 직접 병합하지 않는다.

## 위임 및 평가 방식

1. `automation/exaone_japan_path_fix_codegen.py`가 원본 버전 고정 SHA에서 두 구문만 읽어 EXAONE API에 전달한다. 1회 요청 `k-exaone_v2.5`, `reasoning_effort=low`, `max_tokens=4096`, 자동 재시도 없음.
2. 응답은 두 필드 `repo_assignment`, `replacement_function`만 받는다. 모델이 직접 작성한 Python 코드는 비밀키가 있는 작업에서 **실행하지 않는다**. 원본 종목 데이터·API 가격값도 전달하지 않는다.
3. `.github/workflows/exaone-japan-path-fix.yml`: 수동 실행, 기본 `live=false`. 사용자 허가로 `live=true`를 선택해야 **최대 1회 EXAONE 모델 호출**.
4. 두 번째 `verify-candidate` 작업은 별도 비밀키 없는 GitHub 러너에서 `docker --network none --read-only --user 65534` 등의 격리 설정으로 실행. 모델 패치를 일회성 임시 폴더에만 적용한다.
5. [PR #234](https://github.com/wonbosong-arch/global-stage-radar/pull/234)의 **기존 13개 합성 단위 테스트**, 추가 저장소 루트·내부·형제 디렉터리·심볼릭 링크 경계 테스트를 통과해야 `verified` 결과물로 저장한다. 실패 시에는 미검증 후보로만 보존하고 수동 분석한다.
6. 검증된 모델 산출물조차 **자동으로 PR #234에 적용하거나 병합하지 않는다**. 검토 후 별도 독립 변경 및 CI가 필요하다.
7. 사용량은 API 반환 prompt/completion/total/reasoning 토큰과 API 응답시간을 기록한다. 해당 헤더/사용량이 없으면 `미확인`으로 표시. 모델 제공량을 실제 공급자 한도로 오인하지 않는다.
8. 재시도는 실패 원인을 비교해 새로운 근거가 있을 때만 진행한다.

## 평가 목표

- EXAONE이 단순 요약이 아니라 기존 코드의 **실제 문제를 수정하는 코드**를 만들었는가?
- 기존 동작을 회귀시키지 않고 새로운 경계 조건을 통과했는가?
- 합성 테스트에서 원본은 실패하고 모델 수정 후에는 통과하는가?
- 추가 사용자 개입/모델 호출 수가 이 작은 변경의 사용자 효용에 비해 적정한가?

**중요 제한:** 이번 파일럿의 유효한 모델 성과는 코드 작성·검증에 한정한다. JPX 월말 파일 직접 다운로드나 **TOPIX100 실제 100종목 실측**은 이번 API 작업에 포함되지 않으며, 아직 검증 완료로 주장할 수 없다.

## 출처 및 기존 성과 재사용

- [JPX 월말 상장종목 명부](https://www.jpx.co.jp/english/markets/statistics-equities/misc/01.html): 종목코드, 업종 분류, 규모 구분의 월말 자료.
- [J-Quants 종목 마스터 필드](https://jpx-jquants.com/en/spec/eq-master): `S33`, `S17`, `ScaleCat`의 공식 명세.
- [이전 EXAONE 공식 자료 조사 실측 성공 #42929943785](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/42929943785): 67.749초, prompt 928 / completion 1970 / total 2898 / reasoning 1594. 공식 근거 요약만 수행했고 코드 작성 능력은 검증하지 않음.

## 보호 및 진행 상태

- 통합 대상 `data-validation-mvp`; `main` 수정 금지.
- 실데이터·가격·ETF·미국 종목·운영 앱 불변. 코드는 기존 PR #234의 해당 경계 오류만 대상으로 하며 동시 수정 충돌은 피한다.
- 이 파일럿에서 아직 모델 API 실행/실제 코드 생성 **0회**, 코드 생성 스크립트와 **검증 파이프라인 준비 중**. API 자동 호출, PR 자동 병합, 운영 활성화 없음.
- 누적 일본 EXAONE 공식자료 조사 요청 시도 3회(성공 1회)는 별도 항목으로 계속 추적한다. 이번 코드 생성 파일럿의 요청 회계는 분리한다.
