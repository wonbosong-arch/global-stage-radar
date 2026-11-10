# EXAONE + OpenCode: isolated developer PoC (review only)

This is a **manual-only, opt-in** experiment and is separate from the EXAONE sector-classification pilot.

## Scope

- On `workflow_dispatch`, the default `live=false` validates the OpenCode provider config and permissions **without contacting EXAONE or reading any secrets**.
- An explicitly approved `live=true` run installs OpenCode on a temporary GitHub Actions runner. EXAONE sees only an isolated empty scratch working directory, not the Global Stage Radar source tree. Its single task is to implement `normalize_ticker` in `ticker_utils.py`, with assertions run afterwards.
- The workflow's GitHub token is **read-only** and checkout credentials are not persisted. The OpenCode agent cannot call shell, network tools or subagents. External directory access is denied; only reads and edits in the isolated workspace are allowed.
- The API key comes from the existing `EXAONE_API_KEY` repository secret **only** during the explicitly requested live step. Agent output is suppressed, and only generated source code (not transcripts, API responses, model reasoning or environment) is retained for three days on successful validation.
- The job has an 8-minute maximum; the live agent subprocess has a 180-second maximum. OpenCode's internal request/retry count and provider-side usage must still be checked before large-scale use. This experiment is not a hard single-request guarantee.

## Restrictions and completion criteria

No scheduled run, no repo write, no PR creation by the model, no merge, no dashboard/data activation, and no `main` modification. The agent never receives the repository files; this first test therefore validates **isolated coding tool use**, not its ability to repair a real codebase.

The default offline test confirms only that the manifest parses and the intended permissions are present. It does **not** verify that the installed OpenCode version accepts the EXAONE config or that live calls or file edits succeed. For that, an explicitly approved live workflow run is required, followed by review of the generated file, output validation and usage.

Source for provider setup: https://docs.exaone.ai/en/docs/agent-start
Source for non-interactive execution: https://opencode.ai/docs/cli/commands
Source for permission model: https://opencode.ai/docs/en/permissions/
