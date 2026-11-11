"""Synthetic public GitHub API and independent Streamlit sessions only."""
from base64 import b64decode, b64encode
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
from unittest import TestCase

import requests
from requests.structures import CaseInsensitiveDict
from streamlit.testing.v1 import AppTest

import nasdaq_github_store as gh
import nasdaq_private_review as private
import nasdaq_single_source as engine
import nasdaq_web_upload as upload
from test_nasdaq_private_review import HARNESS, synthetic_inputs
from test_nasdaq_web_upload import upload_csv


def unlock(app, password="synthetic-password"):
    app.text_input[0].set_value(password)
    app.button[0].click().run()


class Response:
    def __init__(self, body=b"", status=200, headers=None):
        self.status_code = status
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.headers = CaseInsensitiveDict(headers or {})

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def iter_content(self, chunk_size):
        for start in range(0, len(self.body), chunk_size):
            yield self.body[start:start + chunk_size]


class GitHub:
    def __init__(self):
        self.history = [{gh.BOOTSTRAP: b"Nasdaq snapshots"}]
        self.posts = 0
        self.reject_reads = False
        self.reject_next_write = False
        self.race = False
        self.timeout_after_commit = False

    @property
    def head(self):
        return f"{len(self.history):040x}"

    def request(self, method, url, *, headers, allow_redirects, stream, timeout, params=None, json=None):
        assert headers["Authorization"] == "Bearer synthetic-github-token"
        assert headers["Cache-Control"] == "no-cache"
        assert allow_redirects is False and stream and timeout == (5, 20)
        if method == "POST":
            self.posts += 1
            assert url == gh.API + "/graphql"
            assert "createCommitOnBranch" in json["query"]
            payload = json["variables"]["input"]
            assert payload["branch"] == {
                "repositoryNameWithOwner": gh.REPO, "branchName": gh.BRANCH,
            }
            if self.reject_next_write:
                self.reject_next_write = False
                return Response(b"private response content", status=403)
            if self.race:
                self.history.append(self.history[-1].copy())
            if payload["expectedHeadOid"] != self.head:
                return Response({"errors": [{"type": "STALE_DATA", "message": "private response content"}]})
            adds = {item["path"]: b64decode(item["contents"], validate=True)
                    for item in payload["fileChanges"]["additions"]}
            assert set(adds) == {gh.CSV_PATH, gh.RECEIPT_PATH}
            self.history.append({**self.history[-1], **adds})
            if self.timeout_after_commit:
                raise requests.Timeout("secret in simulated request error")
            return Response({"data": {"createCommitOnBranch": {"commit": {"oid": self.head}}}})
        assert method == "GET"
        if self.reject_reads:
            return Response(b"private response content", status=403)
        if url == f"{gh.REPO_API}/git/ref/heads/{gh.BRANCH}":
            return Response({"ref": f"refs/heads/{gh.BRANCH}", "object": {"type": "commit", "sha": self.head}})
        assert params and len(params["ref"]) == 40
        files = self.history[int(params["ref"], 16) - 1]
        if url == f"{gh.REPO_API}/contents/{gh.FOLDER}":
            return Response([{"path": path, "type": "file"} for path in files])
        assert headers["Accept"] == "application/vnd.github.raw+json"
        prefix = f"{gh.REPO_API}/contents/"
        assert url.startswith(prefix)
        return Response(files[url.removeprefix(prefix)])


def synthetic_store(monkeypatch, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    source, _, baseline, expansion = synthetic_inputs(data)
    monkeypatch.setattr(private, "ROOT", tmp_path)
    monkeypatch.setattr(engine, "BASELINE", baseline)
    monkeypatch.setattr(engine, "EXPANSION", expansion)
    monkeypatch.setattr(upload, "MIN_ROWS", 10)
    api = GitHub()
    monkeypatch.setattr(requests, "request", api.request)
    store = gh.GitHubStore("synthetic-github-token", "synthetic-password")
    return data, source, api, store


def test_streamlit_approval_and_recovery_in_fresh_app(monkeypatch, tmp_path):
    data, source, api, _ = synthetic_store(monkeypatch, tmp_path)
    monkeypatch.setenv("NASDAQ_PRIVATE_REVIEW_ENABLED", "1")
    monkeypatch.setenv("NASDAQ_PRIVATE_REVIEW_CONTEXT", private.PUBLIC_CONTEXT)
    raw = upload_csv(source, changes={0: {"Name": "Example\tHoldings, Inc."}})

    def new_app():
        app = AppTest.from_string(HARNESS, default_timeout=60)
        app.secrets["APP_PASSWORD"] = "synthetic-password"
        app.secrets["NASDAQ_GITHUB_TOKEN"] = "synthetic-github-token"
        return app.run()

    app = new_app()
    assert not app.get("file_uploader") and not app.dataframe
    unlock(app, "bad-password")
    assert app.error and not app.get("file_uploader") and api.posts == 0
    unlock(app)
    assert not app.checkbox and app.info[0].value == "첫 업로드가 필요합니다."
    app.get("file_uploader")[0].upload("ignored-name.csv", raw, "text/csv").run()
    assert app.date_input[0].value is None and "pending" not in app.session_state[upload.KEY]
    app.date_input(key=upload.PREFIX + "date").set_value(datetime.now(timezone.utc).date()).run()
    assert not app.exception and api.posts == 0 and not app.dataframe
    assert app.get("file_uploader")[0].proto.max_upload_size_mb == 2
    assert not any(button.label == "CSV 품질 검증" for button in app.button)

    def publish():
        return next(button for button in app.button if button.label == "공개 GitHub에 저장")

    api.reject_next_write = True
    publish().click().run()
    assert api.posts == 1 and not app.dataframe and app.warning[0].value == f"{upload.SAVE_ERROR} [permission]"
    app.button(key=upload.PREFIX + "retry").click().run()
    assert api.posts == 1 and not app.warning
    publish().click().run()
    assert not app.exception and api.posts == 2 and app.dataframe
    assert app.success[0].value.startswith("마지막 저장 ")
    assert any("이번 주 업로드 완료" in c.value for c in app.caption)
    assert api.history[-1][gh.CSV_PATH] == raw
    assert b"ignored-name" not in api.history[-1][gh.RECEIPT_PATH]
    good = app.session_state[upload.KEY]["good"]
    assert good["review"]["report"]["operational_additions"] == 0
    app.selectbox(key=upload.PREFIX + "filter").select("보류").run()
    app.get("file_uploader")[0].set_value(None).run()
    app.get("file_uploader")[0].upload("same.csv", raw, "text/csv").run()
    assert app.info[0].value == upload.DUPLICATE_ERROR and not app.date_input
    assert not any(button.label == "공개 GitHub에 저장" for button in app.button)
    app.get("file_uploader")[0].upload("broken.csv", b"bad input", "text/csv").run()
    assert app.date_input[0].value is None
    app.date_input[0].set_value(datetime.now(timezone.utc).date()).run()
    assert app.warning[0].value == f"{upload.PUBLIC_ERROR} [invalid_structure]" and api.posts == 2
    assert app.selectbox(key=upload.PREFIX + "filter").value == "보류"
    assert app.session_state[upload.KEY]["good"] == good

    # Fresh runner and session with no uploads or cached state.
    restarted = new_app()
    assert not restarted.dataframe
    unlock(restarted)
    assert not restarted.exception and restarted.dataframe and api.posts == 2
    assert restarted.session_state[upload.KEY]["good"] == good
    restarted.button(key="nasdaq_private_review_lock").click().run()
    assert not restarted.dataframe and upload.KEY not in restarted.session_state

    # The mock GitHub tree survives outside the app process, like a remote store.
    # Start a new Python/Streamlit runner that cannot use the first one's state.
    transport = data / "synthetic-github-response.json"
    transport.write_text(json.dumps({path: b64encode(content).decode()
                                     for path, content in api.history[-1].items()}), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, 'tests'); "
         "from test_nasdaq_github_store import check_cold_start; check_cold_start(*sys.argv[1:])",
         str(data), good["quality"]["csv_sha256"]],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_public_connection_requires_server_setup_and_retries_read(monkeypatch, tmp_path):
    _, _, api, _ = synthetic_store(monkeypatch, tmp_path)
    monkeypatch.setenv("NASDAQ_PRIVATE_REVIEW_ENABLED", "1")
    monkeypatch.setenv("NASDAQ_PRIVATE_REVIEW_CONTEXT", private.PUBLIC_CONTEXT)
    app = AppTest.from_string(HARNESS)
    app.secrets["APP_PASSWORD"] = "synthetic-password"
    app.run()
    unlock(app)
    assert not app.get("file_uploader") and "공개 저장소 연결이 필요합니다" in app.info[0].value
    app.secrets["NASDAQ_GITHUB_TOKEN"] = "synthetic-github-token"
    api.reject_reads = True
    app.run()
    assert app.get("file_uploader")[0].proto.disabled
    assert app.warning[0].value == f"{upload.STORE_ERROR} [permission]"
    api.reject_reads = False
    app.button(key=upload.PREFIX + "reload").click().run()
    assert not app.get("file_uploader")[0].proto.disabled and api.posts == 0


def check_cold_start(data, expected_hash):
    data = Path(data)
    engine.BASELINE = data / "baseline.json"
    engine.EXPANSION = data / "expansion.json"
    private.ROOT = data.parent
    upload.MIN_ROWS = 10
    backend = GitHub()
    backend.history[-1] = {
        path: b64decode(value) for path, value in
        json.loads((data / "synthetic-github-response.json").read_text(encoding="utf-8")).items()
    }
    requests.request = backend.request
    app = AppTest.from_string(HARNESS, default_timeout=45)
    app.secrets["APP_PASSWORD"] = "synthetic-password"
    app.secrets["NASDAQ_GITHUB_TOKEN"] = "synthetic-github-token"
    app.run()
    unlock(app)
    assert not app.exception and app.dataframe and backend.posts == 0
    assert app.session_state[upload.KEY]["good"]["quality"]["csv_sha256"] == expected_hash


def test_weekly_limits_stale_approval_cas_and_timeout_recovery(monkeypatch, tmp_path):
    data, source, api, store = synthetic_store(monkeypatch, tmp_path)
    now = datetime(2026, 11, 8, 10, tzinfo=timezone.utc)
    raw = upload_csv(source)
    state, other = {}, {}

    def validate(session, csv_bytes=raw, at=now):
        return upload.validate(session, csv_bytes, at.date(), data, now=at, store=store)

    def approve(session, csv_bytes=raw, at=now, consent=True):
        return upload.approve(session, csv_bytes, at.date(), data, now=at, store=store,
                              publication_consent=consent)

    assert validate(state) and not approve(state, consent=False) and api.posts == 0
    assert validate(state) and validate(other)
    assert approve(state)
    assert not approve(other) and other["error"] == upload.STALE_ERROR and api.posts == 1
    good = state["good"]
    changed = upload_csv(source, changes={0: {"Last Sale": "$123.45", "Net Change": "-1.01"}})
    assert not validate(state, changed, now + timedelta(days=6))
    assert not validate(state, raw, now + timedelta(days=7))
    later = now + timedelta(days=7)
    assert validate(state, changed, later)
    api.race = True
    assert not approve(state, changed, later)
    assert state["good"] == good and api.history[-1][gh.CSV_PATH] == raw
    assert state["error"] == f"{upload.SAVE_ERROR} [conflict]" and api.posts == 2
    api.race = False
    assert validate(state, changed, later)
    api.timeout_after_commit = True
    assert not approve(state, changed, later)
    assert api.posts == 3 and state["good"] == good
    assert state["error"] == f"{upload.SAVE_ERROR} [network]"
    assert not approve(state, changed, later) and api.posts == 3
    assert upload.reload_public(state, store, data, now=later)
    assert api.posts == 3 and state["good"]["raw"] == changed
    restarted = {}
    assert not validate(restarted, changed, later)
    assert restarted["error"] == upload.DUPLICATE_ERROR
    assert restarted["good"] == state["good"] and api.posts == 3


def test_corruption_outage_and_older_than_intake_window(monkeypatch, tmp_path):
    data, source, api, store = synthetic_store(monkeypatch, tmp_path)
    raw = upload_csv(source)
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    state = {}
    assert upload.validate(state, raw, now.date(), data, now=now, store=store)
    assert upload.approve(state, raw, now.date(), data, now=now, store=store, publication_consent=True)
    old = now + timedelta(days=65)
    restored = {}
    assert upload.reload_public(restored, store, data, now=old)
    good = restored["good"]
    assert upload.freshness(good, now=old) == "overdue"
    api.reject_reads = True
    assert not upload.reload_public(restored, store, data, now=old)
    assert restored["good"] == good
    assert not upload.validate(restored, raw, old.date(), data, now=old, store=store)
    api.reject_reads = False
    api.history.append({**api.history[-1], gh.CSV_PATH: raw + b"x"})
    assert not upload.reload_public(restored, store, data, now=old)
    assert restored["good"] == good and api.posts == 1
    fresh = {}
    assert not upload.reload_public(fresh, store, data, now=old)
    assert "good" not in fresh and "head" not in fresh


def test_public_screen_blocks_sensitive_cells_without_post(monkeypatch, tmp_path):
    data, source, api, store = synthetic_store(monkeypatch, tmp_path)
    now = datetime(2026, 11, 8, tzinfo=timezone.utc)
    cases = [
        ("Name", "user@example.test", "pii_pattern"),
        ("Name", "987-65-4321", "pii_pattern"),
        ("Name", "010-1111-2222", "pii_pattern"),
        ("Name", "https://example.test", "pii_pattern"),
        ("Name", "e\tmail: hidden", "pii_pattern"),
        ("Name", "password: invented", "credential_pattern"),
        ("Name", "ACCOUNT=hidden", "credential_pattern"),
        ("Name", "ghp_invented", "credential_pattern"),
        ("Name", "Bearer hidden", "credential_pattern"),
        ("Name", "g\thp_invented", "credential_pattern"),
        ("Name", "Bearer\thidden", "credential_pattern"),
        ("Name", "synthetic-pass\tword", "credential_pattern"),
        ("Name", "synthetic-password", "credential_pattern"),
        ("Name", "=HYPERLINK()", "formula_injection"),
        ("Name", "  ＝SUM(1)", "formula_injection"),
        ("Name", "@SUM(1)", "formula_injection"),
        ("Name", "\tExample Corp", "invalid_cell"),
        ("Name", "Example Corp\t", "invalid_cell"),
        ("Name", "Example\t=SUM(1)", "invalid_cell"),
        ("Name", "Ex\tam\tple Corp", "invalid_cell"),
        ("Name", "issuer\nsecret", "invalid_cell"),
        ("Name", "issuer\u200bname", "invalid_cell"),
        ("Country", "Ex\tample", "invalid_cell"),
        ("Last Sale", "=1+2", "formula_injection"),
        ("Last Sale", "$oops", "invalid_cell"),
    ]
    for field, value, code in cases:
        raw = upload_csv(source, changes={0: {field: value}})
        state = {}
        assert not upload.validate(state, raw, now.date(), data, now=now, store=store), value
        assert state["error"] == f"{upload.PUBLIC_ERROR} [{code}]"
        assert "pending" not in state and api.posts == 0


def test_public_screen_reports_encoding_and_malformed_csv(monkeypatch, tmp_path):
    data, source, api, store = synthetic_store(monkeypatch, tmp_path)
    now = datetime(2026, 11, 8, tzinfo=timezone.utc)
    raw = upload_csv(source)
    for suffix, code in [(b"\xff", "invalid_charset"), (b'"unclosed', "invalid_structure")]:
        state = {}
        assert not upload.validate(state, raw + suffix, now.date(), data, now=now, store=store)
        assert state["error"] == f"{upload.PUBLIC_ERROR} [{code}]"
        assert "pending" not in state and api.posts == 0


class TransportTests(TestCase):
    def test_request_fails_closed_without_secret(self):
        from unittest.mock import patch

        with patch.object(requests, "request") as request:
            with self.assertRaisesRegex(gh.GitHubError, "^auth$"):
                gh.GitHubStore("", "synthetic-password").head()
            request.assert_not_called()

    def test_http_errors_only_expose_fixed_codes(self):
        from unittest.mock import patch

        store = gh.GitHubStore("synthetic-github-token", "synthetic-password")
        for status, headers, code in [
            (302, {"Location": "https://example.test/private"}, "github-api"),
            (401, {}, "auth"),
            (403, {}, "permission"),
            (403, {"X-RateLimit-Remaining": "0"}, "rate-limit"),
            (403, {"Retry-After": "60"}, "rate-limit"),
            (404, {}, "github-api"),
            (409, {}, "conflict"),
            (413, {}, "request-too-large"),
            (429, {}, "rate-limit"),
            (503, {}, "github-api"),
        ]:
            with self.subTest(status=status, code=code):
                response = Response(b"private response content", status=status, headers=headers)
                with patch.object(requests, "request", return_value=response) as request:
                    with self.assertRaisesRegex(gh.GitHubError, f"^{code}$"):
                        store.head()
                    request.assert_called_once()


def test_graphql_errors_and_invalid_responses_only_expose_fixed_codes(monkeypatch, tmp_path):
    from unittest.mock import Mock

    data, source, api, store = synthetic_store(monkeypatch, tmp_path)
    raw = upload_csv(source)
    now = datetime(2026, 11, 8, tzinfo=timezone.utc)

    def assert_failed_response(body, code):
        def request(method, *args, **kwargs):
            if method == "POST":
                return Response(body)
            return api.request(method, *args, **kwargs)

        transport = Mock(side_effect=request)
        monkeypatch.setattr(requests, "request", transport)
        state = {}
        assert upload.validate(state, raw, now.date(), data, now=now, store=store)
        assert not upload.approve(state, raw, now.date(), data, now=now, store=store, publication_consent=True)
        assert state["error"] == f"{upload.SAVE_ERROR} [{code}]"
        assert state["head"] == api.head and "good" not in state and "pending" not in state
        assert sum(call.args[0] == "POST" for call in transport.call_args_list) == 1

    # Even with an apparent commit OID, errors must take precedence over data.
    data_with_oid = {"createCommitOnBranch": {"commit": {"oid": "a" * 40}}}
    for error_type, code in [
        ("UNAUTHORIZED", "auth"),
        ("FORBIDDEN", "permission"),
        ("STALE_DATA", "conflict"),
        ("RATE_LIMITED", "rate-limit"),
        ("unknown server text", "graphql"),
    ]:
        response = {"data": data_with_oid, "errors": [{"type": error_type, "message": "private response content"}]}
        assert_failed_response(response, code)
    for response in (b"not JSON", None, {"data": None}, {"errors": "private response content"},
                     {"data": data_with_oid, "errors": ""},
                     {"data": {"createCommitOnBranch": {"commit": {"oid": "invalid"}}}}):
        assert_failed_response(response, "invalid-response")
    assert_failed_response(b"x" * 32769, "response-too-large")



def test_oversized_save_response_reports_safe_metadata_without_retry(monkeypatch, tmp_path):
    from unittest.mock import Mock

    data, source, api, store = synthetic_store(monkeypatch, tmp_path)
    raw = upload_csv(source)
    now = datetime(2026, 11, 8, tzinfo=timezone.utc)
    secret = "private-reply-must-not-appear"
    oversized = secret.encode() + b"x" * (32769 - len(secret))

    def request(method, *args, **kwargs):
        if method == "POST":
            return Response(oversized, headers={
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": "40000",
                "X-GitHub-Request-Id": "ABCD:12FF:EF00",
            })
        return api.request(method, *args, **kwargs)

    transport = Mock(side_effect=request)
    monkeypatch.setattr(requests, "request", transport)
    state = {}
    assert upload.validate(state, raw, now.date(), data, now=now, store=store)
    assert not upload.approve(state, raw, now.date(), data, now=now, store=store,
                              publication_consent=True)
    assert state["error"] == f"{upload.SAVE_ERROR} [response-too-large]"
    assert state["github_diagnostic"] == (
        "status=200 · type=application/json · content_length=40000 · "
        "received_bytes=32769 · request_id=ABCD:12FF:EF00"
    )
    assert secret not in repr(state)
    assert "good" not in state and "pending" not in state
    assert state["head"] == api.head
    assert not upload.approve(state, raw, now.date(), data, now=now, store=store,
                              publication_consent=True)
    assert sum(call.args[0] == "POST" for call in transport.call_args_list) == 1


def test_graphql_error_diagnostics_allowlist_untrusted_headers(monkeypatch, tmp_path):
    from unittest.mock import Mock

    data, source, api, store = synthetic_store(monkeypatch, tmp_path)
    raw = upload_csv(source)
    now = datetime(2026, 11, 8, tzinfo=timezone.utc)
    secret = "private-graphql-message-should-stay-hidden"

    def request(method, *args, **kwargs):
        if method == "POST":
            return Response({"errors": [{"type": "FORBIDDEN", "message": secret}]},
                            headers={
                                "Content-Type": "text/html; bearer " + secret,
                                "Content-Length": "not-a-number",
                                "X-GitHub-Request-Id": secret,
                            })
        return api.request(method, *args, **kwargs)

    transport = Mock(side_effect=request)
    monkeypatch.setattr(requests, "request", transport)
    state = {}
    assert upload.validate(state, raw, now.date(), data, now=now, store=store)
    assert not upload.approve(state, raw, now.date(), data, now=now, store=store,
                              publication_consent=True)
    assert state["error"] == f"{upload.SAVE_ERROR} [permission]"
    received = len(json.dumps({"errors": [{"type": "FORBIDDEN", "message": secret}]}).encode())
    assert state["github_diagnostic"] == (
        "status=200 · type=text/html · content_length=unknown · "
        f"received_bytes={received} · request_id=unavailable · graphql_type=FORBIDDEN"
    )
    assert secret not in repr(state)
    assert sum(call.args[0] == "POST" for call in transport.call_args_list) == 1

def test_public_byte_limit(monkeypatch, tmp_path):
    data, source, api, store = synthetic_store(monkeypatch, tmp_path)
    raw = upload_csv(source)
    now = datetime(2026, 11, 8, tzinfo=timezone.utc)
    monkeypatch.setattr(gh, "PUBLIC_MAX_BYTES", len(raw) - 1)
    state = {}
    assert not upload.validate(state, raw, now.date(), data, now=now, store=store)
    assert state["error"] == f"{upload.PUBLIC_ERROR} [size]"
    assert api.posts == 0
