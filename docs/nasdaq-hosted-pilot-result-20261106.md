# Hosted Nasdaq CSV pilot result — 2026-11-06 KST

## Navigation diagnostic follow-up after pilot 2

Pilot 2 (`42165471426`, merge `eff2834969478c3c1a1f5cecb0c42124a9e2cfdb`)
failed in `page_navigation` with generic `operation_failed`; no HTTP status or
download was observed. This does not establish 403, 429, CAPTCHA or a code defect.

The follow-up reports only fixed diagnostic literals: DNS, TCP, TLS, network
timeout, browser closed, navigation abort, empty response and selected protocol
failures. A recognized Chromium prefix contributes only an explicitly allowed
`browser_error_code`; unknown net codes become `network_error_unknown`. Tokens
inside URLs or call logs do not count as error prefixes. Exception class names
are separately allowlisted; unknown classes become `Exception`.

`navigation_http_status` is the last observed numeric main-frame navigation
response on a Nasdaq host, including a response preceding a thrown `goto`.
It is omitted when no response is observed; subresources and other hosts cannot
supply it. It is evidence of a response, not proof that navigation completed.
Existing denial/challenge stops take precedence. No raw message, URL, body,
cookies, headers, private path or traceback is printed or saved in aggregates.
There is no extra connectivity probe, direct API request or access workaround.

The manual hosted job now passes `--attempts 1`: one collection attempt with no
timeout retry. The existing local collector default of two bounded timeout
attempts, failed-refresh exit 2, verified fallback and quality/replay gates remain.
The user authorized one third hosted pilot only after the tested change is merged
into the actual default integration branch and post-merge CI succeeds. This
source checkpoint does not claim that the third pilot has run. Schedule, private
persistence, publication, deployment and operational activation remain disabled.

Synthetic regression covers network prefixes, timeout/browser closure, main-frame
response filtering, denial precedence, output redaction, unknown exception names,
single-attempt CLI wiring and no timeout retry. Actual results are recorded in
the PR and the local execution checkpoint.

PR #220 was marked Ready and merged into data-validation-mvp at
`dfa73ffc65b73f9bdcc1e0c53a22a534eb281c92`. The merge tree matches the three
successful exact-head checks. Actual default remains data-validation-mvp;
main and Draft #219/#216/#217 were preserved. No competing active Nasdaq chat
was found. No branch protection, default, account or permission was changed.

## Verified execution

- [Post-merge CI](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/42161389296):
  success, exact merge SHA, unittest 429/skip 1; pytest 533 passed, 7 skipped,
  281 subtests passed. Workflow YAML and compilation passed.
- [Hosted manual pilot #1](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/42162170485):
  completed/failure, workflow_dispatch, attempt 1, same merge SHA,
  collect_official_csv=true. Triggered once at 13:23 KST; no rerun/second dispatch.
- Ubuntu hosted runner installed Python, Playwright, browser and dependencies
  successfully. Collection/validation/replay step failed after about 2.3 seconds:
  `{"status":"failed","error_type":"Error","operational_additions":0}`, exit 2.
  Aggregate reporting was skipped because the failed step stopped normal steps.
- Actual CSV download success, row count, eleven-field schema, native Sector /
  Industry validity rates and quality gates are **unmeasured** for this run.
  Status was failed, not refreshed or fallback. No seeded hosted last-good
  generation exists. The prior 6,952-row browser result is separate evidence.
- This was not a GitHub authentication/dispatch rejection. The old collector
  suppresses exception details, so the log cannot distinguish browser launch,
  navigation, page controls or other collection failures. HTTP 403/429 or CAPTCHA
  must not be inferred from this generic Error. No bypass, endpoint substitution,
  retry identity change or further live request was performed.
- Artifact API confirms no artifacts. Raw CSV, company data, screenshots of
  source data and credentials were not uploaded. Public log shows aggregates only.

## Focused diagnostic follow-up — Draft only

The missing failure summary is reproducible without a network. The separate
fix branch adds fixed, allowlisted phase labels (browser launch/context,
navigation, access check, table wait, CSV download/read, private state and
validation/replay/publication), a fixed failure code and a numeric observed
HTTP error status when available. No exception text, response body, URLs,
cookies, browser arguments, private path or trace is printed.

CLI failure and verified fallback now write the same aggregate JSON as stdout;
they still return exit 2. A failed summary write is sanitized and also exits 2.
Successful collection retains status refreshed even if aggregate reporting fails.
The new workflow's reporter runs after failed collection, without
continue-on-error or turning the failed job green. Killed/no-summary processes
produce an explicit unverified aggregate notice, with no invented measurements.
A secondary broken-page body read cannot mask the original browser exception;
observed denials and visible challenges still stop, and timeout retry limits
remain unchanged.

Synthetic verification: 59 tests / 91 subtests passed, including existing
provenance, quality, timeout-only retry, denial/challenge stop, integrity,
last-good pointer/fallback, native mapping and adjacent private delivery tests.
Six new/expanded behavioral regressions each fail against the unchanged #220
source and pass after the fix. Six new tests plus one expanded fallback test
include workflow reporting and successful CLI/report-failure behavior. Automatic exact-head
full Linux CI is recorded in the Draft PR after publication.

## Weekly schedule and persistence

User-confirmed schedule is Sunday 07:00 KST / Saturday 22:00 UTC,
`0 22 * * 6`. No actual schedule block is present. The hosted acquisition
prerequisite failed, so no schedule feature/persistence PR is activated or
merged. This diagnostic Draft changes neither cadence nor the 45-day local
fallback threshold. Weekly freshness and restart/private-store integration
tests remain required in the later schedule change.

The current GitHub default branch already satisfies the workflow registration
requirement. [GitHub schedule rules](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
require the latest default-branch workflow and permit delayed/dropped starts.
Runner temp is ephemeral and public repository artifacts/cache/commits cannot
be used as private data persistence. No approved existing Nasdaq private store
connection was established; no new Secrets, account, storage cost or service
was created. The later design must restore/verify last-good state, validate a
new immutable generation, atomically advance a private pointer and verify a
fresh consumer after runner termination before activation.

Operational additions/public data publication/dashboard deployment: zero.
Existing KIS 07:00 collection, operational universe, market caps, Stage engine,
and other industry sources were not changed.

Next step: review the diagnostic Draft before authorizing another hosted pilot;
this change does not authorize or trigger that second acquisition attempt.
