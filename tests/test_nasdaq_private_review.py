"""Invented CSV only. Real private inputs must never be fixtures/artifacts."""
import copy
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import nasdaq_private_review as subject
import nasdaq_single_source as engine
from test_nasdaq_single_source import parts

NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)


def synthetic_inputs(root):
    registry, universe, master, prices, rows, columns = parts()
    source = root / "input.csv"
    with source.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader(); writer.writerows(rows)
    manifest = dict(dataset_kind="user_supplied_nasdaq_csv", acquisition_method="user_manual_download",
        scope="private_noncommercial_offline", user_instruction_reference="invented test instruction",
        csv_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_url="https://www.nasdaq.com/market-activity/stocks/screener",
        source_as_of=None, downloaded_at_utc=None)
    mp = root / "manifest.json"; mp.write_text(json.dumps(manifest), encoding="utf-8")
    baseline = {"as_of": "2026-10-23", "selected_candidates": 1,
        "candidates": [dict(symbol="TESTA", sector="Materials", sector_benchmark="XLB",
                            market_benchmark="SPY", review_only_stage_label="historical")],
        "review_only_stage_counts": {"historical": 1}, "input_files": {}}
    expansion = {"same_snapshot_comparison": True, "as_of": "2026-10-23", "candidates": [],
        "combined_same_snapshot_counts": {"historical": 1}, "cumulative_review_coverage": 1}
    bp = root / "baseline.json"; bp.write_text(json.dumps(baseline), encoding="utf-8")
    ep = root / "expansion.json"; ep.write_text(json.dumps(expansion), encoding="utf-8")
    inputs = {engine.INPUTS[0]: registry, engine.INPUTS[1]: master,
        engine.INPUTS[2]: pd.DataFrame(columns=["symbol"]), engine.INPUTS[3]: universe,
        "daily_prices.csv": prices, "candidate_daily_prices.csv": prices.iloc[:0]}
    for name, frame in inputs.items(): frame.to_csv(root / name, index=False)
    return source, mp, bp, ep


class PrivateReviewTests(unittest.TestCase):
    def test_opt_in_requires_exact_private_context(self):
        for env in ({}, {"NASDAQ_PRIVATE_REVIEW_ENABLED": "1"},
                    {"NASDAQ_PRIVATE_REVIEW_ENABLED": "true", "NASDAQ_PRIVATE_REVIEW_CONTEXT": "local_private"},
                    {"NASDAQ_PRIVATE_REVIEW_ENABLED": "1", "NASDAQ_PRIVATE_REVIEW_CONTEXT": "public"}):
            self.assertFalse(subject.enabled(env))
        self.assertTrue(subject.enabled(dict(NASDAQ_PRIVATE_REVIEW_ENABLED="1", NASDAQ_PRIVATE_REVIEW_CONTEXT="local_private")))

    def test_full_engine_read_only_replace_failure_fallback_and_no_double_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source, mp, bp, ep = synthetic_inputs(root)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            with patch.object(engine, "BASELINE", bp), patch.object(engine, "EXPANSION", ep), patch(
                    "requests.sessions.Session.request", side_effect=AssertionError("network forbidden")):
                state = {}
                self.assertTrue(subject.refresh_review(state, source, mp, root, now=NOW))
                frame = subject.review_frame(state["report"])
                self.assertEqual(len(frame), 2)
                self.assertEqual(frame.symbol.nunique(), 2)
                self.assertEqual(frame["검토 가능"].sum(), 2)
                self.assertEqual(state["report"]["operational_additions"], 0)
                self.assertEqual(state["freshness"], "unknown")
                self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
                previous = copy.deepcopy(state)
                source.write_text("private-broken-row", encoding="utf-8")
                self.assertFalse(subject.refresh_review(state, source, mp, root, now=NOW))
                self.assertEqual(state, previous)
                source.unlink()
                self.assertFalse(subject.refresh_review(state, source, mp, root, now=NOW))
                self.assertEqual(state, previous)
                empty = {}
                self.assertFalse(subject.refresh_review(empty, source, mp, root, now=NOW))
                self.assertEqual(empty, {})
                # Replace with a valid new source whose identity is invalid: row
                # stays held through the real engine, not a manufactured label.
                source.write_bytes(before["input.csv"].replace(b"TESTB Inc.", b"Unrelated Issuer Inc."))
                manifest = json.loads(mp.read_text()); manifest["csv_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
                mp.write_text(json.dumps(manifest))
                self.assertTrue(subject.refresh_review(state, source, mp, root, now=NOW))
                held = subject.review_frame(state["report"]).set_index("symbol").loc["TESTB"]
                self.assertFalse(held["검토 가능"])
                self.assertEqual(held["검토 Stage"], "보류")

    def test_dates_unknown_fresh_boundary_stale_future_and_no_mtime_inference(self):
        today = NOW.date()
        self.assertEqual(subject.source_freshness({}, today), "unknown")
        self.assertEqual(subject.source_freshness({"source_as_of": "2026-09-09"}, today), "within_review_window")
        self.assertEqual(subject.source_freshness({"downloaded_at_utc": "2026-10-24T00:00:00Z"}, today), "within_review_window")
        for stamp in ("2026-09-08", "2026-10-25", "invalid"):
            with self.assertRaises(ValueError): subject.source_freshness({"source_as_of": stamp}, today)

    def test_structure_hash_dates_git_path_size_and_snapshot_race_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source, mp, bp, ep = synthetic_inputs(root)
            original = source.read_bytes(); manifest = json.loads(mp.read_text())
            def fails():
                self.assertFalse(subject.refresh_review({}, source, mp, root, now=NOW))
            for content in (b"Symbol,Symbol\nX,Y\n", b"Symbol,Name\nX,Y\n", b"", b"\xff", b"Symbol,Name,Sector,Industry,Market Cap\n,X,Y,Z,1\n"):
                source.write_bytes(content)
                mp.write_text(json.dumps({**manifest, "csv_sha256": hashlib.sha256(content).hexdigest()}))
                fails()
            source.write_bytes(original)
            for extra in ({"csv_sha256": "bad"}, {"source_as_of": "2026-08-01", "source_as_of_reference": "synthetic"},
                          {"downloaded_at_utc": "2026-10-25T00:00:00Z", "downloaded_at_utc_reference": "synthetic"},
                          {"symbol_aliases": ["invalid"]}, {"symbol_aliases": {}}):
                mp.write_text(json.dumps({**manifest, **extra})); fails()
            mp.write_text(json.dumps(manifest))
            with patch.object(subject, "MAX_CSV_BYTES", 1): fails()
            with patch.object(subject, "MAX_MANIFEST_BYTES", 1): fails()
            with patch.object(subject, "build_report", side_effect=AssertionError("must not run")):
                (root / ".git").write_text("gitdir: invented")
                fails(); (root / ".git").unlink()
            real = subject.build_report
            def raced(*args, **kwargs):
                result = real(*args, **kwargs)
                source.write_bytes(original + b"\n")
                return result
            with patch.object(engine, "BASELINE", bp), patch.object(engine, "EXPANSION", ep), patch.object(subject, "build_report", raced):
                fails()


HARNESS = '''
import os
import streamlit as st
from nasdaq_private_review import render_private_review
render_private_review(st, os.environ, lambda key: st.secrets.get(key))
'''


def test_private_panel_real_widgets_auth_load_filter_fallback_lock_and_disable(monkeypatch):
    monkeypatch.setenv("NASDAQ_PRIVATE_REVIEW_ENABLED", "1")
    monkeypatch.setenv("NASDAQ_PRIVATE_REVIEW_CONTEXT", "local_private")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp); source, mp, bp, ep = synthetic_inputs(root)
        with patch.object(engine, "BASELINE", bp), patch.object(engine, "EXPANSION", ep):
            loaded = subject.load_review(source, mp, root, now=NOW)
        calls = []
        def load(*args, **kwargs):
            calls.append(1)
            if len(calls) > 1: raise ValueError("SECRET PRIVATE ROW MUST NOT LEAK")
            return copy.deepcopy(loaded)
        monkeypatch.setattr(subject, "load_review", load)
        app = AppTest.from_string(HARNESS)
        app.secrets["APP_PASSWORD"] = "synthetic-password"
        app.run()
        assert not app.exception and not calls
        app.text_input[0].set_value("bad")
        app.button[0].click().run()
        assert not calls and app.error
        app.text_input[0].set_value("synthetic-password")
        app.button[0].click().run()
        assert not calls
        app.checkbox(key="nasdaq_private_review_consent").check().run()
        app.radio(key="nasdaq_private_review_source").set_value("기존 로컬 파일").run()
        app.button(key="nasdaq_private_review_load").click().run()
        assert not app.exception and len(app.dataframe[0].value) == 2
        app.selectbox(key="nasdaq_private_review_filter").select("보류").run()
        assert len(app.dataframe[0].value) == 0
        app.selectbox(key="nasdaq_private_review_filter").select("전체").run()
        app.button(key="nasdaq_private_review_load").click().run()
        assert len(app.dataframe[0].value) == 2
        assert all("SECRET PRIVATE ROW" not in w.value for w in app.warning)
        assert len(calls) == 2
        app.button(key="nasdaq_private_review_lock").click().run()
        assert subject.STATE not in app.session_state and not app.dataframe
        monkeypatch.delenv("NASDAQ_PRIVATE_REVIEW_ENABLED")
        app.run()
        assert not app.exception and not app.expander and subject.AUTH not in app.session_state


def test_disabled_app_integration_preserves_stage_selection_and_watchlist(monkeypatch):
    monkeypatch.delenv("NASDAQ_PRIVATE_REVIEW_ENABLED", raising=False)
    monkeypatch.chdir(subject.ROOT)
    monkeypatch.setattr(subject, "load_review", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("disabled read")))
    monkeypatch.setattr("requests.sessions.Session.request", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("network")))
    app = AppTest.from_file(str(subject.ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception
    app.radio(key="analysis_navigation_choice").set_value("stocks").run()
    selected = app.session_state["stocks_selected_symbol"]
    app.button(key="stocks_favorite").click().run()
    records = app.session_state["analysis_favorite_assets"]
    app.radio(key="stocks_view_mode").set_value("3×3 차트").run()
    app.radio(key="analysis_navigation_choice").set_value("favorites").run()
    app.radio(key="analysis_navigation_choice").set_value("stocks").run()
    assert not app.exception
    assert app.session_state["stocks_selected_symbol"] == selected
    assert app.session_state["analysis_favorite_assets"] == records
    assert subject.STATE not in app.session_state
    assert all("비공개 NASDAQ" not in e.label for e in app.expander)
    # Enabling the separate panel and a failed first input must also leave
    # operational selection, grid and watchlist untouched across reruns.
    monkeypatch.setenv("NASDAQ_PRIVATE_REVIEW_ENABLED", "1")
    monkeypatch.setenv("NASDAQ_PRIVATE_REVIEW_CONTEXT", "local_private")
    monkeypatch.setattr(subject, "load_review", lambda *a, **kw: (_ for _ in ()).throw(ValueError("missing")))
    app.secrets["APP_PASSWORD"] = "synthetic-password"
    app.run()
    next(w for w in app.text_input if w.label == "비공개 검토 비밀번호").set_value("synthetic-password")
    next(w for w in app.button if w.label == "비공개 검토 잠금 해제").click().run()
    app.checkbox(key="nasdaq_private_review_consent").check().run()
    app.radio(key="nasdaq_private_review_source").set_value("기존 로컬 파일").run()
    app.button(key="nasdaq_private_review_load").click().run()
    assert not app.exception
    assert app.session_state["stocks_selected_symbol"] == selected
    assert app.session_state["analysis_favorite_assets"] == records
    assert app.radio(key="stocks_view_mode").value == "3×3 차트"
    assert app.session_state[subject.STATE] == {}
    # Password rotation invalidates the separate auth and destroys its data.
    app.session_state[subject.STATE] = {"private": "invented"}
    app.secrets["APP_PASSWORD"] = "rotated-synthetic-password"
    app.run()
    assert subject.STATE not in app.session_state and subject.AUTH not in app.session_state
    assert not app.exception
