import pandas as pd

from candidate_review_queue import build_benchmark_review_batches, build_queue_summary, build_review_queue


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


def test_captured_issuer_evidence_advances_to_benchmark_review_when_proxy_exists():
    coverage = pd.DataFrame([{
        "symbol": "ETN",
        "instrument_type": "common_stock_candidate",
        "identity_status": "review_required",
        "provider_status": "not_checked",
        "provider_observed_data_returned": True,
        "market_cap_status": "not_verified",
        "sector_benchmark": "",
        "suggested_sector_benchmark": "XLI",
        "activation_gate_status": "blocked_pending_manual_review",
        "activation_recommendation": "keep_pending_review",
    }])
    identity = pd.DataFrame([{
        "symbol": "ETN",
        "identity_marked_verified": False,
        "provider_marked_checked": False,
    }])
    market_cap = pd.DataFrame([{
        "symbol": "ETN",
        "date_review_priority": "P3_routine_evidence",
    }])
    issuer_evidence = pd.DataFrame([{
        "symbol": "ETN",
        "issuer_country": "Ireland",
        "listing_market": "NYSE",
        "security_type": "ordinary shares",
        "official_source_type": "issuer investor FAQ",
        "official_source_url": "https://example.com/issuer",
        "source_observed_date": "2026-10-26",
        "review_outcome": "identity_evidence_captured",
        "remaining_gates": "identity_verification;benchmark_mapping",
        "notes": "Issuer-country evidence only",
    }])
    observations = pd.DataFrame([{
        "symbol": "ETN",
        "market_cap_usd_b_secondary": 100.0,
        "observation_status": "observed_usd",
        "market_cap_status": "not_verified",
    }])

    row = build_review_queue(
        coverage, identity, market_cap,
        issuer_evidence=issuer_evidence,
        yahoo_cap_observations=observations,
    ).iloc[0]

    assert row["issuer_country_evidence_present"]
    assert row["queue_priority"] == "P3_benchmark_mapping"
    assert "미승인 유지" in row["next_action_ko"]
    assert row["activation_recommendation"] == "keep_pending_review"


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
    assert result["queue_priority"] == "P3_provider_mapping"
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
    assert result["queue_priority"] == "P3_provider_mapping"
    assert result["activation_recommendation"] == "keep_pending_review"


def test_queue_summary_counts_minimum_market_cap_size_screen():
    report = pd.DataFrame([
        {"symbol": "BIG", "queue_priority": "P3_provider_mapping", "activation_gate_status": "blocked", "activation_recommendation": "keep_pending_review", "size_screen_result": "pass_estimate"},
        {"symbol": "SMALL", "queue_priority": "P2_market_cap_reconciliation", "activation_gate_status": "blocked", "activation_recommendation": "keep_pending_review", "size_screen_result": "below_minimum"},
        {"symbol": "UNKNOWN", "queue_priority": "P3_market_cap_evidence", "activation_gate_status": "blocked", "activation_recommendation": "keep_pending_review", "size_screen_result": "needs_observation"},
    ])
    summary = build_queue_summary(report)
    counts = {(row.summary_type, row.category): row.candidate_count for row in summary.itertuples(index=False)}
    assert counts[("market_cap_size_screen", "pass_estimate")] == 1
    assert counts[("market_cap_size_screen", "below_minimum")] == 1
    assert counts[("market_cap_size_screen", "needs_observation")] == 1


def test_recent_kis_response_deprioritizes_repeated_provider_mapping_without_approval():
    coverage = pd.DataFrame([{
        "symbol": "LARGE",
        "identity_status": "review_required",
        "provider_status": "not_checked",
        "provider_observed_data_returned": True,
        "market_cap_status": "not_verified",
        "market_cap_usd_b_secondary": 250.0,
    }])
    identity = pd.DataFrame([{
        "symbol": "LARGE",
        "identity_marked_verified": False,
        "provider_marked_checked": False,
    }])
    market_cap = pd.DataFrame([{
        "symbol": "LARGE",
        "date_review_priority": "P2_routine_review",
    }])

    row = build_review_queue(coverage, identity, market_cap).iloc[0]

    assert row["queue_priority"] == "P2_identity_evidence"
    assert row["provider_status"] == "not_checked"
    assert row["activation_recommendation"] == "keep_pending_review"


def test_fx_converted_usd_cap_counts_for_coarse_size_screen_only():
    coverage = pd.DataFrame([{
        "symbol": "KOR", "identity_status": "review_required",
        "provider_status": "not_checked", "market_cap_status": "not_verified",
    }])
    identity = pd.DataFrame([{
        "symbol": "KOR", "identity_marked_verified": False,
        "provider_marked_checked": False,
    }])
    market_cap = pd.DataFrame([{
        "symbol": "KOR", "date_review_priority": "P3_routine_evidence",
    }])
    observations = pd.DataFrame([{
        "symbol": "KOR", "market_cap_usd_b_secondary": "30.8",
        "observation_status": "observed_usd_fx_converted",
        "market_cap_status": "not_verified",
        "market_cap_asof": "", "market_cap_asof_basis": "not_provided_by_yahoo",
    }])

    row = build_review_queue(
        coverage, identity, market_cap, yahoo_cap_observations=observations
    ).iloc[0]

    assert row["size_screen_result"] == "pass_estimate"
    assert row["cap_threshold_review"] == "observed_ge_1b_review_only"
    assert row["cap_size_band_review"] == "observed_ge_1_5b_review_only"
    assert row["candidate_yahoo_market_cap_status"] == "not_verified"
    assert row["activation_recommendation"] == "keep_pending_review"


def test_adr_with_large_observed_cap_is_not_queued_for_full_cap_reconciliation():
    coverage = pd.DataFrame([{
        "symbol": "ADR1", "instrument_type": "adr_candidate",
        "identity_status": "review_required", "provider_status": "not_checked",
        "market_cap_status": "not_verified", "provider_observed_data_returned": True,
    }])
    identity = pd.DataFrame([{
        "symbol": "ADR1", "identity_marked_verified": False,
        "provider_marked_checked": False,
    }])
    market_cap = pd.DataFrame([{
        "symbol": "ADR1", "date_review_priority": "P2_date_alignment",
    }])
    observations = pd.DataFrame([{
        "symbol": "ADR1", "market_cap_usd_b_secondary": "20.0",
        "observation_status": "observed_usd",
        "market_cap_status": "not_verified", "market_cap_asof": "",
        "market_cap_asof_basis": "not_provided_by_yahoo",
    }])

    row = build_review_queue(
        coverage, identity, market_cap, yahoo_cap_observations=observations
    ).iloc[0]

    assert row["size_screen_result"] == "pass_estimate"
    assert row["queue_priority"] == "P2_identity_evidence"
    assert "시가총액 정밀 대조는 보류" in row["next_action_ko"]
    assert row["market_cap_status"] == "not_verified"
    assert row["activation_recommendation"] == "keep_pending_review"


def test_passed_minimum_cap_estimate_does_not_reopen_formal_cap_reconciliation():
    coverage = pd.DataFrame([{
        "symbol": "BIG", "instrument_type": "common_stock_candidate",
        "identity_status": "verified", "provider_status": "not_checked",
        "provider_observed_data_returned": True, "market_cap_status": "not_verified",
        "activation_gate_status": "blocked_pending_manual_review",
        "activation_recommendation": "keep_pending_review",
    }])
    identity = pd.DataFrame([{
        "symbol": "BIG", "identity_marked_verified": True,
        "provider_marked_checked": False,
    }])
    market_cap = pd.DataFrame([{
        "symbol": "BIG", "date_review_priority": "P3_routine_evidence",
    }])
    observations = pd.DataFrame([{
        "symbol": "BIG", "market_cap_usd_b_secondary": "204.5",
        "observation_status": "observed_usd", "market_cap_status": "not_verified",
    }])
    issuer_evidence = pd.DataFrame([{
        "symbol": "BIG", "official_source_url": "https://example.com/issuer",
        "review_outcome": "identity_evidence_captured",
        "issuer_country": "United States", "listing_market": "NASDAQ",
    }])

    row = build_review_queue(
        coverage, identity, market_cap,
        issuer_evidence=issuer_evidence,
        yahoo_cap_observations=observations,
    ).iloc[0]

    assert row["size_screen_result"] == "pass_estimate"
    assert row["market_cap_status"] == "not_verified"
    assert row["queue_priority"] == "P4_final_review"
    assert row["activation_recommendation"] == "keep_pending_review"



def test_below_minimum_cap_is_early_screen_but_etfs_are_exempt():
    coverage = pd.DataFrame([
        {"symbol": "SMALL", "instrument_type": "common_stock_candidate", "discovery_market_cap_usd": 500_000_000, "identity_status": "review_required"},
        {"symbol": "ETF1", "instrument_type": "etf_candidate", "discovery_market_cap_usd": 500_000_000, "identity_status": "review_required"},
    ])
    identity = pd.DataFrame([{"symbol": "SMALL"}, {"symbol": "ETF1"}])
    market_cap = pd.DataFrame([{"symbol": "SMALL"}, {"symbol": "ETF1"}])

    result = build_review_queue(coverage, identity, market_cap).set_index("symbol")

    assert result.loc["SMALL", "size_screen_result"] == "below_minimum"
    assert result.loc["SMALL", "queue_priority"] == "P1_below_minimum_size_screen"
    assert result.loc["ETF1", "size_screen_result"] == "exempt_instrument_type"
    assert result.loc["ETF1", "queue_priority"] != "P1_below_minimum_size_screen"
    assert set(result["activation_recommendation"]) == {"keep_pending_review"}


def test_benchmark_review_batch_groups_candidates_by_proposed_sector_etf():
    coverage = pd.DataFrame([
        {"symbol": "AAA", "instrument_type": "common_stock_candidate", "identity_status": "review_required",
         "provider_status": "not_checked", "provider_observed_data_returned": True,
         "market_cap_status": "not_verified", "market_benchmark": "SPY", "sector_benchmark": "",
         "proposed_sector": "Semiconductors", "suggested_sector_benchmark": "SOXX",
         "suggested_sector_benchmark_active": True, "suggested_sector_benchmark_latest_date": "2026-10-26"},
        {"symbol": "BBB", "instrument_type": "common_stock_candidate", "identity_status": "review_required",
         "provider_status": "not_checked", "provider_observed_data_returned": True,
         "market_cap_status": "not_verified", "market_benchmark": "SPY", "sector_benchmark": "",
         "proposed_sector": "Semiconductors", "suggested_sector_benchmark": "SOXX",
         "suggested_sector_benchmark_active": True, "suggested_sector_benchmark_latest_date": "2026-10-25"},
    ])
    identity = pd.DataFrame([{"symbol": "AAA"}, {"symbol": "BBB"}])
    market_cap = pd.DataFrame([{"symbol": "AAA"}, {"symbol": "BBB"}])
    issuer_evidence = pd.DataFrame([
        {"symbol": symbol, "official_source_url": "https://example.com/issuer",
         "review_outcome": "identity_evidence_captured"}
        for symbol in ("AAA", "BBB")
    ])
    observations = pd.DataFrame([
        {"symbol": symbol, "market_cap_usd_b_secondary": 20.0,
         "observation_status": "observed_usd"}
        for symbol in ("AAA", "BBB")
    ])

    queue = build_review_queue(
        coverage, identity, market_cap,
        issuer_evidence=issuer_evidence,
        yahoo_cap_observations=observations,
    )
    batches = build_benchmark_review_batches(queue)

    assert len(batches) == 1
    row = batches.iloc[0]
    assert row["suggested_sector_benchmark"] == "SOXX"
    assert row["candidate_count"] == 2
    assert row["candidate_symbols"] == "AAA;BBB"
    assert row["approved_sector_benchmark_count"] == 0
    assert row["review_status"] == "provisional_not_approved"
    assert set(queue["activation_recommendation"]) == {"keep_pending_review"}
