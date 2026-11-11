# Development and Regression-Prevention Rules

## Provider trust policy (user decision 2026-11-03)
- Read `docs/provider-trust-policy.md` before price readiness work. Across all markets,
  trust KIS prices and KIS adjusted prices by default. Independent exchange matching
  and adjustment-formula reconstruction are not Stage prerequisites. Use the same
  basic quality checks for fallback providers in KIS-unsupported markets. Investigate
  deeply only when concrete errors occur. Preserve identity/support and quality checks.

These rules apply to all AI-assisted changes in this repository, especially the Streamlit UI in `app.py`.

## Personal, non-commercial research scope (user decision 2026-11-10)

- **Declared purpose:** Global Stage Radar is the user's **personal, non-commercial, non-public investment-research tool**. The user has no plan to commercialize it or publicly release the dashboard. Assume this scope in ordinary development unless the user changes it. Do **not** stop public-source research, metadata investigation, index/sector mapping, local-only validation, or synthetic testing merely because a provider warns against *commercial* use. Do not repeat generic commercial/public-release warnings or demand unnecessary approvals on every task. Restrictions that actually apply to private use, secrets, technical access, or the public GitHub repository still apply.
- **Own use versus sharing:** JPX's published [terms](https://www.jpx.co.jp/english/term-of-use/) explicitly distinguish using TOPIX or other indices as indicators for one's **own use** (no index license required) from disseminating, showing, or providing those indices to **third parties** (license required under JPXI rules). Non-commercial intent **does not automatically authorize** third-party display, redistribution, bulk republication, use of protected files, or access that a separate product's terms restrict.
- **Repository and dashboard boundary:** Treat the GitHub repository as **public**. Keep rights-uncertain exchange raw files and stock-by-stock proprietary datasets, licensed index-level histories, credentials, and potentially redistributable derived files **out of Git and public CI artifacts** until the relevant terms permit their distribution. A publicly accessible dashboard may constitute third-party display even if no fees are charged. Research code, synthetic tests, source links, and original non-infringing summaries may be committed as usual.
- **Practical workflow:** First identify whether the requested action is personal consultation/analysis, private collection and processing, or public distribution/display. Apply a restriction only where a specific source term, technical access rule, privacy/security concern, or planned external release makes it relevant. Do not infer that *all personal data processing is forbidden* from a commercial-use warning. If a real limitation remains, briefly identify the **specific blocked action** and proceed with all independent permitted steps; record uncertainty instead of inventing permission.
- **Reassess only on scope change:** Revisit applicable terms if the user starts commercializing the dashboard, distributing provider datasets, publicly showing restricted index values, or switching to a separately licensed data product. This policy does not waive laws, provider terms, or existing data/security protections.

## Protected integration target
- Work only from a fresh `data-validation-mvp` base and submit changes through a focused pull request targeting `data-validation-mvp`.
- Never edit or merge into `main`; it is maintained separately.
- Do not directly commit feature changes to the integration branch. Keep each change on its own branch/PR so it can be reviewed and reverted independently.

## Autonomous PR integration (user decision 2026-11-11)

- **Default: merge without repeat approval.** For focused development PRs targeting `data-validation-mvp`, complete implementation, relevant regression checks, final-head required CI, conflict/impact checks, and the required GitHub branch-protection and review gates. Recheck the exact PR head and integration head immediately before merge. When these conditions pass, mark a draft ready, merge through the PR, verify the post-merge CI, and report the outcome afterward. Do not stop merely to ask for routine merge approval.
- **Safety gates.** Do not automatically merge changes to `main` or another protected target, real CSV/source data, operational symbols/ETF activation, deployment or secret management, significant architecture, paid services, or work interfering with another developer. Do not automatically merge when required checks fail, relevant regression risks remain unresolved, or GitHub review/branch-protection rules are unmet. Obtain explicit user approval only for these exceptions.
- **Do not confuse states.** Distinguish investigation, implemented code, PR-head CI, merged-and-post-merge-verified code, and confirmed hosted dashboard behavior. Fix a failing post-merge CI within already approved bounds when possible; otherwise report the blocker. Never infer that code merge alone increased live market coverage.
- **Data boundaries.** Previously authorized recurring collection may continue within its approved scope, but a development PR must not silently write actual CSVs or activate an unapproved symbol. A missing saved price series does not prove that a live KIS query or instrument support failed.

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

## Goal-directed work and resource efficiency (user decision 2026-11-07)

- **Goal first:** Define the user's requested outcome and acceptance criteria before implementation. Prefer an outcome the user can actually use over optional technical polish; do not treat research, passing tests, a PR, or an unverified deployment as proof of user-facing completion.
- **Minimum sufficient implementation:** Reuse current code, evidence, and tools; make the smallest change that meets the acceptance criteria. Do not start unsolicited refactors, extra features, or repeated repository-wide analysis. Preserve the existing regression protections above.
- **Bounded retries:** If the same root-cause approach fails twice, pause that approach and compare an alternative, workaround, or deferral against its value and cost. Attempt it a third time only with new evidence or a materially changed method; do not evade the limit by renaming the same retry.
- **Risk-based verification:** Always honor applicable security, data-integrity, regression, and required pre-merge CI gates above. Focus exploratory checks on changed behavior and affected dependencies; avoid redundant independent audits or broader verification without a concrete failure signal or requirement. A faster local check does not waive full pre-merge CI.
- **Opportunity cost:** Before extending investigation or implementation, weigh expected user benefit and likelihood of success against remaining effort, usage, and better available tasks. Defer low-value optional work; do not defer critical outages, security issues, or confirmed data-integrity errors.
- **Stop at acceptance:** Once the original acceptance criteria are met and required checks are complete, stop expanding scope. Record optional improvements separately as candidates rather than making them prerequisites. If actual deployment or usability is not verified, report that explicitly instead of claiming full completion.

## 장시간 작업 및 사용량 한도 대응 원칙

1. 큰 작업은 기능 단위로 분할한다.
2. 완료한 기능은 독립적인 커밋으로 저장한다.
3. 작업 중간에도 원격 작업 브랜치에 푸시하여 변경 사항을 보존한다.
4. 작업 진행 상황을 `CODEX_PROGRESS.md`에 기록한다.
5. 진행 기록에는 완료한 작업, 미완료 작업, 테스트 결과, 다음 실행할 작업을 포함한다.
6. 작업이 중단된 후 재개할 때는 기존 커밋과 진행 기록을 먼저 확인한다.
7. 이미 완료한 작업은 반복하지 않는다.
8. 원격 저장에 실패하면 해당 사실과 보존되지 않은 변경 사항을 명확히 보고한다.
