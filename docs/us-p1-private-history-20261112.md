# P1 retained history → local dashboard → pending intake proposal

User decision 2026-11-12: use the latest approved Nasdaq CSV as the practical
USD 1B size screen. Do not repeat Yahoo cap/date reconciliation. Keep basic
security-class/venue checks, completed daily/weekly history, freshness and anomaly
guards. KIS prices remain trusted under the provider policy.

## Concrete handoff

The #252/#253 probes discarded individual observations and prices. Their 13/2/1
aggregates cannot identify the passing tickers. A bounded new capture uses the
same 16-slot receipt/SEC/KIS cohort and existing KIS adapter, three pages and two
seconds between requests, shared KIS concurrency, one token and systemic-error
stop. The approved source branch still points to `d09ca465` as of this task.

`nasdaq_p1_private_capture.yml` runs only when that file is integrated into
`data-validation-mvp`, with read-only contents permission, no schedule/dispatch,
and only the first run attempt. It uploads **encrypted bytes only**, retained for
seven days. The runner never writes plaintext OHLCV. The ciphertext contains
ticker/venue/status, normalized prices and per-series SHA256, source/input hashes,
SEC class/reference/notes, evaluation clock, workflow run ID and code SHA.
Public logs contain only aggregates and sanitized failure messages. Neither
credentials nor provider response bodies are serialized. The recipient private
key lives only in a user-local folder outside every checkout. The committed PEM
is a public key, not a GitHub Secret or a credential.

Download the artifact from the trusted workflow run, check its run ID and full
code SHA against GitHub before opening it. Encryption protects confidentiality
and ciphertext integrity; possession of the public key does **not** authenticate
the sender. `load_bundle` requires the expected full workflow code SHA. Keep the
download and private key outside all checkouts. A seven-day hosted expiry does
not delete the retained local copy.

## Dashboard path (off by default)

For the user's local, private dashboard only, set these process environment values:

- `NASDAQ_P1_PRIVATE_CONTEXT=local_private`
- `NASDAQ_P1_BUNDLE`: absolute path to the downloaded encrypted JSON
- `NASDAQ_P1_PRIVATE_KEY`: absolute path to the local recipient private PEM
- `NASDAQ_P1_CODE_SHA`: the trusted workflow run's complete code SHA

The existing `APP_PASSWORD` unlocks the panel inside the pending-candidate chart
area. Password/path/context changes revoke authentication. No decoded price data
is cached in session state or written to disk. The panel rechecks saved status at
capture time and freshness at the current time. It shows all valid daily/weekly
histories, including short/anomalous series with a hold warning. Charts use the
existing main-app price/volume chart and completed-session/week engines.

`prepare_review` returns an in-memory candidate-registry proposal through
`merge_candidate_discoveries`; known/active symbols are excluded and existing
review decisions remain intact. Only current history passes without unresolved
SEC identity/continuity notes can be proposed. Nasdaq sector/industry mappings
are suggestions only. Every new proposal is `pending_review`; no Stage, benchmark
approval, operational activation, CSV export/write or live provider request is
performed by the panel. A held sector mapping does not prevent price viewing.

## Acceptance and next gate

Required before reporting actual coverage: final-head Python/unit/browser CI,
PR impact/review/conflict checks, merge, postmerge CI, bounded capture, authenticated
download/decryption, retained per-ticker result and actual chart replay. Record
aggregate results on the PR, keeping real per-symbol results local. If capture
fails, record failure rather than infer identities from historical counts.

Real candidate/price CSV intake and operational activation remain separate user
decisions. Prepare the exact passing subset and price counts first, then ask once
for the concrete data-intake decision. No main, deployment settings, existing
Secrets, costs or existing probe workflows are changed by this development PR.
