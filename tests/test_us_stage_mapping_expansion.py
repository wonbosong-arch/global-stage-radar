import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from stock_mapping import US_REVIEW_SECTOR_ADDITIONS, proposed_stock_mapping
from us_stage_connection_plan import OfflineStageReplay
from us_stage_mapping_expansion import (INPUTS, baseline_input_match, build_report,
                                        expand_rows, fingerprint)


def fixture():
    registry = pd.DataFrame([dict(symbol="NUE", name="NUCOR CORP", exchange="NYS",
        sector="", market="United States", asset_type="stock", market_benchmark="SPY",
        sector_benchmark="", proposed_sector="", proposed_sector_benchmark="",
        discovery_industry_code="", discovery_security_type="2",
        instrument_type="common_stock_candidate_unverified", discovery_source="review",
        market_cap_status="not_verified", market_cap_usd_b_secondary="1",
        market_cap_source_url="https://finance.yahoo.com/quote/NUE/", market_cap_asof="",
        identity_status="review_required", provider_status="not_checked",
        mapping_status="sector_mapping_missing", activation_status="pending_review")])
    master = pd.DataFrame([dict(symbol="NUE", english_name="NUCOR CORP",
        listing_exchange="NYS", master_security_type="2", master_dr_flag="N")])
    obs = [dict(symbol="NUE", discovery_market_cap_usd_b_secondary="1",
        market_cap_source_url=registry.iloc[0].market_cap_source_url,
        market_cap_asof_basis="not_provided_by_yahoo", fetched_at_utc="2026-10-24T00:00:00Z")]
    universe = pd.DataFrame([dict(symbol="SPY", asset_type="market_etf", sector="Market", provider="KIS", active="true"),
                            dict(symbol="XLB", asset_type="sector_etf", sector="Materials", provider="KIS", active="true")])
    prices = pd.DataFrame([dict(symbol=s, date=d, open=100+i, high=102+i, low=99+i,
                               close=101+i, volume=1000)
                          for s in ("NUE", "SPY", "XLB", "ALREADY")
                          for i, d in enumerate(pd.bdate_range(end="2026-10-23", periods=200))])
    return registry, master, obs, universe, prices


def run_fixture(parts):
    return expand_rows(*parts, "2026-10-24", ["ALREADY"])[0]


class MappingExpansionTests(unittest.TestCase):
    def test_primary_source_additions_are_suggestions_and_existing_mappings_survive(self):
        for symbol, sector in US_REVIEW_SECTOR_ADDITIONS.items():
            with self.subTest(symbol=symbol):
                result = proposed_stock_mapping(symbol.lower(), " nas ")
                self.assertEqual(result["proposed_sector"], sector)
                self.assertTrue(result["proposed_sector_benchmark"])
                self.assertEqual(result["mapping_status"], "first_pass_review_required")
                self.assertIn("https://", result["mapping_note"])
                self.assertNotIn("activation_status", result)
        self.assertEqual(proposed_stock_mapping("NVDA", "NAS")["proposed_sector_benchmark"], "SOXX")
        self.assertEqual(proposed_stock_mapping("IBKR", "NAS")["proposed_sector_benchmark"], "XLF")
        self.assertEqual(proposed_stock_mapping("005930", "KRX")["proposed_sector_benchmark"], "091160")
        self.assertEqual(proposed_stock_mapping("NUE", "KRX")["proposed_sector"], "")
        self.assertEqual(proposed_stock_mapping("NUE", "OTHER")["proposed_sector"], "")
        self.assertEqual(proposed_stock_mapping("UNKNOWNXYZ", "NYS")["proposed_sector"], "")
        self.assertEqual(proposed_stock_mapping("TTWO", "NAS", "CN")["proposed_market_benchmark"], "MCHI")

    def test_new_mapping_computes_without_mutation_or_replaying_old_baseline(self):
        parts = fixture()
        originals = [p.copy(deep=True) if isinstance(p, pd.DataFrame) else list(p) for p in parts]
        observed = []
        original_init = OfflineStageReplay.__init__

        def spy_init(instance, prices, as_of):
            observed.extend(prices.symbol.unique())
            original_init(instance, prices, as_of)

        with patch.object(OfflineStageReplay, "__init__", spy_init):
            row = run_fixture(parts)
        self.assertNotIn("ALREADY", observed)
        self.assertTrue(row["offline_review_eligible"])
        self.assertIsNotNone(row["review_only_stage_label"])
        self.assertEqual(row["stored_assigned_mapping"]["sector"], "")
        self.assertEqual(row["proposed_mapping"]["sector_benchmark"], "XLB")
        self.assertFalse(row["operational_approval_granted"])
        self.assertEqual(row["recorded_statuses"]["activation_status"], "pending_review")
        self.assertEqual(row["cap"]["effective_asof"], "")
        for before, after in zip(originals, parts):
            if isinstance(before, pd.DataFrame):
                pd.testing.assert_frame_equal(before, after)
            else:
                self.assertEqual(before, after)

    def test_cap_screen_boundary_and_no_label_on_failure(self):
        for cap, eligible in [("0.999", False), ("1", True), ("", False), ("inf", False)]:
            with self.subTest(cap=cap):
                parts = fixture()
                parts[0].loc[0, "market_cap_usd_b_secondary"] = cap
                row = run_fixture(parts)
                self.assertEqual(row["offline_review_eligible"], eligible)
                self.assertEqual(row["review_only_stage_label"] is not None, eligible)

    def test_missing_conflicting_duplicate_and_adr_master_withhold(self):
        for variant in ("missing", "venue", "duplicate", "adr"):
            with self.subTest(variant=variant):
                parts = list(fixture())
                if variant == "missing":
                    parts[1] = parts[1].iloc[:0]
                elif variant == "venue":
                    parts[1].loc[0, "listing_exchange"] = "NAS"
                elif variant == "duplicate":
                    parts[1] = pd.concat([parts[1], parts[1]])
                else:
                    parts[1].loc[0, "master_dr_flag"] = "Y"
                row = run_fixture(parts)
                self.assertIn("kis_identity_review_required", row["blocking_reasons"])
                self.assertIsNone(row["review_only_stage_label"])

    def test_benchmark_metadata_is_required_separately_from_prices(self):
        for field, value in [("provider", "OTHER"), ("active", "false"),
                             ("sector", "Energy"), ("asset_type", "stock")]:
            parts = fixture()
            parts[3].loc[1, field] = value
            row = run_fixture(parts)
            self.assertIn("sector_benchmark_metadata_missing_or_conflicting", row["blocking_reasons"])
            self.assertIsNone(row["review_only_stage_label"])

    def test_short_stale_duplicate_future_and_invalid_prices_withhold(self):
        for variant in ("short", "stale", "duplicate", "future", "invalid", "missing"):
            with self.subTest(variant=variant):
                parts = list(fixture())
                p = parts[4]
                b = p[p.symbol == "XLB"]
                if variant == "short":
                    p = p[(p.symbol != "XLB") | (p.date >= pd.Timestamp("2026-08-01"))]
                elif variant == "stale":
                    p = p[(p.symbol != "XLB") | (p.date <= pd.Timestamp("2026-10-01"))]
                elif variant == "duplicate":
                    p = pd.concat([p, b.tail(1)])
                elif variant == "future":
                    p = pd.concat([p, b.tail(1).assign(date=pd.Timestamp("2026-10-26"))])
                elif variant == "invalid":
                    p = p.assign(high=p.high.where(p.symbol != "XLB", 0))
                else:
                    p = p[p.symbol != "XLB"]
                parts[4] = p
                self.assertIsNone(run_fixture(parts)["review_only_stage_label"])

    def test_membership_overlap_and_duplicate_registry_fail_closed(self):
        parts = list(fixture())
        with self.assertRaises(ValueError):
            expand_rows(*parts, "2026-10-24", ["NUE"])
        parts[0] = pd.concat([parts[0], parts[0]])
        with self.assertRaises(ValueError):
            run_fixture(parts)

    def test_baseline_comparison_requires_matching_snapshot_and_date(self):
        registry, master, obs, universe, prices = fixture()
        frames = [registry, master, pd.DataFrame(obs), universe,
                  prices[prices.symbol.isin(["SPY", "XLB"])],
                  prices[~prices.symbol.isin(["SPY", "XLB"])]]
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            for name, frame in zip(INPUTS, frames):
                frame.to_csv(data / name, index=False)
            baseline = dict(as_of="2026-10-24", selected_candidates=1,
                candidates=[dict(symbol="ALREADY", review_only_stage_label="Stage 2 후보")],
                review_only_stage_counts={"Stage 2 후보": 1},
                input_files={n: fingerprint(data / n) for n in INPUTS})
            path = data / "baseline.json"
            path.write_text(json.dumps(baseline))
            report = build_report(data, "2026-10-24", path)
            self.assertTrue(report["same_snapshot_comparison"])
            self.assertEqual(report["cumulative_review_coverage"], 2)
            self.assertEqual(report["baseline"]["recomputed_candidates"], 0)
            self.assertEqual(sum(report["combined_same_snapshot_counts"].values()), 2)
            self.assertIsNone(build_report(data, "2026-10-25", path)["combined_same_snapshot_counts"])
            with (data / INPUTS[0]).open("a") as handle:
                handle.write("\n")
            self.assertFalse(build_report(data, "2026-10-24", path)["same_snapshot_comparison"])
            baseline["selected_candidates"] = 2
            path.write_text(json.dumps(baseline))
            with self.assertRaises(ValueError):
                build_report(data, "2026-10-24", path)

    def test_windows_baseline_hash_accepts_only_newline_equivalent_content(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.csv"
            path.write_bytes(b"a,b\r\n1,2\r\n")
            recorded = fingerprint(path)
            path.write_bytes(b"a,b\n1,2\n")
            self.assertEqual(baseline_input_match(path, recorded), "crlf_equivalent")
            path.write_bytes(b"a,b\n1,3\n")
            self.assertEqual(baseline_input_match(path, recorded), "different")


if __name__ == "__main__":
    unittest.main()
