import unittest
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import pandas as pd

from candidate_refresh_queue_audit import audit_queue, main


class QueueAuditTests(unittest.TestCase):
    def test_pending_order_cooldown_exclusion_and_expiry_are_distinct(self):
        candidates = pd.DataFrame([dict(symbol=s, activation_status="pending_review", exchange="NAS", asset_type="stock") for s in ["OLD", "TAIL", "COOL", "ACTIVE"]])
        universe = pd.DataFrame({"symbol": ["ACTIVE"]})
        prices = pd.DataFrame({"symbol": ["OLD", "TAIL", "COOL", "ACTIVE"], "date": ["2026-10-29"] * 4})
        status = {"deferred_symbols": ["TAIL", "OLD"], "fresh_data_symbols": ["COOL"], "collection_state": {"COOL": {"route": "NAS:stock", "retry_after_utc": "2026-12-01T00:00:00Z"}}}
        before = prices.copy(deep=True)
        rows = {r["symbol"]: r for r in audit_queue(candidates, universe, prices, status, ["OLD", "TAIL", "COOL", "ACTIVE", "MISSING"], "2026-11-05", [1, 2])["candidates"]}
        self.assertEqual(rows["TAIL"]["queue_position"], 1)
        self.assertEqual(rows["OLD"]["estimated_successful_runs"], {"1": 2, "2": 1})
        self.assertEqual(rows["OLD"]["freshness_warning"], "expires_within_1_day")
        self.assertEqual(rows["COOL"]["queue_status"], "cooldown")
        self.assertTrue(rows["COOL"]["response_in_last_run"])
        self.assertEqual(rows["ACTIVE"]["queue_status"], "excluded")
        self.assertEqual(rows["MISSING"]["freshness_warning"], "missing")
        expired = audit_queue(candidates, universe, prices, status, ["OLD"], "2026-11-06")["candidates"][0]
        self.assertEqual(expired["freshness_warning"], "expired")
        pd.testing.assert_frame_equal(prices, before)

    def test_estimate_requires_positive_batch_size(self):
        with self.assertRaises(ValueError):
            audit_queue(pd.DataFrame(columns=["symbol", "activation_status"]), pd.DataFrame(columns=["symbol"]), pd.DataFrame(columns=["symbol", "date"]), {}, [], "2026-11-04", [0])

    def test_cli_reads_matching_snapshot_without_writes_and_rejects_stale_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "stock_universe_candidates.csv").write_text("symbol,activation_status,exchange,asset_type\nABC,pending_review,NAS,stock\n")
            (root / "monitoring_universe.csv").write_text("symbol\nSPY\n")
            prices = root / "candidate_daily_prices.csv"
            prices.write_bytes(b"symbol,date\nABC,2026-10-29\n")
            status = root / "candidate_daily_prices_status.json"
            status.write_text(json.dumps({"snapshot_sha256": hashlib.sha256(prices.read_bytes()).hexdigest(), "deferred_symbols": ["ABC"]}))
            cohort = root / "cohort.json"
            cohort.write_text(json.dumps({"as_of": "2026-11-04", "candidates": [{"symbol": "ABC"}]}))
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            argv = ["audit", "--data-dir", tmp, "--cohort", str(cohort), "--as-of", "2026-11-06"]
            with patch("sys.argv", argv), patch("builtins.print") as output:
                main()
                result = json.loads(output.call_args.args[0])
            self.assertEqual(result["candidates"][0]["freshness_warning"], "expired")
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
            prices.write_bytes(prices.read_bytes() + b"XYZ,2026-11-03\n")
            with patch("sys.argv", argv), self.assertRaisesRegex(ValueError, "digest mismatch"):
                main()
