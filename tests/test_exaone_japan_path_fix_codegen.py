"""Offline synthetic tests: no EXAONE API requests and no JPX issuer records."""
import importlib.util
import io
import json
from contextlib import redirect_stderr
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "automation/exaone_japan_path_fix_codegen.py"
V = ROOT / "automation/exaone_japan_path_fix_verify.py"
spec = importlib.util.spec_from_file_location("exaone_japan_path_fix_codegen", G)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
vspec = importlib.util.spec_from_file_location("exaone_japan_path_fix_verify", V)
verify = importlib.util.module_from_spec(vspec)
vspec.loader.exec_module(verify)

ORIGINAL = """from pathlib import Path
REPO = Path(__file__).resolve().parents[1]

def safe_outside_repo(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved == REPO or REPO in resolved.parents:
        raise ValueError("private_jpx_files_must_be_outside_checkout")
    return resolved
"""
SYNTHETIC_FIX = {
    "repo_assignment": "REPO = Path(__file__).resolve().parent",
    "replacement_function": """def safe_outside_repo(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved == REPO or REPO in resolved.parents:
        raise ValueError("private_jpx_files_must_be_outside_checkout")
    return resolved""",
}


class FakeHTTPResponse:
    status = 200
    def __init__(self, result, status=200, headers=None):
        self.result = result
        self.status = status
        self.headers = headers or {}
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit): return self.result[:limit]
    def getheader(self, name): return self.headers.get(name)


def api_response(*, reason="stop", content=None):
    body = {
        "choices": [{"finish_reason": reason, "message": {
            "role": "assistant",
            "content": content if content is not None else json.dumps(SYNTHETIC_FIX),
        }}],
        "usage": {
            "prompt_tokens": 120, "completion_tokens": 330,
            "total_tokens": 450, "reasoning_tokens": 220,
        },
    }
    return json.dumps(body).encode("utf-8")


class ExaoneJapanPathFixTests(unittest.TestCase):
    def test_source_excerpt_contains_real_bug_context(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "source.py"
            path.write_text(ORIGINAL, encoding="utf-8")
            a, f = gen.source_excerpt(path)
            self.assertIn(".parents[1]", a)
            self.assertIn("def safe_outside_repo", f)
            request = json.loads(gen.payload(path).decode("utf-8"))
            self.assertEqual(request["model"], "k-exaone_v2.5")
            self.assertEqual(request["max_tokens"], 4096)
            self.assertFalse(request["stream"])
            self.assertIn(gen.TASK, request["messages"][1]["content"])
            self.assertIn("sibling", request["messages"][0]["content"].lower())

    def test_accept_well_formed_review_only_code(self):
        report = gen.validate_candidate(json.dumps(SYNTHETIC_FIX))
        self.assertEqual(report["repo_assignment"], SYNTHETIC_FIX["repo_assignment"])
        patched = verify.assemble(ORIGINAL, report)
        self.assertIn(".parent\n", patched)
        self.assertNotIn(".parents[1]", patched)
        self.assertEqual(patched.count("def safe_outside_repo"), 1)

    def test_reject_missing_fields_duplicate_declarations_and_unsafe_import(self):
        bads = [
            {"repo_assignment": "REPO = Path(__file__).resolve().parent"},
            {"repo_assignment": "REPO = Path(__file__).resolve().parent",
             "replacement_function": "def broken(path): pass"},
            {"repo_assignment": "REPO = Path(__file__).resolve().parent",
             "replacement_function": "def safe_outside_repo(path):\n    import os"},
            {"repo_assignment": "import os\nREPO = Path(__file__).resolve().parent",
             "replacement_function": SYNTHETIC_FIX["replacement_function"]},
            {**SYNTHETIC_FIX, "extra": "not allowed"},
        ]
        for value in bads:
            with self.subTest(value=value), self.assertRaises(ValueError):
                gen.validate_candidate(json.dumps(value))
        with self.assertRaises(ValueError):
            gen.validate_candidate("not-json")
        with self.assertRaises(ValueError):
            gen.validate_candidate("")
        backticks = chr(96) * 3
        fenced = backticks + "json\n" + json.dumps(SYNTHETIC_FIX) + "\n" + backticks
        self.assertEqual(gen.validate_candidate(fenced), SYNTHETIC_FIX)
        with self.assertRaises(ValueError):
            gen.validate_candidate("PROSE\n" + json.dumps(SYNTHETIC_FIX))
        with self.assertRaises(ValueError):
            gen.validate_candidate(json.dumps({
                **SYNTHETIC_FIX,
                "repo_assignment": "REPO = __import__('os').system('echo forbidden')",
            }))
        with self.assertRaises(ValueError):
            gen.validate_candidate(json.dumps({
                **SYNTHETIC_FIX,
                "replacement_function":
                    "def safe_outside_repo(path: Path):\n"
                    "    path.unlink()\n"
                    "    return path",
            }))


    def test_verifier_accepts_sibling_but_blocks_repo_root_children_and_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "global-stage-radar").mkdir()
            module = types.SimpleNamespace()
            module.REPO = (root / "global-stage-radar").resolve()
            def safe_outside_repo(path):
                resolved = path.expanduser().resolve()
                if resolved == module.REPO or module.REPO in resolved.parents:
                    raise ValueError("private_jpx_files_must_be_outside_checkout")
                return resolved
            module.safe_outside_repo = safe_outside_repo
            self.assertEqual(verify.check_boundary(module, root), 5)

    def test_verifier_rejects_parent_directory_as_repository(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "global-stage-radar").mkdir()
            module = types.SimpleNamespace(
                REPO=root,
                safe_outside_repo=lambda p: p.resolve(),
            )
            with self.assertRaises(AssertionError):
                verify.check_boundary(module, root)

    def test_one_api_call_records_provider_reported_reasoning_tokens(self):
        secret = "SYNTHETIC_EXAONE_KEY_NONREAL"
        with patch.object(gen, "HTTPSConnection") as factory:
            factory.return_value.getresponse.return_value = FakeHTTPResponse(api_response())
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                output = gen.generate(secret, b"{}")
            factory.assert_called_once_with("api.exaone.ai", timeout=90)
            factory.return_value.request.assert_called_once()
            factory.return_value.close.assert_called_once()
            self.assertEqual(output["candidate"], SYNTHETIC_FIX)
            self.assertEqual(output["metrics"]["usage"]["reasoning_tokens"], 220)
            self.assertEqual(output["metrics"]["api_requests"], 1)
            self.assertEqual(
                output["metrics"]["rate_limits"]["x-day-rate-limit-remaining"],
                "미확인",
            )
            self.assertEqual(output["jpx_rows_used"], 0)
            self.assertNotIn(secret, stderr.getvalue())
            self.assertNotIn(SYNTHETIC_FIX["replacement_function"], stderr.getvalue())

    def test_429_logs_only_documented_numeric_quota_headers(self):
        key = "SYNTHETIC_EXAONE_KEY_NONREAL"
        error_body = b"PRIVATE_API_ERROR_NEVER_LOG"
        headers = {
            "x-second-rate-limit": "1",
            "x-second-rate-limit-remaining": "0",
            "x-minute-rate-limit": "60",
            "x-minute-rate-limit-remaining": "3",
            "x-day-rate-limit": "30",
            "x-day-rate-limit-remaining": "0",
            "retry-after": "40",
            "retry-after-ms": "600",
            "x-secret-header": "PRIVATE_HEADER_VALUE",
        }
        response = FakeHTTPResponse(error_body, status=429, headers=headers)
        stderr = io.StringIO()
        with patch.object(gen, "HTTPSConnection") as factory:
            factory.return_value.getresponse.return_value = response
            with redirect_stderr(stderr):
                with self.assertRaisesRegex(ValueError, "exaone_http_429"):
                    gen.generate(key, b"{}")
            factory.return_value.request.assert_called_once()
            factory.return_value.close.assert_called_once()
        logged = stderr.getvalue()
        self.assertIn('"http_status": 429', logged)
        self.assertIn('"x-day-rate-limit-remaining": "0"', logged)
        self.assertIn('"retry-after": "40"', logged)
        self.assertIn('"automatic_retries": 0', logged)
        for sensitive in (key, error_body.decode(), "PRIVATE_HEADER_VALUE"):
            self.assertNotIn(sensitive, logged)
        self.assertNotIn("x-secret-header", logged)

    def test_rate_limit_headers_fail_closed_on_untrusted_values(self):
        class Response:
            def getheader(self, name):
                values = {
                    "x-day-rate-limit": "123",
                    "x-day-rate-limit-remaining": "0\nPRIVATE",
                    "retry-after-ms": "630",
                    "retry-after": "1.5",
                    "x-minute-rate-limit": "-1",
                }
                return values.get(name)
        values = gen.safe_rate_headers(Response())
        self.assertEqual(values["x-day-rate-limit"], "123")
        self.assertEqual(values["x-day-rate-limit-remaining"], "미확인")
        self.assertEqual(values["retry-after-ms"], "630")
        self.assertEqual(values["retry-after"], "1.5")
        self.assertEqual(values["x-minute-rate-limit"], "미확인")
        self.assertEqual(set(values), set(gen.RATE_HEADERS))

    def test_length_error_does_not_retry_or_log_model_code(self):
        with patch.object(gen, "HTTPSConnection") as factory:
            factory.return_value.getresponse.return_value = FakeHTTPResponse(
                api_response(reason="length", content="PRIVATE_MODEL_RESPONSE"))
            stderr = io.StringIO()
            with redirect_stderr(stderr), self.assertRaisesRegex(ValueError, "exaone_output_truncated"):
                gen.generate("SYNTHETIC_EXAONE_KEY_NONREAL", b"{}")
            factory.return_value.request.assert_called_once()
            self.assertNotIn("PRIVATE_MODEL_RESPONSE", stderr.getvalue())

    def test_source_patch_ambiguous_target_fails(self):
        with self.assertRaises(ValueError):
            verify.assemble(ORIGINAL.replace("def safe_outside_repo", "def different"), SYNTHETIC_FIX)
        with self.assertRaises(FileNotFoundError):
            gen.source_excerpt(Path("/definitely-not-present/test.py"))

    def test_no_jpx_file_access_or_exaone_call_in_offline_check(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "synthetic.py"
            path.write_text(ORIGINAL, encoding="utf-8")
            with patch.object(gen, "HTTPSConnection") as conn:
                self.assertEqual(gen.main(["--target", str(path)]), 0)
                conn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
