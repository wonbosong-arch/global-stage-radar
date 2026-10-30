import ast
from pathlib import Path
import unittest


class CandidateRefreshCountTests(unittest.TestCase):
    def test_counts_keep_provider_errors_distinct_from_deferred_candidates(self):
        path = Path(__file__).resolve().parents[1] / 'app.py'
        node = next(n for n in ast.parse(path.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == 'candidate_refresh_counts')
        namespace = {}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
        counts = namespace['candidate_refresh_counts']
        self.assertEqual(counts({'error_count': 1, 'errors': [{'symbol': '*', 'error': 'setup failed'}]}), (1, 0))
        self.assertEqual(counts({'error_count': 3, 'deferred_symbols': ['A', 'B'],
                                 'errors': [{'symbol': 'A', 'error': 'refresh_deferred_time_budget'},
                                            {'symbol': 'B', 'error': 'refresh_deferred_time_budget'},
                                            {'symbol': 'C', 'error': 'timeout'}]}), (1, 2))
        self.assertEqual(counts({'error_count': 240, 'deferred_symbols': [str(i) for i in range(240)]}), (0, 240))
        self.assertEqual(counts({'status_schema_version': 2, 'error_count': 1,
                                 'failed_symbol_count': 1, 'deferred_symbols': ['A', 'B'],
                                 'errors': [{'symbol': 'C', 'error': 'timeout'}]}), (1, 2))
