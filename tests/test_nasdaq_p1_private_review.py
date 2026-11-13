"""Invented symbols/prices only; no real probe data may become a fixture."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import pandas as pd
import plotly.graph_objects as go
from streamlit.testing.v1 import AppTest

from nasdaq_gap_price_readiness import P1
from nasdaq_p1_kis_history_probe import probe_live
from nasdaq_p1_private_bundle import digest, seal, unseal, save_encrypted
from nasdaq_p1_private_review import load_bundle, prepare_review, render_private_charts
from test_nasdaq_p1_kis_history_probe import StubKIS, history, review, NOW

SHA = "a" * 40


def bundle():
    captured = []
    probe = probe_live([review("SYNTHA"), review("SYNTHB")],
                      StubKIS({"SYNTHA": history("SYNTHA"),
                               "SYNTHB": history("SYNTHB", days=10)}),
                      NOW, 3, 2.0, captured=captured)
    for row in captured:
        row["identity"] = dict(symbol=row["symbol"], source_name="Synthetic common stock",
            issuer_identity_review_cohort=P1, kis_venues_by_ticker=["NAS"],
            sec_reference_status="sec_reference_same_saved_kis_venue_review_only",
            nasdaq_sector="Technology", nasdaq_industry="Semiconductors",
            nasdaq_reported_cap_usd="2000000000")
        row["sec_reference"] = dict(symbol=row["symbol"], kis_venue="NAS",
            security_class="common stock", activation_status="pending_review",
            evidence_status="sec_filing_security_and_symbol_checked", review_note="",
            source_url="https://www.sec.gov/invented-test-only")
    probe.pop("review_rows")
    probe["source_sha256"] = "b" * 64
    return dict(schema_version=1, code_sha=SHA, run_id="synthetic",
                evaluated_at=NOW.isoformat(), summary=probe,
                observations=captured, observations_sha256=digest(captured))


class P1PrivateReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        cls.private = cls.key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        cls.public = cls.key.public_key().public_bytes(serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo)

    def test_encrypted_roundtrip_tamper_wrong_key_and_no_plaintext(self):
        payload = bundle()
        encrypted = seal(payload, self.public)
        for word in (b"SYNTHA", b"SYNTHB", b"common stock", b"prices_sha256"):
            self.assertNotIn(word, encrypted)
        self.assertEqual(unseal(encrypted, self.private), payload)
        envelope = json.loads(encrypted)
        envelope["ciphertext"] = "AAAA" + envelope["ciphertext"][4:]
        with self.assertRaises(InvalidTag):
            unseal(json.dumps(envelope), self.private)
        other = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        wrong = other.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        with self.assertRaises(ValueError):
            unseal(encrypted, wrong)

    def test_private_paths_no_overwrite_and_expected_workflow_sha(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target, key = root / "capture.json", root / "key.pem"
            key.write_bytes(self.private)
            save_encrypted(target, bundle(), self.public)
            self.assertEqual(load_bundle(target, key, SHA)["code_sha"], SHA)
            with self.assertRaises(ValueError):
                load_bundle(target, key, "c" * 40)
            with self.assertRaises(FileExistsError):
                save_encrypted(target, bundle(), self.public)
        with self.assertRaises(ValueError):
            save_encrypted(Path(__file__).resolve().parent / "should-not-write.enc", bundle(), self.public)

    def test_capture_and_intake_share_exact_history_without_network_or_file_writes(self):
        payload = bundle()
        before = copy.deepcopy(payload)
        candidates = pd.DataFrame([dict(symbol="EXISTING", exchange="NAS", activation_status="approved")])
        original = candidates.copy(deep=True)
        with patch("requests.sessions.Session.request", side_effect=AssertionError("network forbidden")):
            prepared = prepare_review(payload, candidates, pd.DataFrame(), NOW)
        self.assertEqual(payload, before)
        pd.testing.assert_frame_equal(candidates, original)
        self.assertEqual(prepared["proposed_additions"], 1)
        proposal = prepared["candidate_proposal"].set_index("symbol")
        self.assertEqual(proposal.loc["EXISTING", "activation_status"], "approved")
        self.assertEqual(proposal.loc["SYNTHA", "activation_status"], "pending_review")
        self.assertEqual(proposal.loc["SYNTHA", "discovery_source"], "approved_nasdaq_csv")
        self.assertEqual(proposal.loc["SYNTHA", "proposed_sector_benchmark"], "XLK")
        self.assertNotIn("SYNTHB", proposal.index)
        self.assertEqual(set(prepared["prices"].symbol), {"SYNTHA", "SYNTHB"})
        # Repeat proposal respects the existing intake's deduplication rules.
        repeated = prepare_review(payload, prepared["candidate_proposal"], pd.DataFrame(), NOW)
        self.assertEqual(repeated["proposed_additions"], 0)
        active = prepare_review(payload, pd.DataFrame(), pd.DataFrame([{"symbol": "SYNTHA"}]), NOW)
        self.assertEqual(active["proposed_additions"], 0)

    def test_identity_holds_stale_and_anomaly_never_become_intake_proposals(self):
        payload = bundle()
        payload["observations"][0]["sec_reference"]["review_note"] = "Listing transfer continuity pending"
        payload["observations_sha256"] = digest(payload["observations"])
        prepared = prepare_review(payload, pd.DataFrame(), pd.DataFrame(), NOW)
        self.assertEqual(prepared["proposed_additions"], 0)
        self.assertIn("Listing transfer", prepared["rows"].iloc[0].identity_hold)
        stale = prepare_review(bundle(), pd.DataFrame(), pd.DataFrame(), NOW + timedelta(days=15))
        self.assertEqual(stale["proposed_additions"], 0)
        for field, value in (("symbol", "OTHER"), ("venue", "TSE"), ("activation_approved", True)):
            invalid = bundle()
            invalid["observations"][0][field] = value
            invalid["observations_sha256"] = digest(invalid["observations"])
            with self.subTest(field=field), self.assertRaises(ValueError):
                prepare_review(invalid, pd.DataFrame(), pd.DataFrame(), NOW)

    def test_status_and_price_hash_mismatch_are_rejected(self):
        for corrupt in ("prices", "status"):
            invalid = bundle()
            if corrupt == "prices":
                invalid["observations"][0]["prices"][0]["close"] = 99
            else:
                invalid["observations"][0]["status"] = "insufficient_history"
            invalid["observations_sha256"] = digest(invalid["observations"])
            with self.subTest(corrupt=corrupt), self.assertRaises(ValueError):
                prepare_review(invalid, pd.DataFrame(), pd.DataFrame(), NOW)

    def test_anomalous_capture_retains_chart_but_cannot_enter_proposal(self):
        payload = bundle()
        row = payload["observations"][0]
        bars = history("SYNTHA")
        bars.loc[bars.index[-1], ["open", "high", "low", "close"]] *= 3
        captured = []
        probe_live([review("SYNTHA")], StubKIS({"SYNTHA": bars}), NOW, 3, 2.0,
                   captured=captured)
        row.update(captured[0])
        payload["observations_sha256"] = digest(payload["observations"])
        prepared = prepare_review(payload, pd.DataFrame(), pd.DataFrame(), NOW)
        self.assertEqual(prepared["proposed_additions"], 0)
        self.assertEqual(prepared["rows"].iloc[0].current_status, "price_anomaly_review")
        self.assertIn("SYNTHA", prepared["prices"].symbol.tolist())

    def test_ui_auth_selection_period_rerun_lock_and_context(self):
        source = '''
import streamlit as st
from nasdaq_p1_private_review import render_private_charts
from tests_placeholder import environment, secret, chart
render_private_charts(st, environment, secret, chart)
'''
        import types, sys
        payload = bundle()
        environment = dict(NASDAQ_P1_PRIVATE_CONTEXT="local_private", NASDAQ_P1_BUNDLE="bundle",
                           NASDAQ_P1_PRIVATE_KEY="key", NASDAQ_P1_CODE_SHA=SHA)
        fixture = types.ModuleType("tests_placeholder")
        fixture.environment = environment
        fixture.secret = lambda _: "synthetic-password"
        def chart(symbol, **kwargs):
            import streamlit as st
            st.caption(f"chart:{symbol}:{kwargs['chart_period']}")
            return go.Figure(go.Scatter(x=[1, 2], y=[1, 2]))
        fixture.chart = chart
        prepared = prepare_review(payload, pd.DataFrame(), pd.DataFrame(), NOW)
        with patch.dict(sys.modules, tests_placeholder=fixture), patch(
                "nasdaq_p1_private_review.load_bundle", return_value=payload) as reader, patch(
                "nasdaq_p1_private_review.prepare_review", return_value=prepared):
            app = AppTest.from_string(source).run()
            self.assertFalse(app.exception)
            reader.assert_not_called()
            app.text_input[0].set_value("synthetic-password")
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any("chart:SYNTHA:일봉" in c.value for c in app.caption))
            app.selectbox[0].select("SYNTHB").run()
            app.radio[0].set_value("주봉").run()
            self.assertFalse(app.exception)
            self.assertTrue(any("chart:SYNTHB:주봉" in c.value for c in app.caption))
            self.assertTrue(app.warning)
            app.run()
            self.assertEqual(app.selectbox[0].value, "SYNTHB")
            app.button[0].click().run()
            self.assertFalse(app.selectbox)
            calls = reader.call_count
            environment["NASDAQ_P1_PRIVATE_CONTEXT"] = "public"
            app.run()
            self.assertFalse(app.expander)
            self.assertEqual(reader.call_count, calls)

    def test_real_dashboard_shared_charts_and_area_return_preserve_private_choices(self):
        import os
        import streamlit as st
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            private = Path(temp)
            key, encrypted = private / "key.pem", private / "capture.json"
            key.write_bytes(self.private)
            encrypted.write_bytes(seal(bundle(), self.public))
            environment = dict(NASDAQ_P1_PRIVATE_CONTEXT="local_private",
                NASDAQ_P1_BUNDLE=str(encrypted), NASDAQ_P1_PRIVATE_KEY=str(key),
                NASDAQ_P1_CODE_SHA=SHA)
            rendered = []
            original = st.plotly_chart
            def chart(figure, *args, **kwargs):
                if kwargs.get("key") == "p1_private_chart":
                    candle = next(t for t in figure.data if t.type == "candlestick")
                    self.assertGreater(len(candle.x), 0)
                    self.assertTrue(any(t.type == "bar" for t in figure.data))
                    rendered.append((figure.layout.title.text, candle.name))
                return original(figure, *args, **kwargs)
            with patch.dict(os.environ, environment), patch.object(st, "plotly_chart", chart), patch(
                    "requests.sessions.Session.request", side_effect=AssertionError("provider forbidden")):
                app = AppTest.from_file(str(root / "app.py"), default_timeout=60)
                app.secrets["APP_PASSWORD"] = "synthetic-session-only"
                app.run()
                app.radio(key="analysis_navigation_choice").set_value("stocks").run()
                next(w for w in app.text_input if w.label == "검토 비밀번호").set_value("synthetic-session-only")
                next(w for w in app.button if w.label == "가격 이력 열기").click().run()
                self.assertFalse(app.exception)
                app.selectbox(key="p1_private_symbol").set_value("SYNTHB").run()
                app.radio(key="p1_private_period").set_value("주봉").run()
                self.assertEqual(rendered[-1], ("SYNTHB", "주봉"))
                app.radio(key="analysis_navigation_choice").set_value("markets_commodities").run()
                app.radio(key="analysis_navigation_choice").set_value("stocks").run()
                self.assertFalse(app.exception)
                self.assertEqual(app.selectbox(key="p1_private_symbol").value, "SYNTHB")
                self.assertEqual(app.radio(key="p1_private_period").value, "주봉")
                self.assertEqual(rendered[-1], ("SYNTHB", "주봉"))
                app.button(key="p1_private_lock").click().run()
                self.assertFalse(app.exception)
                self.assertFalse(any(w.key == "p1_private_symbol" for w in app.selectbox))


if __name__ == "__main__":
    unittest.main()
