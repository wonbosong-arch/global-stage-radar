# Manual Nasdaq CSV upload and public GitHub storage

The administrator can validate and explicitly publish a manually downloaded
11-field screener CSV to the existing public repository
`wonbosong-arch/global-stage-radar`. The public uploader requires the existing
app password once per session and one explicit approval per publication.
Candidates and classifications remain review-only. The default is disabled.
The existing `local_private` mode keeps its local-file and session-only flow.

## Operator workflow

1. Confirm that your Nasdaq terms or license permit this download, use and public
   redistribution. The [Nasdaq site terms](https://www.nasdaq.com/legal) restrict
   capture and distribution, and availability of the Download CSV button does
   not establish a redistribution license. Use the official UI under the
   applicable permission. Stop at any access restriction.
2. Open **NASDAQ CSV 업로드** at the top of the dashboard and unlock it with the
   app password. Select or drop the original CSV and choose the actual UTC
   calendar date of download. The date starts blank for every new selection.
   It is required for the 45-day intake window and the newer-download check.
   The source's effective time remains unknown.
3. Validation runs automatically and shows the ticker and classification counts.
   The existing exact schema, 5,000–20,000 rows, unique symbols/class
   aliases, numeric and 80% complete classification checks apply. Replacements
   must pass the existing relative gates: at most 15% row drop, 25% row growth,
   50% byte growth, 20% symbol turnover, and a five-point rise in missing
   classifications. The independent public file cap is 2,000,000 bytes.
   Unusual cell structure, spreadsheet formulas, recognizable credentials and
   personal-data patterns, and configured password/token matches block
   publication. The pattern checks cannot identify all possible secrets or
   personal data embedded in issuer names, so inspect the original before approval.
4. After confirming redistribution rights for that file, click **공개 GitHub에 저장**.
   The button is the explicit approval to publish the original in public Git
   history. Approval revalidates the CSV against the current review inputs and
   the same GitHub branch head used for validation. The panel then displays the
   last save in KST, coverage, and whether another weekly upload is due. An
   identical copy of the last saved file shows a message and cannot be published
   again. There is no scheduled download or publication.

## Storage and recovery

- Dedicated orphan branch `data/nasdaq-manual-screener` with only
  `data/nasdaq_manual_screener/README.md`, then
  `data/nasdaq_manual_screener/latest.csv` and
  `data/nasdaq_manual_screener/latest.json`. The latter records schema version,
  exact byte count, SHA-256, attested download date, and approval timestamp. No
  filename, account identifiers, review reports, password or token are stored
  in these files. GitHub commit metadata can identify the credential owner. Use
  a suitable existing identity and GitHub's private commit email setting.
- A single GitHub GraphQL commit writes both files with an expected branch head.
  A competing update rejects the stale approval. All reads pin the directory,
  receipt and CSV to one commit. Recovery verifies size/hash and reruns the
  offline review before displaying the stored snapshot.
- On reconnect or restart, unlock to load the last approved snapshot. The GitHub
  head is checked again at validation and at approval. A failed read or write retains the last verified session
  copy. A new session during an outage needs a successful read. A lost write
  response can be ambiguous: use **저장본 다시 확인** to reconcile the head before trying again.
  The app never automatically repeats a write. An overdue snapshot stays
  readable even beyond the intake age limit. Missing a week shows a warning.
- One changed snapshot per rolling seven days, with a strictly newer attested
  download date. Only the current two files occupy the working tree. Git history
  retains older snapshots, with a maximum of 104 MB of CSV input per 52 approvals
  before compression, plus small receipts. A deleted or superseded public file
  can remain accessible in commit history, copies, or caches.
- In case of manual corruption, recover by recommitting both files from a
  verified earlier commit as a new commit on the data branch. Review the receipt
  and SHA-256 before restoring it. Do not force-push. Neither the data branch nor
  its recovery path is used as an app deployment source.

## Setup after code review

1. Create the dedicated data branch as an orphan branch using a separate empty
   Git checkout. Commit only `data/nasdaq_manual_screener/README.md` (an ordinary
   text file marking the storage location), then push that root commit to
   `refs/heads/data/nasdaq-manual-screener` on this repository without force.
   The app treats a missing branch, unexpected directory layout or partial file
   pair as an error. Do not copy application code or workflow definitions onto
   the storage branch. Keep the Streamlit deployment pointed at its approved
   code branch and restrict writes to the storage branch to authorized operators.
2. Configure Streamlit's server-side Secrets with the existing strong
   `APP_PASSWORD` and a short-lived fine-grained `NASDAQ_GITHUB_TOKEN` scoped
   only to this repository with **Contents: Read and write** (GitHub also grants
   required read-only metadata). GitHub's Contents permission is repository-wide,
   so keep code branch protections in force and rotate the credential. No
   workflow, pull request, administration, or organization permission is needed
   by the app. Use server-side Secrets, never source control or browser settings.
3. Set `NASDAQ_PRIVATE_REVIEW_ENABLED=1` and
   `NASDAQ_PRIVATE_REVIEW_CONTEXT=public_github_upload` in the app server
   environment (root-level Streamlit Secrets entries are also available as
   environment variables). After deployment review, confirm the empty branch
   reads successfully, then have the user approve the first authorized real CSV
   in the dashboard.

Public writes stay off the deployment branch. The app reads GitHub directly
with commit-pinned files and no shared Streamlit cache. No new service is needed.

- [GitHub commit mutation](https://docs.github.com/en/graphql/reference/commits#createcommitonbranch)
- [Fine-grained token setup](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [Streamlit secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
