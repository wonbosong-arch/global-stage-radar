# GPT Migration Workspace Ownership & Change Rules

**Workspace label:** GPT-assisted migration  
**Integration target:** `data-validation-mvp`  
**Working branch:** `gpt/migration-main-to-data-validation-mvp`  
**Last updated:** 2026-10-26

## Scope boundary
- This GPT-prefixed branch is the designated workspace for this migration.
- Keep migration changes here and propose them to `data-validation-mvp` through draft PR #49.
- Do not make unrelated edits to `main`, `data-validation-mvp`, existing Streamlit apps/settings, secrets, or PR #46.
- Preserve original branches; do not force-push or reset them.
- Review all workflow checkout and push targets before merging.
- Candidate activation remains blocked pending review.
- Manual hosted-app and live KIS validation are intentionally skipped per user direction.
- Automated CI passed on commit `ee1e29db8e06708848e3f7d0964e71e95a51eaeb`: workflow YAML syntax validation, Python compilation, and unit tests.
- A recursive Git tree audit confirms all 68 tracked files on `main` and all 32 tracked files on `data-validation-mvp` are present on this workspace branch; see `MIGRATION_COMPLETENESS_REPORT.md`. This confirms file presence, not replay of all historical commits.
- Static workflow review found data-commit targets set to `data-validation-mvp`; the adapted schedules are not active while the repository default remains `main`.
- A KIS stock-candidate discovery script, a pending-only scheduled workflow, and unit tests were added. It never activates candidates or overwrites existing manual-review decisions.
- Market-cap screening now requires a verified stock security class; unclassified instruments remain pending.

## Important limitation
The GPT prefix and this file are **labels, not locks**. Other AI tools or collaborators can still edit this branch if their GitHub credentials allow it. Technical enforcement requires repository rulesets/branch protection (require pull requests, restrict direct pushes, and require owner approval where available). CODEOWNERS alone does not block writes unless branch rules require code-owner review.

## Workflow note
GitHub scheduled workflows run from the repository's default branch. The copied workflows target `data-validation-mvp` for data commits, but their schedules will not automatically activate merely because they exist on this draft branch. Confirm the intended default/deployment branch before enabling scheduled jobs.

## Core-first execution and parallel exceptions
- Finish the end-to-end MVP path before polishing isolated symbols.
- Handle each failed symbol independently: record symbol, failed step, provider/error, last successful date, next action, and review status. Keep unresolved symbols pending; never silently drop or verify them.
- Continue unaffected symbols and core development. Isolate per-symbol errors so one ticker cannot fail a batch. Use bounded retries for transient errors; avoid repeated retries for permanent identity/provider mismatches.
- Work in parallel on independent areas (core pipeline/UI, symbol-specific exceptions, tests/docs) when files and prerequisites do not overlap. Use separate branches/PRs for conflicting edits.
- Escalate an issue to core priority when it points to a shared provider, schema, rate-limit, currency conversion, or pipeline defect.
- Missing/unverified stock market cap stays pending; exclude only verified stocks below USD 1B. ETFs and market/sector/commodity proxies are exempt.
- Report MVP progress separately from unresolved-symbol count. State verified results separately from assumptions.
- Do not run hosted Streamlit or live KIS validation unless explicitly requested. Preserve `main` and deployment settings; target `data-validation-mvp` through GPT-prefixed branches and PRs.
