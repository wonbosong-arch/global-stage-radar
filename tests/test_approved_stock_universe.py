import unittest

import pandas as pd

from approved_stock_universe import approved_candidates_for_stage


def _candidate(**overrides):
    row = {
        "symbol": "AAPL", "name": "Apple Inc.", "market": "United States",
        "sector": "Information Technology", "asset_type": "stock",
        "market_benchmark": "SPY", "sector_benchmark": "XLK",
        "exchange": "NAS", "activation_status": "pending_review",
        "identity_status": "verified", "provider_status": "supported",
        "market_cap_status": "verified", "market_cap_usd": 3_000_000_000_000,
        "market_cap_usd_b_secondary": 3_100_000_000_000,
    }
    row.update(overrides)
    return row


def _prices(symbols=("AAPL", "SPY", "XLK"), bars=160):
    dates = pd.bdate_range(end="2026-10-23", periods=bars)
    rows = []
    for symbol in symbols:
        for date in dates:
            rows.append({
                "date": date, "symbol": symbol, "open": 100.0,
                "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1000,
            })
    return pd.DataFrame(rows)


class ApprovedStockUniverseTests(unittest.TestCase):
    def test_pending_candidate_never_enters_stage_universe(self):
        result = approved_candidates_for_stage(pd.DataFrame([_candidate()]), _prices())
        self.assertTrue(result.empty)

    def test_only_explicitly_active_candidate_passing_gates_enters(self):
        result = approved_candidates_for_stage(
            pd.DataFrame([_candidate(activation_status="active")]), _prices()
        )
        self.assertEqual(result["symbol"].tolist(), ["AAPL"])
        self.assertEqual(result.loc[0, "market_cap_usd"], 3_000_000_000_000)

    def test_secondary_yahoo_cap_can_pass_minimum_size_screen_without_verification(self):
        row = _candidate(
            activation_status="active", market_cap_status="not_verified",
            market_cap_usd_b_secondary=3100,
        )
        row.pop("market_cap_usd")
        result = approved_candidates_for_stage(pd.DataFrame([row]), _prices())
        self.assertEqual(result["symbol"].tolist(), ["AAPL"])
        self.assertEqual(result.loc[0, "market_cap_usd"], 3_100_000_000_000)

    def test_unverified_identity_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "identity/provider"):
            approved_candidates_for_stage(
                pd.DataFrame([_candidate(activation_status="active", identity_status="review_required")]),
                _prices(),
            )

    def test_provider_not_checked_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "identity/provider"):
            approved_candidates_for_stage(
                pd.DataFrame([_candidate(activation_status="active", provider_status="not_checked")]),
                _prices(),
            )

    def test_active_stock_requires_sector_benchmark(self):
        with self.assertRaisesRegex(ValueError, "identity/provider"):
            approved_candidates_for_stage(
                pd.DataFrame([_candidate(activation_status="active", sector_benchmark="")]),
                _prices(),
            )

    def test_missing_benchmark_history_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "Insufficient price history for XLK"):
            approved_candidates_for_stage(
                pd.DataFrame([_candidate(activation_status="active")]),
                _prices(symbols=("AAPL", "SPY")),
            )

    def test_duplicate_active_symbols_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            approved_candidates_for_stage(
                pd.DataFrame([
                    _candidate(activation_status="active"),
                    _candidate(activation_status="active"),
                ]),
                _prices(),
            )

    def test_secondary_market_cap_below_one_billion_fails_minimum_size_screen(self):
        row = _candidate(
            activation_status="active", market_cap_status="not_verified",
            market_cap_usd_b_secondary=0.5,
        )
        row.pop("market_cap_usd")
        with self.assertRaisesRegex(ValueError, "cap/mapping gates"):
            approved_candidates_for_stage(pd.DataFrame([row]), _prices())

    def test_missing_secondary_market_cap_does_not_auto_exclude_by_size(self):
        row = _candidate(activation_status="active", market_cap_status="not_verified")
        row.pop("market_cap_usd")
        row.pop("market_cap_usd_b_secondary")
        with self.assertRaisesRegex(ValueError, "cap/mapping gates"):
            approved_candidates_for_stage(pd.DataFrame([row]), _prices())

    def test_discovery_usd_cap_is_a_last_resort_size_screen_estimate(self):
        row = _candidate(activation_status="active", market_cap_status="not_verified")
        row.pop("market_cap_usd")
        row.pop("market_cap_usd_b_secondary")
        row["discovery_market_cap_usd"] = 2_000_000_000
        result = approved_candidates_for_stage(pd.DataFrame([row]), _prices())
        self.assertEqual(result["symbol"].tolist(), ["AAPL"])
        self.assertEqual(result.loc[0, "market_cap_usd"], 2_000_000_000)


if __name__ == "__main__":
    unittest.main()
