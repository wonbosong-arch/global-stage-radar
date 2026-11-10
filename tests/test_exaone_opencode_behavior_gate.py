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


if __name__ == "__main__":
    unittest.main()
