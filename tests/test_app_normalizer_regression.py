"""Regression tests for the duplicate candidate normalizer embedded in app.py.

Extract only the function AST so importing Streamlit UI code is not required.
"""
import ast
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from kis_universe import normalize_market_cap_candidates as canonical_normalizer


def load_app_normalizer():
    source = Path(__file__).resolve().parents[1].joinpath("app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    node = next(
        item for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == "normalize_market_cap_candidates"
    )
    namespace = {"pd": pd, "np": np}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "app.py", "exec"), namespace)
    return namespace[node.name]


class AppNormalizerRegressionTests(unittest.TestCase):
    def test_app_and_canonical_normalizers_agree_on_security_eligibility(self):
        app_normalizer = load_app_normalizer()
        raw = pd.DataFrame([
            {"listing_exchange": "NAS", "symb": "AAPL", "ename": "APPLE INC",
             "tomv": "2500000000000", "last": "250", "shar": "10000000000",
             "master_security_type": "2"},
            {"listing_exchange": "NAS", "symb": "UNK", "ename": "UNKNOWN INC",
             "tomv": "10000000000", "last": "100", "shar": "100000000"},
            {"listing_exchange": "NAS", "symb": "ADR1", "ename": "EXAMPLE DEPOSITARY RECEIPT",
             "tomv": "10000000000", "last": "100", "shar": "100000000",
             "master_security_type": "2"},
            {"listing_exchange": "AMS", "symb": "ETF1", "ename": "EXAMPLE ETF",
             "tomv": "10000000000", "last": "100", "shar": "100000000",
             "master_security_type": "3"},
            {"listing_exchange": "KRX", "mksc_shrn_iscd": "005930", "hts_kor_isnm": "삼성전자",
             "stck_avls": "4130000", "stck_prpr": "70000", "lstn_stcn": "5900000000",
             "master_security_type": "2"},
        ])
        app_result = app_normalizer(raw, usdkrw=1400)
        canonical_result = canonical_normalizer(raw, usdkrw=1400)
        columns = [
            "symbol", "master_instrument_type", "master_security_type_code",
            "is_adr_candidate", "cap_threshold_pass", "review_status",
        ]
        for column in columns:
            self.assertEqual(
                app_result[column].astype(str).tolist(),
                canonical_result[column].astype(str).tolist(),
                msg=f"Normalizer mismatch in {column}",
            )

    def test_unknown_security_type_never_passes_market_cap_threshold_in_app(self):
        result = load_app_normalizer()(pd.DataFrame([{
            "listing_exchange": "NAS", "symb": "UNK", "ename": "UNKNOWN INC",
            "tomv": "10000000000", "last": "100", "shar": "100000000",
        }]))
        self.assertTrue(pd.isna(result.loc[0, "cap_threshold_pass"]))
        self.assertEqual(result.loc[0, "review_status"], "manual_review")


if __name__ == "__main__":
    unittest.main()
