"""Regression guard: malformed status metadata must not abort cached price loading.

This is a source-level guard because importing app.py starts Streamlit UI.
"""
import ast
import json
import tempfile
from types import SimpleNamespace
from pathlib import Path
import unittest


APP = Path(__file__).resolve().parents[1] / "app.py"


class SnapshotStatusIsolationTest(unittest.TestCase):
    def test_status_parse_errors_are_handled_inside_snapshot_loader(self):
        tree = ast.parse(APP.read_text(encoding="utf-8"))
        candidates = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            source = ast.get_source_segment(APP.read_text(encoding="utf-8"), node) or ""
            if 'json.load(status_file)' not in source:
                continue
            if 'snapshot_status = {}' not in source:
                continue
            handled = set()
            for handler in node.handlers:
                typ = handler.type
                if isinstance(typ, ast.Tuple):
                    handled.update(item.id for item in typ.elts if isinstance(item, ast.Name))
                elif isinstance(typ, ast.Name):
                    handled.add(typ.id)
            candidates.append(handled)
        self.assertTrue(
            any({"OSError", "ValueError", "TypeError"} <= handled for handled in candidates),
            "Status JSON must be parsed in a local try/except so valid prices remain loaded",
        )


    def test_corrupt_status_json_falls_back_without_raising(self):
        # Execute the exact local status-loader try/except extracted from app.py.
        source = APP.read_text(encoding="utf-8")
        tree = ast.parse(source)
        candidates = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Try)
            and any(
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and isinstance(child.func.value, ast.Name)
                and child.func.value.id == "json"
                and child.func.attr == "load"
                for statement in node.body for child in ast.walk(statement)
            )
            and any(
                isinstance(child, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "snapshot_status" for target in child.targets)
                for statement in node.body for child in ast.walk(statement)
            )
        ]
        self.assertEqual(1, len(candidates))
        loader = ast.fix_missing_locations(ast.Module(body=[candidates[0]], type_ignores=[]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "daily_prices_status.json"
            path.write_text("{not valid json", encoding="utf-8")
            warnings = []
            namespace = {
                "snapshot_status_path": str(path),
                "json": json,
                "st": SimpleNamespace(warning=warnings.append),
            }
            exec(compile(loader, str(APP), "exec"), namespace)
        self.assertEqual({}, namespace["snapshot_status"])
        self.assertEqual(1, len(warnings))
        self.assertIn("가격 데이터는 유지", warnings[0])

    def test_valid_status_json_is_preserved(self):
        source = APP.read_text(encoding="utf-8")
        tree = ast.parse(source)
        candidates = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Try)
            and any(
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and isinstance(child.func.value, ast.Name)
                and child.func.value.id == "json"
                and child.func.attr == "load"
                for statement in node.body for child in ast.walk(statement)
            )
            and any(
                isinstance(child, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "snapshot_status" for target in child.targets)
                for statement in node.body for child in ast.walk(statement)
            )
        ]
        self.assertEqual(1, len(candidates))
        loader = ast.fix_missing_locations(ast.Module(body=[candidates[0]], type_ignores=[]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "daily_prices_status.json"
            path.write_text('{"symbols_with_data": 92}', encoding="utf-8")
            warnings = []
            namespace = {
                "snapshot_status_path": str(path),
                "json": json,
                "st": SimpleNamespace(warning=warnings.append),
            }
            exec(compile(loader, str(APP), "exec"), namespace)
        self.assertEqual(92, namespace["snapshot_status"]["symbols_with_data"])
        self.assertEqual([], warnings)


if __name__ == "__main__":
    unittest.main()
