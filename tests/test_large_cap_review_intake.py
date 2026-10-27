import unittest
import pandas as pd

from intake_large_cap_review_candidates import build_review_only_candidates


CANDIDATE_COLUMNS = [
    "symbol", "name", "market", "sector", "asset_type", "market_benchmark",
    "sector_benchmark", "exchange", "country", "currency", "instrument_type",
    "identity_status", "market_cap_status", "provider_status", "activation_status",
    "review_note", "identity_evidence_url", "identity_reviewed_at",
    "market_cap_source_url", "market_cap_asof", "depositary_ratio_status",
    "market_cap_usd_b_secondary", "discovery_market_cap_usd", "discovery_market_cap_native",
    "discovery_market_cap_currency", "discovery_source", "discovered_at",
    "discovery_cap_threshold_pass", "discovery_security_type", "discovery_review_reason",
    "discovery_industry_code", "discovery_dr_country_code", "proposed_market",
    "proposed_sector", "proposed_asset_type", "proposed_market_benchmark",
    "proposed_sector_benchmark", "mapping_status", "mapping_note",
]


class LargeCapReviewIntakeTests(unittest.TestCase):
    def test_adds_only_bounded_ordinary_equity_rows_and_never_activates(self):
        candidates = pd.DataFrame([{"symbol": "EXISTING"}], columns=["symbol"])
        active = pd.DataFrame([{"symbol": "ACTIVE"}])
        queue = pd.DataFrame([
            {"symbol": "AAA", "name": "Alpha Corp", "exchange": "NAS",
             "instrument_type": "equity_candidate_unverified", "identity_status": "review_required",
             "market_cap_status": "not_verified", "activation_status": "pending_review",
             "discovery_market_cap_usd_b_secondary": 10.0, "market_cap_source_url": "https://finance.yahoo.com/quote/AAA/"},
            {"symbol": "BBB", "name": "Possible ADR SPON ADS", "exchange": "NYS",
             "instrument_type": "possible_adr_or_equity_review", "identity_status": "possible_adr_review_required",
             "market_cap_status": "not_verified", "activation_status": "pending_review",
             "discovery_market_cap_usd_b_secondary": 100.0},
            {"symbol": "EXISTING", "name": "Existing Corp", "exchange": "NAS",
             "instrument_type": "equity_candidate_unverified", "identity_status": "review_required",
             "market_cap_status": "not_verified", "activation_status": "pending_review",
             "discovery_market_cap_usd_b_secondary": 50.0},
            {"symbol": "ACTIVE", "name": "Active Corp", "exchange": "NAS",
             "instrument_type": "equity_candidate_unverified", "identity_status": "review_required",
             "market_cap_status": "not_verified", "activation_status": "pending_review",
             "discovery_market_cap_usd_b_secondary": 40.0},
            {"symbol": "ETF1", "name": "ETF", "exchange": "NAS",
             "instrument_type": "etf_candidate", "identity_status": "review_required",
             "market_cap_status": "not_verified", "activation_status": "pending_review",
             "discovery_market_cap_usd_b_secondary": 30.0},
        ])
        result, status = build_review_only_candidates(
            candidates, active, queue, discovered_at="2026-10-27", max_add=1, max_total=10
        )
        self.assertEqual(result["symbol"].tolist(), ["EXISTING", "AAA"])
        row = result[result["symbol"] == "AAA"].iloc[0]
        self.assertEqual(row["activation_status"], "pending_review")
        self.assertEqual(row["identity_status"], "review_required")
        self.assertEqual(row["market_cap_status"], "not_verified")
        self.assertEqual(row["market_cap_usd_b_secondary"], "10.0")
        self.assertEqual(row["discovery_cap_threshold_pass"], "secondary_estimate_ge_1b_review_only")
        self.assertEqual(status["large_cap_review_candidates_added"], 1)

    def test_respects_total_candidate_limit(self):
        candidates = pd.DataFrame([{"symbol": f"S{i}"} for i in range(5)])
        queue = pd.DataFrame([{
            "symbol": "NEW", "name": "New Corp", "exchange": "NAS",
            "instrument_type": "equity_candidate_unverified", "identity_status": "review_required",
            "market_cap_status": "not_verified", "activation_status": "pending_review",
            "discovery_market_cap_usd_b_secondary": 2.0,
        }])
        result, status = build_review_only_candidates(
            candidates, pd.DataFrame(columns=["symbol"]), queue,
            discovered_at="2026-10-27", max_add=25, max_total=5
        )
        self.assertEqual(len(result), 5)
        self.assertEqual(status["large_cap_review_candidates_added"], 0)


if __name__ == "__main__":
    unittest.main()
