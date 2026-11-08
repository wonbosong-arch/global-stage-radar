"""Synthetic public GitHub API and independent Streamlit sessions only."""
from base64 import b64decode, b64encode
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys

import pytest
import requests
from streamlit.testing.v1 import AppTest

import nasdaq_github_store as gh
import nasdaq_private_review as private
import nasdaq_single_source as engine
import nasdaq_web_upload as upload
from test_nasdaq_private_review import HARNESS, synthetic_inputs
from test_nasdaq_web_upload import unlock, upload_csv


class Response:
    def __init__(self, body=b"", status=200):
        self.status_code = status
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode()

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
                "repositoryNameWithOwner": gh.REPO, "refName": f"refs/heads/{gh.BRANCH}",
            }
            if self.race:
                self.history.append(self.history[-1].copy())
            if payload["expectedHeadOid"] != self.head:
                return Response({"errors": [{"message": "private response content"}]})
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


@pytest.fixture
def setup(monkeypatch, tmp_path):
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


def test_streamlit_approval_and_recovery_in_fresh_app(monkeypatch, setup):
    data, source, api, _ = setup
    monkeypatch.setenv("NASDAQ_PRIVATE_REVIEW_ENABLED", "1")
    monkeypatch.setenv("NASDAQ_PRIVATE_REVIEW_CONTEXT", private.PUBLIC_CONTEXT)
    raw = upload_csv(source)

    def new_app():
        app = AppTest.from_string(HARNESS, default_timeout=60)
        app.secrets["APP_PASSWORD"] = "synthetic-password"
        app.secrets["NASDAQ_GITHUB_TOKEN"] = "synthetic-github-token"
        return app.run()

    app = new_app()
    assert not app.get("file_uploader") and not app.dataframe
    unlock(app)
    app.get("file_uploader")[0].upload("ignored-name.csv", raw, "text/csv").run()
    app.date_input(key=upload.PREFIX + "date").set_value(datetime.now(timezone.utc).date()).run()
    app.button(key=upload.PREFIX + "validate").click().run()
    assert not app.exception and api.posts == 0 and not app.dataframe
    assert app.get("file_uploader")[0].proto.max_upload_size_mb == 2
    assert app.button(key=upload.PREFIX + "approve").proto.disabled
    next(box for box in app.checkbox if box.key.startswith(upload.PREFIX + "publish_")).check().run()
    assert api.posts == 0
    app.button(key=upload.PREFIX + "approve").click().run()
    assert not app.exception and api.posts == 1 and app.dataframe
    assert api.history[-1][gh.CSV_PATH] == raw
    assert b"ignored-name" not in api.history[-1][gh.RECEIPT_PATH]
    good = app.session_state[upload.KEY]["good"]
    assert good["review"]["report"]["operational_additions"] == 0

    # Fresh runner and session with no uploads or cached state.
    restarted = new_app()
    assert not restarted.dataframe
    unlock(restarted)
    assert not restarted.exception and restarted.dataframe and api.posts == 1
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


def test_weekly_limits_stale_approval_cas_and_timeout_recovery(setup):
    data, source, api, store = setup
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
    assert state["error"] == upload.SAVE_ERROR and api.posts == 2
    api.race = False
    assert validate(state, changed, later)
    api.timeout_after_commit = True
    assert not approve(state, changed, later)
    assert api.posts == 3 and state["good"] == good
    assert upload.reload_public(state, store, data, now=later)
    assert api.posts == 3 and state["good"]["raw"] == changed


def test_corruption_outage_and_older_than_intake_window(setup):
    data, source, api, store = setup
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


@pytest.mark.parametrize("value", [
    "user@example.test", "password: invented", "ACCOUNT=hidden", "ghp_invented",
    "Bearer hidden", "987-65-4321", "010-1111-2222", "=HYPERLINK()", "synthetic-password",
    "issuer\tsecret", "issuer\nsecret", "https://example.test",
])
def test_public_screen_blocks_sensitive_cells_without_post(setup, value):
    data, source, api, store = setup
    raw = upload_csv(source, changes={0: {"Name": value}})
    now = datetime(2026, 11, 8, tzinfo=timezone.utc)
    state = {}
    assert not upload.validate(state, raw, now.date(), data, now=now, store=store)
    assert state["error"] == upload.PUBLIC_ERROR and "pending" not in state and api.posts == 0


def test_request_fails_closed_without_secret_or_when_redirected(setup, monkeypatch):
    _, _, api, _ = setup
    monkeypatch.setattr(requests, "request", lambda *_a, **_k: pytest.fail("unexpected API call"))
    with pytest.raises(gh.StoreError, match="secret missing"):
        gh.GitHubStore("", "synthetic-password").head()

    monkeypatch.setattr(requests, "request", lambda *_a, **_k: Response(status=302))
    with pytest.raises(gh.StoreError, match="request rejected"):
        gh.GitHubStore("synthetic-github-token", "synthetic-password").head()
    assert api.posts == 0


def test_public_byte_limit(setup, monkeypatch):
    data, source, api, store = setup
    raw = upload_csv(source)
    now = datetime(2026, 11, 8, tzinfo=timezone.utc)
    monkeypatch.setattr(gh, "PUBLIC_MAX_BYTES", len(raw) - 1)
    assert not upload.validate({}, raw, now.date(), data, now=now, store=store)
    assert api.posts == 0
