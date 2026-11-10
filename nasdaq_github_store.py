"""Fixed-destination GitHub storage for explicitly approved Nasdaq CSVs."""
from __future__ import annotations

from base64 import b64encode
import csv
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import io
import json
import re
import unicodedata

import requests

from nasdaq_local_csv_review import missing
from nasdaq_monthly_refresh import FIELDS, digest

REPO = "wonbosong-arch/global-stage-radar"
BRANCH = "data/nasdaq-manual-screener"
FOLDER = "data/nasdaq_manual_screener"
CSV_PATH = f"{FOLDER}/latest.csv"
RECEIPT_PATH = f"{FOLDER}/latest.json"
BOOTSTRAP = f"{FOLDER}/README.md"
API = "https://api.github.com"
REPO_API = f"{API}/repos/{REPO}"
INTERVAL = timedelta(days=7)
PUBLIC_MAX_BYTES = 2_000_000
MUTATION = """
mutation SaveNasdaq($input: CreateCommitOnBranchInput!) {
  createCommitOnBranch(input: $input) { commit { oid } }
}
"""
NUMERIC = {"Last Sale", "Net Change", "% Change", "Market Cap", "IPO Year", "Volume"}
NUMBER = re.compile(r"\$?[+-]?(?:[0-9]+(?:\.[0-9]+)?|[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?)%?")
CREDENTIAL = re.compile(
    r"\b(?:github_pat_|gh[pousr]_|sk[-_](?:live_|proj-|[a-z0-9]{16})|"
    r"(?:AKIA|ASIA)[A-Z0-9]{16}|eyJ[a-z0-9_-]+\.[a-z0-9_-]+\.|"
    r"bearer\s+|(?:user(?:name|[ _-]?id)?|login|account|password|passwd|pwd|secret|"
    r"token|api[ _-]?key|access[ _-]?key|authorization|비밀번호|계정|토큰)\s*[:=])"
    r"|\b[a-zA-Z0-9_-]{32,}\b",
    re.IGNORECASE,
)
PII = re.compile(
    r"@|://|\bwww\.|\b(?:email|phone|address|ssn|이메일|전화|주소)\s*[:=]"
    r"|\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b|\b[0-9]{9,}\b"
    r"|\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b|\b[0-9]{6}-[1-8][0-9]{6}\b"
    r"|(?<!\w)(?:\+?[0-9]{1,3}[ .-])?(?:\(?[0-9]{2,4}\)?[ .-])[0-9]{3,4}[ .-][0-9]{4}(?!\w)",
    re.IGNORECASE,
)


class StoreError(ValueError):
    """A fixed error safe for the Streamlit boundary."""


class GitHubCode(Enum):
    AUTH = "auth"
    PERMISSION = "permission"
    NETWORK = "network"
    CONFLICT = "conflict"
    RATE_LIMIT = "rate-limit"
    API = "github-api"
    GRAPHQL = "graphql"
    REQUEST_TOO_LARGE = "request-too-large"
    RESPONSE_TOO_LARGE = "response-too-large"
    INVALID_RESPONSE = "invalid-response"


class GitHubError(StoreError):
    def __init__(self, code: GitHubCode):
        super().__init__(code.value)
        self.code = code


def _http_error(response):
    status = response.status_code
    if status == 403 and (response.headers.get("x-ratelimit-remaining") == "0"
                          or response.headers.get("retry-after")):
        return GitHubCode.RATE_LIMIT
    return {
        401: GitHubCode.AUTH,
        403: GitHubCode.PERMISSION,
        409: GitHubCode.CONFLICT,
        413: GitHubCode.REQUEST_TOO_LARGE,
        429: GitHubCode.RATE_LIMIT,
    }.get(status, GitHubCode.API)


def _graphql_error(errors):
    # Inspect structured types only. Messages can echo request data.
    for code, error_type in (
        (GitHubCode.RATE_LIMIT, "RATE_LIMITED"),
        (GitHubCode.AUTH, "UNAUTHORIZED"),
        (GitHubCode.PERMISSION, "FORBIDDEN"),
        (GitHubCode.CONFLICT, "STALE_DATA"),
    ):
        if any(isinstance(error, dict) and error.get("type") == error_type for error in errors):
            return code
    return GitHubCode.GRAPHQL


class PublicCsvError(StoreError):
    """Raised only with a fixed diagnostic code, never with CSV content."""


def check_public_csv(raw, blocked_values=()):
    """Reject unexpected structure and recognizable secrets/PII before transmission."""
    if not raw or len(raw) > PUBLIC_MAX_BYTES:
        raise PublicCsvError("size")
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise PublicCsvError("invalid_charset") from None
    reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
    try:
        if next(reader, None) != FIELDS:
            raise PublicCsvError("invalid_structure")
        for row in reader:
            if not row:
                continue
            if len(row) != len(FIELDS):
                raise PublicCsvError("invalid_structure")
            for field, original in zip(FIELDS, row):
                _check_public_cell(field, original, blocked_values)
    except csv.Error:
        raise PublicCsvError("invalid_structure") from None


def _check_public_cell(field, original, blocked_values):
    if len(original) > 240:
        raise PublicCsvError("invalid_cell")
    name_tab = field == "Name" and original.count("\t") == 1
    for index, char in enumerate(original):
        if not unicodedata.category(char).startswith("C"):
            continue
        # An official export contains a tab between letters in a company name.
        if (name_tab and char == "\t" and 0 < index < len(original) - 1
                and original[index - 1].isalpha() and original[index + 1].isalpha()):
            continue
        raise PublicCsvError("invalid_cell")

    value = unicodedata.normalize("NFKC", original).strip()
    variants = (value,)
    if "\t" in value:
        # Also screen tabs used to split a credential or hide a sensitive label.
        variants = (value, value.replace("\t", " "), value.replace("\t", ""))
    for candidate in variants:
        if any(secret and (secret == candidate or (len(secret) >= 8 and secret in candidate))
               for secret in blocked_values):
            raise PublicCsvError("credential_pattern")
        if field in NUMERIC and (missing(candidate, field) or NUMBER.fullmatch(candidate)):
            continue
        if candidate.startswith(("=", "+", "-", "@")):
            raise PublicCsvError("formula_injection")
        if CREDENTIAL.search(candidate):
            raise PublicCsvError("credential_pattern")
        if PII.search(candidate):
            raise PublicCsvError("pii_pattern")
        if field in NUMERIC:
            raise PublicCsvError("invalid_cell")
    if field == "Symbol" and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.^/\-]{0,15}", value):
        raise PublicCsvError("invalid_cell")


def oid(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise StoreError("Invalid GitHub commit")
    return value


class GitHubStore:
    def __init__(self, token, password):
        self._token = token
        self._password = password

    def check(self, raw):
        check_public_csv(raw, (self._token, self._password))

    def _request(self, method, url, *, limit=32768, accept="application/vnd.github+json", **kwargs):
        if not self._token:
            raise GitHubError(GitHubCode.AUTH)
        try:
            with requests.request(method, url, headers={
                "Authorization": f"Bearer {self._token}", "Accept": accept,
                "Cache-Control": "no-cache",
            }, timeout=(5, 20), allow_redirects=False, stream=True, **kwargs) as response:
                if response.status_code != 200:
                    raise GitHubError(_http_error(response))
                body = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    if len(body) + len(chunk) > limit:
                        raise GitHubError(GitHubCode.RESPONSE_TOO_LARGE)
                    body.extend(chunk)
                return bytes(body)
        except (requests.RequestException, OSError):
            raise GitHubError(GitHubCode.NETWORK) from None

    def head(self):
        ref = json.loads(self._request("GET", f"{REPO_API}/git/ref/heads/{BRANCH}"))
        if ref["ref"] != f"refs/heads/{BRANCH}" or ref["object"]["type"] != "commit":
            raise StoreError("Invalid GitHub data branch")
        return oid(ref["object"]["sha"])

    def read(self, head):
        """Pin directory and both files to a single immutable commit."""
        query = {"ref": oid(head)}
        entries = json.loads(self._request("GET", f"{REPO_API}/contents/{FOLDER}", params=query))
        paths = {entry["path"] for entry in entries}
        if len(entries) != len(paths) or any(entry["type"] != "file" for entry in entries):
            raise StoreError("Invalid GitHub data directory")
        if paths == {BOOTSTRAP}:
            return None
        if paths != {BOOTSTRAP, CSV_PATH, RECEIPT_PATH}:
            raise StoreError("Incomplete GitHub snapshot")
        receipt = self._file(RECEIPT_PATH, query, 2048)
        raw = self._file(CSV_PATH, query, PUBLIC_MAX_BYTES)
        return raw, json.loads(receipt)

    def _file(self, path, query, limit):
        return self._request("GET", f"{REPO_API}/contents/{path}", params=query,
                             limit=limit, accept="application/vnd.github.raw+json")

    def commit(self, head, raw, downloaded_on, approved_at):
        self.check(raw)
        receipt = {
            "version": 1, "sha256": digest(raw), "bytes": len(raw),
            "downloaded_on_utc": downloaded_on.isoformat(), "approved_at_utc": approved_at.isoformat(),
        }
        files = {CSV_PATH: raw, RECEIPT_PATH: (json.dumps(receipt, indent=2) + "\n").encode()}
        payload = {
            "branch": {"repositoryNameWithOwner": REPO, "refName": f"refs/heads/{BRANCH}"},
            "expectedHeadOid": oid(head),
            "message": {"headline": "Publish approved Nasdaq screener snapshot"},
            "fileChanges": {"additions": [
                {"path": path, "contents": b64encode(content).decode("ascii")}
                for path, content in files.items()
            ]},
        }
        body = self._request("POST", f"{API}/graphql",
                             json={"query": MUTATION, "variables": {"input": payload}})
        try:
            result = json.loads(body)
            errors = result.get("errors", [])
            if not isinstance(errors, list):
                raise ValueError
            if errors:
                raise GitHubError(_graphql_error(errors))
            return oid(result["data"]["createCommitOnBranch"]["commit"]["oid"])
        except GitHubError:
            raise
        except (AttributeError, KeyError, TypeError, ValueError, RecursionError):
            raise GitHubError(GitHubCode.INVALID_RESPONSE) from None


def verified_dates(raw, receipt, now):
    if (set(receipt) != {"version", "sha256", "bytes", "downloaded_on_utc", "approved_at_utc"}
            or type(receipt["version"]) is not int or receipt["version"] != 1
            or type(receipt["bytes"]) is not int or receipt["bytes"] != len(raw)
            or receipt["sha256"] != digest(raw)):
        raise StoreError("GitHub snapshot integrity check failed")
    approved = datetime.fromisoformat(receipt["approved_at_utc"])
    downloaded = date.fromisoformat(receipt["downloaded_on_utc"])
    if approved.utcoffset() != timedelta(0) or not downloaded <= approved.date() or approved > now:
        raise StoreError("Invalid GitHub snapshot dates")
    return downloaded, approved
