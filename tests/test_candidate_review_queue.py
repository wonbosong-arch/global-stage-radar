import pandas as pd

from candidate_review_queue import build_queue_summary, build_review_queue


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

    
def test_queue_summary_reports_short_price_history_exceptions():
    report = pd.DataFrame([
        {"symbol": "AAA", "queue_priority": "P1", "activation_gate_status": "blocked", "activation_recommendation": "keep_pending_review", "candidate_history_150_plus_bars": "True", "candidate_price_rows": "300"},
        {"symbol": "BBB", "queue_priority": "P1", "activation_gate_status": "blocked", "activation_recommendation": "keep_pending_review", "candidate_history_150_plus_bars": "False", "candidate_price_rows": "83"},
        {"symbol": "CCC", "queue_priority": "P2", "activation_gate_status": "blocked", "activation_recommendation": "keep_pending_review", "candidate_history_150_plus_bars": "False", "candidate_price_rows": "0"},
    ])

    summary = build_queue_summary(report)
    counts = {(row.summary_type, row.category): row.candidate_count for row in summary.itertuples(index=False)}

    assert counts[("price_history_status", "stage_ready_150_plus_bars")] == 1
    assert counts[("price_history_status", "short_history_under_150")] == 1
    assert counts[("price_history_status", "no_price_rows")] == 1


def test_queue_summary_reports_mapping_suggestion_status_without_marking_verified():
    report = pd.DataFrame([
        {"symbol": "AAA", "queue_priority": "P1", "activation_gate_status": "blocked", "activation_recommendation": "keep_pending_review", "mapping_status": "first_pass_review_required"},
        {"symbol": "BBB", "queue_priority": "P1", "activation_gate_status": "blocked", "activation_recommendation": "keep_pending_review", "mapping_status": "first_pass_review_required"},
        {"symbol": "CCC", "queue_priority": "P2", "activation_gate_status": "blocked", "activation_recommendation": "keep_pending_review", "mapping_status": "sector_mapping_missing"},
    ])

    summary = build_queue_summary(report)
    counts = {(row.summary_type, row.category): row.candidate_count for row in summary.itertuples(index=False)}

    assert counts[("mapping_suggestion_status", "first_pass_review_required")] == 2
    assert counts[("mapping_suggestion_status", "sector_mapping_missing")] == 1
    assert counts[("activation_recommendation", "keep_pending_review")] == 3



def test_queue_summary_reports_proposed_benchmark_coverage_without_approval():
    report = pd.DataFrame([
        {
            "symbol": "AAA",
            "queue_priority": "P1",
            "activation_gate_status": "blocked",
            "activation_recommendation": "keep_pending_review",
            "suggested_sector_benchmark_coverage_status": "usable_for_provisional_analysis_not_approval",
        },
        {
            "symbol": "BBB",
            "queue_priority": "P2",
            "activation_gate_status": "blocked",
            "activation_recommendation": "keep_pending_review",
            "suggested_sector_benchmark_coverage_status": "usable_for_provisional_analysis_not_approval",
        },
        {
            "symbol": "CCC",
            "queue_priority": "P2",
            "activation_gate_status": "blocked",
            "activation_recommendation": "keep_pending_review",
            "suggested_sector_benchmark_coverage_status": "suggestion_missing_or_coverage_incomplete",
        },
    ])

    summary = build_queue_summary(report)
    counts = {(row.summary_type, row.category): row.candidate_count for row in summary.itertuples(index=False)}

    assert counts[("suggested_sector_benchmark_coverage", "usable_for_provisional_analysis_not_approval")] == 2
    assert counts[("suggested_sector_benchmark_coverage", "suggestion_missing_or_coverage_incomplete")] == 1
    assert counts[("activation_recommendation", "keep_pending_review")] == 3


def test_queue_exposes_primary_source_issuer_evidence_without_activating_candidate():
    coverage = pd.DataFrame([
        {"symbol": "ETN", "identity_status": "review_required", "provider_status": "not_checked", "market_cap_status": "not_verified"}
    ])
    identity = pd.DataFrame([
        {"symbol": "ETN", "identity_marked_verified": False, "provider_marked_checked": False}
    ])
    market_cap = pd.DataFrame([
        {"symbol": "ETN", "date_review_priority": "P3_routine_evidence"}
    ])
    issuer_evidence = pd.DataFrame([
        {
            "symbol": "ETN",
            "issuer_country": "Ireland",
            "listing_market": "NYSE",
            "security_type": "ordinary shares",
            "official_source_type": "issuer investor FAQ",
            "official_source_url": "https://example.com/issuer",
            "source_observed_date": "2026-10-26",
            "review_outcome": "identity_evidence_captured",
            "remaining_gates": "market_cap_verification;provider_support",
            "notes": "Issuer-country evidence only",
        }
    ])

    result = build_review_queue(coverage, identity, market_cap, issuer_evidence).iloc[0]

    assert result["issuer_country_evidence_present"]
    assert result["issuer_country"] == "Ireland"
    assert result["listing_market"] == "NYSE"
    assert result["official_source_url"] == "https://example.com/issuer"
    assert result["queue_priority"] == "P3_provider_mapping"
    assert result["activation_recommendation"] == "keep_pending_review"


def test_large_market_cap_mismatch_is_deprioritized_not_hidden():
    coverage = pd.DataFrame([{
        "symbol": "BIG", "identity_status": "verified_primary_listing",
        "provider_status": "not_checked", "market_cap_status": "not_verified",
        "market_cap_usd_b_secondary": "100",
    }])
    identity = pd.DataFrame([{"symbol": "BIG", "identity_marked_verified": True, "provider_marked_checked": False}])
    market_cap = pd.DataFrame([{
        "symbol": "BIG", "date_review_priority": "P1_material_mismatch",
        "implied_vs_reported_shares_pct": 22.0,
    }])
    result = build_review_queue(coverage, identity, market_cap).iloc[0]
    assert result["queue_priority"] == "P3_market_cap_evidence"
    assert result["activation_recommendation"] == "keep_pending_review"
    assert result["date_review_priority"] == "P1_material_mismatch"


def test_yahoo_cap_threshold_is_joined_as_review_only_evidence():
    coverage = pd.DataFrame([
        {"symbol":"BIG","identity_status":"review_required","provider_status":"not_checked","market_cap_status":"not_verified"},
        {"symbol":"SMALL","identity_status":"review_required","provider_status":"not_checked","market_cap_status":"not_verified"},
        {"symbol":"NONE","identity_status":"review_required","provider_status":"not_checked","market_cap_status":"not_verified"},
    ])
    identity = pd.DataFrame([{"symbol":s,"identity_marked_verified":False,"provider_marked_checked":False} for s in ["BIG","SMALL","NONE"]])
    market_cap = pd.DataFrame([{"symbol":s,"date_review_priority":"P3_routine_evidence"} for s in ["BIG","SMALL","NONE"]])
    yahoo = pd.DataFrame([
        {"symbol":"BIG","cap_threshold_review":"observed_ge_1b_review_only","triage_status":"listing_identity_review_required"},
        {"symbol":"SMALL","cap_threshold_review":"observed_lt_1b_review_only","triage_status":"priority_review_cap_lt_1b"},
    ])

    result = build_review_queue(coverage, identity, market_cap, yahoo_cap_triage=yahoo).set_index("symbol")
    assert result.loc["BIG","cap_threshold_review"] == "observed_ge_1b_review_only"
    assert result.loc["BIG","triage_status"] == "listing_identity_review_required"
    assert result.loc["SMALL","cap_threshold_review"] == "observed_lt_1b_review_only"
    assert result.loc["NONE","cap_threshold_review"] == ""
    assert set(result["activation_recommendation"]) == {"keep_pending_review"}


def test_queue_summary_counts_secondary_market_cap_threshold_review():
    report = pd.DataFrame([
        {"symbol":"BIG","queue_priority":"P1","activation_gate_status":"blocked","activation_recommendation":"keep_pending_review","cap_threshold_review":"observed_ge_1b_review_only"},
        {"symbol":"SMALL","queue_priority":"P2","activation_gate_status":"blocked","activation_recommendation":"keep_pending_review","cap_threshold_review":"observed_lt_1b_review_only"},
        {"symbol":"NONE","queue_priority":"P2","activation_gate_status":"blocked","activation_recommendation":"keep_pending_review","cap_threshold_review":""},
    ])
    summary = build_queue_summary(report)
    counts = {(row.summary_type,row.category):row.candidate_count for row in summary.itertuples(index=False)}
    assert counts[("secondary_market_cap_threshold","observed_ge_1b_review_only")] == 1
    assert counts[("secondary_market_cap_threshold","observed_lt_1b_review_only")] == 1
    assert counts[("secondary_market_cap_threshold","no_secondary_cap_observation")] == 1


def test_candidate_yahoo_observation_fills_threshold_when_master_triage_has_no_match():
    coverage = pd.DataFrame([
        {"symbol":"BIG","identity_status":"review_required","provider_status":"not_checked","market_cap_status":"not_verified"},
        {"symbol":"SMALL","identity_status":"review_required","provider_status":"not_checked","market_cap_status":"not_verified"},
    ])
    identity = pd.DataFrame([{"symbol":s,"identity_marked_verified":False,"provider_marked_checked":False} for s in ["BIG","SMALL"]])
    market_cap = pd.DataFrame([{"symbol":s,"date_review_priority":"P3_routine_evidence"} for s in ["BIG","SMALL"]])
    observations = pd.DataFrame([
        {"symbol":"BIG","market_cap_usd_b_secondary":"2.4","observation_status":"observed_usd","market_cap_status":"not_verified","market_cap_asof":"","market_cap_asof_basis":"not_provided_by_yahoo"},
        {"symbol":"SMALL","market_cap_usd_b_secondary":"0.7","observation_status":"observed_usd","market_cap_status":"not_verified","market_cap_asof":"","market_cap_asof_basis":"not_provided_by_yahoo"},
    ])
    result = build_review_queue(coverage, identity, market_cap, yahoo_cap_observations=observations).set_index("symbol")
    assert result.loc["BIG","cap_threshold_review"] == "observed_ge_1b_review_only"
    assert result.loc["SMALL","cap_threshold_review"] == "observed_lt_1b_review_only"
    assert result.loc["BIG","candidate_yahoo_market_cap_status"] == "not_verified"
    assert set(result["activation_recommendation"]) == {"keep_pending_review"}


def test_secondary_cap_size_bands_prioritize_review_without_approval():
    symbols = ["BIG", "NEAR", "SMALL", "UNKNOWN"]
    coverage = pd.DataFrame([{
        "symbol": s, "identity_status": "review_required",
        "provider_status": "not_checked", "market_cap_status": "not_verified",
    } for s in symbols])
    identity = pd.DataFrame([{
        "symbol": s, "identity_marked_verified": False,
        "provider_marked_checked": False,
    } for s in symbols])
    market_cap = pd.DataFrame([{
        "symbol": s, "date_review_priority": "P3_routine_evidence",
    } for s in symbols])
    observations = pd.DataFrame([
        {"symbol": "BIG", "market_cap_usd_b_secondary": "2.4", "observation_status": "observed_usd", "market_cap_status": "not_verified"},
        {"symbol": "NEAR", "market_cap_usd_b_secondary": "1.2", "observation_status": "observed_usd", "market_cap_status": "not_verified"},
        {"symbol": "SMALL", "market_cap_usd_b_secondary": "0.7", "observation_status": "observed_usd", "market_cap_status": "not_verified"},
        {"symbol": "UNKNOWN", "market_cap_usd_b_secondary": "", "observation_status": "request_failed", "market_cap_status": "not_verified"},
    ])
    result = build_review_queue(
        coverage, identity, market_cap, yahoo_cap_observations=observations
    ).set_index("symbol")
    assert result.loc["BIG", "cap_size_band_review"] == "observed_ge_1_5b_review_only"
    assert result.loc["NEAR", "cap_size_band_review"] == "observed_1_to_1_5b_review_only"
    assert result.loc["SMALL", "cap_size_band_review"] == "observed_lt_1b_review_only"
    assert result.loc["UNKNOWN", "cap_size_band_review"] == "cap_unverified"
    assert set(result["activation_recommendation"]) == {"keep_pending_review"}



def test_captured_issuer_evidence_does_not_keep_candidate_in_top_identity_emergency():
    coverage = pd.DataFrame([{
        "symbol": "ETN",
        "identity_status": "issuer_country_review_required",
        "provider_status": "not_checked",
        "market_cap_status": "not_verified",
    }])
    identity = pd.DataFrame([{
        "symbol": "ETN",
        "identity_marked_verified": False,
        "provider_marked_checked": False,
    }])
    market_cap = pd.DataFrame([{
        "symbol": "ETN",
        "date_review_priority": "P2_date_alignment",
    }])
    issuer_evidence = pd.DataFrame([{
        "symbol": "ETN",
        "issuer_country": "Ireland",
        "listing_market": "NYSE",
        "official_source_url": "https://example.com/issuer",
        "source_observed_date": "2026-10-26",
        "review_outcome": "identity_evidence_captured",
        "remaining_gates": "market_cap_verification;provider_support",
    }])

    result = build_review_queue(
        coverage, identity, market_cap, issuer_evidence
    ).iloc[0]

    assert result["issuer_country_evidence_present"]
    assert result["queue_priority"] == "P2_market_cap_reconciliation"
    assert result["activation_recommendation"] == "keep_pending_review"
    assert not result["identity_marked_verified"]


def test_comfortably_above_threshold_cap_moves_to_independent_gate_not_reconciliation():
    coverage = pd.DataFrame([{
        "symbol": "BIG", "identity_status": "review_required",
        "provider_status": "not_checked", "market_cap_status": "not_verified",
        "market_cap_usd_b_secondary": "300",
    }])
    identity = pd.DataFrame([{
        "symbol": "BIG", "identity_marked_verified": False,
        "provider_marked_checked": False,
    }])
    market_cap = pd.DataFrame([{
        "symbol": "BIG", "date_review_priority": "P2_date_alignment",
        "triage_outcome": "arithmetic_consistent_date_basis_still_unverified",
        "market_cap_status_remains": "not_verified",
    }])
    result = build_review_queue(coverage, identity, market_cap).iloc[0]
    assert result["size_screen_result"] == "pass_estimate"
    assert result["queue_priority"] == "P3_provider_mapping"
    assert result["market_cap_status"] == "not_verified"
    assert result["activation_recommendation"] == "keep_pending_review"


def test_near_threshold_estimate_remains_in_market_cap_review_queue():
    coverage = pd.DataFrame([{
        "symbol": "NEAR", "identity_status": "review_required",
        "provider_status": "not_checked", "market_cap_status": "not_verified",
        "market_cap_usd_b_secondary": "1.2",
    }])
    identity = pd.DataFrame([{
        "symbol": "NEAR", "identity_marked_verified": False,
        "provider_marked_checked": False,
    }])
    market_cap = pd.DataFrame([{
        "symbol": "NEAR", "date_review_priority": "P2_date_alignment",
    }])
    result = build_review_queue(coverage, identity, market_cap).iloc[0]
    assert result["size_screen_result"] == "pass_estimate"
    assert result["queue_priority"] == "P2_market_cap_reconciliation"
    assert result["activation_recommendation"] == "keep_pending_review"
