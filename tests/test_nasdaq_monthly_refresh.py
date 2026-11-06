"""Synthetic quality/transaction/browser-control contracts; no Nasdaq/KIS network."""
from datetime import datetime, timezone
import io
import csv
from contextlib import redirect_stdout
import json
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import nasdaq_monthly_refresh as subject
from nasdaq_single_source import check_local_manifest

NOW = datetime(2026, 11, 6, tzinfo=timezone.utc)


def raw_csv(count=10, changes=None):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=subject.FIELDS)
    writer.writeheader()
    for i in range(count):
        row = dict(zip(subject.FIELDS, ["TEST" + str(i), "Invented Company Common Stock",
            "$12.50", "-0.1", "-1%", "1000000000", "", "", "2000", "Basic Materials", "Metal Mining"]))
        row.update((changes or {}).get(i, {}))
        writer.writerow(row)
    return stream.getvalue().encode()


def manifest(raw):
    return subject.official_manifest(raw, NOW.isoformat(), "synthetic test instruction")


def replay(csv_path, manifest_path, data_dir, as_of, now=None):
    return dict(operational_additions=0, csv_sha256=subject.digest(csv_path.read_bytes()),
                counts={"combined_same_date_eligible": 0})


class MonthlyRefreshTests(unittest.TestCase):
    def test_exact_schema_numeric_missing_and_ticker_na(self):
        raw = raw_csv(changes={0: {"Symbol": "NA", "Market Cap": "N/A", "Sector": "", "Industry": ""}})
        result = subject.quality(raw, manifest(raw), min_rows=10)
        self.assertEqual(result["unique_symbols"], 10)
        self.assertEqual(result["native_classification_complete"], 9)
        self.assertFalse(result["source_exchange_column"])
        for raw in (raw_csv().replace(b"Symbol", b"Ticker"), b"<html>blocked</html>",
                    raw_csv(changes={0: {"Volume": "inf"}}),
                    raw_csv(changes={0: {"Name": ""}}),
                    raw_csv(changes={0: {"Symbol": "TEST1"}}),
                    raw_csv(changes={i: {"Sector": ""} for i in range(3)}),
                    raw_csv(changes={0: {"Sector": ""}, 1: {"Sector": ""}, 2: {"Industry": ""}})):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                subject.quality(raw, manifest(raw), min_rows=10)

    def test_row_drop_missing_increase_and_alias_collisions(self):
        original = raw_csv(100)
        previous = subject.quality(original, manifest(original), min_rows=1)
        for raw in (raw_csv(84), raw_csv(100, {i: {"Industry": ""} for i in range(6)}),
                    raw_csv(10, {0: {"Symbol": "TEST/A"}, 1: {"Symbol": "TEST.A"}})):
            with self.assertRaises(ValueError):
                subject.quality(raw, manifest(raw), previous, min_rows=1)
        bad = manifest(original)
        bad["symbol_aliases"] = [dict(source_symbol="TEST.A", kis_symbol="TEST/B", venue="NYS", evidence_reference="invented")]
        with self.assertRaises(ValueError): subject.quality(original, bad, min_rows=1)

    def test_acquisition_provenance_keeps_manual_and_official_distinct(self):
        raw = raw_csv()
        official = manifest(raw)
        check_local_manifest(official, subject.digest(raw), NOW)
        self.assertIsNone(official["source_as_of"])
        manual = dict(official, dataset_kind="user_supplied_nasdaq_csv", acquisition_method="user_manual_download")
        check_local_manifest(manual, subject.digest(raw), NOW)
        for changes in ({"acquisition_method": "user_manual_download"}, {"downloaded_at_utc": None},
                        {"download_control": "hidden API"}, {"csv_sha256": "bad"}):
            with self.assertRaises(ValueError): check_local_manifest(dict(official, **changes), subject.digest(raw), NOW)

    def test_transaction_failure_retains_verified_last_good_and_hash_tampering_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "input.csv"; state = root / "state"
            raw = raw_csv(); source.write_bytes(raw)
            current = subject.refresh(state, source, manifest(raw), root, "2026-11-06", NOW, 10, replay)
            pointer = (state / "current.json").read_bytes()
            self.assertFalse(current["stale_or_unknown"])
            for failure in (ValueError("replay rejected"), OSError("disk full")):
                with self.assertRaises(type(failure)):
                    subject.refresh(state, source, manifest(raw), root, "2026-11-06", NOW, 10, Mock(side_effect=failure))
                self.assertEqual((state / "current.json").read_bytes(), pointer)
                subject.load_current(state, NOW, 10)
            with patch.object(subject.os, "replace", side_effect=OSError("publish failed")):
                with self.assertRaises(OSError): subject.refresh(state, source, manifest(raw), root, "2026-11-06", NOW, 10, replay)
            self.assertEqual((state / "current.json").read_bytes(), pointer)
            current["folder"].joinpath("replay.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "integrity"): subject.load_current(state, NOW, 10)

    def test_lock_stale_fallback_and_path_guards(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "input.csv"; state = root / "state"
            raw = raw_csv(); source.write_bytes(raw)
            subject.refresh(state, source, manifest(raw), root, "2026-11-06", NOW, 10, replay)
            later = datetime(2026, 12, 25, tzinfo=timezone.utc)
            self.assertTrue(subject.load_current(state, later, 10)["stale_or_unknown"])
            (state / ".refresh.lock").touch()
            with self.assertRaises(FileExistsError): subject.refresh(state, source, manifest(raw), root, "2026-11-06", NOW, 10, replay)
            self.assertTrue((state / ".refresh.lock").exists())
            (root / ".git").touch()
            with self.assertRaises(ValueError): subject.load_current(state, NOW, 10)

    def test_official_control_no_api_and_stop_on_denial(self):
        page = Mock()
        page.goto.return_value.status = 200
        page.locator.return_value.inner_text.return_value = "Showing 1-25 of 6000 Download CSV"
        download = Mock(suggested_filename="nasdaq_screener_123.csv")
        download.failure.return_value = None
        page.expect_download.return_value.__enter__ = Mock(return_value=Mock(value=download))
        page.expect_download.return_value.__exit__ = Mock(return_value=False)
        subject.acquire_button(page, Path("invented.csv"))
        page.goto.assert_called_once_with(subject.SOURCE, wait_until="domcontentloaded", timeout=45000)
        page.get_by_role.assert_any_call("button", name="Download CSV", exact=True)
        download.save_as.assert_called_once_with("invented.csv")
        for status in (403, 429):
            denied_page = Mock()
            denied_page.goto.return_value.status = 200
            denied_page.locator.return_value.inner_text.return_value = "Download CSV"
            denied_page.on.side_effect = lambda event, callback: callback(Mock(url="https://api.nasdaq.com/observed-by-page", status=status))
            with self.assertRaises(subject.DownloadStopped): subject.acquire_button(denied_page, Path("never.csv"))
            denied_page.expect_download.assert_not_called()
        page.locator.return_value.inner_text.return_value = "Verify you are human"
        with self.assertRaises(subject.DownloadStopped): subject.acquire_button(page, Path("never.csv"))

    def test_manual_workflow_is_read_only_unpublished_and_unscheduled(self):
        text = (Path(__file__).parents[1] / ".github/workflows/nasdaq-refresh-pilot.yml").read_text()
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("schedule:", text)
        self.assertNotIn("upload-artifact", text)
        self.assertNotIn("actions/cache", text)
        self.assertNotIn("git push", text)

    def test_collector_disables_only_http2_and_keeps_official_button_context(self):
        pw = Mock()
        manager = Mock()
        manager.__enter__ = Mock(return_value=pw)
        manager.__exit__ = Mock(return_value=False)
        module = SimpleNamespace(sync_playwright=Mock(return_value=manager), TimeoutError=TimeoutError)
        browser = pw.chromium.launch.return_value
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "synthetic.csv"
            source.write_bytes(raw_csv())
            with patch.dict(sys.modules, {"playwright": SimpleNamespace(), "playwright.sync_api": module}), \
                    patch.object(subject, "acquire_button") as acquire:
                result = subject.collect(source, "synthetic instruction", attempts=1)
        pw.chromium.launch.assert_called_once_with(headless=True, args=["--disable-http2"])
        browser.new_context.assert_called_once_with(accept_downloads=True)
        acquire.assert_called_once_with(browser.new_context.return_value.new_page.return_value, source)
        browser.close.assert_called_once_with()
        self.assertEqual(result["acquisition_method"], "official_ui_download")

    def test_collector_retries_timeout_once_and_never_denial_or_bad_data(self):
        class BrowserTimeout(Exception):
            pass
        pw = Mock()
        cm = Mock()
        cm.__enter__ = Mock(return_value=pw)
        cm.__exit__ = Mock(return_value=False)
        module = SimpleNamespace(sync_playwright=Mock(return_value=cm), TimeoutError=BrowserTimeout)
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "new.csv"; source.write_bytes(raw_csv())
            with patch.dict(sys.modules, {"playwright": SimpleNamespace(), "playwright.sync_api": module}):
                for error, expected in ((BrowserTimeout(), 2), (subject.DownloadStopped("HTTP403"), 1), (ValueError("bad file"), 1)):
                    sleeper = Mock()
                    with patch.object(subject, "acquire_button", side_effect=[error, None]) as acquire:
                        if expected == 2:
                            result = subject.collect(source, "synthetic instruction", sleep=sleeper)
                            self.assertEqual(result["acquisition_method"], "official_ui_download")
                            sleeper.assert_called_once_with(30)
                        else:
                            with self.assertRaises(type(error)): subject.collect(source, "synthetic instruction", sleep=sleeper)
                            sleeper.assert_not_called()
                        self.assertEqual(acquire.call_count, expected)
                with patch.object(subject, "acquire_button", side_effect=BrowserTimeout()) as acquire:
                    with self.assertRaises(BrowserTimeout): subject.collect(source, "synthetic instruction", sleep=Mock())
                    self.assertEqual(acquire.call_count, 2)

    def test_cli_failure_returns_nonzero_with_last_good_without_republishing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "input.csv"; state = root / "state"
            raw = raw_csv(5000); source.write_bytes(raw)
            m = manifest(raw)
            subject.refresh(state, source, m, root, "2026-11-06", NOW, replay=replay)
            pointer = (state / "current.json").read_bytes()
            mp = root / "manifest.json"; mp.write_text(json.dumps(m))
            source.write_bytes(b"<html>failed replacement</html>")
            output = io.StringIO()
            aggregate = root / "aggregate.json"
            args = ["refresh", "--state-dir", str(state), "--csv", str(source), "--manifest", str(mp), "--as-of", "2026-11-06", "--summary", str(aggregate)]
            with patch.object(sys, "argv", args), redirect_stdout(output):
                code = subject.main()
            result = json.loads(output.getvalue())
            self.assertEqual(code, 2)
            self.assertEqual(result["status"], "fallback")
            self.assertEqual(result["quality"]["rows"], 5000)
            self.assertTrue(result["source_date_unknown"])
            self.assertTrue(result["last_good_available"])
            self.assertEqual(result["failure_stage"], "validation_replay_publish")
            self.assertEqual(json.loads(aggregate.read_text()), result)
            self.assertNotIn(str(source), output.getvalue())
            self.assertEqual((state / "current.json").read_bytes(), pointer)

    def test_failed_first_download_emits_safe_summary_without_claiming_measurements(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); aggregate = root / "aggregate.json"
            error = RuntimeError("private path /private/secret.csv and URL?token=secret")
            error.nasdaq_failure_stage = "browser_launch"
            args = ["refresh", "--state-dir", str(root / "state"), "--download",
                    "--instruction-reference", "synthetic", "--as-of", "2026-11-06",
                    "--summary", str(aggregate)]
            output = io.StringIO()
            with patch.object(sys, "argv", args), patch.object(subject, "collect", side_effect=error) as collect, redirect_stdout(output):
                code = subject.main()
            result = json.loads(output.getvalue())
            self.assertEqual(code, 2)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failure_stage"], "browser_launch")
            self.assertEqual(result["failure_code"], "operation_failed")
            self.assertFalse(result["last_good_available"])
            self.assertNotIn("quality", result)
            self.assertNotIn("stage_counts", result)
            self.assertEqual(json.loads(aggregate.read_text()), result)
            self.assertNotIn("secret", output.getvalue())
            collect.assert_called_once()

    def test_navigation_error_is_not_replaced_by_broken_page_guard(self):
        page = Mock()
        original = RuntimeError("private navigation details")
        page.goto.side_effect = original
        page.locator.return_value.inner_text.side_effect = ValueError("secondary body read")
        with self.assertRaises(RuntimeError) as caught:
            subject.acquire_button(page, Path("never.csv"))
        self.assertIs(caught.exception, original)
        self.assertEqual(subject.failure_details(original)["failure_stage"], "page_navigation")
        page.expect_download.assert_not_called()

    def test_fixed_diagnostics_distinguish_browser_launch_and_denial_without_message(self):
        pw = Mock(); cm = Mock()
        cm.__enter__ = Mock(return_value=pw); cm.__exit__ = Mock(return_value=False)
        module = SimpleNamespace(sync_playwright=Mock(return_value=cm), TimeoutError=TimeoutError)
        pw.chromium.launch.side_effect = RuntimeError("secret browser launch arguments")
        with patch.dict(sys.modules, {"playwright": SimpleNamespace(), "playwright.sync_api": module}):
            with self.assertRaises(RuntimeError) as caught:
                subject.collect(Path("never.csv"), "synthetic")
        self.assertEqual(subject.failure_details(caught.exception)["failure_stage"], "browser_launch")
        pw.chromium.launch.assert_called_once()
        for status in (401, 403, 429):
            page = Mock(); page.goto.return_value.status = status
            page.locator.return_value.inner_text.return_value = "Access denied"
            with self.assertRaises(subject.DownloadStopped) as caught:
                subject.acquire_button(page, Path("never.csv"))
            self.assertEqual(subject.failure_details(caught.exception), dict(
                failure_stage="access_check", failure_code="access_stopped", http_status=status))
            page.expect_download.assert_not_called()
        unknown = RuntimeError("secret")
        unknown.nasdaq_failure_stage = "/private/secret.csv"
        self.assertEqual(subject.failure_details(unknown)["failure_stage"], "unclassified")
        self.assertNotIn("secret", json.dumps(subject.failure_details(unknown)))

    def test_summary_write_error_is_safe_and_does_not_hide_failed_collection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = ["refresh", "--state-dir", str(root / "state"), "--download",
                    "--instruction-reference", "synthetic", "--as-of", "2026-11-06",
                    "--summary", str(root / "missing" / "secret.json")]
            output = io.StringIO()
            with patch.object(sys, "argv", args), patch.object(subject, "collect", side_effect=RuntimeError("secret")), redirect_stdout(output):
                code = subject.main()
            result = json.loads(output.getvalue())
            self.assertEqual(code, 2)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["aggregate_summary_error"], "write_failed")
            self.assertNotIn("secret", output.getvalue())

    def test_failure_summary_workflow_does_not_turn_failed_refresh_into_success(self):
        text = (Path(__file__).parents[1] / ".github/workflows/nasdaq-refresh-pilot.yml").read_text()
        self.assertIn("id: refresh", text)
        self.assertIn("always() && steps.refresh.outcome != 'skipped'", text)
        self.assertNotIn("continue-on-error", text)
        self.assertNotIn("schedule:", text)
        self.assertNotIn("upload-artifact", text)

    def test_cli_success_and_reporting_failure_preserve_refreshed_status(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "input.csv"; state = root / "state"
            raw = raw_csv(5000); source.write_bytes(raw)
            m = manifest(raw); mp = root / "manifest.json"; mp.write_text(json.dumps(m))
            current = subject.refresh(state, source, m, root, "2026-11-06", NOW, replay=replay)
            pointer = (state / "current.json").read_bytes()
            for target, expected in ((root / "aggregate.json", 0), (root / "missing" / "secret.json", 2)):
                args = ["refresh", "--state-dir", str(state), "--csv", str(source),
                        "--manifest", str(mp), "--as-of", "2026-11-06", "--summary", str(target)]
                output = io.StringIO()
                with patch.object(sys, "argv", args), patch.object(subject, "refresh", return_value=current), redirect_stdout(output):
                    code = subject.main()
                result = json.loads(output.getvalue())
                self.assertEqual(code, expected)
                self.assertEqual(result["status"], "refreshed")
                self.assertEqual(result["quality"]["rows"], 5000)
                self.assertEqual((state / "current.json").read_bytes(), pointer)
                if expected == 0:
                    self.assertEqual(json.loads(target.read_text()), result)
                else:
                    self.assertEqual(result["aggregate_summary_error"], "write_failed")
                self.assertNotIn("secret", output.getvalue())


if __name__ == "__main__":
    unittest.main()
