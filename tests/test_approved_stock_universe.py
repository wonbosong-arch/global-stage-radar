import unittest

import pandas as pd

from approved_stock_universe import approved_candidates_for_stage


def _candidate(**overrides):
    row = {
        "symbol": "AAPL", "name": "Apple Inc.", "market": "United States",
        "sector": "Information Technology", "asset_type": "stock",
        "market_benchmark": "SPY", "sector_benchmark": "XLK",
        "exchange": "NAS", "activation_status": "pending_review",
        "market_cap_usd": 3_000_000_000_000,
        "market_cap_usd_b_secondary": 3_100_000_000_000,
    }
    row.update(overrides)
    return row


class ApprovedStockUniverseTests(unittest.TestCase):
    def test_pending_candidate_never_enters_stage_universe(self):
        result = approved_candidates_for_stage(pd.DataFrame([_candidate()]))
        self.assertTrue(result.empty)

    def test_only_explicitly_active_candidate_enters_stage_universe(self):
        result = approved_candidates_for_stage(pd.DataFrame([
            _candidate(),
            _candidate(symbol="MSFT", name="Microsoft", activation_status="active"),
        ]))
        self.assertEqual(result["symbol"].tolist(), ["MSFT"])
        self.assertEqual(result.loc[0, "market_cap_usd"], 3_000_000_000_000)

    def test_secondary_yahoo_cap_is_not_used_as_verified_cap(self):
        row = _candidate(activation_status="active")
        row.pop("market_cap_usd")
        result = approved_candidates_for_stage(pd.DataFrame([row]))
        self.assertTrue(pd.isna(result.loc[0, "market_cap_usd"]))

    def test_active_stock_requires_sector_benchmark(self):
        with self.assertRaisesRegex(ValueError, "Stage mapping"):
            approved_candidates_for_stage(pd.DataFrame([
                _candidate(activation_status="active", sector_benchmark="")
            ]))

    def test_duplicate_active_symbols_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            approved_candidates_for_stage(pd.DataFrame([
                _candidate(activation_status="active"),
                _candidate(activation_status="active"),
            ]))


if __name__ == "__main__":
    unittest.main()
