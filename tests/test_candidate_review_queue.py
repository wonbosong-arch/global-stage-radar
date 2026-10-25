import pandas as pd

from candidate_coverage_audit import build_candidate_coverage_report
from candidate_identity_evidence_audit import build_report as build_identity_evidence_report
from candidate_market_cap_reconciliation import build_report as build_market_cap_reconciliation_report
from candidate_review_queue import (
    assess_report_freshness,
    build_manual_review_worksheet,
    build_queue_summary,
    build_review_queue,
)


def test_queue_prioritizes_adr_identity_and_market_cap_risks_without_activation():
    coverage = pd.DataFrame([
        {"symbol": "TSM", "identity_status": "issuer_proxy_review_required", "provider_status": "not_checked", "market_cap_status": "not_verified"},
        {"symbol": "CRM", "identity_status": "review_required", "provider_status": "not_checked", "market_cap_status": "not_verified"},
        {"symbol": "AMGN", "identity_status": "review_required", "provider_status": "not_checked", "market_cap_status": "not_verified"},
        {"symbol": "ADBE", "identity_status": "review_required", "provider_status": "not_checked", "market_cap_status": "not_verified"},
    ])
    identity = pd.DataFrame([
        {"symbol": s, "identity_marked_verified": False, "provider_marked_checked": False}
        for s in ["TSM", "CRM", "AMGN", "ADBE"]
    ])
    market_cap = pd.DataFrame([
        {"symbol": "TSM", "date_review_priority": "P1_material_mismatch"},
        {"symbol": "CRM", "date_review_priority": "P1_material_mismatch"},
        {"symbol": "AMGN", "date_review_priority": "P1_stale_share_count"},
        {"symbol": "ADBE", "date_review_priority": "P3_routine_evidence"},
    ])

    result = build_review_queue(coverage, identity, market_cap).set_index("symbol")

    assert result.loc["TSM", "queue_priority"] == "P1_identity_classification"
    assert result.loc["CRM", "queue_priority"] == "P2_identity_evidence"
    assert result.loc["AMGN", "queue_priority"] == "P2_identity_evidence"
    assert result.loc["ADBE", "queue_priority"] == "P2_identity_evidence"
    assert set(result["activation_recommendation"]) == {"keep_pending_review"}
    assert result["queue_is_not_verification"].all()
    assert result["review_plan_is_not_approval"].all()
    assert result.loc["TSM", "review_batch"] == "1단계: 발행사/ADR 분류"
    assert result["review_sequence"].is_unique


def test_queue_summary_counts_each_category_and_gate():
    report = pd.DataFrame([
        {"symbol": "AAA", "queue_priority": "P1", "activation_gate_status": "blocked", "activation_recommendation": "keep_pending_review"},
        {"symbol": "BBB", "queue_priority": "P1", "activation_gate_status": "blocked", "activation_recommendation": "keep_pending_review"},
        {"symbol": "CCC", "queue_priority": "P2", "activation_gate_status": "blocked", "activation_recommendation": "keep_pending_review"},
    ])

    summary = build_queue_summary(report)
    counts = {(row.summary_type, row.category): row.candidate_count for row in summary.itertuples(index=False)}

    assert counts[("queue_priority", "P1")] == 2
    assert counts[("queue_priority", "P2")] == 1
    assert counts[("activation_gate_status", "blocked")] == 3
    assert counts[("activation_recommendation", "keep_pending_review")] == 3


def test_manual_worksheet_preserves_evidence_and_never_approves_candidates():
    queue = pd.DataFrame([
        {
            "symbol": "TSM",
            "next_action_ko": "ADR 비율 확인",
            "identity_evidence_url": "https://example.com/identity",
            "market_cap_source_url": "https://example.com/cap",
            "activation_recommendation": "keep_pending_review",
            "manual_activation_decision": "approved",
            "remaining_action": None,
        }
    ])
    worksheet = build_manual_review_worksheet(queue)

    row = worksheet.iloc[0]
    assert row["identity_evidence_url"] == "https://example.com/identity"
    assert row["market_cap_source_url"] == "https://example.com/cap"
    assert row["remaining_action"] == "ADR 비율 확인"
    assert row["manual_activation_decision"] == "keep_pending_review"
    assert row["benchmark_mapping_review_result"] == "not_reviewed"
    assert row["identity_review_result"] == "not_reviewed"
    assert row["market_cap_review_result"] == "not_reviewed"
    assert row["kis_support_review_result"] == "not_verified"
    assert row["manual_activation_decision"] == "keep_pending_review"
    assert bool(row["worksheet_is_not_activation"]) is True


def test_queue_surfaces_missing_report_rows_as_top_priority():
    coverage = pd.DataFrame([{"symbol": "AAA", "identity_status": "review_required"}])
    identity = pd.DataFrame(columns=["symbol", "identity_status"])
    market_cap = pd.DataFrame([{"symbol": "AAA", "date_review_priority": "P3_routine_evidence"}])

    result = build_review_queue(coverage, identity, market_cap)
    row = result.iloc[0]

    assert row["queue_priority"] == "P1_report_reconciliation"
    assert not bool(row["identity_report_row_present"])
    assert bool(row["market_cap_report_row_present"])
    assert not bool(row["all_review_reports_present"])
    assert row["activation_recommendation"] == "keep_pending_review"


def test_queue_rejects_duplicate_symbol_rows_in_source_reports():
    coverage = pd.DataFrame([
        {"symbol": "AAA", "identity_status": "review_required"},
        {"symbol": "AAA", "identity_status": "review_required"},
    ])
    identity = pd.DataFrame(columns=["symbol"])
    market_cap = pd.DataFrame(columns=["symbol"])

    try:
        build_review_queue(coverage, identity, market_cap)
    except ValueError as exc:
        assert "duplicate symbols" in str(exc)
    else:
        raise AssertionError("duplicate symbols should be rejected")


def test_queue_summary_reports_missing_source_reports_and_next_actions():
    report = pd.DataFrame([
        {
            "symbol": "AAA",
            "queue_priority": "P1_report_reconciliation",
            "activation_gate_status": "blocked",
            "activation_recommendation": "keep_pending_review",
            "identity_report_row_present": False,
            "market_cap_report_row_present": True,
            "all_review_reports_present": False,
            "next_action_ko": "식별 보고서 복구",
        },
        {
            "symbol": "BBB",
            "queue_priority": "P2_identity_evidence",
            "activation_gate_status": "blocked",
            "activation_recommendation": "keep_pending_review",
            "identity_report_row_present": True,
            "market_cap_report_row_present": True,
            "all_review_reports_present": True,
            "next_action_ko": "공식 상장 근거 확인",
        },
    ])
    summary = build_queue_summary(report)
    counts = {(row.summary_type, row.category): row.candidate_count for row in summary.itertuples(index=False)}

    assert counts[("report_presence", "identity_report_missing")] == 1
    assert counts[("report_presence", "all_reports_present")] == 1
    assert counts[("next_action", "식별 보고서 복구")] == 1
    assert counts[("activation_recommendation", "keep_pending_review")] == 2


def test_queue_summary_handles_empty_input():
    summary = build_queue_summary(pd.DataFrame(columns=["symbol", "queue_priority"]))
    assert list(summary.columns) == ["summary_type", "category", "candidate_count"]
    assert summary.empty


def test_queue_summary_parses_string_boolean_flags():
    report = pd.DataFrame([
        {
            "symbol": "AAA",
            "queue_priority": "P1_report_reconciliation",
            "identity_report_row_present": "False",
            "market_cap_report_row_present": "True",
            "all_review_reports_present": "False",
        }
    ])
    summary = build_queue_summary(report)
    counts = {(row.summary_type, row.category): row.candidate_count for row in summary.itertuples(index=False)}
    assert counts[("report_presence", "identity_report_missing")] == 1
    assert counts[("report_presence", "market_cap_report_present")] == 1
    assert counts[("report_presence", "all_reports_missing")] == 1


def test_present_report_rows_with_blank_status_fields_are_not_marked_missing():
    coverage = pd.DataFrame([{"symbol": "AAA", "identity_status": "review_required"}])
    identity = pd.DataFrame([{"symbol": "AAA", "identity_status": ""}])
    market_cap = pd.DataFrame([{"symbol": "AAA", "date_review_priority": ""}])

    result = build_review_queue(coverage, identity, market_cap)
    row = result.iloc[0]

    assert bool(row["identity_report_row_present"])
    assert bool(row["market_cap_report_row_present"])
    assert bool(row["all_review_reports_present"])
    assert row["activation_recommendation"] == "keep_pending_review"


def test_queue_rejects_blank_symbol_rows():
    coverage = pd.DataFrame([{"symbol": "   ", "identity_status": "review_required"}])
    identity = pd.DataFrame(columns=["symbol"])
    market_cap = pd.DataFrame(columns=["symbol"])

    try:
        build_review_queue(coverage, identity, market_cap)
    except ValueError as exc:
        assert "blank symbols" in str(exc)
    else:
        raise AssertionError("blank symbols should be rejected")



def test_build_review_queue_does_not_mutate_source_frames():
    coverage = pd.DataFrame([{"symbol": " aaa ", "identity_status": "review_required"}])
    identity = pd.DataFrame([{"symbol": "AAA", "identity_marked_verified": False}])
    market_cap = pd.DataFrame([{"symbol": "AAA", "date_review_priority": "P3_routine_evidence"}])
    original_coverage = coverage.copy(deep=True)
    original_identity = identity.copy(deep=True)
    original_market_cap = market_cap.copy(deep=True)

    result = build_review_queue(coverage, identity, market_cap)

    pd.testing.assert_frame_equal(coverage, original_coverage)
    pd.testing.assert_frame_equal(identity, original_identity)
    pd.testing.assert_frame_equal(market_cap, original_market_cap)
    assert result.loc[0, "symbol"] == "AAA"
    assert result.loc[0, "activation_recommendation"] == "keep_pending_review"


def test_build_review_queue_handles_empty_coverage_report():
    coverage = pd.DataFrame(columns=["symbol", "identity_status"])
    identity = pd.DataFrame(columns=["symbol", "identity_status"])
    market_cap = pd.DataFrame(columns=["symbol", "date_review_priority"])

    result = build_review_queue(coverage, identity, market_cap)

    assert result.empty
    assert "queue_priority" in result.columns
    assert "next_action_ko" in result.columns
    assert "activation_recommendation" in result.columns
    assert "review_sequence" in result.columns


def test_candidate_coverage_audit_rejects_duplicate_and_blank_symbols():
    active = pd.DataFrame([{"symbol": "SPY"}])
    prices = pd.DataFrame([{"symbol": "SPY", "date": "2026-10-23"}])
    duplicate_candidates = pd.DataFrame([
        {"symbol": " aaa ", "market_benchmark": "SPY", "sector_benchmark": "SPY"},
        {"symbol": "AAA", "market_benchmark": "SPY", "sector_benchmark": "SPY"},
    ])
    blank_candidates = pd.DataFrame([
        {"symbol": " ", "market_benchmark": "SPY", "sector_benchmark": "SPY"},
    ])

    try:
        build_candidate_coverage_report(duplicate_candidates, active, prices)
    except ValueError as exc:
        assert "duplicate symbols" in str(exc)
    else:
        raise AssertionError("duplicate candidate symbols should be rejected")

    try:
        build_candidate_coverage_report(blank_candidates, active, prices)
    except ValueError as exc:
        assert "blank symbols" in str(exc)
    else:
        raise AssertionError("blank candidate symbols should be rejected")



def test_identity_evidence_audit_rejects_blank_and_duplicate_symbols():
    duplicate = pd.DataFrame([{"symbol": " aaa "}, {"symbol": "AAA"}])
    blank = pd.DataFrame([{"symbol": "  "}])

    for candidates, expected in [(duplicate, "duplicate symbols"), (blank, "blank symbols")]:
        try:
            build_identity_evidence_report(candidates)
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"{expected} should be rejected")



def test_market_cap_reconciliation_rejects_blank_and_normalized_duplicate_candidate_symbols():
    prices = pd.DataFrame([{"symbol": "AAA", "date": "2026-10-23", "close": 10}])
    duplicate = pd.DataFrame([
        {"symbol": " aaa ", "market_cap_usd_b_secondary": "10"},
        {"symbol": "AAA", "market_cap_usd_b_secondary": "10"},
    ])
    blank = pd.DataFrame([{"symbol": "  "}])

    for candidates, expected in [(duplicate, "duplicate symbols"), (blank, "blank symbols")]:
        try:
            build_market_cap_reconciliation_report(candidates, prices)
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"{expected} should be rejected")


def test_market_cap_reconciliation_normalizes_price_symbols_without_mutating_inputs():
    candidates = pd.DataFrame([
        {"symbol": " aaa ", "market_cap_usd_b_secondary": "10", "market_cap_asof": "2026-10-23",
         "market_cap_status": "not_verified", "market_cap_source_url": "https://example.com/cap",
         "instrument_type": "common_stock"}
    ])
    prices = pd.DataFrame([{"symbol": " aaa ", "date": "2026-10-23", "close": 10}])
    original_candidates = candidates.copy(deep=True)
    original_prices = prices.copy(deep=True)

    report = build_market_cap_reconciliation_report(candidates, prices)

    pd.testing.assert_frame_equal(candidates, original_candidates)
    pd.testing.assert_frame_equal(prices, original_prices)
    assert report.iloc[0]["symbol"] == "AAA"
    assert report.iloc[0]["price_date"] == "2026-10-23"
    assert report.iloc[0]["close_usd"] == 10
    assert report.iloc[0]["market_cap_status_remains"] == "not_verified"



def test_market_cap_reconciliation_prioritizes_missing_required_inputs():
    candidates = pd.DataFrame([
        {"symbol": "UNPRICED", "market_cap_usd_b_secondary": "10", "market_cap_asof": "2026-10-23",
         "market_cap_status": "not_verified", "market_cap_source_url": "https://example.com/cap",
         "instrument_type": "common_stock"},
        {"symbol": "NOCOUNT", "market_cap_usd_b_secondary": "10", "market_cap_asof": "2026-10-23",
         "market_cap_status": "not_verified", "market_cap_source_url": "https://example.com/cap",
         "instrument_type": "common_stock"},
    ])
    prices = pd.DataFrame([{"symbol": "NOCOUNT", "date": "2026-10-23", "close": 10}])

    report = build_market_cap_reconciliation_report(candidates, prices).set_index("symbol")

    assert report.loc["UNPRICED", "date_review_priority"] == "P2_missing_reconciliation_input"
    assert report.loc["NOCOUNT", "date_review_priority"] == "P2_missing_reconciliation_input"
    assert set(report["market_cap_status_remains"]) == {"not_verified"}



def test_adr_market_cap_report_surfaces_material_mismatch_and_missing_inputs():
    candidates = pd.DataFrame([
        {"symbol": "TSM", "market_cap_usd_b_secondary": "1900", "market_cap_asof": "2026-10-23",
         "market_cap_status": "not_verified", "market_cap_source_url": "https://example.com/cap",
         "instrument_type": "adr_candidate"},
        {"symbol": "BABA", "market_cap_usd_b_secondary": "", "market_cap_asof": "2026-10-23",
         "market_cap_status": "not_verified", "market_cap_source_url": "https://example.com/cap",
         "instrument_type": "adr_candidate"},
    ])
    prices = pd.DataFrame([
        {"symbol": "TSM", "date": "2026-10-23", "close": 418.51},
        {"symbol": "BABA", "date": "2026-10-23", "close": 99.64},
    ])

    report = build_market_cap_reconciliation_report(candidates, prices).set_index("symbol")

    assert report.loc["TSM", "triage_outcome"] == "adr_share_class_and_material_mismatch_review"
    assert report.loc["TSM", "date_review_priority"] == "P1_material_mismatch"
    assert report.loc["BABA", "triage_outcome"] == "price_or_secondary_cap_missing"
    assert report.loc["BABA", "date_review_priority"] == "P2_missing_reconciliation_input"
    assert set(report["market_cap_status_remains"]) == {"not_verified"}



def test_future_share_count_date_is_not_misclassified_as_stale():
    candidates = pd.DataFrame([
        {"symbol": "COST", "market_cap_usd_b_secondary": "444.60", "market_cap_asof": "2026-08-01",
         "market_cap_status": "not_verified", "market_cap_source_url": "https://example.com/cap",
         "instrument_type": "common_stock_candidate"}
    ])
    prices = pd.DataFrame([{"symbol": "COST", "date": "2026-08-01", "close": 1003.32}])

    report = build_market_cap_reconciliation_report(candidates, prices)
    row = report.iloc[0]

    assert row["price_to_share_count_asof_gap_days"] == 59
    assert row["price_after_share_count_asof_days"] == -59
    assert row["share_count_date_alignment"] == "share_count_date_after_price_date"
    assert row["date_review_priority"] == "P3_routine_evidence"
    assert row["date_review_reason"] == "arithmetic_consistent_but_market_cap_not_verified"



def test_future_market_cap_asof_is_flagged_as_date_alignment():
    candidates = pd.DataFrame([
        {"symbol": "COST", "market_cap_usd_b_secondary": "444.60", "market_cap_asof": "2026-10-24",
         "market_cap_status": "not_verified", "market_cap_source_url": "https://example.com/cap",
         "instrument_type": "common_stock_candidate"}
    ])
    prices = pd.DataFrame([{"symbol": "COST", "date": "2026-10-23", "close": 1003.32}])

    row = build_market_cap_reconciliation_report(candidates, prices).iloc[0]

    assert row["price_to_cap_asof_gap_days"] == 1
    assert row["price_after_market_cap_asof_days"] == -1
    assert row["market_cap_date_alignment"] == "market_cap_date_after_price_date"
    assert row["date_review_priority"] == "P2_date_alignment"
    assert row["date_review_reason"] == "secondary_market_cap_asof_after_price_date"
    assert row["market_cap_status_remains"] == "not_verified"



def test_market_cap_reconciliation_handles_nonpositive_price_or_cap_as_missing_input():
    candidates = pd.DataFrame([
        {"symbol": "ZERO_CAP", "market_cap_usd_b_secondary": "0", "market_cap_asof": "2026-10-23",
         "market_cap_status": "not_verified", "market_cap_source_url": "https://example.com/cap",
         "instrument_type": "common_stock_candidate"},
        {"symbol": "NEG_CAP", "market_cap_usd_b_secondary": "-10", "market_cap_asof": "2026-10-23",
         "market_cap_status": "not_verified", "market_cap_source_url": "https://example.com/cap",
         "instrument_type": "common_stock_candidate"},
        {"symbol": "NEG_PRICE", "market_cap_usd_b_secondary": "10", "market_cap_asof": "2026-10-23",
         "market_cap_status": "not_verified", "market_cap_source_url": "https://example.com/cap",
         "instrument_type": "common_stock_candidate"},
    ])
    prices = pd.DataFrame([
        {"symbol": "ZERO_CAP", "date": "2026-10-23", "close": 10},
        {"symbol": "NEG_CAP", "date": "2026-10-23", "close": 10},
        {"symbol": "NEG_PRICE", "date": "2026-10-23", "close": -1},
    ])

    report = build_market_cap_reconciliation_report(candidates, prices).set_index("symbol")

    assert report.loc["ZERO_CAP", "triage_outcome"] == "price_or_secondary_cap_missing"
    assert report.loc["NEG_CAP", "triage_outcome"] == "price_or_secondary_cap_missing"
    assert report.loc["NEG_PRICE", "triage_outcome"] == "price_or_secondary_cap_missing"
    assert report.loc["ZERO_CAP", "date_review_priority"] == "P2_missing_reconciliation_input"
    assert report.loc["NEG_CAP", "date_review_priority"] == "P2_missing_reconciliation_input"
    assert report.loc["NEG_PRICE", "date_review_priority"] == "P2_missing_reconciliation_input"



def test_missing_or_stale_market_cap_date_precedes_arithmetic_mismatch():
    candidates = pd.DataFrame([
        {"symbol": "COST", "market_cap_usd_b_secondary": "1000", "market_cap_asof": "",
         "market_cap_status": "not_verified", "market_cap_source_url": "https://example.com/cap",
         "instrument_type": "common_stock_candidate"},
        {"symbol": "PG", "market_cap_usd_b_secondary": "1000", "market_cap_asof": "2026-08-01",
         "market_cap_status": "not_verified", "market_cap_source_url": "https://example.com/cap",
         "instrument_type": "common_stock_candidate"},
    ])
    prices = pd.DataFrame([
        {"symbol": "COST", "date": "2026-10-23", "close": 100},
        {"symbol": "PG", "date": "2026-10-23", "close": 100},
    ])

    report = build_market_cap_reconciliation_report(candidates, prices).set_index("symbol")

    assert report.loc["COST", "triage_outcome"] == "material_arithmetic_mismatch_review"
    assert report.loc["COST", "date_review_priority"] == "P2_date_alignment"
    assert report.loc["COST", "date_review_reason"] == "secondary_market_cap_asof_date_missing"
    assert report.loc["PG", "triage_outcome"] == "material_arithmetic_mismatch_review"
    assert report.loc["PG", "date_review_priority"] == "P2_date_alignment"
    assert report.loc["PG", "date_review_reason"] == "secondary_market_cap_asof_more_than_30_days_before_price"



def test_report_freshness_normalizes_timezone_offsets_to_same_instant():
    result = assess_report_freshness(
        "2026-10-25T08:00:00+09:00",
        "2026-10-24T23:00:00Z",
        now="2026-10-25T08:30:00+09:00",
    )

    assert result["queue_stamp_valid"] is True
    assert result["summary_stamp_valid"] is True
    assert result["stamps_match"] is True
    assert result["queue_timestamp_in_future"] is False
    assert result["queue_stale"] is False
    assert result["queue_age_hours"] == 0.5


def test_report_freshness_flags_materially_future_queue_timestamp():
    result = assess_report_freshness(
        "2026-10-25T09:00:00+09:00",
        "2026-10-25T00:00:00Z",
        now="2026-10-25T08:00:00+09:00",
    )

    assert result["queue_timestamp_in_future"] is True
    assert result["queue_age_hours"] == -1.0


def test_report_freshness_treats_missing_and_invalid_timestamps_as_invalid():
    for missing in (None, pd.NA, pd.NaT, "", "not-a-timestamp"):
        result = assess_report_freshness(
            missing,
            "not-a-timestamp",
            now="2026-10-25T08:00:00+09:00",
        )

        assert result["queue_stamp_valid"] is False
        assert result["summary_stamp_valid"] is False
        assert result["stamps_match"] is False
        assert result["queue_age_hours"] is None
        assert result["queue_timestamp_in_future"] is False
        assert result["queue_stale"] is False
