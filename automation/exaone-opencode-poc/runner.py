"""Offline preparation and verification for a strictly review-only EXAONE coding experiment.

Never imports or executes generated code. Never reads API secrets or writes repository files.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "automation/exaone-opencode-poc/opencode.json"
TASKS = {
    "ticker-smoke": {
        "inputs": [],
        "output": "ticker_utils.py",
        "prompt": (
            "In this scratch workspace create ONLY ticker_utils.py. Implement "
            "normalize_ticker(value) that returns stripped uppercase ASCII tickers "
            "containing only A-Z 0-9 . and -, with maximum length 20. Raise "
            "ValueError for invalid input, including nonstrings. No other files. "
            "Do not use shell or external tools."
        ),
    },
    "exaone-regression-tests": {
        "inputs": [
            "exaone_sector_pilot.py",
            "stock_mapping.py",
        ],
        "output": "tests/test_exaone_sector_pilot_agent.py",
        "prompt": (
            "Create ONLY tests/test_exaone_sector_pilot_agent.py (under 70 lines). "
            "Use stdlib unittest and json; import exaone_sector_pilot as pilot. "
            "Focus ONLY on pilot.parse_completion(raw_bytes, symbol). "
            "Add a unittest.TestCase with exactly two test_ methods: "
            "(1) a valid choices[0] assistant envelope with finish_reason=stop and "
            "message.content containing JSON with the exact five classification "
            "fields symbol, sector, industry, confidence, evidence, matching AAPL, "
            "sector Information Technology, Korean industry, confidence 0.9; "
            "assert the parsed sector is Information Technology; "
            "(2) the same envelope with finish_reason=length must raise pilot.PilotError. "
            "Create the raw bytes with json.dumps(..., ensure_ascii=False).encode('utf-8'). "
            "You may read exaone_sector_pilot.py to confirm the schema; avoid "
            "reading other files. Do not execute tests or use shell tools; do not "
            "change any other file."
        ),
    },
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def within(base, name):
    path = base / name
    if path.is_symlink() or not path.resolve().is_relative_to(base.resolve()):
        raise ValueError("unsafe_workspace_path")
    return path


def validate_config(config):
    assert config["model"] == "exaone/k-exaone_v2.5"
    provider = config["providers"]["exaone"]
    assert provider["package"] == "@opencode/ai/providers/openai-compatible"
    assert provider["settings"] == {
        "baseURL": "https://api.exaone.ai/v1",
        "apiKey": "{env:EXAONE_API_KEY}",
    }
    assert config["permission"] == {"*": "deny", "read": "allow", "edit": "allow"}


def prepare(task, workspace):
    if task not in TASKS:
        raise ValueError("unknown_task")
    workspace.mkdir(parents=True, exist_ok=True)
    if any(workspace.iterdir()):
        raise ValueError("workspace_not_empty")
    data = TASKS[task]
    shutil.copy2(CONFIG, workspace / "opencode.json")
    manifest = {"task": task, "inputs": {}, "output": data["output"]}
    for name in data["inputs"]:
        source = within(ROOT, name)
        destination = within(workspace, name)
        if not source.is_file():
            raise ValueError("missing_input")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        manifest["inputs"][name] = digest(destination)
    (workspace / "task.txt").write_text(data["prompt"] + "\n", encoding="utf-8")
    (workspace / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    validate_config(json.loads((workspace / "opencode.json").read_text(encoding="utf-8")))


def verify(workspace):
    manifest = json.loads((workspace / "manifest.json").read_text(encoding="utf-8"))
    task = manifest["task"]
    if task not in TASKS or manifest["output"] != TASKS[task]["output"]:
        raise ValueError("unexpected_manifest")
    expected_manifest = {
        "task": task,
        "inputs": {name: digest(within(ROOT, name)) for name in TASKS[task]["inputs"]},
        "output": TASKS[task]["output"],
    }
    if manifest != expected_manifest:
        raise ValueError("manifest_modified")
    if (workspace / "task.txt").read_text(encoding="utf-8") != TASKS[task]["prompt"] + "\n":
        raise ValueError("task_instruction_modified")
    allowed = {"opencode.json", "manifest.json", "task.txt", manifest["output"]}
    allowed.update(TASKS[task]["inputs"])
    observed = set()
    for path in workspace.rglob("*"):
        if path.is_symlink():
            raise ValueError("symbolic_link_forbidden")
        if path.is_file():
            observed.add(path.relative_to(workspace).as_posix())
    if observed != allowed:
        raise ValueError("unexpected_file_changes")
    for name, expected in manifest["inputs"].items():
        if digest(within(workspace, name)) != expected:
            raise ValueError("reference_file_modified")
    if digest(workspace / "opencode.json") != digest(CONFIG):
        raise ValueError("config_modified")
    output = within(workspace, manifest["output"])
    if not 0 < output.stat().st_size <= 12000:
        raise ValueError("invalid_output_size")
    source = output.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=output.name)
    # Never execute or import model-generated code inside a runner carrying secrets.
    safe_imports = {"unittest", "unittest.mock", "json", "exaone_sector_pilot", "re", "typing"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name not in safe_imports for alias in node.names):
                raise ValueError("unexpected_generated_import")
        elif isinstance(node, ast.ImportFrom):
            if node.module not in safe_imports or node.level:
                raise ValueError("unexpected_generated_import")
    if task == "ticker-smoke":
        if not any(isinstance(n, ast.FunctionDef) and n.name == "normalize_ticker" for n in tree.body):
            raise ValueError("missing_normalize_ticker")
    else:
        count = sum(
            isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name.startswith("test_")
            for n in ast.walk(tree)
        )
        if count < 2:
            raise ValueError("missing_regression_tests")
    print("Review-only artifact structure verified; generated code was not executed.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("check", "prepare", "verify"))
    parser.add_argument("--task", choices=tuple(TASKS), default="ticker-smoke")
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()
    validate_config(json.loads(CONFIG.read_text(encoding="utf-8")))
    if args.command != "check" and args.workspace is None:
        parser.error("--workspace is required")
    if args.command == "prepare":
        prepare(args.task, args.workspace)
    elif args.command == "verify":
        verify(args.workspace)
    else:
        print("Offline config and task allowlist checks passed; no API calls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
