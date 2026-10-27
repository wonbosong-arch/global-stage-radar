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
        self.assertEqual(row["suggested_sector_benchmark"], "SOXX")
        self.assertTrue(row["suggested_sector_benchmark_active"])
        self.assertEqual(row["suggested_sector_benchmark_price_rows"], 1)
        self.assertEqual(
            row["suggested_sector_benchmark_coverage_status"],
            "usable_for_provisional_analysis_not_approval",
        )
        self.assertEqual(row["mapping_status"], "first_pass_review_required")
        self.assertEqual(row["discovery_industry_code"], "IND42")
        self.assertEqual(row["activation_gate_status"], "blocked_pending_manual_review")
        self.assertEqual(row["activation_recommendation"], "keep_pending_review")


    def test_separate_korean_etf_snapshot_can_show_provisional_coverage_without_activation(self):
        candidates = pd.DataFrame([{
            "symbol": "005380",
            "name": "Hyundai Motor",
            "sector": "Consumer Discretionary",
            "market": "South Korea",
            "exchange": "KRX",
            "country": "South Korea",
            "currency": "KRW",
            "instrument_type": "equity_candidate_unverified",
            "activation_status": "pending_review",
            "identity_status": "review_required",
            "depositary_ratio_status": "not_applicable",
            "market_cap_status": "not_verified",
            "provider_status": "not_checked",
            "market_benchmark": "069500",
            "sector_benchmark": "",
            "proposed_sector": "Consumer Discretionary",
            "proposed_sector_benchmark": "091180",
            "mapping_status": "first_pass_review_required",
            "mapping_note": "Suggestion only.",
        }])
        # The ETF is intentionally not in the active universe; its rows come from
        # the separate review-only benchmark snapshot.
        active = pd.DataFrame([{"symbol": "069500"}])
        dates = pd.date_range("2026-10-01", "2026-10-26", freq="B")
        prices = pd.DataFrame(
            [{"symbol": symbol, "date": date.strftime("%Y-%m-%d")}
             for symbol in ("005380", "069500", "091180") for date in dates]
        )
        report = build_candidate_coverage_report(candidates, active, prices)
        row = report.iloc[0]
        self.assertFalse(row["suggested_sector_benchmark_active"])
        self.assertGreater(row["suggested_sector_benchmark_price_rows"], 0)
        self.assertEqual(
            row["suggested_sector_benchmark_coverage_status"],
            "usable_for_provisional_analysis_not_approval",
        )
        self.assertEqual(row["sector_benchmark"], "")
        self.assertEqual(row["activation_recommendation"], "keep_pending_review")

    def test_korean_sector_etf_suggestions_remain_proposals_until_coverage_is_verified(self):
        candidates = pd.DataFrame([{
            "symbol": "005380",
            "name": "Hyundai Motor",
            "sector": "Consumer Discretionary",
            "market": "South Korea",
            "exchange": "KRX",
            "country": "South Korea",
            "currency": "KRW",
            "instrument_type": "equity_candidate_unverified",
            "activation_status": "pending_review",
            "identity_status": "review_required",
            "depositary_ratio_status": "not_applicable",
            "market_cap_status": "not_verified",
            "provider_status": "not_checked",
            "market_benchmark": "069500",
            "sector_benchmark": "",
            "proposed_sector": "Consumer Discretionary",
            "proposed_sector_benchmark": "091180",
            "mapping_status": "first_pass_review_required",
            "mapping_note": "Korean-listed sector ETF suggestion only; KIS coverage unverified.",
        }])
        active = pd.DataFrame([{"symbol": "069500"}])
        prices = pd.DataFrame([
            {"symbol": "005380", "date": "2026-10-26"},
            {"symbol": "069500", "date": "2026-10-26"},
        ])
        report = build_candidate_coverage_report(candidates, active, prices)
        row = report.iloc[0]
        self.assertEqual(row["proposed_sector_benchmark"], "091180")
        self.assertEqual(row["sector_benchmark"], "")
        self.assertEqual(row["suggested_sector_benchmark_coverage_status"], "benchmark_snapshot_missing")
        self.assertEqual(row["activation_recommendation"], "keep_pending_review")

    def test_missing_suggestion_is_distinct_from_missing_benchmark_data(self):
        candidates = pd.DataFrame([{
            "symbol": "000270",
            "name": "Kia",
            "sector": "",
            "market": "South Korea",
            "exchange": "KRX",
            "country": "South Korea",
            "currency": "KRW",
            "instrument_type": "equity_candidate_unverified",
            "identity_status": "review_required",
            "market_cap_status": "not_verified",
            "provider_status": "not_checked",
            "market_benchmark": "069500",
            "sector_benchmark": "",
            "proposed_sector": "Consumer Discretionary",
            "proposed_sector_benchmark": "",
            "mapping_status": "first_pass_review_required",
        }])
        active = pd.DataFrame([{"symbol": "069500"}])
        prices = pd.DataFrame([
            {"symbol": "000270", "date": "2026-10-26"},
            {"symbol": "069500", "date": "2026-10-26"},
        ])
        report = build_candidate_coverage_report(candidates, active, prices)
        row = report.iloc[0]
        self.assertEqual(row["suggested_sector_benchmark"], "")
        self.assertEqual(row["suggested_sector_benchmark_coverage_status"], "suggestion_missing")
        self.assertEqual(row["activation_recommendation"], "keep_pending_review")

    def test_official_adr_ratio_registry_is_applied_without_approving_candidate(self):
        candidates = pd.DataFrame([{
            "symbol": "HDB", "name": "HDFC BANK LTD SPON ADS EACH REP 3 ORD SHS",
            "sector": "Financials", "market": "United States", "exchange": "NYS",
            "country": "India (ADR issuer; proxy)", "currency": "USD",
            "instrument_type": "adr_candidate", "activation_status": "pending_review",
            "identity_status": "issuer_proxy_review_required",
            "depositary_ratio_status": "listing_description_only_pending_primary_source",
            "market_cap_status": "not_verified", "provider_status": "not_checked",
            "market_benchmark": "SPY", "sector_benchmark": "",
            "proposed_sector": "Financials", "proposed_sector_benchmark": "XLF",
            "mapping_status": "first_pass_review_required",
        }])
        active = pd.DataFrame([{"symbol": "SPY"}, {"symbol": "XLF"}])
        prices = pd.DataFrame([
            {"symbol": "SPY", "date": "2026-10-26"},
            {"symbol": "XLF", "date": "2026-10-26"},
        ])
        registry = pd.DataFrame([{
            "symbol": "HDB", "depositary_ratio_observed": "3",
            "depositary_ratio_basis": "ordinary_shares_per_depositary_share",
            "depositary_ratio_source_url": "https://www.hdfc.bank.in/about-us/investor-relations/adr",
            "status": "official_source_confirmed",
        }])

        report = build_candidate_coverage_report(candidates, active, prices, adr_ratio_registry=registry)
        row = report.set_index("symbol").loc["HDB"]

        self.assertEqual(row["depositary_ratio_status"], "verified")
        self.assertEqual(row["depositary_ratio_observed"], "3")
        self.assertEqual(row["depositary_ratio_source_url"], "https://www.hdfc.bank.in/about-us/investor-relations/adr")
        self.assertNotIn("adr_depositary_ratio_unverified", row["review_blockers"])
        self.assertEqual(row["activation_recommendation"], "keep_pending_review")
        self.assertEqual(row["activation_gate_status"], "blocked_pending_manual_review")


    def test_secondary_cap_estimate_clears_only_the_minimum_size_screen(self):
        candidates = pd.DataFrame([{
            "symbol": "BIG", "name": "Big Co", "sector": "Information Technology",
            "market": "United States", "exchange": "NAS", "country": "United States",
            "currency": "USD", "instrument_type": "common_stock_candidate_unverified",
            "identity_status": "review_required", "market_cap_status": "not_verified",
            "provider_status": "not_checked", "market_benchmark": "SPY",
            "sector_benchmark": "XLK", "proposed_sector": "Information Technology",
            "proposed_sector_benchmark": "XLK",
        }])
        active = pd.DataFrame([{"symbol": "SPY"}, {"symbol": "XLK"}])
        prices = pd.DataFrame([
            {"symbol": "BIG", "date": "2026-10-26"},
            {"symbol": "SPY", "date": "2026-10-26"},
            {"symbol": "XLK", "date": "2026-10-26"},
        ])
        cap_observations = pd.DataFrame([{
            "symbol": "BIG", "market_cap_usd_b_secondary": 8.2,
            "observation_status": "observed_usd",
        }])

        report = build_candidate_coverage_report(
            candidates, active, prices,
            yahoo_market_cap_observations=cap_observations,
        )
        row = report.iloc[0]
        self.assertEqual(row["market_cap_size_screen_result"], "pass_estimate")
        self.assertEqual(row["market_cap_status"], "not_verified")
        self.assertNotIn("market_cap_unverified", row["review_blockers"])
        self.assertIn("listing_identity_unverified", row["review_blockers"])
        self.assertEqual(row["activation_gate_status"], "blocked_pending_manual_review")


if __name__ == "__main__":
    unittest.main()
