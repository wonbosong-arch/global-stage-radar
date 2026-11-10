"""Regression: known EXAONE output bug must fail in the trusted behavior gate.

The fixture source in this test is written by us, never by a remote model.
"""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

CHECKER_PATH = Path(__file__).resolve().parents[1] / "automation/exaone-opencode-poc/behavior_check.py"
spec = importlib.util.spec_from_file_location("exaone_behavior_check", CHECKER_PATH)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class BehaviorGateTests(unittest.TestCase):
    def test_correct_ticker_function_passes(self):
        code = (
            "import re\n"
            "def normalize_ticker(value):\n"
            "    if not isinstance(value, str): raise ValueError('not string')\n"
            "    value = value.strip().upper()\n"
            "    if not 0 < len(value) <= 20 or not re.fullmatch(r'[A-Z0-9.-]+', value):\n"
            "        raise ValueError('invalid ticker')\n"
            "    return value\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "ticker_utils.py").write_text(code, encoding="utf-8")
            with patch.object(checker, "ROOT", Path(directory)):
                checker.check_ticker()

    def test_original_uppercase_before_normalize_bug_is_rejected(self):
        faulty = (
            "import re\n"
            "def normalize_ticker(value):\n"
            "    if not isinstance(value, str): raise ValueError('not string')\n"
            "    if not re.fullmatch(r'[A-Z0-9.-]+', value): raise ValueError('invalid')\n"
            "    return value.strip().upper()\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "ticker_utils.py").write_text(faulty, encoding="utf-8")
            with patch.object(checker, "ROOT", Path(directory)):
                with self.assertRaises((ValueError, AssertionError)):
                    checker.check_ticker()

    def test_accepts_non_string_must_fail(self):
        faulty = (
            "def normalize_ticker(value):\n"
            "    return str(value).strip().upper()\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "ticker_utils.py").write_text(faulty, encoding="utf-8")
            with patch.object(checker, "ROOT", Path(directory)):
                with self.assertRaises(AssertionError):
                    checker.check_ticker()

    def test_parser_regression_tests_must_detect_deliberately_broken_parser(self):
        import sys
        valid = (
            "import unittest\nimport json\nimport exaone_sector_pilot as pilot\n"
            "class ParserRegressionTests(unittest.TestCase):\n"
            "    def _raw(self, reason='stop'):\n"
            "        record = {'symbol': 'AAPL', 'sector': 'Information Technology',\n"
            "                  'industry': '소비자 전자기기', 'confidence': 0.9,\n"
            "                  'evidence': 'Consumer electronics'}\n"
            "        envelope = {'choices': [{'finish_reason': reason, 'message':\n"
            "                    {'role': 'assistant', 'content': json.dumps(record)}}]}\n"
            "        return json.dumps(envelope).encode('utf-8')\n"
            "    def test_valid_completion(self):\n"
            "        parsed = pilot.parse_completion(self._raw(), 'AAPL')\n"
            "        self.assertEqual(parsed['sector'], 'Information Technology')\n"
            "    def test_truncated_completion(self):\n"
            "        with self.assertRaises(pilot.PilotError):\n"
            "            pilot.parse_completion(self._raw('length'), 'AAPL')\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            (root / "tests/test_exaone_sector_pilot_agent.py").write_text(
                valid, encoding="utf-8"
            )
            try:
                with patch.object(checker, "ROOT", root):
                    checker.check_regression_tests()
            finally:
                sys.modules.pop("test_exaone_sector_pilot_agent", None)



if __name__ == "__main__":
    unittest.main()
