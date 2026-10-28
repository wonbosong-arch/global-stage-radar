"""Execute the app's actual new-entry calculation without starting Streamlit."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

import numpy as np
import pandas as pd

from stage_engine import classify_stage


APP = Path(__file__).resolve().parents[1] / "app.py"


def calculate_entry(dates, *, asset_type="stock", previous_close=90.0,
                    previous_market_rs=5.0, previous_sector_rs=4.0,
                    previous_ma=100.0, current_label="Stage 2 후보"):
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    loop = next(node for node in tree.body if isinstance(node, ast.For)
                and any(isinstance(child, ast.Assign)
                        and any(isinstance(target, ast.Name) and target.id == "stage2_new_entry"
                                for target in child.targets) for child in node.body))
    start = next(i for i, node in enumerate(loop.body)
                 if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "previous_stage_label"
                         for target in node.targets))
    end = next(i for i, node in enumerate(loop.body)
               if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == "stage2_new_entry"
                       for target in node.targets))
    rows = [dict(date=pd.Timestamp(date), close=previous_close, ma30=previous_ma,
                 slope4_pct=1.0, rs_market_26w_pct=previous_market_rs,
                 rs_sector_26w_pct=previous_sector_rs) for date in dates]
    namespace = dict(w=pd.DataFrame(rows), item=SimpleNamespace(asset_type=asset_type),
                     label=current_label, pd=pd, np=np, classify_stage=classify_stage)
    exec(compile(ast.Module(body=loop.body[start:end + 1], type_ignores=[]),
                 str(APP), "exec"), namespace)
    return namespace["stage2_new_entry"], namespace["previous_week_comparable"]


class Stage2NewEntryRegressionTests(unittest.TestCase):
    def test_missing_previous_week_must_not_be_called_new_entry(self):
        self.assertEqual(calculate_entry(["2026-10-09", "2026-10-23"]), (False, False))

    def test_consecutive_week_transition_is_new_entry(self):
        self.assertEqual(calculate_entry(["2026-10-16", "2026-10-23"]), (True, True))

    def test_existing_stage2_is_not_new_entry(self):
        self.assertEqual(calculate_entry(["2026-10-16", "2026-10-23"],
                                        previous_close=110), (False, True))

    def test_missing_prior_indicators_or_stock_benchmarks_are_not_comparable(self):
        for kwargs in ({"previous_ma": np.nan}, {"previous_market_rs": np.nan},
                       {"previous_sector_rs": np.nan}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(calculate_entry(["2026-10-16", "2026-10-23"], **kwargs),
                                 (False, False))

    def test_one_week_is_not_comparable(self):
        self.assertEqual(calculate_entry(["2026-10-23"]), (False, False))

    def test_guarded_current_label_cannot_be_new_entry(self):
        self.assertEqual(calculate_entry(["2026-10-16", "2026-10-23"],
                                        current_label="판정 보류"), (False, True))

    def test_market_proxy_does_not_require_self_relative_strength(self):
        self.assertEqual(calculate_entry(["2026-10-16", "2026-10-23"],
                                        asset_type="market_etf", previous_market_rs=np.nan,
                                        previous_sector_rs=np.nan), (True, True))

    def test_crypto_sunday_weeks_keep_existing_no_benchmark_behavior(self):
        self.assertEqual(calculate_entry(["2026-10-18", "2026-10-25"],
                                        asset_type="crypto_asset", previous_market_rs=np.nan,
                                        previous_sector_rs=np.nan), (True, True))
        self.assertEqual(calculate_entry(["2026-10-11", "2026-10-25"],
                                        asset_type="crypto_asset"), (False, False))
