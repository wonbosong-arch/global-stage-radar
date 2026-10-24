import pandas as pd

from candidate_review_queue import build_manual_review_worksheet, build_queue_summary, build_review_queue


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
    assert result.loc["CRM", "queue_priority"] == "P1_market_cap_reconciliation"
    assert result.loc["AMGN", "queue_priority"] == "P1_market_cap_reconciliation"
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
