# EXAONE direct code generation: first actual regression-test deliverable

## Why this path exists

OpenCode's live `exaone-regression-tests` tasks did not deliver a verified artifact:
- [42762382008](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/42762382008) — agent command timed out after 180 seconds.
- [42763942875](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/42763942875) — agent command succeeded but scratch directory failed `unexpected_file_changes`.
- [42765477302](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/42765477302) — agent command succeeded in about 32 seconds but verifier failed `missing_expected_files`. Exact missing paths are unknown.

Stop repeating this OpenCode task. Use the existing, previously verified EXAONE HTTPS integration **without an external coding agent**.

## Scope and safety

Manual workflow: `.github/workflows/exaone-direct-codegen.yml`. Its `live` input defaults to **false**. An offline dispatch never accesses the API key. A `live=true` dispatch performs **at most one HTTPS request** to `api.exaone.ai/v1/chat/completions` and has no API retry, no shell tool for the model, no scheduler, no GitHub write permission and no access to other secrets. It reuses the existing tested `exaone_sector_pilot.ExaoneClient` transport with `max_attempts=1`.

The task is fixed: write exactly one Python test module `test_exaone_sector_pilot_agent.py`, containing two regression tests for `parse_completion`. The prompt contains the existing parser function body rather than loading or editing the full codebase. Only code text can return from the model; the repository never grants it filesystem tools.

The secret-bearing generation job validates JSON envelope, bounded source size/line count, AST syntax, imports, the required two named test methods, explicit parser calls and assertions, and the one exact output file. It **never imports or runs the generated file**. A separate GitHub job with **no EXAONE_API_KEY** executes the two tests inside the existing no-network, read-only Docker gate, then deliberately replaces the parser with an incorrect implementation and requires **both tests to fail**. Code passing both the normal and mutation checks is kept as `exaone-direct-verified-code` for **human review**, not automatically merged. A failed generator or behavior test produces no verified artifact.

Offline tests cover fixed prompt, strict response parsing, one-call behavior, invalid completions, no-secret logging and no output on error. Green CI only verifies this offline infrastructure; it does not prove EXAONE's new direct-code output is correct.

## Decision gate

No changes to `main`, `data-validation-mvp` without explicit PR approval, the operational dashboard, or production datasets. Do not run `live=true` without a user's explicit approval of the new direct API workflow. Review the generated tests and compare them with existing tests before proposing a separate PR for any real repository code.

If this one-shot path also produces low-quality code, do not keep trying the same generator repeatedly: prioritize ordinary developer completion and reassess the benefit of EXAONE.
