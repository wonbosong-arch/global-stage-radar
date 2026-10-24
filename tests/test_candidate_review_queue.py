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
