"""Exercise persisted rotation, checkpoints and failures without live API calls."""
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

import refresh_candidate_prices as refresh
import candidate_refresh_state as state


def bars(symbol, close=101):
    return pd.DataFrame([dict(date="2026-10-27", symbol=symbol, open=100,
                              high=102, low=99, close=close, volume=1000)])


class RotationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = {name: self.root / (name + ".csv") for name in ("CANDIDATES", "UNIVERSE", "PRICES")}
        self.paths["STATUS"] = self.root / "status.json"
        self.runs = 0
        pd.DataFrame(columns=["symbol"]).to_csv(self.paths["UNIVERSE"], index=False)

    def candidates(self, symbols):
        pd.DataFrame([dict(symbol=s, exchange="NAS", market="United States", asset_type="stock",
                           activation_status="pending_review") for s in symbols]).to_csv(self.paths["CANDIDATES"], index=False)

    def run_batch(self, limit, responses=None, interrupt_after=None):
        self.runs += 1
        called = []
        now = datetime(2026, 10, 28, tzinfo=timezone.utc) + timedelta(minutes=self.runs)
        def fetch(row, *args, **kwargs):
            if interrupt_after is not None and len(called) == interrupt_after:
                raise KeyboardInterrupt()
            called.append(row.symbol)
            result = (responses or {}).get(row.symbol, bars(row.symbol))
            if isinstance(result, Exception):
                raise result
            return result.copy(), row.exchange
        with ExitStack() as stack:
            for name, path in self.paths.items():
                stack.enter_context(patch.object(refresh, name, path))
            stack.enter_context(patch.dict("os.environ", KIS_APP_KEY="test", KIS_APP_SECRET="test",
                                           CANDIDATE_REFRESH_BUDGET_SECONDS="1"))
            stack.enter_context(patch.object(refresh.time, "monotonic", side_effect=[0] + [0] * limit + [2]))
            stack.enter_context(patch.object(refresh.time, "sleep"))
            stack.enter_context(patch.object(refresh, "fetch_candidate_daily", side_effect=fetch))
            stack.enter_context(patch.object(refresh, "KISOverseasPrices"))
            stack.enter_context(patch.object(refresh, "KISDomesticPrices"))
            clock = stack.enter_context(patch.object(refresh, "datetime"))
            clock.now.side_effect = lambda *args: now + timedelta(seconds=clock.now.call_count)
            stack.enter_context(patch("builtins.print"))
            if interrupt_after is not None:
                with self.assertRaises(KeyboardInterrupt):
                    refresh.main()
            else:
                self.assertEqual(refresh.main(), 0)
        return called, json.loads(self.paths["STATUS"].read_text())

    def test_1426_candidates_rotate_in_350_symbol_batches_despite_repeated_failure(self):
        symbols = [f"S{i:04}" for i in range(1426)]
        self.candidates(symbols)
        batches = []
        for i in range(5):
            called, status = self.run_batch(350, {symbols[0]: RuntimeError("server timeout")})
            batches.append(called)
            self.assertEqual(status["attempted_symbol_count"], 350)
            self.assertEqual(status["deferred_symbol_count"], 1076)
            self.assertEqual(status["failed_symbol_count"], int(symbols[0] in called))
            self.assertEqual(status["error_count"], status["failed_symbol_count"])
            self.assertFalse(status["refresh_complete"])
            self.assertLess(status["started_at_utc"], status["finished_at_utc"])
        self.assertEqual(len(set(sum(batches[:4], []))), 1400)
        self.assertEqual(len(set(sum(batches, []))), 1426)
        self.assertEqual(batches[4][:26], symbols[1400:])
        self.assertEqual(status["missing_symbols"], [symbols[0]])
        self.assertEqual(status["symbols_with_data"], 1425)

    def test_missing_history_is_prioritized_once_then_failure_yields_to_pending(self):
        self.candidates(["RECENT", "DEFERRED", "MISSING"])
        pd.concat([bars("RECENT"), bars("DEFERRED")]).to_csv(self.paths["PRICES"], index=False)
        self.paths["STATUS"].write_text(json.dumps({"deferred_symbols": ["DEFERRED"]}))
        first, _ = self.run_batch(1, {"MISSING": RuntimeError("timeout")})
        second, _ = self.run_batch(1, {"MISSING": RuntimeError("timeout")})
        third, _ = self.run_batch(1)
        self.assertEqual([first, second, third], [["MISSING"], ["DEFERRED"], ["RECENT"]])

    def test_legacy_errors_only_resume_and_new_removed_candidates(self):
        self.candidates(["RECENT", "TAIL"])
        pd.concat([bars("RECENT"), bars("TAIL")]).to_csv(self.paths["PRICES"], index=False)
        self.paths["STATUS"].write_text(json.dumps({"errors": [
            {"symbol": "TAIL", "error": "refresh_deferred_time_budget"},
            {"symbol": "REMOVED", "error": "refresh_deferred_time_budget"}]}))
        called, _ = self.run_batch(1)
        self.assertEqual(called, ["TAIL"])
        self.candidates(["RECENT", "NEW"])
        called, status = self.run_batch(1)
        self.assertEqual(called, ["NEW"])
        self.assertNotIn("TAIL", status["collection_state"])
        self.assertIn("TAIL", set(pd.read_csv(self.paths["PRICES"]).symbol))

    def test_unsupported_route_cooldown_and_route_change_retries(self):
        self.candidates(["BAD", "GOOD"])
        _, first = self.run_batch(2, {"BAD": ValueError("Unsupported KIS overseas exchange code.")})
        self.assertEqual(first["errors"][0]["category"], "unsupported_symbol")
        called, status = self.run_batch(2)
        self.assertEqual(called, ["GOOD"])
        self.assertEqual(status["skipped_symbols"], ["BAD"])
        self.assertFalse(status["refresh_complete"])
        candidates = pd.read_csv(self.paths["CANDIDATES"])
        candidates.loc[candidates.symbol.eq("BAD"), "exchange"] = "NYS"
        candidates.to_csv(self.paths["CANDIDATES"], index=False)
        called, status = self.run_batch(2)
        self.assertIn("BAD", called)
        self.assertTrue(status["refresh_complete"])

    def test_checkpoint_survives_interrupt_and_actions_fallback_keeps_pending_queue(self):
        symbols = [f"S{i:02}" for i in range(30)]
        self.candidates(symbols)
        _, checkpoint = self.run_batch(30, interrupt_after=26)
        self.assertEqual(checkpoint["collection_phase"], "in_progress")
        self.assertIsNone(checkpoint["finished_at_utc"])
        self.assertEqual(checkpoint["pending_symbols"], symbols[25:])
        self.assertEqual(len(pd.read_csv(self.paths["PRICES"])), 25)
        original = self.paths["PRICES"].read_bytes()
        state.record_refresh_failure(self.paths["PRICES"], self.paths["STATUS"])
        failed = json.loads(self.paths["STATUS"].read_text())
        self.assertEqual(failed["collection_state"], checkpoint["collection_state"])
        self.assertEqual(failed["pending_symbols"], symbols[25:])
        self.assertEqual(self.paths["PRICES"].read_bytes(), original)
        called, _ = self.run_batch(1)
        self.assertEqual(called, [symbols[25]])

    def test_malformed_metadata_does_not_discard_history(self):
        self.candidates(["AAPL"])
        bars("AAPL").to_csv(self.paths["PRICES"], index=False)
        self.paths["STATUS"].write_text("{bad json")
        _, status = self.run_batch(1, {"AAPL": RuntimeError("timeout")})
        self.assertEqual(status["symbols_with_data"], 1)
        self.assertEqual(status["preserved_symbol_count"], 1)

    def test_invalid_prices_and_wrong_symbol_never_overwrite_valid_history(self):
        self.candidates(["AAPL"])
        for invalid in [bars("AAPL", close=-1), bars("MSFT"), bars("AAPL", close=float("inf")),
                        bars("AAPL").drop(columns="volume")]:
            with self.subTest(columns=invalid.columns.tolist()):
                bars("AAPL").to_csv(self.paths["PRICES"], index=False)
                _, status = self.run_batch(1, {"AAPL": invalid})
                self.assertEqual(status["failed_symbol_count"], 1)
                self.assertEqual(status["errors"][0]["category"], "validation_error")
                self.assertEqual(pd.read_csv(self.paths["PRICES"]).close.tolist(), [101])


class SnapshotPublicationTests(unittest.TestCase):
    def test_staging_or_rename_failure_restores_both_previous_files(self):
        for failure in ["serialization", "csv_write", "price_replace", "status_replace"]:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                prices_path, status_path = Path(tmp) / "prices.csv", Path(tmp) / "status.json"
                bars("OLD").to_csv(prices_path, index=False)
                status_path.write_text('{"previous":true}')
                old = [p.read_bytes() for p in [prices_path, status_path]]
                status = {"symbols_with_data": 1, "per_symbol_coverage": [{"symbol": "NEW", "rows": 1}]}
                replace = state.os.replace
                def fail_replace(source, destination):
                    if str(source).endswith(".tmp") and destination == (
                        status_path if failure == "status_replace" else prices_path
                    ):
                        raise OSError("simulated disk failure")
                    return replace(source, destination)
                if failure == "serialization":
                    status["invalid"] = object()
                with ExitStack() as stack:
                    if failure.endswith("replace"):
                        stack.enter_context(patch.object(state.os, "replace", side_effect=fail_replace))
                    if failure == "csv_write":
                        stack.enter_context(patch.object(pd.DataFrame, "to_csv", side_effect=OSError("disk full")))
                    with self.assertRaises((OSError, TypeError)):
                        state.publish_snapshot(bars("NEW"), status, prices_path, status_path)
                self.assertEqual([p.read_bytes() for p in [prices_path, status_path]], old)
                self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["prices.csv", "status.json"])

    def test_mismatched_hash_or_coverage_is_rejected_without_losing_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            prices_path, status_path = Path(tmp) / "prices.csv", Path(tmp) / "status.json"
            bars("OLD").to_csv(prices_path, index=False)
            status_path.write_text(json.dumps({"snapshot_sha256": "bad"}))
            original = prices_path.read_bytes()
            self.assertEqual(state.read_collection_status(status_path, prices_path), {})
            with self.assertRaises(ValueError):
                state.publish_snapshot(bars("NEW"), {"symbols_with_data": 1, "per_symbol_coverage": []}, prices_path, status_path)
            self.assertEqual(prices_path.read_bytes(), original)

    def test_failure_categories_are_distinct(self):
        for exc, expected in [
            (RuntimeError("HTTP 429"), "rate_limited"),
            (RuntimeError("EGW00201"), "rate_limited"),
            (RuntimeError("KIS token request failed (HTTP 403)"), "authentication_failed"),
            (ValueError("Unsupported KIS overseas exchange code"), "unsupported_symbol"),
            (RuntimeError("HTTP 503"), "temporary_server_error"),
            (TimeoutError("timeout"), "temporary_server_error"),
            (ValueError("bad OHLCV"), "validation_error"),
        ]:
            with self.subTest(exception=str(exc)):
                self.assertEqual(state.classify_failure(exc), expected)

    def test_bad_optional_metadata_shapes_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            prices_path, status_path = Path(tmp) / "prices.csv", Path(tmp) / "status.json"
            bars("OLD").to_csv(prices_path, index=False)
            for value in [[], {"deferred_symbols": None}, {"errors": ["bad"]},
                          {"collection_state": {"OLD": {"last_attempt_at_utc": []}}}]:
                status_path.write_text(json.dumps(value))
                self.assertEqual(state.read_collection_status(status_path, prices_path), {})

    def test_expired_unsupported_cooldown_retries(self):
        now = datetime(2026, 10, 30, tzinfo=timezone.utc)
        candidates = pd.DataFrame([dict(symbol="OLD", exchange="NAS", asset_type="stock")])
        previous = state.validate_prices(bars("OLD"))
        plan, _, skipped = state.collection_plan(candidates, previous, {"collection_state": {
            "OLD": {"route": "NAS:stock", "last_attempt_at_utc": "2026-09-29T00:00:00+00:00",
                    "retry_after_utc": "2026-10-29T00:00:00+00:00"}}}, now)
        self.assertEqual(plan.symbol.tolist(), ["OLD"])
        self.assertEqual(skipped, [])
