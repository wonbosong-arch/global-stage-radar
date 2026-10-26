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
