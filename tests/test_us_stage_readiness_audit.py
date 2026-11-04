import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from audit_us_stage_readiness import build_audit, summarize


class USReadinessAuditTests(unittest.TestCase):
    def fixture(self, root):
        rows = []
        prices = []
        for symbol, weeks in [("THIRTY", 30), ("THIRTYFOUR", 34), ("THIRTYFIVE", 35)]:
            rows.append(dict(symbol=symbol, name=symbol, exchange="NAS", market="United States",
                             sector="Technology", asset_type="stock", market_benchmark="SPY",
                             sector_benchmark="XLK", activation_status="pending_review",
                             identity_status="review_required", provider_status="not_checked",
                             market_cap_status="not_verified", market_cap_usd_b_secondary=2,
                             discovery_market_cap_usd="", market_cap_source_url="https://example.test/cap",
                             market_cap_asof="2026-10-30", mapping_status="review_required",
                             instrument_type="common_stock_candidate", discovery_source="yahoo",
                             proposed_sector="Technology", proposed_market_benchmark="SPY",
                             proposed_sector_benchmark="XLK"))
            for date in pd.date_range(end="2026-10-30", periods=weeks, freq="W-FRI"):
                prices.append(dict(symbol=symbol, date=date, open=100, high=102, low=99, close=101, volume=100))
        registry = pd.DataFrame(rows)
        registry.to_csv(root / "stock_universe_candidates.csv", index=False)
        pd.DataFrame([dict(symbol=s, fetched_at_utc="2026-10-30T00:00:00Z",
                           market_cap_source_url="https://example.test/cap", market_cap_asof="",
                           market_cap_asof_basis="not_provided_by_yahoo") for s in registry.symbol]).to_csv(
                               root / "yahoo_large_cap_candidate_review.csv", index=False)
        for name in ["stock_candidate_coverage_report", "provisional_candidate_stage_report", "candidate_review_queue"]:
            registry[["symbol"]].to_csv(root / (name + ".csv"), index=False)
        pd.DataFrame(prices).to_csv(root / "candidate_daily_prices.csv", index=False)
        bench = pd.DataFrame([dict(symbol=s, date=d, open=100, high=102, low=99, close=101, volume=100)
                              for s in ["SPY", "XLK"] for d in pd.date_range(end="2026-10-30", periods=35, freq="W-FRI")])
        bench.to_csv(root / "daily_prices.csv", index=False)
        pd.DataFrame([dict(symbol="SPY")]).to_csv(root / "monitoring_universe.csv", index=False)
        for name in ["candidate_daily_prices_status", "daily_prices_status", "candidate_collection_status"]:
            (root / (name + ".json")).write_text(json.dumps({"updated_at_utc": "2026-10-31T00:00:00Z"}))

    def test_week_thresholds_provenance_and_pending_are_separate_and_inputs_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}
            result = build_audit(root, "2026-11-04")
            c = result["counts"]
            self.assertEqual((c["weeks30"], c["weeks34"], c["weeks35"]), (3, 2, 1))
            self.assertEqual((c["ma30_finite"], c["slope4_finite"]), (3, 2))
            self.assertEqual((c["cap_screen_pass"], c["cap_verified"], c["active"]), (3, 0, 0))
            self.assertEqual(result["yahoo_review_provenance"]["fetched_at_valid"], 3)
            self.assertEqual(result["yahoo_review_provenance"]["cap_asof_present"], 0)
            self.assertEqual(c["daily150"], 0)
            self.assertEqual(result["actual_bridge"], {"added": 0, "errors": 0})
            self.assertEqual(sum(result["disjoint_missing_signatures"].values()), 3)
            self.assertEqual(sum(result["disjoint_first_missing"].values()), 3)
            self.assertEqual(result["intersections"]["cap_screen_pass & weeks30 & mapping_fields_present"], 3)
            self.assertEqual(before, {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()})

    def test_duplicate_registry_and_saved_report_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            saved = root / "candidate_review_queue.csv"
            pd.DataFrame({"symbol": ["THIRTY"]}).to_csv(saved, index=False)
            with self.assertRaisesRegex(ValueError, "membership mismatch"):
                build_audit(root, "2026-11-04")
            registry = root / "stock_universe_candidates.csv"
            frame = pd.read_csv(registry)
            pd.concat([frame, frame.iloc[:1]]).to_csv(registry, index=False)
            with self.assertRaisesRegex(ValueError, "unique non-empty"):
                build_audit(root, "2026-11-04")

    def test_invalid_price_is_not_counted_as_weekly_availability(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            path = root / "candidate_daily_prices.csv"
            frame = pd.read_csv(path)
            frame["close"] = frame["close"].astype(float)
            frame.loc[frame.symbol.eq("THIRTYFIVE"), "close"] = float("inf")
            frame.to_csv(path, index=False)
            result = build_audit(root, "2026-11-04")
            self.assertEqual(result["counts"]["price_quality_pass"], 2)
            self.assertEqual(result["counts"]["weeks35"], 0)

    def test_duplicate_summary_symbols_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            summarize([{"symbol": "A"}, {"symbol": "A"}])
