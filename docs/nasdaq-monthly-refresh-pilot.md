# Official Nasdaq CSV pilot — schedule inactive

Continuation: #220 merged at `dfa73ffc65b73f9bdcc1e0c53a22a534eb281c92`.
The one authorized GitHub-hosted pilot failed; see
[the hosted result and diagnostic follow-up](nasdaq-hosted-pilot-result-20261106.md).
The user-confirmed cadence is now weekly, Sunday 07:00 KST. The historical
browser/supplied-file measurements below are not hosted-runner measurements.

## Preflight, 2026-11-06

Fresh integration base: `7fdd875982a91ae37dbe7b3ac92f70317acc60b3` (#218).
Main: `997628e34c48bfbb5ba568d267b1d7bcd5367c4d`. GitHub currently reports
**data-validation-mvp as default branch**, not main. Neither branch/settings is
changed. #219 remains an independent Draft at `7a245cfc0e8201ecf5f338078cb762aa9d3c830d`,
with successful PR CI. #216/#217/#206 remain open. Related Codex chats are idle.
The original research checkout has unrelated dirty China files and is untouched.

## Live acquisition versus supplied-file test

An ordinary browser loaded the official [Stock Screener](https://www.nasdaq.com/market-activity/stocks/screener)
without filters, waited for the populated table (Showing 1-25 of 6952), and clicked
**Download CSV** through browser automation. The attachment completed and was read
from disk. This is **one successful live official-button download**, not evidence
of monthly stability, fresh headless-browser success or GitHub-runner success.
No stable direct CSV URL was established. The implementation uses the visible
button and attachment event, without guessing/replaying a hidden API. No CAPTCHA,
403/429 bypass, cookie reuse, stealth, proxy or account change occurred.

The supplied `/mnt/data/nasdaq_screener_1793860336072.csv` path does not exist on
this Windows host. A local Downloads copy with that basename is accessible and
matches the previously validated manifest hash. This is **supplied-file validation**,
not the live download. Its source/download dates remain unknown. Filename timestamps
are not interpreted as classification dates.

| Aggregate | Supplied prior file | New live download |
| --- | ---: | ---: |
| Bytes | 983,982 | 985,219 |
| Rows / unique symbols | 6,925 / 6,925 | 6,952 / 6,952 |
| Complete native Sector + Industry | 6,277 | 6,300 |
| Missing Sector / Industry | 648 / 648 | 652 / 652 |
| Missing Market Cap | 382 | 381 |
| Blank Symbol / Name, duplicate symbol keys | 0 | 0 |
| Explicit aliases supplied | 0 | 0 |
| Source Exchange column | absent | absent |
| Classification effective date | unknown | unknown |
| KIS candidate matches | 2,319 / 2,334 | 2,319 / 2,334 |
| Same-date offline review eligible | 1,341 | 1,341 |
| Stage 2 / Stage 2A review | 401 / 106 | 401 / 106 |

Supplied SHA256: `c339fd629fdb890399a880b81c80540990848e90a98aa64f96a0d0b166afdb90`.
New live SHA256: `57575f2912cf6c6a95f150363f735018c964ce342d5fc0cf76ecdc0ca0e0c65e`.
Both replays use stored KIS inputs and evaluation date 2026-11-06; operational
additions are 0. Unchanged Stage totals do not imply byte-identical CSVs.
Raw CSV and company-level reports remain outside Git/CI.

Both files have the eleven fields in this order:
`Symbol, Name, Last Sale, Net Change, % Change, Market Cap, Country, IPO Year,
Volume, Sector, Industry`. Native taxonomy stays native, not GICS.

## Implementation and quality gates

`nasdaq_monthly_refresh.py` supports separate official acquisition and offline import:

```sh
python nasdaq_monthly_refresh.py --download --state-dir /private/nasdaq \
  --as-of YYYY-MM-DD --instruction-reference 'explicit user instruction reference'

python nasdaq_monthly_refresh.py --csv /private/incoming.csv \
  --manifest /private/incoming-manifest.json --state-dir /private/nasdaq \
  --as-of YYYY-MM-DD
```

Optional dependencies: `pip install -r requirements-nasdaq-refresh.txt`, then
`python -m playwright install --with-deps chromium` in a suitable test runner.
Application dependencies/UI are unchanged. The driver uses
[Playwright's documented download event](https://playwright.dev/python/docs/downloads).

- At most two isolated browser attempts, one 30-second wait only for timeout.
  Observed Nasdaq-host 401/403/429 or a visible challenge stops without retry.
  Unknown errors/malformed downloads stop. No direct endpoint collection.
- Exact eleven fields, <=10 MB, 5,000–20,000 rows, unique nonblank symbols,
  nonblank names, finite numeric values where present, classification >=80%.
  Prior accepted file also limits row loss to 15% and missing-rate increase to
  5 percentage points. These explicit pilot thresholds are not exchange totals.
- Reuse `read_table`, missing-value handling (ticker NA remains valid), explicit
  same-class venue-aware aliases, and `nasdaq_single_source.build_report`.
  Notation/alias collisions stop. No automatic aliases or missing-field filling.
  Manual and automated manifests have separate hash-bound provenance; collection
  time never becomes source effective date. Source date stays null when unknown.
- KIS identity/type/venue/cap, baseline, native proxy conflicts, price quality/
  freshness/150-day/35-week, RS and Stage engine gates are reused offline. Nasdaq
  quote/cap fields do not replace those gates. No live KIS or active promotion.
- Private paths outside every checkout; immutable generations plus hash-bound
  `current.json`. Concurrent writers stop. Quality and replay finish before an
  atomic pointer replacement. Failure retains the old pointer; fallback rechecks
  all hashes/CSV quality. Old/unknown download age and unknown classification date
  are explicit. Failed refresh exits 2 even with usable fallback.
- `load_current` is the offline consumer interface. No #219 UI import, registry
  activation, operational data overwrite, public data upload or deployment.

Unreferenced generations can remain privately after failure; they are never
current. An interrupted process may leave a lock requiring inspection/removal.

## Workflow, persistence and publication

`.github/workflows/nasdaq-refresh-pilot.yml` is **workflow_dispatch only**, with a
false-by-default collection input, read-only contents permission, independent
concurrency and 15-minute limit. No schedule, push/PR network collection, data
commit, cache/artifact upload, secrets or manual dispatch/rerun in this work.
Only aggregate validation counts can enter the run log/summary.

Runner temp is ephemeral. **Persistent local fallback works; fallback across
GitHub runs and automated GitHub data publication are not enabled.** Raw/company
data must not silently enter this public repository or public workflow artifacts.
Code publication and synthetic CI are separate from operational data publication.

Concrete next connection: retrieve an accepted generation/pointer from an approved
private store, verify it before collection, upload a validated new generation,
then atomically advance the private pointer; a hosted dashboard reads that private
generation. The same Nasdaq CSV remains the classification source. Existing
disabled private delivery code may inform this later work, but no store, credential,
Secrets, permissions or cost is changed. #219 remains a separate local review path.

## User-confirmed weekly target — NOT APPLIED

After successful GitHub-hosted acquisition and verified private persistence,
the confirmed target is Sunday 07:00 KST = Saturday 22:00 UTC, after the US
Friday close. Existing KIS Monday–Saturday 07:00 KST remains unchanged:

```yaml
on:
  schedule:
    - cron: '0 22 * * 6'
```

A later approved change must deliberately update the current dispatch-only job
input gate too; adding this block alone will not run the collection job.
[GitHub schedule uses the latest default-branch commit and requires the workflow
there](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
Manual dispatch also requires the workflow on the default branch; merged #220
has now registered the manual workflow. Today's default is data-validation-mvp, so a future enabled
schedule merged there would take effect. No need to edit main or switch defaults
is inferred. Existing KIS workflow files are unchanged. Schedule activation,
private persistent delivery and operational publication remain separate decisions.
The first hosted pilot failed, so no schedule block or scheduled-job input gate
has been applied. The current monthly-era 45-day fallback warning also remains
unchanged; a future weekly implementation must explicitly test a shorter
freshness policy and cross-run persistence before activation. Cron is a target
start time; GitHub documents that scheduled runs can be delayed or dropped.

## Verification

Synthetic regression covers schema, numeric/empty input, row/coverage decline,
aliases, both provenance kinds, challenge/403/429 stops, retry limit, atomic/disk/
replay failure, hash corruption, stale fallback, lock, private path and nonzero
CLI fallback. The adjacent Nasdaq suites pass. Real files each completed the
existing offline engine pipeline. Full local suite/base comparison and final
remote SHA CI are recorded in the PR. The Python collector's fresh-headless and
GitHub live-download executions remain unverified, independently of these results.
