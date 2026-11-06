"""Synthetic navigation failures only: no browser launch or external requests."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import nasdaq_monthly_refresh as subject


class NavigationDiagnosticsTests(unittest.TestCase):
    def test_known_network_codes_are_allowlisted_and_unknown_is_bounded(self):
        cases = {
            "ERR_NAME_NOT_RESOLVED": "dns_failure",
            "ERR_NAME_RESOLUTION_FAILED": "dns_failure",
            "ERR_CONNECTION_REFUSED": "tcp_failure",
            "ERR_CONNECTION_RESET": "tcp_failure",
            "ERR_SSL_PROTOCOL_ERROR": "tls_failure",
            "ERR_CERT_AUTHORITY_INVALID": "tls_failure",
            "ERR_CONNECTION_TIMED_OUT": "network_timeout",
            "ERR_TIMED_OUT": "network_timeout",
            "ERR_ABORTED": "navigation_aborted",
            "ERR_EMPTY_RESPONSE": "empty_response",
            "ERR_HTTP2_PROTOCOL_ERROR": "http_protocol_failure",
            "ERR_HTTP_RESPONSE_CODE_FAILURE": "http_response_failure",
            "ERR_FUTURE_SECRET": "network_error_unknown",
        }
        for token, expected in cases.items():
            with self.subTest(token=token):
                page = Mock()
                error = RuntimeError("Page.goto: net::" + token +
                    " at https://private.invalid/?cookie=secret\nCall log: /private/secret.csv")
                page.goto.side_effect = error
                page.locator.return_value.inner_text.side_effect = ValueError("secret body")
                with self.assertRaises(RuntimeError) as caught:
                    subject.acquire_button(page, Path("never.csv"))
                self.assertIs(caught.exception, error)
                details = subject.failure_details(error)
                self.assertEqual(details["failure_stage"], "page_navigation")
                self.assertEqual(details["failure_code"], expected)
                self.assertEqual(details.get("browser_error_code"),
                                 None if token == "ERR_FUTURE_SECRET" else token)
                self.assertNotIn("secret", json.dumps(details).lower())
                self.assertNotIn("http_status", details)
                page.goto.assert_called_once()
                page.expect_download.assert_not_called()

    def test_timeout_closed_and_url_tokens_are_not_confused_with_network_cause(self):
        closed = type("TargetClosedError", (Exception,), {})
        for error, expected in (
            (TimeoutError("secret timeout"), "timeout"),
            (closed("secret browser log"), "browser_closed"),
            (RuntimeError("Page.goto: Target page, context or browser has been closed\nsecret"), "browser_closed"),
            (RuntimeError("Page.goto: failed at https://private/net::ERR_NAME_NOT_RESOLVED"), "operation_failed"),
            (RuntimeError("Page.goto: net::ERR_CONNECTION_RESET_SECRET at private"), "network_error_unknown"),
        ):
            with self.subTest(expected=expected):
                error.nasdaq_failure_stage = "page_navigation"
                self.assertEqual(subject.failure_details(error)["failure_code"], expected)

    def test_main_document_status_survives_goto_failure_without_subresource_confusion(self):
        for host, navigation, main_frame, status, expected in (
            ("www.nasdaq.com", True, True, 200, 200),
            ("www.nasdaq.com", True, True, 503, 503),
            ("www.nasdaq.com", False, True, 500, None),
            ("www.nasdaq.com", True, False, 500, None),
            ("unrelated.invalid", True, True, 500, None),
            ("www.nasdaq.com", True, True, True, None),
            ("www.nasdaq.com", True, True, 600, None),
        ):
            with self.subTest(host=host, navigation=navigation, main=main_frame, status=status):
                page = Mock(); callbacks = {}
                page.on.side_effect = lambda event, fn: callbacks.update({event: fn})
                request = SimpleNamespace(is_navigation_request=lambda: navigation,
                                          frame=page.main_frame if main_frame else object())
                response = SimpleNamespace(url="https://" + host + "/secret?token=secret",
                                           status=status, request=request)
                def fail(*args, **kwargs):
                    callbacks["response"](response)
                    raise RuntimeError("Page.goto: net::ERR_CONNECTION_RESET at private")
                page.goto.side_effect = fail
                page.locator.return_value.inner_text.side_effect = ValueError("secret")
                with self.assertRaises(RuntimeError) as caught:
                    subject.acquire_button(page, Path("never.csv"))
                details = subject.failure_details(caught.exception)
                self.assertEqual(details.get("navigation_http_status"), expected)
                self.assertEqual(details["failure_code"], "tcp_failure")
                self.assertNotIn("secret", json.dumps(details))

    def test_denial_takes_precedence_over_transport_failure_and_stops(self):
        for status in (401, 403, 429):
            page = Mock(); callbacks = {}
            page.on.side_effect = lambda event, fn: callbacks.update({event: fn})
            request = SimpleNamespace(is_navigation_request=lambda: True, frame=page.main_frame)
            def fail(*args, **kwargs):
                callbacks["response"](SimpleNamespace(url=subject.SOURCE, status=status, request=request))
                raise RuntimeError("Page.goto: net::ERR_ABORTED at secret")
            page.goto.side_effect = fail
            with self.assertRaises(subject.DownloadStopped) as caught:
                subject.acquire_button(page, Path("never.csv"))
            self.assertEqual(subject.failure_details(caught.exception), dict(
                failure_stage="page_navigation", failure_code="access_stopped",
                http_status=status, navigation_http_status=status))
            page.goto.assert_called_once()
            page.expect_download.assert_not_called()

    def test_cli_logs_and_summary_only_safe_literals_and_passes_single_attempt(self):
        for error in (RuntimeError("Page.goto: net::ERR_NAME_NOT_RESOLVED at https://secret/?cookie=secret"),
                      type("SecretCookieClass", (Exception,), {})("/private/secret.csv")):
            error.nasdaq_failure_stage = "page_navigation"
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp); aggregate = root / "aggregate.json"; output = io.StringIO()
                args = ["refresh", "--download", "--attempts", "1", "--state-dir", str(root / "state"),
                        "--as-of", "2026-11-06", "--instruction-reference", "synthetic",
                        "--summary", str(aggregate)]
                with patch.object(sys, "argv", args), patch.object(subject, "collect", side_effect=error) as collect, redirect_stdout(output):
                    self.assertEqual(subject.main(), 2)
                result = json.loads(output.getvalue())
                self.assertEqual(json.loads(aggregate.read_text()), result)
                self.assertEqual(result["error_type"], "RuntimeError" if type(error) is RuntimeError else "Exception")
                self.assertFalse(result["last_good_available"])
                self.assertNotIn("quality", result)
                self.assertNotIn("secret", output.getvalue().lower())
                collect.assert_called_once()
                self.assertEqual(collect.call_args.args[0].name, "download.csv")
                self.assertEqual(collect.call_args.args[1], "synthetic")
                self.assertEqual(collect.call_args.kwargs, {"attempts": 1})

    def test_single_attempt_timeout_does_not_sleep_or_retry(self):
        pw = Mock(); cm = Mock()
        cm.__enter__ = Mock(return_value=pw); cm.__exit__ = Mock(return_value=False)
        module = SimpleNamespace(sync_playwright=Mock(return_value=cm), TimeoutError=TimeoutError)
        with patch.dict(sys.modules, {"playwright": SimpleNamespace(), "playwright.sync_api": module}):
            with patch.object(subject, "acquire_button", side_effect=TimeoutError("secret")) as acquire:
                sleeper = Mock()
                with self.assertRaises(TimeoutError):
                    subject.collect(Path("never.csv"), "synthetic", attempts=1, sleep=sleeper)
                acquire.assert_called_once(); sleeper.assert_not_called()
        workflow = (Path(__file__).parents[1] / "docs/retired/nasdaq-refresh-pilot.yml.disabled").read_text(encoding="utf-8")
        self.assertIn("--attempts 1", workflow)


if __name__ == "__main__":
    unittest.main()
