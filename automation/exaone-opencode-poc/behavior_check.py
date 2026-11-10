"""Test EXAONE-generated code only inside a no-secret, network-disabled container.

This module deliberately *executes* the generated Python module. Never run this
on the agent runner or any runner with EXAONE_API_KEY or repository credentials.
"""
import argparse
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path("/work")


def check_ticker():
    source = ROOT / "ticker_utils.py"
    if not source.is_file():
        raise AssertionError("missing_generated_source")
    spec = importlib.util.spec_from_file_location("generated_ticker_utils", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    valid = (
        ("AAPL", "AAPL"),
        (" aapl ", "AAPL"),
        ("brk.b", "BRK.B"),
        (" aBc-1 ", "ABC-1"),
        ("005930", "005930"),
        ("Z" * 20, "Z" * 20),
    )
    for value, expected in valid:
        actual = module.normalize_ticker(value)
        if actual != expected:
            raise AssertionError(f"valid_case_failed: {value!r}")
    invalid = ("", "   ", "a b", "한글", "A_B", "/", "A\nB",
               "X" * 21, 5, None, True)
    for value in invalid:
        try:
            module.normalize_ticker(value)
        except ValueError:
            continue
        except Exception as exc:
            raise AssertionError(f"wrong_error_type: {type(exc).__name__}") from None
        raise AssertionError(f"invalid_case_accepted: {value!r}")
    print("Ticker behavior: all positive and negative cases passed.")


def check_regression_tests():
    # Only reviewed reference files and the generated test file are mounted.
    sys.path.insert(0, str(ROOT))
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"), pattern="test_exaone_sector_pilot_agent.py"
    )
    count = suite.countTestCases()
    if count < 2:
        raise AssertionError(f"insufficient_discovered_tests: {count}")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if result.testsRun < 2 or not result.wasSuccessful() or result.skipped:
        raise AssertionError("generated_regression_tests_failed")

    # A passing suite alone is insufficient: intentionally break the trusted
    # parser inside this isolated container. Both generated tests must catch it.
    import contextlib
    import io
    from unittest.mock import patch
    import exaone_sector_pilot as pilot
    mutated_suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"), pattern="test_exaone_sector_pilot_agent.py"
    )
    with patch.object(pilot, "parse_completion",
                      return_value={"sector": "__BROKEN_PARSER__"}):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            mutated_result = unittest.TextTestRunner(stream=io.StringIO()).run(mutated_suite)
    failures = len(mutated_result.failures) + len(mutated_result.errors)
    if mutated_result.testsRun != count or failures < 2:
        raise AssertionError("generated_tests_do_not_detect_parser_regression")
    print(f"Generated regression tests: {result.testsRun} passed, both detected a parser regression.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("ticker-smoke", "exaone-regression-tests"), required=True)
    args = parser.parse_args()
    if args.task == "ticker-smoke":
        check_ticker()
    else:
        check_regression_tests()


if __name__ == "__main__":
    main()
