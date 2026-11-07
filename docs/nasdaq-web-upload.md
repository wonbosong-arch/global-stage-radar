# Private manual Nasdaq upload — implementation and persistence boundary

Draft only. Starts from integration 1e103ca and selectively reuses #219's private
adapter, auth, UI hook and tests, without merging its stale branch or changing
#216/#217. #219 stays separate. Two exact existing opt-ins, APP_PASSWORD
reauthentication and explicit consent are retained. `local_private` is an
operator declaration, not proof of hosting access controls. Deployment settings
are unchanged. This is a browser upload UI usable in an explicitly private app;
no public-hosting deployment or storage connection is authorized by this PR.

## Sunday procedure

1. Download the official Stock Screener CSV manually. No computer must stay on.
2. Unlock private review in Data Management and consent. Choose web CSV upload,
   select the CSV, and attest its actual download date in UTC. Do not invent an
   original source date: it stays unknown, regardless of upload time/filename.
3. Validate. The uploader respects the lower existing server limit and 10 MB
   widget limit, with an independent 10,000,000-byte gate. The shared quality
   engine requires the exact 11-column schema, 5,000–20,000 rows, unique symbols,
   explicit class aliases, finite numbers and at least 80% complete native
   Sector/Industry coverage. SHA256 binds the bytes and manifest.
4. Approval is a separate action after successful full offline replay. Changed
   bytes/date invalidate the pending approval; approval repeats the checks
   against the current local KIS snapshot. Relative gates retain the previous
   accepted quality: row drop >15%, row growth >25%, byte growth >50%, symbol
   turnover >20%, or classification missing increase >5 percentage points fail.
5. Review classifications/new candidates only. Existing native Nasdaq taxonomy,
   KIS identity, KIS/Yahoo cap reconciliation, price/RS/Stage and proxy policies
   remain in the shared engine. Approval has no operational activation API.

Failure leaves the last approved session copy intact. The warning survives
reruns. Seven days without a new accepted download/approval shows an overdue
warning without deleting that copy. Last successful approval and attested
download date are separate from the unknown original data date. Filters and
switching to other dashboard areas do not approve or publish a replacement.
Lock, consent withdrawal, feature disable and password rotation clear upload
state. Different browser sessions do not share approved data.

## Current storage: explicitly session-only

The accepted bytes, manifest and report live in `st.session_state`, not a public
commit, Actions artifact/cache, shared Streamlit cache or browser local storage.
The path-based #219 adapter uses constant-name, bounded temporary files outside
Git, removed before the validation call returns. Uploaded filenames and parser
exceptions are never written to application logs. Process interruption can
leave temporary files until the host cleans its temp directory; these are not a
backup. No external data request or logging/analytics service is introduced.

Closing/reconnecting the browser, hibernation or an app restart can erase the
session copy. There is no last-good recovery across those events in this PR.
Therefore one skipped week retains the accepted copy only while that session
survives. The UI states this before upload and on every render. Source files
must still be retained privately by the operator. No persistence or live Cloud
success is claimed.

## Deferred private persistent-store contract

No approved general Nasdaq persistent store exists. The existing China-specific
delivery code is not permission to create/reuse a Nasdaq service, account,
bucket, Secrets or billable resource. This PR adds none. A future independent
storage PR must be approved with a concrete private location/access policy.

- An authenticated backend reads a last-good pointer and its version/ETag.
- Validate/replay bytes before publishing immutable generation objects: original
  CSV, hash-bound manual manifest and report, each with hash/length receipts.
- Verify read-back integrity and private access, then conditional compare-and-
  swap the pointer only if its expected version is still current. Stale writers
  must reload/revalidate; partial upload/timeout leaves the pointer untouched.
- Keep at least the previous verified generation; rollback selects a verified
  generation rather than deleting/replacing originals. Define retention and
  encryption/access policies for that store before activation.
- Reconnect/restart loads and hash-verifies the pointer/generation before
  display. Corruption/access failure warns and retains any already verified
  session copy, never treats an empty/failed fetch as a valid replacement.
- No public bucket/URL, public repo raw data, Actions artifacts/cache, signed
  URL in logs, or company-level metrics in public logs. Log only fixed error
  codes and aggregate operation status. Secrets remain server-side.
- Test concurrent approval, pointer conflict, partial write, tampering,
  permission failure, rollback, restart recovery and missing-week freshness
  against a fake store, then the separately authorized private deployment.

The integration/deployment gate stays closed until that independent storage and
private hosted-app validation is completed. No new cron or automatic download.

References: [Streamlit file uploader](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader)
and [session lifetime](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state).
