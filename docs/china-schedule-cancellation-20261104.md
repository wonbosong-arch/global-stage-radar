# China 07:00 KST cancellations: read-only investigation, 2026-11-04

## Finding and evidence strength

**Confirmed mechanism: pending concurrency request replacement before any job existed.**
Both public GitHub run pages contain the annotation:

> Canceling since a higher priority waiting request for daily-closing-price-snapshot exists

The sanitized annotation capture is in `evidence/china-cancellation-annotations-20261104.json`.
The REST jobs endpoint with `filter=all` returns `total_count: 0` for both canceled runs.
This is not evidence of a KIS error: neither run reached the collection step.

| KST intended date | Run | Actual creation UTC | Last update UTC | Jobs/result |
|---|---|---|---|---|
| Nov 2 | [41356890322](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/41356890322) | Nov 1 22:23:27 | Nov 1 22:25:56 | observe 124998764400, success |
| Nov 3 | [41537626610](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/41537626610) | Nov 2 22:28:57 | Nov 2 22:29:22 | none, cancelled |
| Nov 4 | [41731127547](https://github.com/wonbosong-arch/global-stage-radar/actions/runs/41731127547) | Nov 3 22:28:41 | Nov 3 22:29:27 | none, cancelled |

Successful Nov 2 observe fetched KIS data from 22:23:52 to 22:25:52 and then committed isolated observation files. This historical success does not establish current data freshness or authorize live collection.

## Contending executions

All `.github/workflows/` files were scanned at fresh integration SHA
`9d53acf858403fe2b82dd27b7071b87ed6866f16`, and at both canceled run SHAs
`2faaccb32dd1995dea1ac38e18d33cc9002ea5d6` and
`f8792297bdc0f48e65460274cf80dde921bfc059`. These five files use the same
literal group and `cancel-in-progress: false`, with no explicit queue policy:

| Workflow | Cron UTC | KST | Additional trigger |
|---|---|---|---|
| candidate_collection.yml | `0 22 * * 0-5` | Mon–Sat 07:00 | dispatch; integration push with code/workflow path filters |
| china_candidate_prices.yml | `0 22 * * 0-5` | Mon–Sat 07:00 | integration push, observation manifest only |
| daily_prices.yml | `0 22 * * 0-5` | Mon–Sat 07:00 | dispatch; integration push with universe/code/workflow path filters |
| japan_candidate_prices.yml | `0 22 * * 0-5` | Mon–Sat 07:00 | integration push with path filters |
| candidate_prices_manual.yml | `5 22 * * 0-5` | Mon–Sat 07:05 | dispatch (also automatically dispatched by discovery) |

The entire 2026-11-02 20:00 through 2026-11-04 01:00 UTC Actions list was
read in two pages (106 runs). No shared-group `push` run occurs in either
incident window. Other workflows have push triggers, but are not contenders
in this group. Test workflow push and PR runs duplicate CI, not KIS collection.
Crypto, Yahoo market-cap and coverage report use distinct groups.

| UTC day | Running discovery | Automated price dispatch step | New candidate-price run | China cancel update |
|---|---|---|---|---|
| Nov 2 | 41537565845 / job125593198178, 22:28:33–22:29:22 | 22:29:19–22:29:20, success | 41537678032, created 22:29:20; job starts 22:29:25 | 22:29:22 |
| Nov 3 | 41731087308 / job126248310557, 22:28:27–22:29:28 | 22:29:24–22:29:25, success | 41731232136, created 22:29:25; job starts 22:29:31 | 22:29:27 |

Discovery dispatches `candidate_prices_manual.yml` while it still owns the
shared group. China is pending at that time. This strongly identifies the new
automated dispatch as the replacement request on both days. GitHub's annotation
confirms the group mechanism, but does not name the replacing run ID; that
specific pairing remains a timeline inference, not a direct event ID link.
Later daily runs 41537809892 / 41731268126 also have no jobs and are canceled;
Japan runs 41537949134 / 41731552928 are later canceled near the separately
scheduled candidate-price arrivals 41539591042 / 41733324359.

REST `actor` and `triggering_actor` are `wonbosong-arch` on the China schedule
runs. These identify the trigger actor, **not a canceling person**. The public
annotation reports scheduler replacement. No canceling-human identity is
exposed by these run responses. Check-suite subresource reads were rejected by
the connector URL allowlist; no administrative/audit-log access was attempted.

## Minimal proposal, NOT applied

GitHub's current [official concurrency documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
documents `queue: max`: up to 100 pending runs while retaining one running
member; excess arrivals are canceled. `cancel-in-progress: false` alone does
not prevent pending replacement. FIFO is by actual waiting time, not nominal
cron time. Scheduled execution already arrives 23–29 minutes after nominal time.

The exact candidate patch is `evidence/kis-queue-max-unapplied.diff`: add only
`queue: max` under the existing concurrency mapping in all five members.
All group members are included so later arrivals do not retain default single
pending behavior. No cron, trigger, job, KIS pause, credential, data commit or
trust-policy changes are proposed. The patch is stored as documentation, not
under `.github/workflows/`, and has not been applied or executed.

This retains cross-workflow KIS serialization, per-process pacing and existing
data/rebase safeguards. It does not create a global limiter for unrelated
external KIS clients; those remain outside this queue. Separate workflow groups
would permit simultaneous KIS requests, and local sleeps would not enforce the
shared account limit, so that alternative is not recommended. A unified ordered
collector would require a larger trigger/job refactor. Changing cron times is
unnecessary and would still not guarantee no overlap during slow runs.

Tradeoff: max queue preserves arrivals rather than coalescing duplicate
scheduled/automatic dispatches. It can increase lag and KIS call volume, and a
100-pending cap remains. Existing collection semantics determine which dates
are fetched; this does not promise historical backfill. Push/data integrity
behavior is unchanged. Monitor queue depth, freshness and duplicate batches
after a separately authorized rollout. Local tests do not prove GitHub accepts
the proposed workflow syntax or establish live scheduling behavior.

## Safe implementation and verification

`audit_kis_workflow_queue.py` is an offline preflight, with no HTTP, credentials
or file-writing operation. It detects the current five pending replacement
risks; `--proposal` prints the exact diff without applying it. Its deliberately
narrow literal-block parser fails closed on unsupported syntax and is not a
general YAML validator. Unit tests cover queue adoption in memory, unchanged
cron and serialization, cancellation protection, new/missing members, unknown
syntax and idempotent proposal generation. No collection/data/UI logic changed.

Commands:

```text
python -m unittest discover -s tests -p test_kis_workflow_queue.py -v
python audit_kis_workflow_queue.py            # expected exit 1: current risk
python audit_kis_workflow_queue.py --proposal # exit 0, print only
```

Five local tests passed. CI results are reported on the draft PR at its exact
head SHA; no workflow was manually dispatched or rerun.

## Coordination and approval boundary

Remote branches and open PRs were read before editing. Integration is 9d53acf;
main is 997628e and has no China workflow at that ref. Main was not modified.
Open PRs: 205, 202, 200, 199, 198, 197, 194, 193, 192, 181, 47, 46.
PR205 latest head 7c9580e had passing Python push/PR and unit CI. Integration
Python run41743038552 passed. Earlier failed CI attempts were not mistaken for
latest-head failures. Existing dirty data in the shared research checkout was
left untouched; this work uses its own fresh integration-based worktree.

**Next requested approval:** authorize preparing the documented five-line
workflow queue patch on an independent PR for review. This does not authorize
protected-branch merge, manual dispatch/rerun, deployment or schedule activation.
