import unittest

import pandas as pd

from candidate_stage_integration import extend_universe_with_approved_candidates
from stock_mapping import proposed_stock_mapping
from us_stage_connection_plan import cap_provenance, prepare_connection_rows, OfflineStageReplay


def fixture():
    mapping = proposed_stock_mapping("IBKR", "NAS")
    row = dict(symbol="IBKR", name="Synthetic broker", exchange="NAS", market="United States",
               sector="Financials", asset_type="stock", market_benchmark="SPY", sector_benchmark="XLF",
               market_cap_status="not_verified", market_cap_usd_b_secondary="2",
               market_cap_source_url="https://finance.yahoo.com/quote/IBKR/", market_cap_asof="",
               identity_status="review_required", provider_status="not_checked", activation_status="pending_review")
    row.update(mapping)
    evidence = [dict(symbol="IBKR", offline_review_eligible=True, identity_basis="kis_master_consistent",
                     source="unranked_us_stock_master.csv", review_reasons=[])]
    obs = [dict(symbol="IBKR", discovery_market_cap_usd_b_secondary="2", market_cap_source_url=row["market_cap_source_url"],
                market_cap_asof="2026-10-23", market_cap_asof_basis="not_provided_by_yahoo", fetched_at_utc="2026-10-24T00:00:00Z")]
    prices = pd.DataFrame([dict(symbol=s, date=d, open=100+i, high=102+i, low=99+i, close=101+i, volume=1000)
                           for s in ("IBKR", "SPY", "XLF", "XLK")
                           for i, d in enumerate(pd.bdate_range(end="2026-10-23", periods=200))])
    return pd.DataFrame([row]), evidence, obs, prices


class ConnectionPlanTests(unittest.TestCase):
    def test_replay_never_approves_or_changes_inputs_and_real_bridge_stays_empty(self):
        registry, evidence, obs, prices = fixture()
        original, original_prices = registry.copy(deep=True), prices.copy(deep=True)
        row = prepare_connection_rows(registry, evidence, obs, prices, "2026-10-24")[0]
        self.assertTrue(row["assigned_replay"]["inputs_ready"])
        self.assertTrue(row["suggested_replay"]["inputs_ready"])
        self.assertIsNotNone(row["assigned_replay"]["review_only_stage_label"])
        self.assertEqual(row["mapping_class"], "consistent_suggestion_review")
        self.assertIn("mapping_suitability_review", row["remaining_gates"])
        self.assertFalse(row["operational_approval_granted"])
        self.assertEqual(row["cap"]["basis"], "screening_estimate")
        self.assertEqual(row["cap"]["effective_asof"], "")
        base = pd.DataFrame([dict(symbol="SPY")])
        universe, errors = extend_universe_with_approved_candidates(base, registry, prices, "2026-10-24")
        pd.testing.assert_frame_equal(universe, base)
        self.assertEqual(errors, [])
        pd.testing.assert_frame_equal(registry, original)
        pd.testing.assert_frame_equal(prices, original_prices)

    def test_fetched_at_is_not_cap_asof_and_other_quote_cannot_supply_provenance(self):
        registry, _, obs, _ = fixture()
        row = registry.iloc[0]
        result = cap_provenance(row, obs)
        self.assertEqual(result["observation_at_utc"], obs[0]["fetched_at_utc"])
        self.assertEqual(result["effective_asof"], "")
        for key, value in (("discovery_market_cap_usd_b_secondary", "3"), ("market_cap_source_url", "other")):
            altered = [dict(obs[0], **{key: value})]
            result = cap_provenance(row, altered)
            self.assertEqual(result["evidence_link"], "unlinked")
            self.assertEqual(result["observation_at_utc"], "")
        self.assertEqual(cap_provenance(row, obs + obs)["evidence_link"], "ambiguous")
        obs[0]["market_cap_asof_basis"] = "source_provided_market_cap_date"
        self.assertEqual(cap_provenance(row, obs)["effective_asof"], "2026-10-23")

    def test_assigned_mapping_does_not_override_conflicting_suggestion(self):
        registry, evidence, obs, prices = fixture()
        registry.loc[0, "sector_benchmark"] = "XLK"
        row = prepare_connection_rows(registry, evidence, obs, prices, "2026-10-24")[0]
        self.assertEqual(row["input_mapping_differences"], ["sector_benchmark"])
        self.assertIn("mapping_difference_review", row["remaining_gates"])
        self.assertEqual(row["assigned_mapping"]["sector_benchmark"], "XLK")
        self.assertEqual(row["suggested_mapping"]["sector_benchmark"], "XLF")

    def test_stored_proposal_drift_is_visible(self):
        registry, evidence, obs, prices = fixture()
        registry.loc[0, "proposed_sector"] = "old suggestion"
        row = prepare_connection_rows(registry, evidence, obs, prices, "2026-10-24")[0]
        self.assertEqual(row["stored_proposal_differences"], ["sector"])
        self.assertEqual(row["mapping_class"], "different_inputs_review")

    def test_missing_short_stale_duplicate_future_and_invalid_benchmark_withhold(self):
        registry, evidence, obs, prices = fixture()
        variants = {
            "missing": prices[prices.symbol != "XLF"],
            "short": prices[~((prices.symbol == "XLF") & (prices.date < pd.Timestamp("2026-08-01")))],
            "stale": prices[~((prices.symbol == "XLF") & (prices.date > pd.Timestamp("2026-10-01")))],
            "duplicate": pd.concat([prices, prices[prices.symbol == "XLF"].tail(1)]),
            "future": pd.concat([prices, prices[prices.symbol == "XLF"].tail(1).assign(date=pd.Timestamp("2026-10-26"))]),
            "invalid": prices.assign(close=prices.close.where(prices.symbol != "XLF", float("inf"))),
        }
        for name, frame in variants.items():
            with self.subTest(name=name):
                row = prepare_connection_rows(registry, evidence, obs, frame, "2026-10-24")[0]
                self.assertFalse(row["assigned_replay"]["inputs_ready"])
                self.assertIsNone(row["assigned_replay"]["review_only_stage_label"])
                self.assertIn("stage_inputs_repair", row["remaining_gates"])

    def test_current_partial_week_and_self_benchmark_do_not_clear_gates(self):
        registry, _, _, prices = fixture()
        mapping = registry.iloc[0].to_dict()
        result = OfflineStageReplay(prices, "2026-10-23").replay("IBKR", mapping)
        self.assertEqual(result["completed_weeks"]["IBKR"], 39)
        mapping["sector_benchmark"] = "IBKR"
        self.assertIn("self_benchmark", OfflineStageReplay(prices, "2026-10-24").replay("IBKR", mapping)["reasons"])

    def test_recent_daily_data_with_non_aligned_completed_week_cannot_supply_rs(self):
        registry, evidence, obs, prices = fixture()
        gap = prices[(prices.symbol != "XLF") | ~prices.date.between("2026-10-12", "2026-10-16")]
        row = prepare_connection_rows(registry, evidence, obs, gap, "2026-10-23")[0]
        self.assertTrue(row["assigned_replay"]["bridge_fresh7"])
        self.assertIn("aligned_rs_missing", row["assigned_replay"]["reasons"])
        self.assertIsNone(row["assigned_replay"]["review_only_stage_label"])

    def test_only_eligible_rows_selected_and_duplicates_fail_closed(self):
        registry, evidence, obs, prices = fixture()
        evidence[0]["offline_review_eligible"] = False
        self.assertEqual(prepare_connection_rows(registry, evidence, obs, prices, "2026-10-24"), [])
        with self.assertRaises(ValueError):
            prepare_connection_rows(pd.concat([registry, registry]), evidence, obs, prices, "2026-10-24")


if __name__ == "__main__":
    unittest.main()
