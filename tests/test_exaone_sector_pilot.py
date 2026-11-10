import io
import json
import os
import secrets
import sys
import unittest
from unittest.mock import Mock, call, patch

import exaone_sector_pilot as pilot


SAMPLES = json.loads(pilot.SAMPLES.read_text(encoding="utf-8"))
SAMPLE = SAMPLES[0]


def completion(**changes):
    classification = {"symbol": SAMPLE["symbol"], **SAMPLE["mock"], **changes}
    body = {"choices": [{
        "finish_reason": "stop",
        "message": {
            "role": "assistant",
            "content": "\n\n" + json.dumps(classification, ensure_ascii=False),
            "reasoning_content": "출력에 쓰지 않는 추론",
        },
    }]}
    return json.dumps(body, ensure_ascii=False).encode("utf-8")


def response(status=200, headers=None, body=None):
    reply = Mock(status=status)
    reply.__enter__ = Mock(return_value=reply)
    reply.__exit__ = Mock(return_value=False)
    reply.getheader.side_effect = (headers or {}).get
    reply.read.return_value = completion() if body is None else body
    return reply


class PilotReportTests(unittest.TestCase):
    def test_twenty_stock_replay_with_explicit_review_outcomes(self):
        self.assertEqual(len({sample["symbol"] for sample in SAMPLES}), 20)
        with patch.object(pilot, "HTTPSConnection") as network:
            report = pilot.build_report(SAMPLES, pilot.mock_classify, "mock")
            network.assert_not_called()
        self.assertEqual(report["mode"], "mock")
        self.assertEqual(report["summary"], {
            "samples": 20, "valid_responses": 19, "sector_matches": 18,
            "sector_disagreements": 1, "errors": 1, "not_attempted": 0, "pending_review": 20,
        })
        rows = {row["symbol"]: row for row in report["rows"]}
        self.assertEqual({row["reference_sector"] for row in rows.values()}, set(pilot.SECTORS))
        self.assertEqual(rows["AAPL"]["industry"], "소비자 전자기기")
        self.assertEqual(rows["AAPL"]["evidence"], {
            "source": "pilot_sample_description", "excerpt": SAMPLE["description"],
        })
        self.assertIn("reference_disagreement", rows["NVDA"]["review_reasons"])
        self.assertIn("low_model_confidence", rows["NEE"]["review_reasons"])
        self.assertIn("missing_or_unmatched_evidence", rows["PLD"]["review_reasons"])
        self.assertIsNone(rows["PLD"]["evidence"])
        self.assertEqual(rows["GE"]["error"], "invalid_classification")
        self.assertTrue(all(row["review_status"] == "pending_review" for row in rows.values()))
        self.assertTrue(all("active" not in row and "approved" not in row for row in rows.values()))

    def test_abstention_keeps_no_classification_or_comparison(self):
        def classify(sample):
            return pilot.parse_completion(completion(
                sector=None, industry=None, evidence=None, confidence=0,
            ), sample["symbol"])

        row = pilot.build_report([SAMPLE], classify, "mock")["rows"][0]
        self.assertIsNone(row["sector"])
        self.assertIsNone(row["sector_matches_reference"])
        self.assertIn("unclassified", row["review_reasons"])

    def test_rejects_bad_encoding_envelope_and_truncation(self):
        envelope = json.loads(completion())
        envelope["choices"][0]["finish_reason"] = "length"
        for raw in (b"\xff", b"{}", json.dumps(envelope).encode("utf-8")):
            with self.subTest(raw=raw), self.assertRaisesRegex(pilot.PilotError, "^invalid_completion$"):
                pilot.parse_completion(raw, SAMPLE["symbol"])

    def test_rejects_invalid_classification_fields(self):
        for change in (
            {"symbol": "MSFT"}, {"sector": "unknown"}, {"industry": ""},
            {"industry": "소비자\n전자기기"}, {"confidence": True}, {"confidence": 1.1},
            {"confidence": float("nan")}, {"confidence": "0.91"}, {"evidence": ["bad"]},
            {"active": True},
        ):
            with self.subTest(change=change), self.assertRaisesRegex(pilot.PilotError, "^invalid_classification$"):
                pilot.parse_completion(completion(**change), SAMPLE["symbol"])


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.key = secrets.token_hex(24)
        self.enterContext(patch.dict(os.environ, {"EXAONE_API_KEY": self.key}))
        self.connection = self.enterContext(patch.object(pilot, "HTTPSConnection"))
        self.http = self.connection.return_value
        self.sleep = self.enterContext(patch.object(pilot.time, "sleep"))

    def test_missing_or_invalid_key_fails_without_network(self):
        for value in ("", "invalid\nheader"):
            with self.subTest(value=value), patch.dict(os.environ, {"EXAONE_API_KEY": value}):
                with self.assertRaisesRegex(pilot.PilotError, "^missing_or_invalid_api_key$"):
                    pilot.ExaoneClient()
        self.connection.assert_not_called()

    def test_utf8_request_and_final_answer_over_fixed_https(self):
        self.http.getresponse.return_value = response()
        result = pilot.ExaoneClient().classify(SAMPLE)
        self.connection.assert_called_once_with("api.exaone.ai", timeout=90)
        request = self.http.request.call_args
        self.assertEqual(request.args, ("POST", "/v1/chat/completions"))
        headers, raw = request.kwargs["headers"], request.kwargs["body"]
        self.assertTrue(headers["Authorization"] == f"Bearer {self.key}")
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertTrue(self.key.encode() not in raw)
        self.assertIn(SAMPLE["description"].encode("utf-8"), raw)
        payload = json.loads(raw.decode("utf-8"))
        self.assertEqual(payload["model"], "k-exaone_v2.5")
        self.assertIs(payload["stream"], False)
        self.assertEqual(json.loads(payload["messages"][1]["content"]), {
            field: SAMPLE[field] for field in ("symbol", "exchange", "issuer", "description")
        })
        self.assertEqual(result["industry"], "소비자 전자기기")
        self.assertNotIn("reasoning_content", result)
        self.http.close.assert_called_once()

    def test_paces_successive_requests_and_retries_with_provider_delay(self):
        throttled = response(429, {"retry-after": "2", "retry-after-ms": "2500"})
        self.http.getresponse.side_effect = [throttled, response(), response()]
        client = pilot.ExaoneClient()
        client.classify(SAMPLE)
        client.classify(SAMPLE)
        self.assertEqual(self.sleep.call_args_list, [call(2.5), call(1)])
        self.assertEqual(self.http.request.call_count, 3)
        throttled.read.assert_not_called()

    def test_retries_timeout_and_server_error_with_bounded_backoff(self):
        self.http.getresponse.side_effect = [
            TimeoutError(self.key), response(503), response(500),
        ]
        report = pilot.build_report(SAMPLES[:2], pilot.ExaoneClient().classify, "live")
        self.assertEqual(self.sleep.call_args_list, [call(1), call(2)])
        self.assertEqual(self.http.request.call_count, 3)
        self.assertEqual(report["rows"][0]["error"], "http_500")
        self.assertEqual(report["rows"][1]["error"], "not_attempted_after_stop")
        self.assertTrue(self.key not in json.dumps(report))

    def test_actions_live_arguments_limit_requests_and_disable_retries(self):
        self.http.getresponse.side_effect = [response(), response(429, {"retry-after": "1"})]
        args = ["pilot", "--live", "--limit", "3", "--no-retries"]
        with (io.TextIOWrapper(io.BytesIO()) as output,
              patch.object(sys, "argv", args), patch.object(sys, "stdout", output)):
            self.assertEqual(pilot.main(), 1)
            output.flush()
            report = json.loads(output.buffer.getvalue())
        self.assertEqual(report["mode"], "live")
        self.assertEqual(report["summary"]["samples"], 3)
        self.assertEqual([row["error"] for row in report["rows"]], [
            None, "http_429", "not_attempted_after_stop",
        ])
        self.assertEqual(self.http.request.call_count, 2)
        self.assertNotIn(self.key, json.dumps(report))

    def test_invalid_limit_fails_before_network(self):
        for limit in ("0", "21", "1.5"):
            args = ["pilot", "--live", "--limit", limit]
            with (self.subTest(limit=limit), patch.object(sys, "argv", args),
                  patch.object(sys, "stderr", io.StringIO()), self.assertRaises(SystemExit) as error):
                pilot.main()
            self.assertEqual(error.exception.code, 2)
        self.connection.assert_not_called()

    def test_auth_redirect_and_long_quota_wait_stop_without_retry(self):
        for status in (301, 401, 403, 429):
            with self.subTest(status=status):
                self.http.reset_mock()
                reply = response(status, {"retry-after": "60"}, body=self.key.encode())
                self.http.getresponse.return_value = reply
                report = pilot.build_report(SAMPLES[:2], pilot.ExaoneClient().classify, "live")
                self.http.request.assert_called_once()
                reply.read.assert_not_called()
                self.assertEqual(report["rows"][0]["error"], f"http_{status}")
                self.assertEqual(report["summary"]["not_attempted"], 1)
                self.assertTrue(self.key not in json.dumps(report))
        self.sleep.assert_not_called()

    def test_invalid_payload_is_not_retried_and_next_sample_runs(self):
        self.http.getresponse.side_effect = [response(422), response()]
        report = pilot.build_report([SAMPLE, SAMPLE], pilot.ExaoneClient().classify, "live")
        self.assertEqual([row["error"] for row in report["rows"]], ["http_422", None])
        self.assertEqual(self.sleep.call_args_list, [call(1)])

    def test_rejects_oversize_and_credential_echo(self):
        oversized = response(body=b"x" * (pilot.MAX_RESPONSE_BYTES + 1))
        self.http.getresponse.side_effect = [
            oversized, response(body=completion(industry=self.key)),
        ]
        report = pilot.build_report([SAMPLE] * 3, pilot.ExaoneClient().classify, "live")
        oversized.read.assert_called_once_with(pilot.MAX_RESPONSE_BYTES + 1)
        self.assertEqual([row["error"] for row in report["rows"]], [
            "response_too_large", "sensitive_response", "not_attempted_after_stop",
        ])
        self.assertTrue(self.key not in json.dumps(report))


if __name__ == "__main__":
    unittest.main()
