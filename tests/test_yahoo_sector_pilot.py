import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from us_sector_mapping_batch import evaluate_new_rows
from yahoo_sector_pilot import (ROOT, SECTOR_TO_ETF, balanced_sample, build_report,
    conditional_symbols, load_observations, mapping_packets, profile_url)


def fixture():
    registry = pd.DataFrame([dict(symbol=s, name=s + " CORPORATION", exchange="NYS",
        discovery_security_type="2", instrument_type="common_stock_candidate_unverified",
        market_cap_usd_b_secondary="1", market_cap_status="not_verified",
        identity_status="review_required", provider_status="not_checked",
        activation_status="pending_review") for s in ("NUE", "VMC")])
    master = pd.DataFrame([dict(symbol=s, english_name=s + " CORPORATION", listing_exchange="NYS",
        master_security_type="2", master_dr_flag="N") for s in registry.symbol])
    universe = pd.DataFrame([dict(symbol="SPY", sector="Market", asset_type="market_etf", provider="KIS", active="true"),
        dict(symbol="XLB", sector="Materials", asset_type="sector_etf", provider="KIS", active="true")])
    _, records = load_observations(ROOT / "tests/fixtures/yahoo_sector_profile_synthetic.json")
    observations = [dict(records[0], symbol=s, yahoo_symbol=s, source_url=profile_url(s)) for s in registry.symbol]
    prices = pd.DataFrame([dict(symbol=s, date=d, open=100+i, high=102+i, low=99+i, close=101+i, volume=1000)
        for s in ("NUE", "VMC", "SPY", "XLB")
        for i, d in enumerate(pd.bdate_range(end="2026-11-04", periods=200))])
    return registry, master, universe, observations, prices


def run(parts):
    registry, master, universe, observations, prices = parts
    packets = mapping_packets(registry, observations, universe, "2026-11-05")
    return evaluate_new_rows(packets, registry, master, [], universe, prices, "2026-11-05", set())


class YahooSectorPilotTests(unittest.TestCase):
    def test_explicit_eleven_sector_crosswalk_and_no_specialist_inference(self):
        self.assertEqual(len(SECTOR_TO_ETF), 11)
        self.assertEqual(len({v[1] for v in SECTOR_TO_ETF.values()}), 11)
        for sector, etf in {"Technology": "XLK", "Consumer Cyclical": "XLY",
                            "Consumer Defensive": "XLP", "Basic Materials": "XLB",
                            "Financial Services": "XLF", "Healthcare": "XLV"}.items():
            self.assertEqual(SECTOR_TO_ETF[sector][1], etf)
        self.assertNotIn("SOXX", {v[1] for v in SECTOR_TO_ETF.values()})
        self.assertNotIn("Technology Services", SECTOR_TO_ETF)

    def test_reproducible_balanced_100_from_conditional_135(self):
        evidence = json.loads((ROOT / "docs/evidence/us-sector-mapping-batch-20261105.json").read_text(encoding="utf-8"))
        registry = pd.read_csv(ROOT / "data/stock_universe_candidates.csv", dtype=str, keep_default_na=False)
        symbols = evidence["proposal_only_otherwise_ready_symbols"]
        first = balanced_sample(registry, symbols)
        second = balanced_sample(registry.sample(frac=1, random_state=19), list(reversed(symbols)))
        self.assertEqual(first, second)
        self.assertEqual(len({r["symbol"] for r in first}), 100)
        self.assertTrue({r["symbol"] for r in first}.issubset(symbols))
        self.assertEqual({r["kis_exchange"] for r in first}, {"NAS", "NYS", "AMS"})
        self.assertEqual(len({r["sampling_sector_proposal"] for r in first}), 12)  # 11 broad + semiconductors
        self.assertTrue({"BRK/A", "BRK/B"}.issubset({r["symbol"] for r in first}))
        self.assertEqual(profile_url("BRK/B"), "https://finance.yahoo.com/quote/BRK-B/profile/")
        with self.assertRaises(ValueError):
            balanced_sample(registry, symbols, 136)
        with self.assertRaises(ValueError):
            balanced_sample(pd.concat([registry, registry.iloc[[0]]]), symbols)

    def test_synthetic_multiple_mappings_reuse_engine_without_status_or_input_mutations(self):
        parts = fixture()
        before = copy.deepcopy(parts)
        rows = run(parts)
        self.assertEqual(len(rows), 2)
        for r in rows:
            self.assertTrue(r["offline_review_eligible"])
            self.assertIsNotNone(r["review_only_stage_label"])
            self.assertEqual(r["batch_mapping"]["sector_benchmark"], "XLB")
            self.assertFalse(r["operational_approval_granted"])
            self.assertEqual(r["recorded_statuses"]["activation_status"], "pending_review")
            self.assertEqual(r["audit"]["network_calls_in_this_run"], 0)
        for a, b in zip(before, parts):
            if isinstance(a, pd.DataFrame):
                pd.testing.assert_frame_equal(a, b)
            else:
                self.assertEqual(a, b)

    def test_missing_duplicate_unknown_stale_future_errors_and_bindings_withhold(self):
        variants = {"sector": "Tech", "industry": "", "fetched_at_utc": "2026-10-01T00:00:00Z",
            "source_url": "https://finance.yahoo.com/quote/OTHER/profile/",
            "requested_kis_exchange": "NAS", "yahoo_symbol": "OTHER", "error_code": "http_429"}
        cases = list(variants.items()) + [("fetched_at_utc", "2026-11-07T00:00:00Z"),
            ("fetched_at_utc", "2026-11-05"), ("fetched_at_utc", "bad"),
            ("fetched_at_utc", []), ("http_status", 403), ("sector", []),
            ("sector", ""), ("duplicate", True), ("missing", True)]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                parts = fixture()
                obs = parts[3]
                if key == "duplicate": obs.append(dict(obs[0]))
                elif key == "missing": obs.pop(0)
                else: obs[0][key] = value
                rows = run(parts)
                self.assertIsNone(rows[0]["batch_mapping"])
                self.assertIsNone(rows[0]["review_only_stage_label"])
                self.assertFalse(rows[0]["offline_review_eligible"])
                self.assertTrue(rows[1]["offline_review_eligible"])

    def test_stored_curated_and_specialist_conflicts_never_overwrite(self):
        for variant in ("stored", "sector_etf", "specialist"):
            with self.subTest(variant=variant):
                parts = fixture()
                if variant == "stored": parts[0].loc[0, "sector"] = "Utilities"
                if variant == "sector_etf": parts[2].loc[1, "active"] = "false"
                if variant == "specialist":
                    parts[0].loc[0, "symbol"] = "NVDA"
                    parts[3][0].update(symbol="NVDA", yahoo_symbol="NVDA", sector="Technology", source_url=profile_url("NVDA"))
                packets = mapping_packets(parts[0], parts[3], parts[2], "2026-11-05")
                packet = next(p for p in packets if p["symbol"] == parts[0].iloc[0].symbol)
                self.assertIsNone(packet["batch_mapping"])
                self.assertTrue(packet["mapping_reasons"])

    def test_yahoo_never_clears_kis_type_venue_cap_history_freshness_or_benchmark_gate(self):
        for variant in ("missing_identity", "wrong_venue", "fund", "adr", "cap", "weeks", "stale", "benchmark"):
            with self.subTest(variant=variant):
                registry, master, universe, observations, prices = fixture()
                if variant == "missing_identity": master = master[master.symbol.ne("NUE")]
                if variant == "wrong_venue": master.loc[0, "listing_exchange"] = "NAS"
                if variant == "fund": master.loc[0, "master_security_type"] = "3"
                if variant == "adr": master.loc[0, "master_dr_flag"] = "Y"
                if variant == "cap": registry.loc[0, "market_cap_usd_b_secondary"] = "0.999"
                if variant == "weeks": prices = prices[prices.symbol.ne("NUE") | prices.date.gt("2026-09-01")]
                if variant == "stale": prices = prices[prices.date.lt("2026-10-01")]
                if variant == "benchmark": universe.loc[0, "provider"] = "Other"
                row = run((registry, master, universe, observations, prices))[0]
                self.assertFalse(row["offline_review_eligible"])
                self.assertIsNone(row["review_only_stage_label"])

    def test_envelope_requires_explicit_cache_or_fixture_and_diagnostics_are_bounded(self):
        path = ROOT / "tests/fixtures/yahoo_sector_profile_synthetic.json"
        origin, records = load_observations(path)
        self.assertEqual(origin, "fixture")
        self.assertEqual(load_observations(None), ("none", []))
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "invalid.json"
            invalid.write_text(json.dumps({"schema_version": 1, "data_origin": "live", "records": []}))
            with self.assertRaises(ValueError): load_observations(invalid)
        parts = fixture()
        parts[3][0].update(error_code="provider message with private cookie", http_status=429,
                           duration_ms=42, retry_after_seconds=60)
        p = mapping_packets(parts[0], parts[3], parts[2], "2026-11-05")[0]
        self.assertEqual(p["audit"]["error_code"], "other_error")
        self.assertEqual(p["audit"]["retry_after_seconds"], 60)
        self.assertNotIn("private cookie", json.dumps(p))

    def test_report_never_counts_fixture_as_actual_coverage_and_never_fetches(self):
        registry, master, universe, observations, prices = fixture()
        base = {"as_of": "2026-11-05", "saved_baseline": {"count": 85, "symbols": []},
            "candidates": [dict(symbol=s, proposal_only_stage_inputs={"inputs_ready": True},
                cap={"threshold_pass": True}, kis_identity={"identity_basis": "kis_master_consistent"}) for s in registry.symbol]}
        self.assertEqual(conditional_symbols(base), ["NUE", "VMC"])
        frames = dict(zip(INPUT_NAMES, [registry, master, pd.DataFrame(), universe, prices, prices.iloc[:0]]))
        def read(path, **kwargs):
            return frames[Path(path).name].copy()
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            for name in INPUT_NAMES: (data / name).write_text("synthetic")
            for origin in ("cache", "fixture"):
                path = data / "observations.json"
                path.write_text(json.dumps(dict(schema_version=1, data_origin=origin, records=observations)))
                with patch("yahoo_sector_pilot.batch_report", return_value=base), \
                     patch("yahoo_sector_pilot.pd.read_csv", side_effect=read), \
                     patch("yfinance.Ticker", side_effect=AssertionError("network not allowed")):
                    report = build_report(data, "2026-11-05", path)
                self.assertEqual(report["conditional_targets"]["stage_review_ready"], 2)
                self.assertEqual(report["actual_additional_review_coverage"], 2 if origin == "cache" else 0)
                self.assertEqual(report["live"]["ticker_attempts"], 0)
                self.assertIsNone(report["live"]["ticker_success_rate"])
                self.assertEqual(report["operational_additions"], 0)
                self.assertEqual(report["baseline_recomputed"], 0)

    def test_cached_batch_replay_rejects_changed_inputs_or_code(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            from us_stage_mapping_expansion import fingerprint
            for name in INPUT_NAMES: (data / name).write_text("synthetic")
            replay = data / "replay.json"
            base = dict(as_of="2026-11-05", input_files={n: fingerprint(data / n) for n in INPUT_NAMES},
                implementation_files={"stock_mapping.py": {"bytes": 0, "sha256": "invalid"}})
            replay.write_text(json.dumps(base))
            with self.assertRaisesRegex(ValueError, "inputs/code/as-of"):
                build_report(data, "2026-11-05", replay_path=replay)
            base["implementation_files"] = {}
            replay.write_text(json.dumps(base))
            (data / INPUT_NAMES[0]).write_text("changed")
            with self.assertRaisesRegex(ValueError, "inputs/code/as-of"):
                build_report(data, "2026-11-05", replay_path=replay)


INPUT_NAMES = ("stock_universe_candidates.csv", "unranked_us_stock_master.csv",
    "yahoo_large_cap_candidate_review.csv", "monitoring_universe.csv", "daily_prices.csv", "candidate_daily_prices.csv")


if __name__ == "__main__":
    unittest.main()
