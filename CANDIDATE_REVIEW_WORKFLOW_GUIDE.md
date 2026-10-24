# Candidate review workflow (operator guide)

This workflow keeps new stock candidates separate from the active dashboard universe until independent review is complete.

## Automatic schedule (Korea Standard Time)

| Time | Workflow | Purpose |
|---|---|---|
| 08:00, Monday–Saturday | Daily closing-price snapshot | Refresh the active monitoring universe |
| 08:05, Monday–Saturday | Manual pending-candidate price review v5 | Fetch price history for pending candidates into an isolated snapshot |
| 09:00, Monday–Saturday | Candidate coverage report | Rebuild evidence, market-cap triage, provider-observation and review-queue reports |

Sunday KST is intentionally skipped. GitHub scheduled workflows can start late during platform load; check the run record rather than assuming a job ran at its scheduled minute.

## Where to look

- [Candidate price review workflow](https://github.com/wonbosong-arch/global-stage-radar/actions/workflows/candidate_prices_manual.yml)
- [Candidate coverage report workflow](https://github.com/wonbosong-arch/global-stage-radar/actions/workflows/candidate_coverage_report.yml)
- [Daily active price snapshot workflow](https://github.com/wonbosong-arch/global-stage-radar/actions/workflows/daily_prices.yml)
- In the dashboard, open **후보 편입 검토 작업대** to search/filter candidates and export the filtered queue.
- `data/candidate_daily_prices_status.json` records the candidate refresh timestamp and, when run under GitHub Actions, `github_run_id`, `github_run_attempt`, and `github_run_url` so the saved snapshot can be traced to its exact collection attempt. A blank run URL means the script ran outside GitHub Actions or the run metadata was unavailable.
- Files produced by the review pipeline include `data/candidate_daily_prices.csv`, `data/candidate_daily_prices_status.json`, `data/stock_candidate_coverage_report.csv`, `data/candidate_identity_evidence_coverage.csv`, `data/candidate_market_cap_reconciliation.csv`, `data/candidate_provider_observation_audit.csv`, and `data/candidate_review_queue.csv`.

## What a successful price refresh means

A successful run means the configured KIS request returned price history for the symbol in that run. It does **not** by itself prove:

- the symbol maps to the intended listed instrument or share class;
- the listing is an ordinary common share rather than an ADR/ADS or another security type;
- KIS support is stable or the symbol is suitable for the active provider mapping;
- the market-cap value, share-count basis, ADS ratio, or as-of date is correct;
- the candidate is eligible for activation.

The queue ranks the next manual review action only. `activation_recommendation` must remain `keep_pending_review` until identity, market-cap basis, provider mapping, benchmark mapping, and other applicable evidence have been independently reviewed. The workflow never auto-adds a candidate to `data/monitoring_universe.csv`.

## If a run fails

1. Open the workflow run and inspect the failed step and its logs.
2. Check whether `KIS_APP_KEY` and `KIS_APP_SECRET` repository secrets are configured, and whether the KIS app remains in the intended environment.
3. Check for KIS throttling, authentication errors, and per-symbol response errors.
4. Treat the status JSON as the outcome of that particular attempt; do not infer current support from an older successful snapshot.
5. Re-run the candidate review workflow manually only when needed. The active universe is not changed by this action.

## Current guardrail

This is a screening and review pipeline, not an investment signal or a verified market-data certification. Automated tests validate code behavior, not live KIS responses, listing identity, data rights, or profitability of the Stage rules.
