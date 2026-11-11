"""Secretless isolated verifier for an untrusted EXAONE TOPIX100 bugfix candidate.

Run this ONLY inside Docker with --network none, read-only mounts, user nobody,
no secrets and resource limits. The module under test is model-modified code.
"""
import argparse
import ast
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from exaone_japan_path_fix_codegen import TASK, TARGET_SHA, validate_candidate


def replace_segment(source, original, replacement):
    count = source.count(original)
    if count != 1:
        raise ValueError("non_unique_original_source_segment")
    return source.replace(original, replacement, 1)


def assemble(original_source, candidate):
    tree = ast.parse(original_source)
    assignment = next(
        (n for n in tree.body if isinstance(n, ast.Assign)
         and any(isinstance(t, ast.Name) and t.id == "REPO"
                 for t in n.targets)), None
    )
    function = next(
        (n for n in tree.body if isinstance(n, ast.FunctionDef)
         and n.name == "safe_outside_repo"), None
    )
    if assignment is None or function is None:
        raise ValueError("missing_patch_target")
    # Apply function first because the assignment lies earlier in the file.
    patched = replace_segment(
        original_source, ast.get_source_segment(original_source, function),
        candidate["replacement_function"],
    )
    patched = replace_segment(
        patched, ast.get_source_segment(original_source, assignment),
        candidate["repo_assignment"],
    )
    ast.parse(patched)
    return patched


def check_boundary(module, root):
    repo_root = root / "global-stage-radar"
    private = root / "outside-private-research"
    private.mkdir(exist_ok=True)

    if module.REPO != repo_root.resolve():
        raise AssertionError("repo_root_not_exact_module_parent")
    target = private / "jpx_private.xlsx"
    result = module.safe_outside_repo(target)
    if result != target.resolve() or not isinstance(result, Path):
        raise AssertionError("external_path_not_allowed_and_resolved")

    for forbidden in (repo_root, repo_root / "data" / "private.xlsx"):
        try:
            module.safe_outside_repo(forbidden)
        except ValueError as ex:
            if "private_jpx_files_must_be_outside_checkout" not in str(ex):
                raise AssertionError("incorrect_forbidden_path_error")
        else:
            raise AssertionError("repository_path_was_accepted")

    symlink = private / "alias-to-checkout"
    symlink.symlink_to(repo_root, target_is_directory=True)
    try:
        module.safe_outside_repo(symlink / "data" / "private.xlsx")
    except ValueError as ex:
        if "private_jpx_files_must_be_outside_checkout" not in str(ex):
            raise AssertionError("incorrect_symlink_error")
    else:
        raise AssertionError("symlink_into_checkout_was_accepted")

    allowed_sibling = repo_root.parent / "another-private-research-folder"
    if module.safe_outside_repo(allowed_sibling) != allowed_sibling.resolve():
        raise AssertionError("sibling_location_not_allowed")
    return 5


def run(candidate_path, source_path, tests_path):
    data = json.loads(candidate_path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("task") != TASK
            or data.get("target_sha") != TARGET_SHA):
        raise ValueError("invalid_exaone_artifact_identity")
    candidate = validate_candidate(json.dumps(data["candidate"], ensure_ascii=False))
    original = source_path.read_text(encoding="utf-8")
    modified = assemble(original, candidate)
    if source_path.name != "japan_topix100_review.py":
        raise ValueError("wrong_validator_filename")

    with tempfile.TemporaryDirectory(prefix="exaone-jp-", dir="/tmp") as d:
        root = Path(d)
        project = root / "global-stage-radar"
        (project / "tests").mkdir(parents=True)
        (project / "japan_topix100_review.py").write_text(modified, encoding="utf-8")
        shutil.copyfile(tests_path, project / "tests" / "test_japan_topix100_review.py")
        sys.path.insert(0, str(project))
        sys.path.insert(0, str(project / "tests"))

        spec = importlib.util.spec_from_file_location(
            "japan_topix100_review", project / "japan_topix100_review.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["japan_topix100_review"] = module
        spec.loader.exec_module(module)

        guards = check_boundary(module, root)
        suite = unittest.defaultTestLoader.discover(
            str(project / "tests"), pattern="test_japan_topix100_review.py"
        )
        # Never log full model-modified source or private input fields.
        capture = io.StringIO()
        result = unittest.TextTestRunner(stream=capture, verbosity=0).run(suite)
        if result.testsRun < 13 or result.failures or result.errors or result.skipped:
            raise AssertionError(
                "target_regressions_failed: tests=" + str(result.testsRun)
                + ", failures=" + str(len(result.failures))
                + ", errors=" + str(len(result.errors))
                + ", skipped=" + str(len(result.skipped))
            )
        print(json.dumps({
            "target_sha": TARGET_SHA,
            "model_generated_code": True,
            "target_unit_tests": result.testsRun,
            "additional_path_guards": guards,
            "result": "candidate_passed_offline_isolated_tests",
            "real_jpx_stock_rows_checked": 0,
            "approved_for_automatic_merge": False,
        }, ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--target", type=Path, required=True)
    ap.add_argument("--tests", type=Path, required=True)
    args = ap.parse_args()
    try:
        return run(args.candidate, args.target, args.tests)
    except (ValueError, AssertionError, OSError, SyntaxError) as ex:
        # Fixed category only: model/source exception strings can contain secrets.
        print("candidate_verification_failed: " + type(ex).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
