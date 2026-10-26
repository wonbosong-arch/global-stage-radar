import unittest
import pandas as pd

from collect_stock_candidates import (
    build_discovered_candidate_rows,
    merge_candidate_discoveries,
)


class CandidateDiscoveryTests(unittest.TestCase):
    def normalized_rows(self):
        return pd.DataFrame([
            {
                "symbol": "BIG", "name": "Big Corp", "exchange": "NAS", "master_industry_code": "IND42",
                "market_cap_usd": 2_500_000_000, "market_cap_native": 2_500_000_000,
                "master_instrument_type": "stock", "instrument_type_guess": "equity_candidate_unverified",
                "stock_eligible": "review_required", "cap_threshold_pass": True,
                "is_adr_candidate": False, "review_reason": "cap verified by price × shares",
            },
            {
                "symbol": "SMALL", "name": "Small Corp", "exchange": "NAS",
                "market_cap_usd": 500_000_000, "market_cap_native": 500_000_000,
                "master_instrument_type": "stock", "instrument_type_guess": "equity_candidate_unverified",
                "stock_eligible": "review_required", "cap_threshold_pass": False,
                "is_adr_candidate": False, "review_reason": "below_minimum_market_cap",
            },
            {
                "symbol": "FUND", "name": "Example ETF", "exchange": "NYS",
                "market_cap_usd": 8_000_000_000, "market_cap_native": 8_000_000_000,
                "master_instrument_type": "etp", "instrument_type_guess": "fund_or_etf_likely",
                "stock_eligible": "exclude_from_stock_universe_pending_confirmation",
                "cap_threshold_pass": pd.NA, "is_adr_candidate": False, "review_reason": "ETP",
            },
            {
                "symbol": "UNKNOWN", "name": "Unknown Cap Corp", "exchange": "KRX",
                "market_cap_usd": pd.NA, "market_cap_native": 1_000_000_000,
                "master_instrument_type": "stock", "instrument_type_guess": "equity_candidate_unverified",
                "stock_eligible": "review_required", "cap_threshold_pass": pd.NA,
                "is_adr_candidate": False, "review_reason": "usd_market_cap_unavailable",
            },
        ])

    def test_discovery_keeps_near_threshold_stocks_for_review(self):
        rows = self.normalized_rows()
        near = rows.iloc[[0]].copy()
        near.loc[near.index[0], "symbol"] = "NEAR"
        near.loc[near.index[0], "market_cap_usd"] = 900_000_000
        near.loc[near.index[0], "market_cap_native"] = 900_000_000
        near.loc[near.index[0], "cap_threshold_pass"] = False
        near.loc[near.index[0], "review_reason"] = "below_minimum_market_cap"
        result = build_discovered_candidate_rows(near, "2026-10-26")
        self.assertEqual(list(result["symbol"]), ["NEAR"])
        self.assertIn("Near-threshold cap retained for review", result.iloc[0]["review_note"])

    def test_discovery_excludes_verified_small_stocks_and_etfs_but_keeps_unknown_cap(self):
        rows = build_discovered_candidate_rows(self.normalized_rows(), "2026-10-26")
        self.assertEqual(set(rows["symbol"]), {"BIG", "UNKNOWN"})
        big = rows.set_index("symbol").loc["BIG"]
        unknown = rows.set_index("symbol").loc["UNKNOWN"]
        self.assertEqual(big["activation_status"], "pending_review")
        self.assertEqual(big["market_cap_status"], "not_verified")
        self.assertEqual(big["discovery_industry_code"], "IND42")
        self.assertTrue(pd.isna(unknown["discovery_market_cap_usd"]))
        self.assertEqual(unknown["market"], "South Korea")
        self.assertEqual(unknown["market_benchmark"], "EWY")


    def test_discovery_stores_sector_suggestions_without_approving_them(self):
        rows = build_discovered_candidate_rows(pd.DataFrame([{
            "symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NAS",
            "market_cap_usd": 2_500_000_000_000, "market_cap_native": 2_500_000_000_000,
            "master_instrument_type": "stock", "instrument_type_guess": "equity_candidate_unverified",
            "stock_eligible": "review_required", "cap_threshold_pass": True,
            "is_adr_candidate": False, "master_dr_country_code": "",
            "master_industry_code": "IND42", "review_reason": "review required",
        }]), "2026-10-26")
        row = rows.iloc[0]
        self.assertEqual(row["proposed_sector"], "Semiconductors")
        self.assertEqual(row["proposed_sector_benchmark"], "SOXX")
        self.assertEqual(row["mapping_status"], "first_pass_review_required")
        self.assertEqual(row["sector"], "")
        self.assertEqual(row["sector_benchmark"], "")
        self.assertEqual(row["activation_status"], "pending_review")

    def test_merge_backfills_blank_mapping_suggestions_without_overwriting_reviewed_values(self):
        discoveries = build_discovered_candidate_rows(pd.DataFrame([{
            "symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NAS",
            "market_cap_usd": 2_500_000_000_000, "market_cap_native": 2_500_000_000_000,
            "master_instrument_type": "stock", "instrument_type_guess": "equity_candidate_unverified",
            "stock_eligible": "review_required", "cap_threshold_pass": True,
            "is_adr_candidate": False, "master_dr_country_code": "",
            "master_industry_code": "IND42", "review_reason": "review required",
        }]), "2026-10-26")
        existing = pd.DataFrame([{
            "symbol": "NVDA", "name": "Reviewed name", "activation_status": "pending_review",
            "sector": "Information Technology", "proposed_sector": "",
            "proposed_sector_benchmark": "", "mapping_note": "",
        }])
        merged, added = merge_candidate_discoveries(
            existing, discoveries, pd.DataFrame(columns=["symbol"])
        )
        row = merged.iloc[0]
        self.assertEqual(added, 0)
        self.assertEqual(row["name"], "Reviewed name")
        self.assertEqual(row["sector"], "Information Technology")
        self.assertEqual(row["proposed_sector"], "Semiconductors")
        self.assertEqual(row["proposed_sector_benchmark"], "SOXX")
        self.assertEqual(row["activation_status"], "pending_review")

    def test_merge_backfills_mapping_suggestions_without_current_ranking_row(self):
        existing = pd.DataFrame([{
            "symbol": "CCEP", "name": "COCA-COLA EUROPACIFIC PARTNERS",
            "exchange": "NAS", "activation_status": "pending_review",
            "sector": "", "sector_benchmark": "",
            "proposed_sector": "", "proposed_sector_benchmark": "",
            "mapping_status": "sector_mapping_missing",
            "mapping_note": "No ticker sector mapping; verify sector manually.",
        }])
        merged, added = merge_candidate_discoveries(
            existing, pd.DataFrame(columns=["symbol"]), pd.DataFrame(columns=["symbol"])
        )
        row = merged.iloc[0]
        self.assertEqual(added, 0)
        self.assertEqual(row["proposed_sector"], "Consumer Staples")
        self.assertEqual(row["proposed_sector_benchmark"], "XLP")
        self.assertEqual(row["mapping_status"], "first_pass_review_required")
        self.assertEqual(row["sector"], "")
        self.assertEqual(row["sector_benchmark"], "")
        self.assertEqual(row["activation_status"], "pending_review")

    def test_merge_does_not_overwrite_existing_mapping_suggestion(self):
        discoveries = build_discovered_candidate_rows(pd.DataFrame([{
            "symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NAS",
            "market_cap_usd": 2_500_000_000_000, "market_cap_native": 2_500_000_000_000,
            "master_instrument_type": "stock", "instrument_type_guess": "equity_candidate_unverified",
            "stock_eligible": "review_required", "cap_threshold_pass": True,
            "is_adr_candidate": False, "master_dr_country_code": "",
            "master_industry_code": "IND42", "review_reason": "review required",
        }]), "2026-10-26")
        existing = pd.DataFrame([{
            "symbol": "NVDA", "name": "Reviewed name", "activation_status": "pending_review",
            "proposed_sector": "Manually reviewed sector",
            "proposed_sector_benchmark": "XLK", "mapping_note": "manual review note",
        }])
        merged, added = merge_candidate_discoveries(
            existing, discoveries, pd.DataFrame(columns=["symbol"])
        )
        row = merged.iloc[0]
        self.assertEqual(added, 0)
        self.assertEqual(row["proposed_sector"], "Manually reviewed sector")
        self.assertEqual(row["proposed_sector_benchmark"], "XLK")
        self.assertEqual(row["mapping_note"], "manual review note")
        self.assertEqual(row["activation_status"], "pending_review")

    def test_merge_repairs_stale_missing_status_when_suggestion_already_exists(self):
        existing = pd.DataFrame([{
            "symbol": "CCEP", "name": "COCA-COLA EUROPACIFIC PARTNERS",
            "exchange": "NAS", "activation_status": "pending_review",
            "sector": "", "sector_benchmark": "",
            "proposed_sector": "Consumer Staples", "proposed_sector_benchmark": "XLP",
            "mapping_status": "sector_mapping_missing",
            "mapping_note": "No ticker sector mapping; verify sector manually.",
        }])
        merged, added = merge_candidate_discoveries(
            existing, pd.DataFrame(columns=["symbol"]), pd.DataFrame(columns=["symbol"])
        )
        row = merged.iloc[0]
        self.assertEqual(added, 0)
        self.assertEqual(row["proposed_sector"], "Consumer Staples")
        self.assertEqual(row["proposed_sector_benchmark"], "XLP")
        self.assertEqual(row["mapping_status"], "first_pass_review_required")
        self.assertIn("verify", row["mapping_note"].lower())
        self.assertEqual(row["sector"], "")
        self.assertEqual(row["sector_benchmark"], "")
        self.assertEqual(row["activation_status"], "pending_review")

    def test_merge_backfills_only_missing_industry_evidence(self):
        existing = pd.DataFrame([{
            "symbol": "BIG", "name": "Manually reviewed name",
            "activation_status": "pending_review", "sector": "Information Technology",
            "discovery_industry_code": "",
        }])
        discoveries = build_discovered_candidate_rows(
            pd.DataFrame([{
                "symbol": "BIG", "name": "Big Corp", "exchange": "NAS",
                "market_cap_usd": 2_500_000_000, "market_cap_native": 2_500_000_000,
                "master_instrument_type": "stock", "instrument_type_guess": "equity_candidate_unverified",
                "stock_eligible": "review_required", "cap_threshold_pass": True,
                "is_adr_candidate": False, "master_industry_code": "IND42",
                "review_reason": "cap verified by price x shares",
            }]),
            "2026-10-26",
        )
        merged, added = merge_candidate_discoveries(
            existing, discoveries, pd.DataFrame(columns=["symbol"])
        )
        self.assertEqual(added, 0)
        self.assertEqual(merged.iloc[0]["name"], "Manually reviewed name")
        self.assertEqual(merged.iloc[0]["sector"], "Information Technology")
        self.assertEqual(merged.iloc[0]["activation_status"], "pending_review")
        self.assertEqual(merged.iloc[0]["discovery_industry_code"], "IND42")

    def test_merge_does_not_overwrite_existing_or_add_active_symbols(self):
        existing = pd.DataFrame([{
            "symbol": "BIG", "name": "Manually reviewed name",
            "activation_status": "pending_review", "review_note": "Keep this note",
        }])
        discoveries = build_discovered_candidate_rows(self.normalized_rows(), "2026-10-26")
        active = pd.DataFrame([{"symbol": "UNKNOWN"}])
        merged, added = merge_candidate_discoveries(existing, discoveries, active)
        self.assertEqual(added, 0)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged.iloc[0]["name"], "Manually reviewed name")
        self.assertEqual(merged.iloc[0]["review_note"], "Keep this note")

    def test_new_discovery_appends_without_activating(self):
        discoveries = build_discovered_candidate_rows(self.normalized_rows(), "2026-10-26")
        merged, added = merge_candidate_discoveries(
            pd.DataFrame(columns=["symbol", "name", "activation_status"]),
            discoveries,
            pd.DataFrame(columns=["symbol"]),
        )
        self.assertEqual(added, 2)
        self.assertEqual(set(merged["symbol"]), {"BIG", "UNKNOWN"})
        self.assertTrue(merged["activation_status"].eq("pending_review").all())


if __name__ == "__main__":
    unittest.main()
