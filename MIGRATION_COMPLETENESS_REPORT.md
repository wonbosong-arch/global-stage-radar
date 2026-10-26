# Migration completeness report

**Audit date:** 2026-10-26  
**Source snapshot:** `main`  
**Integration target:** `data-validation-mvp`  
**Audited branch:** `gpt/migration-main-to-data-validation-mvp`  
**Pull request:** [#49](https://github.com/wonbosong-arch/global-stage-radar/pull/49)

## File-presence audit

GitHub recursive tree comparison was run against both source and target branches.

- Tracked files on `main`: **68**
- Tracked files on the GPT workspace branch: **75**
- Tracked files on `main` absent from GPT workspace: **0**
- Tracked files on `data-validation-mvp`: **32**
- Tracked files from `data-validation-mvp` absent from GPT workspace: **0**

The GPT workspace therefore contains every tracked file present in both the current source snapshot (`main`) and integration target (`data-validation-mvp`). Seven additional files provide GPT workspace ownership rules, candidate-discovery code, documentation, workflow, and tests.

This is a **file-tree completeness audit**, not a claim that all historical commits from `main` were replayed. The migration intentionally did not merge the highly divergent `main` history wholesale.

## Intentional differences from the source snapshot

The following areas were adapted or extended rather than copied byte-for-byte:

- GitHub workflows that need to read or commit generated files were reviewed and adapted to target `data-validation-mvp`; they must not write to `main`.
- Dashboard, Stage engine, data-provider, candidate-review, and monitoring files retain the target branch's project work where appropriate.
- The candidate discovery workflow and its tests/docs are new.
- Market-cap screening now requires a verified stock classification; unknown security types remain pending rather than passing the market-cap threshold.
- Unit-test fixtures were updated to identify the instrument type explicitly where a positive stock-cap result is expected.

## Verification status

- Automated Python compilation: **passed**
- Automated unit tests: **passed** on commit `ee1e29db8e06708848e3f7d0964e71e95a51eaeb`
- Workflow YAML syntax validation: **passed**
- Hosted Streamlit app verification: **not performed** (intentionally skipped per user instruction)
- Live KIS API validation / scheduled collection: **not performed** (intentionally skipped per user instruction)

## Remaining release gate

PR #49 remains draft and unmerged. The repository default branch is currently `main`, and GitHub scheduled workflows run only from the default branch. Consequently, the schedules in this workspace are not active just because their files exist here or because the PR is merged into `data-validation-mvp`. Do not change the default branch or existing app settings without an explicit deployment decision.

The existing `main`, `data-validation-mvp`, and PR #46 were not merged, reset, or force-pushed as part of this audit.

## Dashboard feature review (static code inspection)

The current `app.py` contains the requested screen structure and chart interactions:

- Separate tabs for **국가 및 원자재**, **업종**, and **종목**.
- List view and up-to-nine chart grid (3 columns), with a detail-chart action from grid cards.
- Daily/weekly chart selector, candlestick OHLC, a moving-average overlay, volume beneath price, close-to-close percentage change in hover, and Plotly scroll zoom.
- Stage 2 screening based on completed weekly bars, 30-week SMA/slope, and market/sector relative strength; volume is shown as soft context rather than a hard pass/fail rule.
- ETF rows are not subjected to the stock market-cap cutoff.

This was a **static source review only**. It does not establish that the hosted Streamlit app renders correctly, that every KIS symbol is supported, or that stored price data is fresh.

## Merge side effects to be aware of

The adapted `daily_prices.yml` and `candidate_collection.yml` have push triggers on `data-validation-mvp`. Merging this PR changes those workflow files on that branch and can trigger a one-time live KIS request and data-commit attempt. This has not been triggered from this workspace. The regular schedules still will not run until the workflow definitions are present on the repository's default branch (`main`) or the default-branch strategy is deliberately changed. Do not merge solely on the assumption that schedules will become active automatically.
