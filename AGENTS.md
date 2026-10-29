# Development and Regression-Prevention Rules

These rules apply to all AI-assisted changes in this repository, especially the Streamlit UI in `app.py`.

## Protected integration target
- Work only from a fresh `data-validation-mvp` base and submit changes through a focused pull request targeting `data-validation-mvp`.
- Never edit or merge into `main`; it is maintained separately.
- Do not directly commit feature changes to the integration branch. Keep each change on its own branch/PR so it can be reviewed and reverted independently.

## Preserve existing behavior
- Treat every previously accepted feature and user requirement as a regression constraint, not as disposable context.
- Before editing, inspect the current implementation and the recent changes to the affected code. Identify neighboring features that share state, rendering, navigation, data, or callbacks.
- Make the smallest targeted change possible. Do not replace a whole function/file with an older or simplified version when a narrow patch will do.
- If work is split across branches or PRs, start from the latest integration branch and ensure the new branch includes all already-merged fixes. Never merge a stale snapshot over newer code.
- Before opening a PR, inspect the complete diff against its target branch. Investigate unexpected deletions, reversions, or unrelated edits.

## Regression tests are required
- Every bug fix must add or update an automated regression test that would fail before the fix and pass after it.
- When fixing feature B in code that also supports feature A, test both: the new behavior in B and the already-working behavior in A.
- For UI/navigation changes, cover the full user sequence, including reruns, page changes, mode changes, and relevant independent sections where applicable. Source-text assertions alone are not enough when a behavior-level test is feasible.
- Run the relevant test suite and the repository's full automated CI checks before merging. A successful test run on a stale commit does not validate a newer commit; verify the tested SHA matches the PR head.
- After merging, confirm the integration branch contains the intended fix and that earlier accepted fixes remain present. Report hosted-app behavior as unverified until actually checked.

## Change tracking and user communication
- Keep PRs focused and describe: the reported problem, the intended change, related behavior that must remain unchanged, tests added/run, and any checks not performed.
- Maintain a short list of accepted UI behaviors and add to it when the user confirms a requirement. Use that list when reviewing changes that touch shared UI code.
- Clearly distinguish code changed, automated tests passed, merged code, and live deployment verified. Never imply one proves another.

## 장시간 작업 및 사용량 한도 대응 원칙

1. 큰 작업은 기능 단위로 분할한다.
2. 완료한 기능은 독립적인 커밋으로 저장한다.
3. 작업 중간에도 원격 작업 브랜치에 푸시하여 변경 사항을 보존한다.
4. 작업 진행 상황을 `CODEX_PROGRESS.md`에 기록한다.
5. 진행 기록에는 완료한 작업, 미완료 작업, 테스트 결과, 다음 실행할 작업을 포함한다.
6. 작업이 중단된 후 재개할 때는 기존 커밋과 진행 기록을 먼저 확인한다.
7. 이미 완료한 작업은 반복하지 않는다.
8. 원격 저장에 실패하면 해당 사실과 보존되지 않은 변경 사항을 명확히 보고한다.
9. `main` 브랜치는 수정하지 않는다.
10. 기능 변경은 별도 작업 브랜치에서 진행하고 `data-validation-mvp`를 대상으로 PR을 생성한다.
