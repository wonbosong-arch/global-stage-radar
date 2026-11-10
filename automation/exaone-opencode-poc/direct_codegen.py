"""Generate review-only EXAONE parser regression tests via ONE direct API request.

No agent, no shell tools, no model-created paths, no retries, no repo writes.
The generated Python is NEVER executed in this secret-bearing process.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from exaone_sector_pilot import ExaoneClient, PilotError, MODEL
from runner import TASKS, prepare, verify

TASK = "exaone-regression-tests"
FILE = TASKS[TASK]["output"]
SOURCE_LIMIT = 12000


class CodegenError(Exception):
    pass


def parser_source():
    """Send a minimal trusted source excerpt, not the entire repository."""
    text = (ROOT / "exaone_sector_pilot.py").read_text(encoding="utf-8")
    module = ast.parse(text)
    function = next(
        node for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "parse_completion"
    )
    return ast.get_source_segment(text, function)


def payload_bytes():
    instruction = (
        "You are writing REVIEW-ONLY regression tests for an existing Python project. "
        "Return ONLY valid Python source code, without markdown or explanation. "
        "Create exactly one Python module with at most 70 lines. "
        "Use only import unittest, import json, and import exaone_sector_pilot as pilot. "
        "Implement class ParserRegressionTests(unittest.TestCase) with exactly two methods: "
        "test_valid_completion and test_truncated_completion. "
        "Both call pilot.parse_completion(raw, 'AAPL') using a synthetic JSON chat "
        "completion envelope with one choices item, assistant role, and message.content "
        "containing JSON with the five exact keys: symbol, sector, industry, confidence, evidence. "
        "For the valid case use symbol AAPL, sector Information Technology, "
        "industry '소비자 전자기기', confidence 0.9, evidence 'Consumer electronics', "
        "finish_reason 'stop', assert sector equals Information Technology. "
        "For the truncated case use the same envelope but finish_reason 'length', "
        "and assert pilot.PilotError is raised. Encode the envelope with "
        "json.dumps(..., ensure_ascii=False).encode('utf-8'). "
        "Do not use stubs, skip, mock, network, file I/O, shell commands, or any other imports. "
        "Do not embed any secrets. Do not modify existing source files."
    )
    return json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": instruction},
            {"role": "user", "content": "Existing function to test (reference only):\n" + parser_source()},
        ],
        "reasoning_effort": "low",
        "max_tokens": 4096,
        "stream": False,
    }, ensure_ascii=False).encode("utf-8")


def extract_source(raw):
    try:
        envelope = json.loads(raw.decode("utf-8"))
        choices = envelope["choices"]
        if not isinstance(choices, list) or len(choices) != 1:
            raise ValueError
        item = choices[0]
        message = item["message"]
        if (item["finish_reason"] != "stop"
                or message["role"] != "assistant"
                or message.get("refusal") or message.get("tool_calls")):
            raise ValueError
        source = message["content"]
        if not isinstance(source, str):
            raise ValueError
        source = source.strip()
        fenced = re.fullmatch(r"```(?:python)?\s*\n(.*?)\n```", source, re.DOTALL)
        if fenced:
            source = fenced.group(1).strip()
        data = source.encode("utf-8")
        if not 0 < len(data) <= SOURCE_LIMIT or len(source.splitlines()) > 70:
            raise ValueError
        tree = ast.parse(source)
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == "ParserRegressionTests"]
        if len(classes) != 1:
            raise ValueError
        methods = {node.name: node for node in classes[0].body
                   if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}
        if set(methods) != {"test_valid_completion", "test_truncated_completion"}:
            raise ValueError
        def calls(method, object_name, name):
            return any(
                isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == object_name and node.func.attr == name
                for node in ast.walk(method)
            )
        for method in methods.values():
            if not calls(method, "pilot", "parse_completion"):
                raise ValueError
        if not calls(methods["test_valid_completion"], "self", "assertEqual"):
            raise ValueError
        if not calls(methods["test_truncated_completion"], "self", "assertRaises"):
            raise ValueError
        return source + "\n"
    except (UnicodeError, KeyError, TypeError, ValueError, RecursionError, SyntaxError):
        raise CodegenError("invalid_generated_source") from None


def generate(workspace):
    """One HTTPS POST; the only imported transport is already pilot-tested."""
    prepare(TASK, workspace)
    client = ExaoneClient(max_attempts=1)
    try:
        raw, error, _ = client._attempt(payload_bytes(), 0)
        if error is not None or raw is None:
            raise CodegenError("exaone_request_failed")
        source = extract_source(raw)
        if client._key in source:
            raise CodegenError("sensitive_generated_source")
        output = workspace / FILE
        output.write_text(source, encoding="utf-8")
        verify(workspace)
        return output
    except PilotError:
        raise CodegenError("exaone_response_failed") from None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        payload = json.loads(payload_bytes())
        if (payload["model"] != MODEL or len(payload["messages"]) != 2
                or not payload["messages"][1]["content"].endswith("return result")):
            raise CodegenError("invalid_prompt")
        if args.check_only:
            print("Direct EXAONE prompt validated offline; no API request.")
            return 0
        if args.workspace is None or args.destination is None:
            parser.error("--workspace and --destination are required for a live run")
        output = generate(args.workspace)
        args.destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output, args.destination / output.name)
        print("One direct request produced a structurally valid, unexecuted review candidate.")
        return 0
    except (CodegenError, PilotError) as error:
        # Never print model completions, request bodies, tokens, or provider diagnostics.
        print("direct_codegen_failed: " + (
            str(error) if isinstance(error, CodegenError) else "invalid_api_key"
        ), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
