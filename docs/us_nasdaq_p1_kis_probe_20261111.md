# Nasdaq P1: bounded KIS price-history probe (review only)

**Status:** PR #250 integrated; standalone local probe is available. The separate one-time integration workflow below performs a bounded read-only live pilot, without candidate intake or activation.

After PR #249 merged as `14a805ea47b679fbe36b605ebcae3b19f44ccc38`,
the 16 highest-priority Nasdaq/KIS name-coherent gaps had **zero saved
price series** in both `data/daily_prices.csv` and
`data/candidate_daily_prices.csv`. This does not establish live KIS support.

`nasdaq_p1_kis_history_probe.py` reuses the already approved screener
CSV/receipt validation, SEC reference checks, master venue joins,
`nasdaq_gap_price_readiness` 150 completed daily / 35 completed-week tests,
and the existing KIS overseas-price client. It does not change provider APIs,
Stage rules, market-cap decisions or scheduled tasks.

## Default: offline preview (zero KIS requests)

Use the authorized `latest.csv` and `latest.json` downloaded from the
approved `data/nasdaq-manual-screener` branch. Keep these local; do not
redistribute derived issuer lists or commit real per-symbol probe responses.

```bash
python nasdaq_p1_kis_history_probe.py \
  --nasdaq-csv /local/latest.csv \
  --receipt /local/latest.json \
  --max-symbols 2
```

The script validates hashes and local candidate/master/price snapshots. It
selects, in sorted ticker order, only P1 gaps with missing saved history and
the SEC reference venue equal to the unique saved KIS venue. **No network is
used unless `--execute` is provided**, and KIS keys are not read in offline
mode. Aggregate-only JSON is printed; `--preview 2` explicitly displays
at most two research-only names.

## Optional operator-initiated live check

```bash
KIS_APP_KEY=... KIS_APP_SECRET=... python nasdaq_p1_kis_history_probe.py \
  --nasdaq-csv /local/latest.csv \
  --receipt /local/latest.json \
  --max-symbols 2 --max-pages 3 --pause-seconds 2 \
  --execute
```

Set credentials securely in environment variables, **never on the command
line, in docs or chat**; the shell line is illustrative, not a recommendation
to leave sensitive values in shell history. Default budget: **at most two
symbols, three pages per symbol**, with KIS's own bounded retry behavior.
Upper bounds are 16 symbols, five pages per symbol, pause 2–30 seconds. The
client's internal retries can cause more HTTP attempts than page count; do
not interpret page caps as strict HTTP request counts. An authentication,
rate-limit or server error stops additional symbols.

This tool **does not create a CSV, commit real data, open another provider,
fall back to another exchange, add a candidate, activate any symbol, calculate
Stage labels, or modify the operating dashboard**. Live availability and
quality are reported only as review statuses. `--preview N` can display
individual results locally for manual inspection; by default none are exposed.
The one-time workflow `.github/workflows/nasdaq_p1_kis_readonly_pilot.yml` is
independent of the existing CSV-writing candidate workflow. It triggers only
when that workflow file itself is newly merged/changed on `data-validation-mvp`.
It checks out the already-approved screener source at commit `d09ca465`,
uses the existing KIS secrets and shared KIS concurrency group, checks exactly
two P1 symbols at most three history pages each, and prints aggregates only.
It has `contents: read`, does not push or upload files, and cannot activate
symbols. No scheduled recurrence or default-branch change is introduced.
GitHub Actions success or failure and the actual KIS result must be verified
after integration; code/CI success alone is not evidence of successful prices.

A 150-row/35-week pass still leaves security-level USD 1B market-cap basis
and date, exact class/venue identity, corporate actions, listing/session
continuity and sector benchmarks unresolved. A zero-row result remains
`kis_empty_response_support_unknown`, **not** a definitive unsupported
security classification. The KIS adapter drops some invalid returned bars;
this diagnostic is not an independent raw-response audit.

## Verification and next gate

Synthetic tests cover P1 allowlisting and limits, complete/short/empty
histories, rate/auth/server stop behavior, and review-only status. No live
queries or market-cap validation are claimed by these tests.

**Next:** confirm the one-time workflow's actual GitHub Actions run and the
aggregate KIS response (a missing credential is not KIS non-support). Then
review security-level USD cap evidence and listing continuity before even
proposing review-queue intake. `main`, actual CSVs, operational stock universe and deployment remain
off limits.
