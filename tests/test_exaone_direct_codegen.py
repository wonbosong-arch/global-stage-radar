"""Offline-only tests for single-request EXAONE direct code generation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "automation/exaone-opencode-poc/direct_codegen.py"
spec = importlib.util.spec_from_file_location("exaone_direct_codegen", SOURCE)
direct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(direct)


SAMPLE_SOURCE = (
    "import unittest\n"
    "import json\n"
    "import exaone_sector_pilot as pilot\n"
    "class ParserRegressionTests(unittest.TestCase):\n"
    "    def test_valid_completion(self):\n"
    "        result = 1\n"
    "        self.assertEqual(result, 1)\n"
    "    def test_truncated_completion(self):\n"
    "        with self.assertRaises(ValueError):\n"
    "            raise ValueError('truncated')\n"
)


def completion(code=SAMPLE_SOURCE, *, finish_reason="stop", tool_calls=None):
    response = {
        "choices": [{
            "finish_reason": finish_reason,
            "message": {
                "role": "assistant",
                "content": code,
            },
        }],
    }
    if tool_calls is not None:
        response["choices"][0]["message"]["tool_calls"] = tool_calls
    return json.dumps(response, ensure_ascii=False).encode("utf-8")


class DirectCodegenTests(unittest.TestCase):
    def test_prompt_is_fixed_and_contains_only_parser_contract(self):
        payload = json.loads(direct.payload_bytes())
        self.assertEqual(payload["model"], "k-exaone_v2.5")
        self.assertEqual(len(payload["messages"]), 2)
        self.assertEqual(payload["max_tokens"], 4096)
        self.assertEqual(payload["stream"], False)
        self.assertIn("def parse_completion", payload["messages"][1]["content"])
        self.assertIn("exactly two methods", payload["messages"][0]["content"])

    def test_extracts_plain_or_fenced_python_and_rejects_tool_calls(self):
        self.assertEqual(direct.extract_source(completion()), SAMPLE_SOURCE)
        fenced = "ࠀࠀࠀpython\n" + SAMPLE_SOURCE.rstrip() + "\nࠀࠀࠀ"
        # Use an ordinary literal markdown fence, not a model-provided filename.
        fenced = fenced.replace("ࠀ", "`")
        self.assertEqual(direct.extract_source(completion(fenced)), SAMPLE_SOURCE)
        with self.assertRaisesRegex(direct.CodegenError, "invalid_generated_source"):
            direct.extract_source(completion(tool_calls=[{"id": "x"}]))

    def test_does_not_accept_partial_or_invalid_completion(self):
        for data in (
            completion(finish_reason="length"),
            completion("invalid python = ???"),
            completion("x = 'y'\n" * 10001),
            b"not-json",
            b'{"choices":[]}',
        ):
            with self.subTest(data=data[:20]):
                with self.assertRaisesRegex(direct.CodegenError, "invalid_generated_source"):
                    direct.extract_source(data)

    def test_single_request_writes_only_one_approved_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "scratch"
            client = Mock()
            client._key = "FAKE_API_KEY_FOR_UNIT_TEST"
            client._attempt.return_value = (completion(), None, 0)
            with patch.object(direct, "ExaoneClient", return_value=client):
                generated = direct.generate(workspace)
            self.assertEqual(generated.name, "test_exaone_sector_pilot_agent.py")
            self.assertEqual(generated.read_text(encoding="utf-8"), SAMPLE_SOURCE)
            client._attempt.assert_called_once()
            self.assertEqual(client._attempt.call_args.args[1], 0)
            self.assertEqual(
                {p.name for p in workspace.iterdir()},
                {"exaone_sector_pilot.py", "stock_mapping.py", "tests", "opencode.json", "task.txt", "manifest.json"},
            )

    def test_sensitive_or_failed_response_never_publishes_source(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "scratch"
            client = Mock()
            client._key = "SECRET_EXAONE_UNIT_TEST_KEY"
            client._attempt.return_value = (completion("x = 'SECRET_EXAONE_UNIT_TEST_KEY'\n"), None, 0)
            with patch.object(direct, "ExaoneClient", return_value=client):
                with self.assertRaisesRegex(direct.CodegenError, "sensitive_generated_source"):
                    direct.generate(workspace)
            self.assertFalse((workspace / "tests/test_exaone_sector_pilot_agent.py").exists())
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "scratch"
            client = Mock()
            client._key = "FAKE_API_KEY"
            client._attempt.return_value = (None, "http_429", 0)
            with patch.object(direct, "ExaoneClient", return_value=client):
                with self.assertRaisesRegex(direct.CodegenError, "exaone_request_failed"):
                    direct.generate(workspace)
            client._attempt.assert_called_once()


if __name__ == "__main__":
    unittest.main()
