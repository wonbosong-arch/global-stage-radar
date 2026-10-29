"""Regression guard: malformed status metadata must not abort cached price loading.

This is a source-level guard because importing app.py starts Streamlit UI.
"""
import ast
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


if __name__ == "__main__":
    unittest.main()
