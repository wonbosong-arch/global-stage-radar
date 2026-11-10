# EXAONE + OpenCode: review-only coding agent (initial readiness)

This is a **manual-only, opt-in** coding experiment, separate from the existing EXAONE sector-classification pilot. No production data or repository file can be changed by the OpenCode agent in this workflow.

## Launch and task choices

The `EXAONE OpenCode isolated coding PoC` workflow accepts:

| Input | Default | Description |
| --- | --- | --- |
| `task` | `ticker-smoke` | An allowlisted task name, NOT arbitrary instructions |
| `live` | `false` | Offline checks only; no key or EXAONE request |
| `live=true` | Explicit opt-in | Call EXAONE once per manual workflow run, subject to internal agent continuation requests |

There are two strictly allowlisted tasks, defined in `automation/exaone-opencode-poc/runner.py`.

1. `ticker-smoke`: create `ticker_utils.py` only in an empty scratch workspace. Demonstrates that an agent can write a Python file using tools.
2. `exaone-regression-tests`: review copies of `exaone_sector_pilot.py`, `stock_mapping.py`, the original tests and sample fixture. Create **only** a new `tests/test_exaone_sector_pilot_agent.py` containing at least two regression tests, for review. This is the first actual project maintenance task. The agent is not permitted to change the referenced code.

Before a live run, the workflow copies only the task's allowlisted reference files into an isolated temporary directory. The checked-out repository remains read-only to the workflow. The agent's working directory has no repository credentials, and the OpenCode config grants `read` and `edit` only, denying everything else including shell, subagents, external directories and web tools. These are tool permission controls, **not a hardened operating-system sandbox**.

The runner verifies a fixed allowlist of file paths and source hashes, checks the Python syntax and imports in the generated file, but **never imports or executes the generated source**. Unexpected modifications or files fail the run. After a successful live run, only the generated Python source is retained as a downloadable Actions artifact for three days. No model transcript or request body is published.

## Authentication and cost control

- GitHub Actions key source: existing repository secret `EXAONE_API_KEY`, available only in the model invocation step for `live=true`.
- Fixed official OpenCode CLI version: `@opencode/cli@2.2.6`; no local install for the user.
- Model: `exaone/k-exaone_v2.5` via LG official-compatible OpenCode provider configuration.
- Limits: one manually selected task, one agent command, 180-second external timeout, eight-minute job timeout, no workflow retries and no schedules.
- **Important:** The agent may make multiple model requests and its internal retry/token consumption is **not hard-capped** by this workflow. Do not treat it as a one-API-call test. Keep usage limited to the approved task and monitor account usage before widening it.

## Validation and next gate

Existing PR CI runs offline Python tests for task preparation, tamper detection, forbidden files/imports, config and no-execution verification. The workflow itself can only be dispatched once merged into the repository default branch `data-validation-mvp`. A green PR CI is **not proof** of a working live OpenCode-to-EXAONE session.

**No live coding task has been run** by this PR. First live run requires separate explicit approval: merge this PR into `data-validation-mvp`, then select `task=ticker-smoke`, `live=true` in Actions, inspect the resulting Python source and usage; only then try `exaone-regression-tests`. No PR auto-creation, branch write, scheduler or operational activation is included.

Sources: [LG EXAONE agent setup](https://docs.exaone.ai/en/docs/agent-start), [OpenCode CLI](https://opencode.ai/docs/cli/commands), [OpenCode permissions](https://opencode.ai/docs/permissions/).

## Generated-code behavior gate (subsequent safety fix)

The first live `ticker-smoke` run completed structurally but generated a
normalization bug (lowercase / whitespace inputs were rejected). This showed why
syntax-only success is insufficient.

For subsequent live runs, the workflow now has **two separate jobs**:

1. `generate-candidate` uses the EXAONE secret only during OpenCode invocation;
   structural validation runs without executing the generated code. Its artifact
   is explicitly called `exaone-opencode-unverified-candidate` (1-day retention).
2. `verify-behavior` runs on a **different GitHub runner with no EXAONE key**.
   It downloads the candidate and executes it only in a temporary Docker
   container with `--network none`, read-only mounts and root filesystem,
   dropped Linux capabilities, restricted process/memory/CPU resources and a
   60-second timeout. This runs deterministic ticker test vectors or at least
   two generated regression tests, according to the approved task. Only passing
   output becomes `exaone-opencode-verified-code`.

There is **no automatic re-prompt or paid retry** on failure. The workflow
fails instead; review the failure and only then decide whether to regenerate.
Successful functional checks do not replace human review, since malicious or
weak test implementations can still pass limited tests. No generated code is
automatically committed, merged or activated.

The standalone offline regression tests in
`tests/test_exaone_opencode_behavior_gate.py` deliberately reproduce the first
ticker normalization bug and assert it is rejected. First live re-validation
and any follow-on project task require separate workflow dispatches.

## First project-task timeout and reduced retry scope (2026-11-10)

GitHub Actions run [42762382008](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/42762382008) tried `exaone-regression-tests` and stopped after the 180-second model-command timeout. OpenCode installation and scratch preparation passed; no candidate was published and the separate behavior gate was correctly skipped. The secret-bearing agent session log is deliberately not uploaded, so the underlying model/tool bottleneck is unknown.

The next attempted task is now deliberately smaller: generate just **two** focused `parse_completion` unittest cases in a single new file of fewer than 70 lines, reading the pilot source only as needed. The supplied reference set was reduced from four files to two. No workflow time or automatic retry budget was increased.

On future errors the workflow prints only the exit status, whether the 180-second timeout occurred, and whether a candidate file exists; it never exposes raw prompts, responses, or the session transcript. A second equivalent failure should trigger alternative approaches (e.g. simpler direct API generation plus manual review) rather than repeating the same agent run.

A green PR CI verifies only offline logic. This mitigation must not be described as validated with live EXAONE until a separate approved manual run succeeds. Existing no-secret behavior testing and `main`/production protections are unchanged.

## First short EXAONE run: scratch-file validation failure (2026-11-10)

[Actions #42763942875](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/42763942875) ran the narrowed task. OpenCode returned successfully in about 40 seconds, but the subsequent file-set check raised `unexpected_file_changes`. The run did not record path details, so we **cannot** establish whether the requested output file was created, which extra files appeared, or whether its content would have passed behavioral tests.

The verifier now treats extra temporary files as *untrusted scratch data* and ignores them only within the temporary agent working directory. It does not upload, import, execute, or commit these files. The following remain mandatory:
- All expected reference/config/manifest/instruction files must remain present and unchanged.
- The one approved output file must exist, parse successfully, satisfy import/size and test-count restrictions, and be the only code copied to the candidate artifact.
- Symbolic links and excessive scratch-file creation still fail closed. Raw extra filenames and contents are not logged.
- A separate no-secret, networkless behavior-check job must succeed before the generated file is eligible for review as verified code.

This is **not** evidence of a successful EXAONE-generated regression test: another explicitly approved live run is needed to demonstrate the entire path. No model request or production change occurs in this PR.
