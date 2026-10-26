import unittest

import pandas as pd

from candidate_coverage_audit import build_candidate_coverage_report


class CandidateCoverageMappingSuggestionTests(unittest.TestCase):
    def test_report_exposes_suggestions_but_keeps_reviewed_mapping_and_activation_gate_separate(self):
        candidates = pd.DataFrame([{
            "symbol": "NVDA",
            "name": "NVIDIA Corporation",
            "sector": "",
            "market": "United States",
            "exchange": "NAS",
            "country": "Unknown",
            "currency": "USD",
            "instrument_type": "equity_candidate_unverified",
            "activation_status": "pending_review",
            "identity_status": "review_required",
            "depositary_ratio_status": "not_applicable",
            "market_cap_status": "not_verified",
            "provider_status": "not_checked",
            "market_benchmark": "SPY",
            "sector_benchmark": "",
            "proposed_market": "United States (US-listed instrument)",
            "proposed_sector": "Semiconductors",
            "proposed_asset_type": "stock",
            "proposed_market_benchmark": "SPY",
            "proposed_sector_benchmark": "SOXX",
            "mapping_status": "first_pass_review_required",
            "mapping_note": "Curated sector suggestion requires verification.",
            "discovery_industry_code": "IND42",
            "discovery_dr_country_code": "",
        }])
        active = pd.DataFrame([{"symbol": "SPY"}, {"symbol": "SOXX"}])
        prices = pd.DataFrame([
            {"symbol": "NVDA", "date": "2026-10-26"},
            {"symbol": "SPY", "date": "2026-10-26"},
            {"symbol": "SOXX", "date": "2026-10-26"},
        ])

        report = build_candidate_coverage_report(candidates, active, prices)
        row = report.iloc[0]

        self.assertEqual(row["sector"], "")
        self.assertEqual(row["sector_benchmark"], "")
        self.assertEqual(row["proposed_sector"], "Semiconductors")
        self.assertEqual(row["proposed_sector_benchmark"], "SOXX")
        self.assertEqual(row["mapping_status"], "first_pass_review_required")
        self.assertEqual(row["discovery_industry_code"], "IND42")
        self.assertEqual(row["activation_gate_status"], "blocked_pending_manual_review")
        self.assertEqual(row["activation_recommendation"], "keep_pending_review")


if __name__ == "__main__":
    unittest.main()
