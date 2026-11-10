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
