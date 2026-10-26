import unittest

import pandas as pd

from candidate_coverage_audit import build_candidate_coverage_report


class CandidateCoverageMappingSuggestionTests(unittest.TestCase):
    def test_report_explains_known_recent_listing_history_gaps_with_primary_sources(self):
        listing_specs = [
            ("SPCX", "Space Exploration Technologies Corp.", "2026-06-12", "Industrials", "XLI"),
            ("HONA", "Honeywell Aerospace Inc.", "2026-06-29", "Industrials", "XLI"),
            ("SKHY", "SK hynix ADR", "2026-07-10", "Semiconductors", "SOXX"),
        ]
        candidates = pd.DataFrame([{
            "symbol": symbol, "name": name, "sector": sector,
            "market": "United States", "exchange": "NAS", "country": "Unknown",
            "currency": "USD", "instrument_type": "adr_candidate" if symbol == "SKHY" else "equity_candidate_unverified",
            "activation_status": "pending_review", "identity_status": "review_required",
            "depositary_ratio_status": "verified" if symbol == "SKHY" else "not_applicable",
            "market_cap_status": "not_verified", "provider_status": "not_checked",
            "market_benchmark": "SPY", "sector_benchmark": benchmark,
            "proposed_sector": sector, "proposed_sector_benchmark": benchmark,
            "mapping_status": "first_pass_review_required",
        } for symbol, name, _, sector, benchmark in listing_specs])
        active = pd.DataFrame([{"symbol": "SPY"}, {"symbol": "XLI"}, {"symbol": "SOXX"}])
        price_rows = []
        for symbol, _, start, _, _ in listing_specs:
            dates = pd.date_range(start, "2026-10-23", freq="B")
            price_rows.extend({"symbol": symbol, "date": date.strftime("%Y-%m-%d")} for date in dates)
        benchmark_dates = pd.date_range("2026-06-12", "2026-10-23", freq="B")
        for symbol in ("SPY", "XLI", "SOXX"):
            price_rows.extend({"symbol": symbol, "date": date.strftime("%Y-%m-%d")} for date in benchmark_dates)

        report = build_candidate_coverage_report(candidates, active, pd.DataFrame(price_rows))
        rows = report.set_index("symbol")

        self.assertIn("began Nasdaq trading on 2026-06-12", rows.loc["SPCX", "price_history_exception_note"])
        self.assertEqual(rows.loc["SPCX", "price_history_exception_source_url"],
                         "https://ir.spacex.com/updates/releases-details/2026/Space-Exploration-Technologies-Corp--Announces-Pricing-of-Initial-Public-Offering/default.aspx")
        self.assertIn("2026-06-29", rows.loc["HONA", "price_history_exception_note"])
        self.assertIn("2026-07-10", rows.loc["SKHY", "price_history_exception_note"])
        self.assertTrue((report["candidate_history_150_plus_bars"] == False).all())
        self.assertTrue((report["activation_recommendation"] == "keep_pending_review").all())

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
