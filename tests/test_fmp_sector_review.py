import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from fmp_sector_review import (PROFILE_URL, SECTORS, cache_policy, normalize_sec_sic,
    pilot_plan, profile_packets, profile_symbol, report)
from us_sector_mapping_batch import evaluate_new_rows
from us_stage_connection_plan import OfflineStageReplay

FIXTURE = Path(__file__).parent / "fixtures/fmp_profiles_synthetic.json"


def fixture():
    cache = json.loads(FIXTURE.read_text(encoding="utf-8"))
    symbols = [o["registry_symbol"] for o in cache["observations"]]
    registry = pd.DataFrame([dict(symbol=s, name=s + " CORPORATION", exchange="NYS",
        discovery_industry_code="", discovery_security_type="2", discovery_source="review",
        instrument_type="common_stock_candidate_unverified", market_cap_status="not_verified",
        market_cap_usd_b_secondary="1", identity_status="review_required",
        provider_status="not_checked", activation_status="pending_review") for s in symbols])
    master = pd.DataFrame([dict(symbol=s, english_name=s + " CORPORATION", listing_exchange="NYS",
        master_security_type="2", master_dr_flag="N") for s in symbols])
    universe = pd.DataFrame([dict(symbol="SPY", sector="Market", asset_type="market_etf", provider="KIS", active="true")]
        + [dict(symbol=etf, sector=sector, asset_type="sector_etf", provider="KIS", active="true")
           for sector, etf in SECTORS.values()])
    prices = pd.DataFrame([dict(symbol=s, date=d, open=100+i, high=102+i, low=99+i, close=101+i, volume=1000)
        for s in symbols + universe.symbol.tolist()
        for i, d in enumerate(pd.bdate_range(end="2026-10-23", periods=200))])
    return registry, universe, master, prices, cache


def evaluate(parts, baseline=()):
    registry, universe, master, prices, cache = parts
    packets = profile_packets(registry, universe, cache, "2026-10-24")
    return evaluate_new_rows(packets, registry, master, [], universe, prices, "2026-10-24", set(baseline))


class FmpSectorTests(unittest.TestCase):
    def test_five_synthetic_profiles_use_existing_engine_without_real_coverage_or_writes(self):
        parts = fixture()
        before = copy.deepcopy(parts)
        rows = evaluate(parts)
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(r["offline_review_eligible"] for r in rows))
        self.assertTrue(all(r["review_only_stage_label"] for r in rows))
        self.assertTrue(all(r["mapping_class"] == "provider_based_proposed" for r in rows))
        self.assertTrue(all(r["cache_mode"] == "synthetic" for r in rows))
        self.assertTrue(all(r["source_as_of"] is None for r in rows))
        self.assertTrue(all(not r["operational_approval_granted"] for r in rows))
        self.assertTrue(all(r["recorded_statuses"]["activation_status"] == "pending_review" for r in rows))
        for old, new in zip(before, parts):
            if isinstance(old, pd.DataFrame): pd.testing.assert_frame_equal(old, new)
            else: self.assertEqual(old, new)

    def test_exceptions_withhold_without_manufacturing_mapping(self):
        cases = {"sector": "Unknown", "industry": "", "exchange": "NASDAQ", "symbol": "OTHER",
                 "companyName": "", "isEtf": True, "isFund": True, "isActivelyTrading": False}
        for field, value in cases.items():
            parts = fixture()
            parts[-1]["observations"][0]["response"][0][field] = value
            with self.subTest(field=field):
                row = evaluate(parts)[0]
                self.assertEqual(row["mapping_class"], "review_required")
                self.assertIsNone(row["review_only_stage_label"])

    def test_source_link_time_payload_status_and_duplicates_fail_closed(self):
        for variant in ("host", "key", "request", "future", "naive", "malformed", "empty", "ambiguous", "403", "429", "duplicate"):
            parts = fixture()
            obs = parts[-1]["observations"][0]
            if variant == "host": obs["source_url"] = "https://untrusted.example/stable/profile?symbol=TESTA"
            if variant == "key": obs["source_url"] += "&apikey=synthetic-secret"
            if variant == "request": obs["requested_symbol"] = "OTHER"
            if variant == "future": obs["fetched_at_utc"] = "2026-10-25T00:00:00Z"
            if variant == "naive": obs["fetched_at_utc"] = "2026-10-23T00:00:00"
            if variant == "malformed": obs["response"] = {"Error Message": "denied"}
            if variant == "empty": obs["response"] = []
            if variant == "ambiguous": obs["response"] *= 2
            if variant in ("403", "429"): obs["http_status"] = int(variant)
            if variant == "duplicate": parts[-1]["observations"].append(copy.deepcopy(obs))
            with self.subTest(variant=variant):
                self.assertIsNone(evaluate(parts)[0]["review_only_stage_label"])

    def test_observed_cache_requires_documented_storage_and_processing_permission(self):
        parts = fixture()
        cache = parts[-1]
        cache["mode"] = "observed"
        self.assertTrue(all(r["batch_mapping"] is None for r in evaluate(parts)))
        cache["rights"] = {"local_storage": True, "offline_processing": True,
                           "evidence_reference": "owner-supplied-written-permission-reference"}
        self.assertTrue(all(r["batch_mapping"] for r in evaluate(parts)))
        cache["rights"]["local_storage"] = "true"
        self.assertTrue(all(r["batch_mapping"] is None for r in evaluate(parts)))
        with self.assertRaises(ValueError): cache_policy({"mode": "live"})

    def test_all_explicit_native_sector_labels_and_no_industry_inference(self):
        for native, (sector, etf) in SECTORS.items():
            parts = fixture()
            p = parts[-1]["observations"][0]["response"][0]
            p.update(sector=native, industry="Semiconductors")
            with self.subTest(native=native):
                row = evaluate(parts)[0]
                self.assertEqual(row["batch_mapping"]["sector"], sector)
                self.assertEqual(row["batch_mapping"]["sector_benchmark"], etf)
        self.assertEqual(SECTORS["Technology"][1], "XLK")

    def test_stored_curated_and_etf_conflicts_remain_exceptions(self):
        for variant in ("stored", "curated", "inactive", "metadata"):
            parts = fixture()
            registry, universe, master, prices, cache = parts
            if variant == "stored": registry.loc[0, "proposed_sector"] = "Utilities"
            if variant == "curated":
                registry.loc[0, "symbol"] = "NVDA"
                cache["observations"][0].update(registry_symbol="NVDA", requested_symbol="NVDA",
                    source_url=PROFILE_URL + "?symbol=NVDA")
                cache["observations"][0]["response"][0].update(symbol="NVDA", sector="Technology")
            if variant == "inactive": universe.loc[universe.symbol.eq("XLB"), "active"] = "false"
            if variant == "metadata": universe.loc[universe.symbol.eq("XLB"), "sector"] = "Other"
            packets = profile_packets(registry, universe, cache, "2026-10-24")
            target = next(r for r in packets if r["symbol"] == ("NVDA" if variant == "curated" else "TESTA"))
            with self.subTest(variant=variant):
                self.assertIsNone(target["batch_mapping"])
                self.assertEqual(target["mapping_class"], "review_required")

    def test_existing_kis_cap_history_price_and_benchmark_gates_are_reused(self):
        for variant in ("kis", "adr", "cap", "weeks", "daily", "stale", "ohlc", "duplicate", "benchmark"):
            parts = list(fixture())
            registry, universe, master, prices, _ = parts
            if variant == "kis": parts[2] = master[master.symbol.ne("TESTA")]
            if variant == "adr": master.loc[0, "master_dr_flag"] = "Y"
            if variant == "cap": registry.loc[0, "market_cap_usd_b_secondary"] = "0.999"
            if variant == "weeks": parts[3] = prices[prices.symbol.ne("TESTA") | prices.date.ge("2026-08-01")]
            if variant == "daily":
                keep = prices[prices.symbol.eq("TESTA")].iloc[::2].index
                parts[3] = prices[prices.symbol.ne("TESTA") | prices.index.isin(keep)]
            if variant == "stale": parts[3] = prices[prices.date.lt("2026-10-01")]
            if variant == "ohlc": prices.loc[0, "high"] = 1
            if variant == "duplicate": parts[3] = pd.concat([prices, prices.iloc[[0]]])
            if variant == "benchmark": universe.loc[universe.symbol.eq("SPY"), "active"] = "false"
            with self.subTest(variant=variant):
                row = evaluate(parts)[0]
                self.assertFalse(row["offline_review_eligible"])
                self.assertIsNone(row["review_only_stage_label"])

    def test_baseline_never_enters_replay(self):
        captured = []
        original = OfflineStageReplay.__init__
        def spy(instance, prices, as_of):
            captured.extend(prices.symbol.unique())
            original(instance, prices, as_of)
        with patch.object(OfflineStageReplay, "__init__", spy):
            evaluate(fixture(), ["TESTA"])
        self.assertNotIn("TESTA", captured)

    def test_share_classes_are_explicit_and_mismatch_is_not_retried(self):
        self.assertEqual(profile_symbol("BRK/A"), "BRK-A")
        self.assertEqual(profile_symbol("BRK/B"), "BRK-B")
        with self.assertRaises(ValueError): profile_symbol("BRK.B")

    def test_report_separates_fixture_engine_results_from_actual_additions(self):
        registry, universe, master, prices, cache = fixture()
        conditional = [dict(symbol=s, venue="NYS", existing_proposal={"sector": "Materials"},
            proposal_only_stage_inputs={"inputs_ready": True}, cap={"threshold_pass": True},
            kis_identity={"identity_basis": "kis_master_consistent"}) for s in registry.symbol]
        baseline = {"candidates": conditional, "saved_baseline": {"count": 85}}
        frames = {"stock_universe_candidates.csv": registry, "unranked_us_stock_master.csv": master,
            "monitoring_universe.csv": universe, "daily_prices.csv": prices,
            "candidate_daily_prices.csv": prices.iloc[:0], "yahoo_large_cap_candidate_review.csv": pd.DataFrame()}
        for mode, expected in (("synthetic", 0), ("observed", 5), ("missing", 0)):
            current = copy.deepcopy(cache)
            current["mode"] = mode
            current["rights"] = {"local_storage": True, "offline_processing": True, "evidence_reference": "test"}
            with self.subTest(mode=mode), patch("fmp_sector_review.build_report", return_value=baseline), \
                    patch("fmp_sector_review.pd.read_csv", side_effect=lambda path, **kw: frames[path.name].copy()), \
                    patch("fmp_sector_review.fingerprint", return_value={}):
                result = report(Path("unused"), "2026-10-24", current)
                self.assertEqual(result["actual_additional_eligible_count"], expected)
                self.assertEqual(result["cumulative_review_coverage"], 85 + expected)
                self.assertEqual(result["network_requests_this_run"], 0)
                self.assertEqual(len(result["planned_five_symbol_pilot"]), 5)
                self.assertEqual(pilot_plan(conditional), pilot_plan(list(reversed(conditional))))

    def test_sec_sic_retains_taxonomy_listing_pairs_and_unknown_effective_date(self):
        payload = dict(cik="123456", sic="3571", sicDescription="ELECTRONIC COMPUTERS",
                       tickers=["TESTA", "TESTB"], exchanges=["NYSE", "Nasdaq"])
        url = "https://data.sec.gov/submissions/CIK0000123456.json"
        result = normalize_sec_sic(payload, url, "2026-10-23T12:00:00Z", "2026-10-24")
        self.assertEqual(len(result["listing_pairs"]), 2)
        self.assertEqual(result["classification_system"], "SEC SIC")
        self.assertIsNone(result["source_as_of"])
        self.assertIsNone(result["proposed_sector_benchmark"])
        for variant in ("cik", "sic", "pairs", "time", "url"):
            p = copy.deepcopy(payload)
            if variant == "cik": p["cik"] = "other"
            if variant == "sic": p["sic"] = "000"
            if variant == "pairs": p["exchanges"] = []
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                normalize_sec_sic(p, "https://untrusted.example" if variant == "url" else url,
                    "2026-10-25T00:00:00Z" if variant == "time" else "2026-10-23T12:00:00Z", "2026-10-24")


if __name__ == "__main__":
    unittest.main()
