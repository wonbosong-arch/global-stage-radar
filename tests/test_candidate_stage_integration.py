import unittest

import pandas as pd

from candidate_stage_integration import extend_universe_with_approved_candidates


def _candidate(symbol="AAPL", **overrides):
    row = {
        "symbol": symbol, "name": symbol + " Inc.", "market": "United States",
        "sector": "Information Technology", "asset_type": "stock",
        "market_benchmark": "SPY", "sector_benchmark": "XLK",
        "exchange": "NAS", "activation_status": "active",
        "identity_status": "verified", "provider_status": "supported",
        "market_cap_status": "verified", "market_cap_usd": 2_000_000_000,
    }
    row.update(overrides)
    return row


def _prices(symbols=("AAPL", "MSFT", "SPY", "XLK"), bars=160):
    dates = pd.bdate_range(end="2026-10-23", periods=bars)
    rows = []
    for symbol in symbols:
        for date in dates:
            rows.append({
                "date": date, "symbol": symbol, "open": 100.0,
                "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1000,
            })
    return pd.DataFrame(rows)


class CandidateStageIntegrationTests(unittest.TestCase):
    def test_one_bad_candidate_does_not_block_another(self):
        base = pd.DataFrame([{
            "symbol": "SPY", "name": "S&P 500 ETF", "market": "United States",
            "sector": "Market", "asset_type": "market_etf", "market_cap_usd": None,
            "market_benchmark": "", "sector_benchmark": "", "exchange": "AMS",
        }])
        candidates = pd.DataFrame([
            _candidate("AAPL"),
            _candidate("MSFT", provider_status="not_checked"),
        ])
        universe, errors = extend_universe_with_approved_candidates(
            base, candidates, _prices(), latest_snapshot_date="2026-10-23"
        )
        self.assertIn("AAPL", universe["symbol"].tolist())
        self.assertNotIn("MSFT", universe["symbol"].tolist())
        self.assertEqual([item["symbol"] for item in errors], ["MSFT"])

    def test_pending_candidates_are_not_examined_or_added(self):
        base = pd.DataFrame([{"symbol": "SPY"}])
        candidates = pd.DataFrame([_candidate("AAPL", activation_status="pending_review")])
        universe, errors = extend_universe_with_approved_candidates(base, candidates, _prices())
        self.assertEqual(universe["symbol"].tolist(), ["SPY"])
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
