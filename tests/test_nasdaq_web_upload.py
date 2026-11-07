"""Only invented inputs, including the actual Streamlit file-uploader transport."""
import copy
import csv
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
import tempfile
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import nasdaq_private_review as private
import nasdaq_single_source as engine
import nasdaq_web_upload as subject
from nasdaq_monthly_refresh import FIELDS
from test_nasdaq_private_review import HARNESS, NOW, synthetic_inputs


def upload_csv(source, count=10, changes=None):
    rows = list(csv.DictReader(io.StringIO(source.read_text(encoding="utf-8")) ))
    rows += [dict(Symbol=f"EXTRA{i}", Name=f"Invented Extra {i} Common Stock", Sector="Basic Materials", Industry="Metal Mining")
             for i in range(count - len(rows))]
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDS)
    writer.writeheader()
    for i, row in enumerate(rows[:count]):
        writer.writerow({**dict.fromkeys(FIELDS, ""), **row, **(changes or {}).get(i, {})})
    return out.getvalue().encode()


def test_full_replay_two_phase_fallback_week_skip_and_no_network(monkeypatch):
    monkeypatch.setattr(subject, "MIN_ROWS", 10)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp); source, mp, bp, ep = synthetic_inputs(root)
        raw = upload_csv(source)
        before = {p.name: p.read_bytes() for p in root.iterdir()}
        with patch.object(engine, "BASELINE", bp), patch.object(engine, "EXPANSION", ep), patch(
                "requests.sessions.Session.request", side_effect=AssertionError("no network")):
            state = {}
            assert subject.validate(state, raw, NOW.date(), root, now=NOW)
            assert "good" not in state
            assert state["pending"]["review"]["report"]["operational_additions"] == 0
            assert subject.approve(state, raw, NOW.date(), root, now=NOW)
            good = copy.deepcopy(state["good"])
            assert good["manifest"]["source_as_of"] is None
            assert good["manifest"]["acquisition_method"] == "user_manual_download"
            assert subject.freshness(good, now=NOW + timedelta(days=7)) == "overdue"
            assert subject.freshness(good, now=NOW + timedelta(days=6)) == "current"
            assert not subject.validate(state, b"SECRET-ROW", NOW.date(), root, now=NOW)
            assert state["good"] == good and "SECRET" not in state["error"]
            assert not subject.approve(state, raw, NOW.date(), root, now=NOW)
            assert state["good"] == good
            assert subject.validate(state, raw, NOW.date(), root, now=NOW)
            assert not subject.approve(state, raw + b"\n", NOW.date(), root, now=NOW)
            assert state["good"] == good
            assert subject.validate(state, raw, NOW.date(), root, now=NOW)
            with patch.object(private, "load_review", side_effect=OSError("PRIVATE PATH ROW")):
                assert not subject.approve(state, raw, NOW.date(), root, now=NOW)
            assert state["good"] == good and "PRIVATE" not in state["error"]
            assert before == {p.name: p.read_bytes() for p in root.iterdir()}


def test_quality_size_hash_dates_and_relative_anomaly_gates(monkeypatch):
    monkeypatch.setattr(subject, "MIN_ROWS", 10)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp); source, mp, bp, ep = synthetic_inputs(root)
        raw = upload_csv(source)
        with patch.object(engine, "BASELINE", bp), patch.object(engine, "EXPANSION", ep):
            previous = subject.prepare(raw, NOW.date(), root, now=NOW)
            bad_inputs = [raw.replace(b"Symbol", b"Ticker"), raw.replace(b"EXTRA0", b"TESTA"), b"\xff", b"",
                upload_csv(source, changes={i: {"Sector": ""} for i in range(3)}),
                upload_csv(source, changes={0: {"Market Cap": "inf"}}),
                upload_csv(source, count=13),
                upload_csv(source, changes={i: {"Symbol": f"NEW{i}"} for i in range(3)})]
            for bad in bad_inputs:
                state = {"good": copy.deepcopy(previous)}
                assert not subject.validate(state, bad, NOW.date(), root, now=NOW)
                assert state["good"] == previous
            for stamp in (NOW.date() + timedelta(days=1), NOW.date() - timedelta(days=46)):
                assert not subject.validate({}, raw, stamp, root, now=NOW)
            with patch.object(subject, "MAX_BYTES", 1):
                class Uploaded:
                    size = 2
                    def getvalue(self):
                        raise AssertionError("must reject size before copying bytes")
                try:
                    subject.selected_bytes(Uploaded())
                    assert False
                except ValueError:
                    pass
            report = copy.deepcopy(previous["review"])
            report["report"]["csv_sha256"] = "wrong"
            with patch.object(private, "load_review", return_value=report):
                assert not subject.validate({}, raw, NOW.date(), root, now=NOW)


def unlock(app):
    app.text_input[0].set_value("synthetic-password")
    app.button[0].click().run()
    app.checkbox(key="nasdaq_private_review_consent").check().run()


def test_real_uploader_validation_approval_reruns_failure_filter_lock_and_isolation(monkeypatch):
    monkeypatch.setenv("NASDAQ_PRIVATE_REVIEW_ENABLED", "1")
    monkeypatch.setenv("NASDAQ_PRIVATE_REVIEW_CONTEXT", "local_private")
    monkeypatch.setattr(subject, "MIN_ROWS", 10)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp); data = root / "data"; data.mkdir()
        source, mp, bp, ep = synthetic_inputs(data)
        raw = upload_csv(source)
        monkeypatch.setattr(private, "ROOT", root)
        monkeypatch.setattr(engine, "BASELINE", bp); monkeypatch.setattr(engine, "EXPANSION", ep)
        monkeypatch.setattr("requests.sessions.Session.request", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("network")))
        app = AppTest.from_string(HARNESS, default_timeout=60)
        app.secrets["APP_PASSWORD"] = "synthetic-password"
        app.run()
        assert not app.get("file_uploader")
        unlock(app)
        assert not app.exception and app.get("file_uploader")[0].proto.max_upload_size_mb == 10
        app.get("file_uploader")[0].upload("invented.csv", raw, "text/csv").run()
        app.date_input(key=subject.PREFIX + "date").set_value(datetime.now(timezone.utc).date()).run()
        app.button(key=subject.PREFIX + "validate").click().run()
        assert not app.exception and "good" not in app.session_state[subject.KEY]
        app.button(key=subject.PREFIX + "approve").click().run()
        assert not app.exception and len(app.dataframe) == 1
        good_hash = app.session_state[subject.KEY]["good"]["quality"]["csv_sha256"]
        app.selectbox(key=subject.PREFIX + "filter").select("보류").run()
        app.run()
        assert app.session_state[subject.KEY]["good"]["quality"]["csv_sha256"] == good_hash
        app.get("file_uploader")[0].set_value(("secret-filename.csv", b"SECRET PRIVATE ROW", "text/csv")).run()
        app.button(key=subject.PREFIX + "validate").click().run()
        assert not app.exception
        assert app.session_state[subject.KEY]["good"]["quality"]["csv_sha256"] == good_hash
        assert all("SECRET" not in w.value and "secret-filename" not in w.value for w in app.warning)
        # A fresh independent session/restart has no last-good copy.
        other = AppTest.from_string(HARNESS); other.secrets["APP_PASSWORD"] = "synthetic-password"
        other.run(); unlock(other)
        assert "good" not in other.session_state[subject.KEY]
        app.button(key="nasdaq_private_review_lock").click().run()
        assert not app.exception and subject.KEY not in app.session_state and not app.dataframe
        unlock(app)
        assert "good" not in app.session_state[subject.KEY]


def test_consent_disable_password_rotation_purge_pending_and_good(monkeypatch):
    monkeypatch.setenv("NASDAQ_PRIVATE_REVIEW_ENABLED", "1")
    monkeypatch.setenv("NASDAQ_PRIVATE_REVIEW_CONTEXT", "local_private")
    app = AppTest.from_string(HARNESS)
    app.secrets["APP_PASSWORD"] = "synthetic-password"
    app.run(); unlock(app)
    app.session_state[subject.KEY] = {"good": {"invented": True}, "pending": {"invented": True}}
    app.checkbox(key="nasdaq_private_review_consent").uncheck().run()
    assert subject.KEY not in app.session_state and not app.exception
    app.session_state[subject.KEY] = {"good": {"invented": True}}
    app.secrets["APP_PASSWORD"] = "rotated"
    app.run()
    assert subject.KEY not in app.session_state and private.AUTH not in app.session_state
    app.session_state[subject.KEY] = {"good": {"invented": True}}
    monkeypatch.delenv("NASDAQ_PRIVATE_REVIEW_ENABLED")
    app.run()
    assert not app.exception and subject.KEY not in app.session_state
