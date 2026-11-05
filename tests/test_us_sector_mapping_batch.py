import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from stock_mapping import proposed_stock_mapping
from us_stage_connection_plan import OfflineStageReplay
from us_sector_mapping_batch import (BASELINE, EXPANSION, HOLDINGS, SOURCES,
    batch_mapping_rows, evaluate_new_rows, saved_baseline)


def fixture():
    registry = pd.DataFrame([dict(symbol=s, name=s + " CORPORATION", exchange="NYS",
        discovery_industry_code="", discovery_security_type="2", discovery_source="review",
        instrument_type="common_stock_candidate_unverified", market_cap_status="not_verified",
        market_cap_usd_b_secondary="1", identity_status="review_required",
        provider_status="not_checked", activation_status="pending_review") for s in ("TESTA", "TESTB")])
    universe = pd.DataFrame([dict(symbol="SPY", asset_type="market_etf", sector="Market", provider="KIS", active="true"),
        dict(symbol="XLB", asset_type="sector_etf", sector="Materials", provider="KIS", active="true")])
    records = [dict(symbol=s, kis_recorded_name=s + " CORPORATION", listing_exchange="NYS",
        proposed_sector="Materials", proposed_sector_benchmark="XLB", basis=HOLDINGS,
        source_url="https://issuer.example/holdings", observed_on="2026-10-24",
        source_as_of="2026-10-23", retained_kis_industry_code="") for s in ("TESTA", "TESTB")]
    master = pd.DataFrame([dict(symbol=s, english_name=s + " CORPORATION", listing_exchange="NYS",
        master_security_type="2", master_dr_flag="N") for s in ("TESTA", "TESTB")])
    prices = pd.DataFrame([dict(symbol=s, date=d, open=100+i, high=102+i, low=99+i, close=101+i, volume=1000)
        for s in ("TESTA", "TESTB", "SPY", "XLB")
        for i, d in enumerate(pd.bdate_range(end="2026-10-23", periods=200))])
    return registry, records, universe, master, prices


def evaluate(parts, baseline=()):
    registry, records, universe, master, prices = parts
    packets = batch_mapping_rows(registry, records, universe, "2026-10-24")
    return evaluate_new_rows(packets, registry, master, [], universe, prices, "2026-10-24", set(baseline))


class BatchMappingTests(unittest.TestCase):
    def test_batch_membership_maps_multiple_new_symbols_without_changing_global_proposals(self):
        parts = fixture()
        before = copy.deepcopy(parts)
        rows = evaluate(parts)
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertTrue(row["offline_review_eligible"])
            self.assertIsNotNone(row["review_only_stage_label"])
            self.assertEqual(row["batch_mapping"]["sector_benchmark"], "XLB")
            self.assertEqual(row["recorded_statuses"]["activation_status"], "pending_review")
            self.assertFalse(row["operational_approval_granted"])
            self.assertEqual(proposed_stock_mapping(row["symbol"], "NYS")["proposed_sector"], "")
        for original, after in zip(before, parts):
            if isinstance(original, pd.DataFrame):
                pd.testing.assert_frame_equal(original, after)
            else:
                self.assertEqual(original, after)

    def test_blank_and_unanchored_kis_codes_never_generate_sector(self):
        registry, _, universe, _, _ = fixture()
        for code in ("", "000", "910", "510", "610"):
            with self.subTest(code=code):
                registry["discovery_industry_code"] = code
                packets = batch_mapping_rows(registry, [], universe, "2026-10-24")
                self.assertTrue(all(p["batch_mapping"] is None for p in packets))
                self.assertTrue(all(p["mapping_class"] == "sector_evidence_missing_or_invalid" for p in packets))

    def test_existing_curated_proposal_without_saved_source_withholds_label(self):
        registry, _, universe, master, prices = fixture()
        registry.loc[0, ["symbol", "name"]] = ["NUE", "NUCOR CORP"]
        master.loc[0, ["symbol", "english_name"]] = ["NUE", "NUCOR CORP"]
        prices.loc[prices.symbol.eq("TESTA"), "symbol"] = "NUE"
        rows = evaluate((registry, [], universe, master, prices))
        row = next(r for r in rows if r["symbol"] == "NUE")
        self.assertTrue(row["proposal_only_stage_inputs"]["inputs_ready"])
        self.assertIsNone(row["review_only_stage_label"])
        self.assertFalse(row["offline_review_eligible"])
        self.assertEqual(row["blocking_reasons"], ["saved_sector_evidence_missing"])

    def test_duplicates_and_disagreements_withhold_without_overwriting(self):
        for variant in ("duplicate", "source_sector", "venue", "name", "code", "assigned", "proposed", "etf"):
            with self.subTest(variant=variant):
                registry, records, universe, master, prices = fixture()
                if variant == "duplicate": records.append(dict(records[0]))
                if variant == "source_sector": records[0]["proposed_sector"] = "Utilities"
                if variant == "venue": records[0]["listing_exchange"] = "NAS"
                if variant == "name": records[0]["kis_recorded_name"] = "OTHER ISSUER"
                if variant == "code": records[0]["retained_kis_industry_code"] = "910"
                if variant == "assigned": registry.loc[0, "sector"] = "Utilities"
                if variant == "proposed": registry.loc[0, "proposed_sector_benchmark"] = "XLU"
                if variant == "etf": universe.loc[1, "active"] = "false"
                rows = evaluate((registry, records, universe, master, prices))
                self.assertIsNone(rows[0]["batch_mapping"])
                self.assertIsNone(rows[0]["review_only_stage_label"])

    def test_invalid_provenance_and_unknown_basis_withhold(self):
        for field, value in (("basis", "name_guess"), ("source_url", ""),
                             ("source_as_of", ""), ("source_as_of", "2026-10-25"),
                             ("observed_on", "2026-10-22")):
            with self.subTest(field=field, value=value):
                parts = fixture()
                parts[1][0][field] = value
                self.assertIsNone(evaluate(parts)[0]["review_only_stage_label"])

    def test_existing_baseline_never_enters_weekly_replay(self):
        parts = fixture()
        captured = []
        original = OfflineStageReplay.__init__
        def spy(instance, prices, as_of):
            captured.extend(prices.symbol.unique())
            original(instance, prices, as_of)
        with patch.object(OfflineStageReplay, "__init__", spy):
            rows = evaluate(parts, ["TESTA"])
        self.assertNotIn("TESTA", captured)
        self.assertIn("TESTB", captured)
        self.assertEqual(rows[0]["evaluation_class"], "saved_baseline_preserved")
        self.assertIsNone(rows[0]["stage_inputs"])

    def test_no_additions_performs_no_replay(self):
        with patch.object(OfflineStageReplay, "__init__", side_effect=AssertionError("baseline replay")):
            evaluate(fixture(), ["TESTA", "TESTB"])

    def test_cap_boundary_identity_history_and_benchmarks_gate_labels(self):
        for variant in ("cap_below", "cap_missing", "cap_infinite", "identity", "adr", "history", "benchmark", "duplicate_price", "ohlc", "stale"):
            with self.subTest(variant=variant):
                registry, records, universe, master, prices = fixture()
                if variant == "cap_below": registry.loc[0, "market_cap_usd_b_secondary"] = "0.999"
                if variant == "cap_missing": registry.loc[0, "market_cap_usd_b_secondary"] = ""
                if variant == "cap_infinite": registry.loc[0, "market_cap_usd_b_secondary"] = "inf"
                if variant == "identity": master = master[master.symbol.ne("TESTA")]
                if variant == "adr": master.loc[0, "master_dr_flag"] = "Y"
                if variant == "history": prices = prices[prices.symbol.ne("TESTA") | prices.date.ge("2026-08-01")]
                if variant == "benchmark": universe.loc[0, "provider"] = "OTHER"
                if variant == "duplicate_price": prices = pd.concat([prices, prices.iloc[[0]]])
                if variant == "ohlc": prices.loc[0, "high"] = 1
                if variant == "stale": prices = prices[prices.date.lt("2026-10-01")]
                row = evaluate((registry, records, universe, master, prices))[0]
                self.assertFalse(row["offline_review_eligible"])
                self.assertIsNone(row["review_only_stage_label"])
                self.assertTrue(row["blocking_reasons"])
        self.assertTrue(evaluate(fixture())[0]["offline_review_eligible"])

    def test_real_saved_sources_are_bounded_and_baseline_is_85(self):
        baseline = json.loads(BASELINE.read_text())
        expansion = json.loads(EXPANSION.read_text())
        symbols, counts = saved_baseline(baseline, expansion)
        self.assertEqual(len(symbols), 85)
        self.assertEqual(counts["Stage 2 후보"], 28)
        self.assertEqual(counts["Stage 2A 관찰 후보"], 5)
        sources = json.loads(SOURCES.read_text())["records"]
        holdings = {r["symbol"] for r in sources if r["basis"] == HOLDINGS}
        self.assertEqual(len(holdings), 13)
        self.assertTrue(holdings.issubset(symbols))
        for bad in ("overlap", "count", "label", "snapshot"):
            b, e = copy.deepcopy(baseline), copy.deepcopy(expansion)
            if bad == "overlap": e["candidates"][0]["symbol"] = b["candidates"][0]["symbol"]
            if bad == "count": b["selected_candidates"] += 1
            if bad == "label": e["combined_same_snapshot_counts"]["Stage 2 후보"] += 1
            if bad == "snapshot": e["same_snapshot_comparison"] = False
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                saved_baseline(b, e)


if __name__ == "__main__":
    unittest.main()
