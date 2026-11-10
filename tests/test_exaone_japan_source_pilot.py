"""Offline-only EXAONE Japan sector source pilot tests; all HTTP is mocked."""
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "automation/exaone_japan_source_pilot.py"
spec = spec_from_file_location("exaone_japan_source_pilot", SOURCE)
audit = module_from_spec(spec)
spec.loader.exec_module(audit)


def model_report():
    return {
        "task": "japan_sector_source_audit",
        "findings": [
            {
                "topic": topic,
                "access": access,
                "status": "supported_by_supplied_evidence",
                "evidence_ids": ids,
                "conclusion": "공식 사이트에서 해당 정보의 제공 경로를 확인함",
                "gap": "해당 자료의 실제 다운로드 및 재배포 권한은 미확인",
            }
            for topic, access, ids in [
                ("sector_index_values", "public_web_current", ["JPX-A", "JPX-B"]),
                ("index_history", "account_or_paid", ["JPX-A", "JPX-E"]),
                ("listed_stock_classification", "public_monthly_master", ["JPX-C", "JPX-D"]),
                ("licensed_reuse", "permission_required", ["JPX-F"]),
            ]
        ],
        "next_actions": [
            "공식 월말 상장종목 명부의 실제 데이터 필드를 확인",
            "상업적 이용 및 인덱스 시계열 라이선스를 검토",
        ],
    }


def response_object(body, reason="stop", usage=None):
    return json.dumps({
        "choices": [{"finish_reason": reason, "message": {
            "role": "assistant", "content": json.dumps(body, ensure_ascii=False)
        }}],
        "usage": usage if usage is not None else {
            "prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300,
            "completion_tokens_details": {"reasoning_tokens": 20},
        },
    }, ensure_ascii=False).encode("utf-8")


class FakeReply:
    status = 200
    def __init__(self, raw, *, status=200):
        self.raw = raw
        self.status = status
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def getheader(self, name):
        return {"x-ratelimit-remaining-requests": "25",
                "x-ratelimit-limit-requests": "30"}.get(name)
    def read(self, size):
        return self.raw[:size]


class JapanEvidencePilotTests(unittest.TestCase):
    def test_fixed_official_sources_without_index_prices_or_stock_identifiers(self):
        self.assertEqual(len(audit.EVIDENCE), 6)
        self.assertEqual(len(set(item["id"] for item in audit.EVIDENCE)), 6)
        data = json.loads(audit.payload())
        self.assertEqual(data["model"], "k-exaone_v2.5")
        self.assertEqual(data["reasoning_effort"], "low")
        self.assertEqual(data["max_tokens"], 1600)
        self.assertEqual(data["stream"], False)
        prompt = data["messages"][0]["content"]
        self.assertIn("NO browser", prompt)
        self.assertIn("Do not invent index prices", prompt)
        self.assertTrue(all(item["url"].startswith("https://") for item in audit.EVIDENCE))

    def test_valid_report_is_review_only(self):
        output = audit.validate_report(json.dumps(model_report(), ensure_ascii=False))
        self.assertEqual({x["topic"] for x in output["findings"]}, set(audit.TOPICS))

    def test_reject_unverified_citations_hallucinated_topics_or_missing_fields(self):
        variants = []
        wrong_ref = model_report()
        wrong_ref["findings"][0]["evidence_ids"] = ["JPX-UNSUPPORTED"]
        variants.append(wrong_ref)
        wrong_topic = model_report()
        wrong_topic["findings"][0]["topic"] = "tokyo_100_verified"
        variants.append(wrong_topic)
        missing = model_report()
        del missing["findings"][0]["gap"]
        variants.append(missing)
        freeform = model_report()
        freeform["topix100_company_records_verified"] = 100
        variants.append(freeform)
        for candidate in variants:
            with self.subTest(candidate=candidate["findings"][0]), self.assertRaises(ValueError):
                audit.validate_report(json.dumps(candidate, ensure_ascii=False))
        with self.assertRaises(ValueError):
            audit.validate_report("not json")

    def test_usage_unavailable_not_invented(self):
        self.assertEqual(audit.safe_usage(None)["reasoning_tokens"], "미확인")
        self.assertEqual(audit.safe_usage({"total_tokens": 321})["total_tokens"], 321)
        self.assertEqual(audit.safe_usage({"total_tokens": True})["total_tokens"], "미확인")

    def test_single_https_request_and_safe_usage_record(self):
        secret = "UNIT_TEST_NON_REAL_EXAONE_SECRET"
        fake = FakeReply(response_object(model_report()))
        with patch.object(audit, "HTTPSConnection") as factory:
            factory.return_value.getresponse.return_value = fake
            report, usage = audit.one_request(secret, audit.payload())
        self.assertEqual(report["task"], "japan_sector_source_audit")
        factory.assert_called_once_with("api.exaone.ai", timeout=audit.HTTP_TIMEOUT_SECONDS)
        connection = factory.return_value
        connection.request.assert_called_once()
        self.assertEqual(connection.request.call_args.args[:2],
                         ("POST", "/v1/chat/completions"))
        self.assertEqual(connection.request.call_args.kwargs["headers"]["Authorization"], f"Bearer {secret}")
        self.assertEqual(usage["api_requests"], 1)
        self.assertEqual(usage["usage"]["prompt_tokens"], 100)
        self.assertEqual(usage["usage"]["reasoning_tokens"], 20)
        self.assertEqual(usage["rate_limit_headers"]["x-ratelimit-remaining-requests"], "25")
        self.assertNotIn(secret, json.dumps(usage))

    def test_invalid_completion_refused_and_no_retry(self):
        for raw, status in [
            (response_object(model_report(), reason="length"), 200),
            (b"not-json", 200),
            (response_object(model_report()), 429),
        ]:
            with self.subTest(status=status):
                fake = FakeReply(raw, status=status)
                with patch.object(audit, "HTTPSConnection") as factory:
                    factory.return_value.getresponse.return_value = fake
                    with self.assertRaisesRegex(ValueError, "exaone_"):
                        audit.one_request("UNIT_TEST_NON_REAL_EXAONE_SECRET", audit.payload())
                factory.return_value.request.assert_called_once()

    def test_real_timeout_is_identified_without_secret_or_retries(self):
        secret = "UNIT_TEST_NON_REAL_EXAONE_SECRET"
        for error, expected in (
            (TimeoutError("sensitive provider details"), "exaone_timeout_await_headers_after_"),
            (ConnectionError("sensitive provider details"), "exaone_connection_error"),
            (OSError("sensitive provider details"), "exaone_transport_error"),
        ):
            with self.subTest(error=type(error).__name__):
                with patch.object(audit, "HTTPSConnection") as factory:
                    factory.return_value.getresponse.side_effect = error
                    with self.assertRaisesRegex(ValueError, expected) as caught:
                        audit.one_request(secret, audit.payload())
                    self.assertNotIn(secret, str(caught.exception))
                    self.assertNotIn("sensitive provider details", str(caught.exception))
                    factory.return_value.request.assert_called_once()
                    factory.return_value.close.assert_called_once()

    def test_secret_echo_rejected(self):
        secret = "UNIT_TEST_NON_REAL_EXAONE_SECRET"
        report = model_report()
        report["findings"][0]["conclusion"] = secret
        with patch.object(audit, "HTTPSConnection") as factory:
            factory.return_value.getresponse.return_value = FakeReply(response_object(report))
            with self.assertRaisesRegex(ValueError, "model_echoed_secret"):
                audit.one_request(secret, audit.payload())

    def test_check_only_never_calls_api_or_writes_file(self):
        with patch.object(audit, "HTTPSConnection") as connection:
            with patch("sys.argv", ["script"]):
                self.assertEqual(audit.main(), 0)
            connection.assert_not_called()

    def test_live_mock_writes_review_only_artifact(self):
        secret = "UNIT_TEST_NON_REAL_EXAONE_SECRET"
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "source-audit.json"
            with patch.dict("os.environ", {"EXAONE_API_KEY": secret}):
                with patch.object(audit, "one_request", return_value=(
                    model_report(),
                    {"api_requests": 1, "api_success": 1, "api_failures": 0,
                     "elapsed_seconds": 0.2, "usage": audit.safe_usage(None),
                     "rate_limit_headers": {}},
                )) as client:
                    with patch("sys.argv", ["script", "--live", "--out", str(target)]):
                        self.assertEqual(audit.main(), 0)
                    client.assert_called_once()
            saved = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(saved["actual_index_values_downloaded"], 0)
            self.assertEqual(saved["topix100_company_records_verified"], 0)
            self.assertEqual(saved["source_review_status"], "unverified_model_report_for_human_review")
            self.assertNotIn(secret, target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
