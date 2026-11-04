import unittest
import pandas as pd

from intake_large_cap_review_candidates import build_review_only_candidates


CANDIDATE_COLUMNS = [
    "symbol", "name", "market", "sector", "asset_type", "market_benchmark",
    "sector_benchmark", "exchange", "country", "currency", "instrument_type",
    "identity_status", "market_cap_status", "provider_status", "activation_status",
    "review_note", "identity_evidence_url", "identity_reviewed_at",
    "market_cap_source_url", "market_cap_asof", "depositary_ratio_status",
    "market_cap_usd_b_secondary", "discovery_market_cap_usd", "discovery_market_cap_native",
    "discovery_market_cap_currency", "discovery_source", "discovered_at",
    "discovery_cap_threshold_pass", "discovery_security_type", "discovery_review_reason",
    "discovery_industry_code", "discovery_dr_country_code", "proposed_market",
    "proposed_sector", "proposed_asset_type", "proposed_market_benchmark",
    "proposed_sector_benchmark", "mapping_status", "mapping_note",
]


class LargeCapReviewIntakeTests(unittest.TestCase):
    def test_adds_only_bounded_ordinary_equity_rows_and_never_activates(self):
        candidates = pd.DataFrame([{"symbol": "EXISTING", "exchange": "NAS"}], columns=CANDIDATE_COLUMNS)
        active = pd.DataFrame([{"symbol": "ACTIVE", "exchange": "NAS"}])
        queue = pd.DataFrame([
            {"symbol": "AAA", "name": "Alpha Corp", "exchange": "NAS",
             "instrument_type": "equity_candidate_unverified", "identity_status": "review_required",
             "market_cap_status": "not_verified", "activation_status": "pending_review",
             "discovery_market_cap_usd_b_secondary": 10.0, "market_cap_source_url": "https://finance.yahoo.com/quote/AAA/"},
            {"symbol": "BBB", "name": "Possible ADR SPON ADS", "exchange": "NYS",
             "instrument_type": "possible_adr_or_equity_review", "identity_status": "possible_adr_review_required",
             "market_cap_status": "not_verified", "activation_status": "pending_review",
             "discovery_market_cap_usd_b_secondary": 100.0},
            {"symbol": "EXISTING", "name": "Existing Corp", "exchange": "NAS",
             "instrument_type": "equity_candidate_unverified", "identity_status": "review_required",
             "market_cap_status": "not_verified", "activation_status": "pending_review",
             "discovery_market_cap_usd_b_secondary": 50.0},
            {"symbol": "ACTIVE", "name": "Active Corp", "exchange": "NAS",
             "instrument_type": "equity_candidate_unverified", "identity_status": "review_required",
             "market_cap_status": "not_verified", "activation_status": "pending_review",
             "discovery_market_cap_usd_b_secondary": 40.0},
            {"symbol": "ETF1", "name": "ETF", "exchange": "NAS",
             "instrument_type": "etf_candidate", "identity_status": "review_required",
             "market_cap_status": "not_verified", "activation_status": "pending_review",
             "discovery_market_cap_usd_b_secondary": 30.0},
        ])
        result, status = build_review_only_candidates(
            candidates, active, queue, discovered_at="2026-10-27", max_add=1, max_total=10
        )
        self.assertEqual(result["symbol"].tolist(), ["EXISTING", "AAA"])
        row = result[result["symbol"] == "AAA"].iloc[0]
        self.assertEqual(row["activation_status"], "pending_review")
        self.assertEqual(row["identity_status"], "review_required")
        self.assertEqual(row["market_cap_status"], "not_verified")
        self.assertEqual(row["market_cap_usd_b_secondary"], "10.0")
        self.assertEqual(row["discovery_cap_threshold_pass"], "secondary_estimate_ge_1b_review_only")
        self.assertEqual(status["large_cap_review_candidates_added"], 1)

    def test_respects_total_candidate_limit(self):
        candidates = pd.DataFrame([{"symbol": f"S{i}"} for i in range(5)], columns=CANDIDATE_COLUMNS)
        queue = pd.DataFrame([{
            "symbol": "NEW", "name": "New Corp", "exchange": "NAS",
            "instrument_type": "equity_candidate_unverified", "identity_status": "review_required",
            "market_cap_status": "not_verified", "activation_status": "pending_review",
            "discovery_market_cap_usd_b_secondary": 2.0,
        }])
        result, status = build_review_only_candidates(
            candidates, pd.DataFrame(columns=["symbol"]), queue,
            discovered_at="2026-10-27", max_add=25, max_total=5
        )
        self.assertEqual(len(result), 5)
        self.assertEqual(status["large_cap_review_candidates_added"], 0)


if __name__ == "__main__":
    unittest.main()


def test_intake_uses_listing_identity_and_preserves_existing_rows():
    original = pd.DataFrame([
        {"symbol": "SAME", "exchange": "KRX"},
        {"symbol": "DUAL", "exchange": "NAS"},
        {"symbol": "DUAL", "exchange": "NYS"},
    ], columns=CANDIDATE_COLUMNS).fillna("")
    active = pd.DataFrame([{"symbol": "LIVE", "exchange": "NYS"}])
    def row(symbol, exchange, cap=2):
        return dict(symbol=symbol, exchange=exchange,
                    instrument_type="equity_candidate_unverified", identity_status="review_required",
                    market_cap_status="not_verified", activation_status="pending_review",
                    discovery_market_cap_usd_b_secondary=cap)
    queue = pd.DataFrame([
        row("SAME", "NAS", 10), row(" same ", " nas ", 9),
        row("LIVE", "NYS", 8), row("LIVE", "NAS", 7),
        row("BAD", "OTC", 100), row("", "NAS", 100),
        row("NEXT", "AMS", 6), row("DUAL", "NAS", 5),
    ])
    result, status = build_review_only_candidates(original, active, queue, "2026-11-05", max_add=2)
    pd.testing.assert_frame_equal(result.iloc[:3].reset_index(drop=True), original)
    assert list(zip(result.iloc[3:].symbol, result.iloc[3:].exchange)) == [("SAME", "NAS"), ("LIVE", "NAS")]
    assert status["large_cap_review_candidates_added"] == 2
    assert status["large_cap_review_candidates_remaining_after_batch"] == 1
    second, status = build_review_only_candidates(result, active, queue, "2026-11-06", max_add=250, max_total=6)
    assert len(second) == 6
    assert second.iloc[-1].symbol == "NEXT"
    assert status["large_cap_review_candidates_added"] == 1
    assert second.iloc[3:].activation_status.eq("pending_review").all()


def test_duplicate_queue_rows_do_not_consume_batch_slots():
    queue = pd.DataFrame([dict(symbol=s, exchange="NAS", instrument_type="equity_candidate_unverified",
        identity_status="review_required", market_cap_status="not_verified", activation_status="pending_review",
        discovery_market_cap_usd_b_secondary=c) for s,c in [("A",10),("A",9),("B",8)]])
    result, status = build_review_only_candidates(pd.DataFrame(columns=CANDIDATE_COLUMNS), pd.DataFrame(), queue, "2026-11-05", max_add=2)
    assert result.symbol.tolist() == ["A", "B"]
    assert status["large_cap_review_candidates_added"] == 2
    assert status["large_cap_review_candidates_remaining_after_batch"] == 0


def test_queue_freshness_boundary(tmp_path):
    import json
    from datetime import datetime, timezone, timedelta
    from unittest.mock import patch
    import intake_large_cap_review_candidates as intake
    now = datetime(2026, 11, 5, tzinfo=timezone.utc)
    path = tmp_path / "status.json"
    with patch.object(intake, "datetime") as clock:
        clock.now.return_value = now
        clock.fromisoformat.side_effect = datetime.fromisoformat
        for hours, expected in [(72, True), (72.01, False), (-1.01, False)]:
            path.write_text(json.dumps(dict(updated_at_utc=(now-timedelta(hours=hours)).isoformat(), market_cap_status="secondary_estimates_only_not_verified")))
            assert intake._queue_is_fresh(path)[0] is expected
        path.write_text(json.dumps(dict(updated_at_utc=now.isoformat(), market_cap_status="verified")))
        assert intake._queue_is_fresh(path)[0] is False


def test_default_batch_and_total_limits():
    queue = pd.DataFrame([dict(symbol=f"NEW{i}", exchange="NAS", instrument_type="equity_candidate_unverified",
        identity_status="review_required", market_cap_status="not_verified", activation_status="pending_review",
        discovery_market_cap_usd_b_secondary=2) for i in range(300)])
    original = pd.DataFrame([dict(symbol=f"OLD{i}", exchange="NYS") for i in range(2177)], columns=CANDIDATE_COLUMNS).fillna("")
    first, status = build_review_only_candidates(original, pd.DataFrame(), queue, "2026-11-05")
    assert len(first) == 2427 and status["large_cap_review_candidates_added"] == 250
    full = pd.concat([first, pd.DataFrame([dict(symbol=f"EXTRA{i}", exchange="NYS") for i in range(50)], columns=CANDIDATE_COLUMNS).fillna("")], ignore_index=True)
    second, status = build_review_only_candidates(full, pd.DataFrame(), queue, "2026-11-06")
    assert len(second) == 2500 and status["large_cap_review_candidates_added"] == 23
