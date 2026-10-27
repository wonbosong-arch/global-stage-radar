"""Consolidated, conservative action queue for pending stock candidates.

Combines candidate coverage, identity evidence, market-cap triage, and sourced
issuer-country evidence reports. It prioritizes work only; it never verifies or activates a candidate.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
COVERAGE = ROOT / "data" / "stock_candidate_coverage_report.csv"
IDENTITY = ROOT / "data" / "candidate_identity_evidence_coverage.csv"
MARKET_CAP = ROOT / "data" / "candidate_market_cap_reconciliation.csv"
ISSUER_EVIDENCE = ROOT / "data" / "issuer_country_evidence_review.csv"
YAHOO_CAP_TRIAGE = ROOT / "data" / "yahoo_master_cap_triage.csv"
YAHOO_CAP_OBSERVATIONS = ROOT / "data" / "yahoo_market_cap_supplement.csv"
OUTPUT = ROOT / "data" / "candidate_review_queue.csv"
SUMMARY_OUTPUT = ROOT / "data" / "candidate_review_queue_summary.csv"
BENCHMARK_BATCH_OUTPUT = ROOT / "data" / "sector_benchmark_review_batches.csv"


def build_review_queue(coverage: pd.DataFrame, identity: pd.DataFrame, market_cap: pd.DataFrame, issuer_evidence: pd.DataFrame | None = None, yahoo_cap_triage: pd.DataFrame | None = None, yahoo_cap_observations: pd.DataFrame | None = None) -> pd.DataFrame:
    """Join review reports by symbol; evidence never grants verification or activation."""
    if issuer_evidence is None:
        issuer_evidence = pd.DataFrame(columns=["symbol"])
    for frame in (coverage, identity, market_cap, issuer_evidence):
        if "symbol" not in frame.columns:
            raise ValueError("Each input report must contain a symbol column.")
        frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()

    id_cols = [c for c in (
        "symbol", "identity_status", "identity_marked_verified",
        "identity_source_url_present", "identity_review_date_present",
        "depositary_ratio_required", "depositary_ratio_verified",
        "market_cap_marked_verified", "provider_status", "provider_marked_checked",
        "review_gaps",
    ) if c in identity.columns]
    cap_cols = [c for c in (
        "symbol", "date_review_priority", "date_review_reason",
        "price_to_share_count_asof_gap_days", "implied_vs_reported_shares_pct",
        "triage_outcome", "market_cap_status_remains",
    ) if c in market_cap.columns]

    result = coverage.merge(identity[id_cols], on="symbol", how="left", suffixes=("", "_identity"))
    result = result.merge(market_cap[cap_cols], on="symbol", how="left", suffixes=("", "_market_cap"))
    evidence_cols = [c for c in (
        "symbol", "issuer_country", "listing_market", "security_type",
        "official_source_type", "official_source_url", "source_observed_date",
        "review_outcome", "remaining_gates", "notes",
    ) if c in issuer_evidence.columns]
    if len(evidence_cols) > 1:
        evidence = issuer_evidence[evidence_cols].drop_duplicates(subset=["symbol"], keep="last").copy()
        evidence["issuer_country_evidence_present"] = (
            evidence.get("official_source_url", pd.Series("", index=evidence.index)).astype(str).str.strip().ne("")
            & evidence.get("review_outcome", pd.Series("", index=evidence.index)).astype(str).str.strip().eq("identity_evidence_captured")
        )
        result = result.merge(evidence, on="symbol", how="left", suffixes=("", "_issuer_evidence"))
    else:
        result["issuer_country_evidence_present"] = False
        result["official_source_type"] = ""
        result["official_source_url"] = ""
        result["source_observed_date"] = ""
        result["review_outcome"] = ""
        result["remaining_gates"] = ""
        result["issuer_evidence_notes"] = ""
    result["issuer_country_evidence_present"] = result["issuer_country_evidence_present"].fillna(False).astype(bool)

    # Secondary Yahoo market-cap observations are an independent screening
    # signal. Join only the explicit threshold and triage fields; never treat
    # these observations as verified market cap or activation approval.
    if yahoo_cap_triage is not None and "symbol" in yahoo_cap_triage.columns:
        cap_triage_cols = [col for col in (
            "symbol", "cap_threshold_review", "triage_status"
        ) if col in yahoo_cap_triage.columns]
        cap_triage = yahoo_cap_triage[cap_triage_cols].copy()
        cap_triage["symbol"] = cap_triage["symbol"].astype(str).str.strip().str.upper()
        cap_triage = cap_triage.drop_duplicates(subset=["symbol"], keep="last")
        result = result.merge(cap_triage, on="symbol", how="left", suffixes=("", "_yahoo"))
    if "cap_threshold_review" not in result.columns:
        result["cap_threshold_review"] = ""
    if "triage_status" not in result.columns:
        result["triage_status"] = ""
    result["cap_threshold_review"] = result["cap_threshold_review"].fillna("")
    result["triage_status"] = result["triage_status"].fillna("")

    # The unranked-master triage may not contain symbols already in the
    # candidate queue. Use the candidate-level Yahoo supplement as a fallback
    # threshold observation, while preserving its explicitly unverified status.
    if yahoo_cap_observations is not None and "symbol" in yahoo_cap_observations.columns:
        obs_cols = [col for col in (
            "symbol", "market_cap_usd_b_secondary", "observation_status",
            "market_cap_status", "market_cap_asof", "market_cap_asof_basis",
        ) if col in yahoo_cap_observations.columns]
        observations = yahoo_cap_observations[obs_cols].copy()
        observations["symbol"] = observations["symbol"].astype(str).str.strip().str.upper()
        observations = observations.drop_duplicates(subset=["symbol"], keep="last")
        rename = {col: f"candidate_yahoo_{col}" for col in obs_cols if col != "symbol"}
        observations = observations.rename(columns=rename)
        result = result.merge(observations, on="symbol", how="left")
        has_threshold = result["cap_threshold_review"].astype(str).str.strip().ne("")
        cap = pd.to_numeric(result.get("candidate_yahoo_market_cap_usd_b_secondary", pd.Series(index=result.index, dtype=float)), errors="coerce")
        observed = result.get("candidate_yahoo_observation_status", pd.Series("", index=result.index)).astype(str).str.strip().isin({"observed_usd", "observed_usd_fx_converted"})
        result.loc[~has_threshold & observed & cap.ge(1), "cap_threshold_review"] = "observed_ge_1b_review_only"
        result.loc[~has_threshold & observed & cap.lt(1), "cap_threshold_review"] = "observed_lt_1b_review_only"
        result.loc[~has_threshold & ~observed, "cap_threshold_review"] = "cap_unverified"

    # A second, explicitly review-only band distinguishes comfortably-above-
    # hurdle observations from values close to the $1B boundary. This is a
    # prioritization aid, not a new eligibility rule or verified market cap.
    cap_for_band = pd.to_numeric(
        result.get("candidate_yahoo_market_cap_usd_b_secondary", pd.Series(index=result.index, dtype=float)),
        errors="coerce",
    )
    observed_for_band = result.get(
        "candidate_yahoo_observation_status", pd.Series("", index=result.index)
    ).astype(str).str.strip().isin({"observed_usd", "observed_usd_fx_converted"})
    result["cap_size_band_review"] = "cap_unverified"
    result.loc[observed_for_band & cap_for_band.lt(1), "cap_size_band_review"] = "observed_lt_1b_review_only"
    result.loc[observed_for_band & cap_for_band.ge(1) & cap_for_band.lt(1.5), "cap_size_band_review"] = "observed_1_to_1_5b_review_only"
    result.loc[observed_for_band & cap_for_band.ge(1.5), "cap_size_band_review"] = "observed_ge_1_5b_review_only"

    # Make the $1B screen explicit using whichever source-backed USD estimate
    # is already available. This is a size-screen result, not cap verification.
    secondary_b = pd.to_numeric(result.get("market_cap_usd_b_secondary", pd.Series(index=result.index, dtype=float)), errors="coerce")
    yahoo_b = pd.to_numeric(result.get("candidate_yahoo_market_cap_usd_b_secondary", pd.Series(index=result.index, dtype=float)), errors="coerce")
    discovery_usd = pd.to_numeric(result.get("discovery_market_cap_usd", pd.Series(index=result.index, dtype=float)), errors="coerce")
    cap_b = secondary_b.where(secondary_b.notna(), yahoo_b)
    cap_b = cap_b.where(cap_b.notna(), discovery_usd / 1_000_000_000)
    result["size_screen_result"] = "needs_observation"
    result.loc[cap_b.notna() & cap_b.ge(1), "size_screen_result"] = "pass_estimate"
    result.loc[cap_b.notna() & cap_b.lt(1), "size_screen_result"] = "below_minimum"
    cap_exempt_mask = result.get(
        "instrument_type", pd.Series("", index=result.index)
    ).astype(str).str.strip().str.lower().isin({"etf", "etf_candidate", "fund", "index_fund"})
    result.loc[cap_exempt_mask, "size_screen_result"] = "exempt_instrument_type"

    def decide(row: pd.Series) -> tuple[str, str]:
        status = str(row.get("identity_status", "")).strip()
        cap_priority = str(row.get("date_review_priority", "")).strip()
        instrument_type = str(row.get("instrument_type", "")).strip().lower()
        screen_result = str(row.get("size_screen_result", "")).strip()

        # Apply the $1B minimum only as an early coarse screen. ETFs and funds
        # are trend/benchmark instruments and must never be excluded by cap.
        cap_exempt_instrument_types = {"etf", "etf_candidate", "fund", "index_fund"}
        if screen_result == "below_minimum" and instrument_type not in cap_exempt_instrument_types:
            return "P1_below_minimum_size_screen", "Estimated market cap is below $1B; hold at the coarse size screen rather than repeating detailed review"

        # A comfortably-above-threshold estimate clears the coarse size screen.
        # Do not spend review time reconciling share-count arithmetic before the
        # independent identity/provider gates; retain all source and status fields.
        if screen_result == "pass_estimate":
            observed_b = pd.to_numeric(pd.Series([row.get("market_cap_usd_b_secondary")]), errors="coerce").iloc[0]
            if pd.isna(observed_b):
                observed_b = pd.to_numeric(pd.Series([row.get("candidate_yahoo_market_cap_usd_b_secondary")]), errors="coerce").iloc[0]
            if pd.isna(observed_b):
                discovered_usd = pd.to_numeric(pd.Series([row.get("discovery_market_cap_usd")]), errors="coerce").iloc[0]
                observed_b = discovered_usd / 1_000_000_000 if pd.notna(discovered_usd) else float("nan")
            if pd.notna(observed_b) and observed_b >= 1.0 and instrument_type not in {"adr_candidate", "adr", "american_depositary_receipt"}:
                # A fresh KIS price response is useful evidence that the symbol
                # was retrievable through the requested provider route. It is
                # not formal provider approval or identity verification, but it
                # should prevent repeating provider-discovery work before the
                # more actionable identity/benchmark gates are reviewed.
                response_observed = str(row.get("provider_observed_data_returned", "")).strip().lower() in {"true", "1", "yes"}
                if str(row.get("provider_status", "")).strip() not in {"verified", "supported"} and not response_observed:
                    return "P3_provider_mapping", "KIS 가격 응답 관측이 없어 종목 매핑·지원 여부 확인"
                issuer_evidence_captured = bool(row.get("issuer_country_evidence_present", False))
                approved_sector_benchmark = str(row.get("sector_benchmark", "")).strip()
                suggested_sector_benchmark = str(row.get("suggested_sector_benchmark", "")).strip()
                if status not in {"verified", "verified_primary_listing"} and issuer_evidence_captured:
                    if not approved_sector_benchmark and suggested_sector_benchmark:
                        return "P3_benchmark_mapping", "발행사 근거는 이미 확보됨; 제안 ETF의 지수 구성·업종 적합성을 검토하되 미승인 유지; 정식 상장 식별은 별도 확인"
                    return "P2_identity_evidence", "발행사 근거는 이미 확보됨; 기존 근거를 검토해 상장 식별 판단을 진행하고 같은 자료를 재수집하지 않음"
                if status not in {"verified", "verified_primary_listing"}:
                    return "P2_identity_evidence", "규모 필터는 추정치로 통과; 공식 상장·발행사 식별 검토; KIS 응답 관측은 정식 승인과 구분"
                return "P4_final_review", "규모 필터는 추정치로 통과; KIS 응답 관측은 정식 승인과 구분; 남은 독립 게이트 최종 검토"

        # ADR share-class and depositary-ratio review remains a separate identity
        # gate, but a comfortably-above-threshold estimate is sufficient for the
        # MVP size screen. Do not keep ADRs in a market-cap reconciliation queue
        # merely because formal cap verification is intentionally deferred.
        if instrument_type == "adr_candidate":
            response_observed = str(row.get("provider_observed_data_returned", "")).strip().lower() in {"true", "1", "yes"}
            if str(row.get("provider_status", "")).strip() not in {"verified", "supported"} and not response_observed:
                return "P3_provider_mapping", "KIS 응답 관측이 없어 지원 여부를 확인; 시가총액 추정치는 규모 필터에만 사용"
            if screen_result == "pass_estimate":
                return "P2_identity_evidence", "규모 필터는 추정치로 통과; ADR 발행사·예탁비율·상장 종목 식별 검토를 진행하고 시가총액 정밀 대조는 보류"
            return "P3_market_cap_evidence", "규모 허들 근처 또는 자료 부족; 최소 시가총액 필터에 필요한 자료만 확인"

        # Once official issuer-country evidence has been captured, keep the
        # identity gate unverified but stop treating it as an evidence-not-found
        # emergency. This lets the queue advance to cap/date and provider work.
        # Evidence capture is not verification and never permits activation.
        issuer_evidence_captured = bool(row.get("issuer_country_evidence_present", False))
        if status in {"issuer_proxy_review_required", "issuer_country_review_required"} and not issuer_evidence_captured:
            return "P1_identity_classification", "발행사 국가·상장 종목 식별 근거가 부족해 공식 자료부터 확인"
        if cap_priority in {"P1_material_mismatch", "P1_stale_share_count"}:
            # A mismatch still remains visible in the evidence columns, but it
            # should not block the practical screening queue when the available
            # cap estimate is comfortably above the $1B universe hurdle.
            cap_b = pd.to_numeric(pd.Series([row.get("market_cap_usd_b_secondary")]), errors="coerce").iloc[0]
            discovery_cap = pd.to_numeric(pd.Series([row.get("discovery_market_cap_usd")]), errors="coerce").iloc[0]
            if pd.isna(cap_b) and pd.notna(discovery_cap):
                cap_b = discovery_cap / 1_000_000_000
            if pd.notna(cap_b) and cap_b >= 1.5:
                return "P3_market_cap_evidence", "시가총액 추정치가 15억 달러 이상으로 허들을 충분히 상회해 후보 검토는 진행; 산식 불일치는 별도 표시"
            return "P1_market_cap_reconciliation", "허들 부근 또는 규모 불명: 시가총액 역산 차이/기준일 우선 재검토"
        if cap_priority.startswith("P2_"):
            return "P2_market_cap_reconciliation", "시가총액 산식·주식 종류·기준일을 수동 대조"
        if issuer_evidence_captured and status not in {"verified", "verified_primary_listing"}:
            # Evidence is present but the identity gate remains unverified.
            # Prioritize the next independent gate instead of repeatedly asking
            # for the same issuer evidence to be collected again.
            response_observed = str(row.get("provider_observed_data_returned", "")).strip().lower() in {"true", "1", "yes"}
            if str(row.get("provider_status", "")).strip() not in {"verified", "supported"} and not response_observed:
                return "P3_provider_mapping", "발행사·상장 근거는 확보됨; KIS 응답 관측이 없어 종목 매핑 확인"
            if str(row.get("market_cap_status", "")).strip() != "verified":
                return "P3_market_cap_evidence", "발행사·상장 근거는 확보됨; 시가총액 출처·주식 수·기준일 정합성 확인"
            return "P4_final_review", "신원 상태는 미검증으로 유지; 나머지 독립 게이트 확인 후 최종 검토"
        if status not in {"verified", "verified_primary_listing"}:
            return "P2_identity_evidence", "공식 거래소/발행사 자료로 상장 종목과 발행사 정보를 검토"
        if str(row.get("provider_status", "")).strip() not in {"verified", "supported"}:
            return "P3_provider_mapping", "KIS 응답의 종목 매핑과 지원 여부를 별도 확인"
        if str(row.get("market_cap_status", "")).strip() != "verified":
            return "P3_market_cap_evidence", "시가총액 출처·주식 수·기준일 정합성을 확인"
        return "P4_final_review", "모든 독립 검토 항목을 확인한 뒤 활성화 적격성을 판단"

    decisions = result.apply(decide, axis=1, result_type="expand")
    decisions.columns = ["queue_priority", "next_action_ko"]
    result = pd.concat([result, decisions], axis=1)
    result["activation_recommendation"] = "keep_pending_review"
    result["queue_is_not_verification"] = True
    order = {
        "P1_below_minimum_size_screen": 1,
        "P1_identity_classification": 2,
        "P1_market_cap_reconciliation": 3,
        "P2_market_cap_reconciliation": 4,
        "P2_identity_evidence": 5,
        "P3_provider_mapping": 6,
        "P3_market_cap_evidence": 7,
        "P3_benchmark_mapping": 7,
        "P4_final_review": 8,
    }
    result["_order"] = result["queue_priority"].map(order).fillna(99)
    result = result.sort_values(["_order", "symbol"]).drop(columns="_order").reset_index(drop=True)
    return result




def build_queue_summary(report: pd.DataFrame) -> pd.DataFrame:
    """Build compact counts for priority, gate status, and recommendation."""
    priority_summary = (
        report.groupby("queue_priority", dropna=False)
        .agg(candidate_count=("symbol", "nunique"))
        .reset_index()
        .rename(columns={"queue_priority": "category"})
    )
    priority_summary["summary_type"] = "queue_priority"
    gate_summary = (
        report.groupby("activation_gate_status", dropna=False)
        .agg(candidate_count=("symbol", "nunique"))
        .reset_index()
        .rename(columns={"activation_gate_status": "category"})
    )
    gate_summary["summary_type"] = "activation_gate_status"
    recommendation_summary = (
        report.groupby("activation_recommendation", dropna=False)
        .agg(candidate_count=("symbol", "nunique"))
        .reset_index()
        .rename(columns={"activation_recommendation": "category"})
    )
    recommendation_summary["summary_type"] = "activation_recommendation"
    summaries = [priority_summary, gate_summary, recommendation_summary]
    if "size_screen_result" in report.columns:
        size_screen = report["size_screen_result"].astype(str).str.strip()
        size_screen = size_screen.where(size_screen.ne(""), "needs_observation")
        size_summary = (
            pd.DataFrame({"symbol": report["symbol"], "category": size_screen})
            .groupby("category", dropna=False)
            .agg(candidate_count=("symbol", "nunique"))
            .reset_index()
        )
        size_summary["summary_type"] = "market_cap_size_screen"
        summaries.append(size_summary)
    if "cap_threshold_review" in report.columns:
        cap_review = report["cap_threshold_review"].astype(str).str.strip()
        cap_review = cap_review.where(cap_review.ne(""), "no_secondary_cap_observation")
        cap_summary = (
            pd.DataFrame({"symbol": report["symbol"], "category": cap_review})
            .groupby("category", dropna=False)
            .agg(candidate_count=("symbol", "nunique"))
            .reset_index()
        )
        cap_summary["summary_type"] = "secondary_market_cap_threshold"
        summaries.append(cap_summary)
    if "cap_size_band_review" in report.columns:
        band = report["cap_size_band_review"].astype(str).str.strip()
        band = band.where(band.ne(""), "cap_unverified")
        band_summary = (
            pd.DataFrame({"symbol": report["symbol"], "category": band})
            .groupby("category", dropna=False)
            .agg(candidate_count=("symbol", "nunique"))
            .reset_index()
        )
        band_summary["summary_type"] = "secondary_market_cap_size_band_review"
        summaries.append(band_summary)
    # Show how much of the sector/benchmark review queue has a curated first-pass
    # suggestion, without treating a suggestion as a verified mapping.
    if "mapping_status" in report.columns:
        mapping_summary = (
            report.groupby("mapping_status", dropna=False)
            .agg(candidate_count=("symbol", "nunique"))
            .reset_index()
            .rename(columns={"mapping_status": "category"})
        )
        mapping_summary["summary_type"] = "mapping_suggestion_status"
        summaries.append(mapping_summary)
    if "suggested_sector_benchmark_coverage_status" in report.columns:
        suggested_status = report["suggested_sector_benchmark_coverage_status"].astype(str).str.strip()
        suggested_category = suggested_status.where(
            suggested_status.ne(""),
            "suggestion_missing_or_coverage_incomplete",
        )
        suggested_summary = (
            pd.DataFrame({"symbol": report["symbol"], "category": suggested_category})
            .groupby("category", dropna=False)
            .agg(candidate_count=("symbol", "nunique"))
            .reset_index()
        )
        suggested_summary["summary_type"] = "suggested_sector_benchmark_coverage"
        summaries.append(suggested_summary)
    if "candidate_history_150_plus_bars" in report.columns:
        has_history = report["candidate_history_150_plus_bars"].astype(str).str.strip().str.lower().isin(
            {"true", "1", "yes"}
        )
        price_rows = pd.to_numeric(
            report.get("candidate_price_rows", pd.Series(0, index=report.index)),
            errors="coerce",
        ).fillna(0)
        history_category = pd.Series("short_history_under_150", index=report.index, dtype=str)
        history_category.loc[has_history] = "stage_ready_150_plus_bars"
        history_category.loc[price_rows.le(0)] = "no_price_rows"
        history_summary = (
            pd.DataFrame({"symbol": report["symbol"], "category": history_category})
            .groupby("category", dropna=False)
            .agg(candidate_count=("symbol", "nunique"))
            .reset_index()
        )
        history_summary["summary_type"] = "price_history_status"
        summaries.append(history_summary)
    summary = pd.concat(summaries, ignore_index=True)[
        ["summary_type", "category", "candidate_count"]
    ]
    summary = summary.sort_values(["summary_type", "category"]).reset_index(drop=True)
    
    return summary.sort_values(["summary_type", "category"]).reset_index(drop=True)

def build_benchmark_review_batches(report: pd.DataFrame) -> pd.DataFrame:
    """Group proposed sector ETF checks so each proxy is reviewed once for many stocks."""
    columns = [
        "proposed_sector", "suggested_sector_benchmark", "candidate_count",
        "candidate_symbols", "approved_sector_benchmark_count",
        "suggested_etf_active", "suggested_etf_latest_date",
        "issuer_reference_url", "reference_scope", "official_index_methodology_url", "benchmark_scope_note",
        "index_methodology_review_status", "review_status", "review_action",
    ]
    # Official references verified from issuer pages. A broad issuer lineup page
    # is explicitly not treated as proof of the individual fund's index methodology.
    issuer_lineup_url = "https://www.ssga.com/us/en/intermediary/capabilities/equities/sector-investing/select-sector-etfs"
    official_refs = {
        "SOXX": ("https://www.ishares.com/us/products/239705/SOX", "individual_fund_page_index_identified"),
        "XLK": ("https://www.ssga.com/us/en/intermediary/etfs/state-street-technology-select-sector-spdr-etf-xlk", "individual_fund_page_benchmark_and_holdings_available"),
        "XLF": ("https://www.ssga.com/us/en/intermediary/etfs/state-street-financial-select-sector-spdr-etf-xlf", "individual_fund_page_benchmark_and_holdings_available"),
        "XLY": ("https://www.ssga.com/us/en/intermediary/etfs/state-street-consumer-discretionary-select-sector-spdr-etf-xly", "individual_fund_page_benchmark_and_holdings_available"),
        "XLV": ("https://www.ssga.com/us/en/intermediary/etfs/state-street-health-care-select-sector-spdr-etf-xlv", "individual_fund_page_benchmark_and_holdings_available"),
        "XLC": ("https://www.ssga.com/us/en/intermediary/etfs/state-street-communication-services-select-sector-spdr-etf-xlc", "individual_fund_page_benchmark_and_holdings_available"),
        "XLI": ("https://www.ssga.com/us/en/intermediary/etfs/state-street-industrial-select-sector-spdr-etf-xli", "individual_fund_page_benchmark_and_holdings_available"),
        "XLP": ("https://www.ssga.com/us/en/intermediary/etfs/state-street-consumer-staples-select-sector-spdr-etf-xlp", "individual_fund_page_benchmark_and_holdings_available"),
        "XLE": ("https://www.ssga.com/us/en/intermediary/etfs/state-street-energy-select-sector-spdr-etf-xle", "individual_fund_page_benchmark_and_holdings_available"),
        "XLRE": ("https://www.ssga.com/us/en/intermediary/etfs/real-estate-select-sector-spdr-fund-xlre", "individual_fund_page_benchmark_and_holdings_available"),
    }
    if report.empty or "queue_priority" not in report.columns:
        return pd.DataFrame(columns=columns)
    pending = report[
        report["queue_priority"].astype(str).eq("P3_benchmark_mapping")
    ].copy()
    if pending.empty:
        return pd.DataFrame(columns=columns)
    benchmark_scope_notes = {
        "SOXX": "Tracks the NYSE Semiconductor Index; compare issuer revenue mix with semiconductor design, manufacturing, equipment and related businesses.",
        "XLK": "Technology Select Sector Index covers S&P 500 technology industries including hardware, software, communications equipment, semiconductors and IT services; broad coverage can overlap with specialist sectors.",
        "XLF": "Financial Select Sector Index; verify financial-services business model, including banks, insurers, capital markets, exchanges and payment networks.",
        "XLY": "Consumer Discretionary Select Sector Index; distinguish discretionary consumer spending from staples, travel platforms and auto-related business models.",
        "XLV": "Health Care Select Sector Index; verify healthcare equipment, services, pharmaceuticals and biotechnology exposure.",
        "XLC": "Communication Services Select Sector Index; verify telecom, media, entertainment and interactive-platform classification.",
        "XLI": "Industrials Select Sector Index; verify industrial products, transportation, aerospace/defense and business-services exposure.",
        "XLP": "Consumer Staples Select Sector Index; verify essential consumer goods, food retail and household/personal products exposure.",
        "XLE": "Energy Select Sector Index; verify energy-sector business exposure rather than broad commodity sensitivity alone.",
        "XLRE": "Real Estate Select Sector Index; verify real-estate ownership, operation and REIT business exposure.",
    }
    for col in ("proposed_sector", "suggested_sector_benchmark", "sector_benchmark",
                "suggested_sector_benchmark_active", "suggested_sector_benchmark_latest_date"):
        if col not in pending.columns:
            pending[col] = ""
    pending["proposed_sector"] = pending["proposed_sector"].fillna("").astype(str).str.strip()
    pending["suggested_sector_benchmark"] = pending["suggested_sector_benchmark"].fillna("").astype(str).str.strip()
    pending = pending[pending["suggested_sector_benchmark"].ne("")]
    if pending.empty:
        return pd.DataFrame(columns=columns)
    pending["sector_benchmark"] = pending["sector_benchmark"].fillna("").astype(str).str.strip()
    pending["suggested_sector_benchmark_active"] = pending["suggested_sector_benchmark_active"].fillna("").astype(str).str.lower().isin({"true", "1", "yes"})
    rows = []
    for (sector, benchmark), group in pending.groupby(["proposed_sector", "suggested_sector_benchmark"], dropna=False, sort=True):
        approved = group["sector_benchmark"].eq(benchmark).sum()
        dates = group["suggested_sector_benchmark_latest_date"].fillna("").astype(str).str.strip()
        dates = dates[dates.ne("")]
        rows.append({
            "proposed_sector": sector,
            "suggested_sector_benchmark": benchmark,
            "candidate_count": int(group["symbol"].nunique()),
            "candidate_symbols": ";".join(sorted(group["symbol"].astype(str).str.strip().unique())),
            "approved_sector_benchmark_count": int(approved),
            "suggested_etf_active": bool(group["suggested_sector_benchmark_active"].all()),
            "suggested_etf_latest_date": dates.max() if not dates.empty else "",
            "issuer_reference_url": official_refs.get(benchmark, (issuer_lineup_url, "issuer_lineup_only_not_index_methodology"))[0],
            "reference_scope": official_refs.get(benchmark, (issuer_lineup_url, "issuer_lineup_only_not_index_methodology"))[1],
            "official_index_methodology_url": "https://www.spglobal.com/spdji/en/landing/investment-themes/select-sector/",
            "benchmark_scope_note": benchmark_scope_notes.get(benchmark, "Confirm official index methodology and sector boundaries before mapping."),
            "index_methodology_review_status": "needs_constituent_and_sector_fit_review",
            "review_status": "provisional_not_approved",
            "review_action": "Check official index methodology and current holdings against candidate business; lineup-only references are not enough for approval; keep mappings unapproved until evidence supports approval",
        })
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["candidate_count", "proposed_sector", "suggested_sector_benchmark"],
        ascending=[False, True, True],
    ).reset_index(drop=True)


def build_benchmark_candidate_review(report: pd.DataFrame) -> pd.DataFrame:
    """Expand sector benchmark batches into one non-approving checklist row per candidate."""
    columns = [
        "symbol", "name", "proposed_sector", "suggested_sector_benchmark",
        "current_sector_benchmark", "issuer_evidence_url", "fund_reference_url",
        "official_index_methodology_url", "official_taxonomy_evidence_url", "official_taxonomy_evidence_note", "sector_scope_note",
        "official_holdings_observed_date", "secondary_holdings_observed_date",
        "membership_evidence_url", "membership_evidence_source_type",
        "business_fit_status", "business_fit_evidence_note", "business_fit_review_flag", "business_fit_review_action", "business_fit_review_standard", "index_membership_status", "mapping_status",
    ]
    if report.empty or "queue_priority" not in report.columns:
        return pd.DataFrame(columns=columns)
    pending = report[report["queue_priority"].astype(str).eq("P3_benchmark_mapping")].copy()
    if pending.empty:
        return pd.DataFrame(columns=columns)
    fund_urls = {
        "SOXX": "https://www.ishares.com/us/products/239705/ishares-phlx-semiconductor-etf",
        "XLK": "https://www.ssga.com/us/en/intermediary/etfs/state-street-technology-select-sector-spdr-etf-xlk",
        "XLF": "https://www.ssga.com/us/en/intermediary/etfs/state-street-financial-select-sector-spdr-etf-xlf",
        "XLY": "https://www.ssga.com/us/en/intermediary/etfs/state-street-consumer-discretionary-select-sector-spdr-etf-xly",
        "XLV": "https://www.ssga.com/us/en/intermediary/etfs/state-street-health-care-select-sector-spdr-etf-xlv",
        "XLC": "https://www.ssga.com/us/en/intermediary/etfs/state-street-communication-services-select-sector-spdr-etf-xlc",
        "XLI": "https://www.ssga.com/us/en/intermediary/etfs/state-street-industrial-select-sector-spdr-etf-xli",
        "XLP": "https://www.ssga.com/us/en/intermediary/etfs/state-street-consumer-staples-select-sector-spdr-etf-xlp",
        "XLE": "https://www.ssga.com/us/en/intermediary/etfs/state-street-energy-select-sector-spdr-etf-xle",
        "XLRE": "https://www.ssga.com/us/en/intermediary/etfs/real-estate-select-sector-spdr-fund-xlre",
    }
    scope_notes = {
        "SOXX": "Semiconductor design, manufacturing, equipment and related business exposure",
        "XLK": "Technology industries; check overlap with specialist sectors",
        "XLF": "Banks, insurers, capital markets, exchanges and payment networks",
        "XLY": "Discretionary consumer spending, retail, travel and autos",
        "XLV": "Healthcare equipment, services, pharmaceuticals and biotechnology",
        "XLC": "Telecom, media, entertainment and interactive platforms",
        "XLI": "Industrial products, transportation, aerospace/defense and business services",
        "XLP": "Essential consumer goods, food retail and household/personal products",
        "XLE": "Energy-sector business exposure, not commodity sensitivity alone",
        "XLRE": "Real-estate ownership, operations and REIT exposure",
    }
    for col in columns:
        if col not in pending.columns:
            pending[col] = ""
    pending["fund_reference_url"] = pending["suggested_sector_benchmark"].map(fund_urls).fillna("")
    # Curated official company pages collected for the first semiconductor review batch.
    # These links provide business evidence to inspect; they do not certify a sector mapping.
    issuer_evidence_urls = {
        "ADI": "https://investor.analog.com/about-adi/company-overview/",
        "AMAT": "https://www.appliedmaterials.com/us/en/about.html",
        "AMD": "https://www.amd.com/en/corporate.html",
        "KLAC": "https://ir.kla.com/company-information",
        "LRCX": "https://www.lamresearch.com/company/company-overview/",
        "MRVL": "https://investor.marvell.com/",
        "AVGO": "https://www.broadcom.com/company",
        "INTC": "https://www.intel.com/content/www/us/en/company-overview/company-overview.html",
        "MU": "https://www.micron.com/about/company/corporate-profile",
        "NVDA": "https://www.nvidia.com/en-us/about-nvidia/",
        "QCOM": "https://www.qualcomm.com/company",
        "TXN": "https://www.ti.com/about-ti.html",
        # Communication services
        "APP": "https://www.applovin.com/",
        "CMCSA": "https://corporate.comcast.com/",
        "GOOG": "https://abc.xyz/",
        "GOOGL": "https://abc.xyz/",
        "META": "https://about.meta.com/",
        "WBD": "https://www.wbd.com/",
        # Energy
        "XOM": "https://corporate.exxonmobil.com/",
        # Financials
        "BRK/A": "https://www.berkshirehathaway.com/",
        "BRK/B": "https://www.berkshirehathaway.com/",
        "CME": "https://www.cmegroup.com/company.html",
        "GS": "https://www.goldmansachs.com/",
        "JPM": "https://www.jpmorganchase.com/",
        "MA": "https://www.mastercard.com/global/en/vision/who-we-are.html",
        "MS": "https://www.morganstanley.com/about-us",
        "NDAQ": "https://www.nasdaq.com/about",
        "V": "https://corporate.visa.com/en/about-visa.html",
        "WFC": "https://www.wellsfargo.com/about/",
        # Industrials
        "ADP": "https://www.adp.com/about-adp.aspx",
        "CSX": "https://www.csx.com/index.cfm/about-us/",
        "GE": "https://www.geaerospace.com/company",
        "HON": "https://www.honeywell.com/us/en/company",
        "RTX": "https://www.rtx.com/our-company",
        # Information technology
        "AAPL": "https://www.apple.com/",
        "CDNS": "https://www.cadence.com/en_US/home/company.html",
        "CRWD": "https://www.crowdstrike.com/about-us/",
        "DDOG": "https://www.datadoghq.com/about/",
        "FTNT": "https://www.fortinet.com/corporate/about-us",
        "INTU": "https://www.intuit.com/company/",
        "MSFT": "https://www.microsoft.com/en-us/about",
        "PANW": "https://www.paloaltonetworks.com/company",
        "SHOP": "https://www.shopify.com/about",
        "SNPS": "https://www.synopsys.com/company.html",
        "WDC": "https://www.westerndigital.com/company",
        # Consumer staples
        "MNST": "https://www.monsterbevcorp.com/",
        "PEP": "https://www.pepsico.com/about",
        "WMT": "https://corporate.walmart.com/about",
        # Real estate
        "EQIX": "https://www.equinix.com/about",
        # Health care
        "ABBV": "https://www.abbvie.com/our-company.html",
        "GILD": "https://www.gilead.com/company",
        "ISRG": "https://www.intuitive.com/en-us/about-us",
        "JNJ": "https://www.jnj.com/our-company",
        "LLY": "https://www.lilly.com/who-we-are",
        "REGN": "https://www.regeneron.com/about",
        "TMO": "https://corporate.thermofisher.com/us/en/index.html",
        "VRTX": "https://www.vrtx.com/about-us/",
        # Consumer discretionary
        "ABNB": "https://news.airbnb.com/about-us/",
        "AMZN": "https://www.aboutamazon.com/",
        "BKNG": "https://www.bookingholdings.com/about/",
        "DASH": "https://about.doordash.com/",
        "MAR": "https://www.marriott.com/marriott/aboutmarriott.mi",
        "ORLY": "https://corporate.oreillyauto.com/",
        "ROST": "https://www.rossstores.com/",
        "TSLA": "https://www.tesla.com/about",
    }
    pending["issuer_evidence_url"] = pending["symbol"].map(issuer_evidence_urls).fillna("")
    pending["official_index_methodology_url"] = "https://www.msci.com/indexes/index-resources/gics"
    # Record issuer-specific classification evidence only where an authoritative
    # source was located; do not infer a complete mapping approval from it.
    taxonomy_evidence_urls = {
        "APP": "https://app2.msci.com/webapp/index_ann/DocGet?format=html&lang=en&pub_key=vy22KGhm2eA%3D",
        "BRK/A": "https://www.msci.com/documents/1296102/34913405/MSCI%2BBusiness%2BSegment%2BData%2BProduct%2BBrochure.pdf/409e50f3-fa44-5e50-7f32-46a487e11632?t=1723241386037",
        "BRK/B": "https://www.msci.com/documents/1296102/34913405/MSCI%2BBusiness%2BSegment%2BData%2BProduct%2BBrochure.pdf/409e50f3-fa44-5e50-7f32-46a487e11632?t=1723241386037",
        "AMZN": "https://app2.msci.com/webapp/index_ann/DocGet?format=html&lang=en&pub_key=9piYXWAaifg%3D",
        "ADP": "https://app2.msci.com/webapp/index_ann/DocGet?format=html&lang=en&pub_key=9piYXWAaifg%3D",
        "DASH": "https://app2.msci.com/webapp/index_ann/DocGet?format=html&lang=en&pub_key=9piYXWAaifg%3D",
        "NDAQ": "https://www.sec.gov/Archives/edgar/data/1408198/000140819826000023/msci-20260310.htm",
        "CME": "https://www.sec.gov/Archives/edgar/data/1408198/000140819826000023/msci-20260310.htm",
        "GOOG": "https://www.msci.com/documents/10199/9a860d20-008a-90ee-fbdb-ae462e24c8f8",
        "GOOGL": "https://www.msci.com/documents/10199/9a860d20-008a-90ee-fbdb-ae462e24c8f8",
        "AVGO": "https://www.msci.com/documents/10199/9a860d20-008a-90ee-fbdb-ae462e24c8f8",
        "CDNS": "https://www.msci.com/documents/10199/9a860d20-008a-90ee-fbdb-ae462e24c8f8",
        "AAPL": "https://www.msci.com/documents/10199/178e6643-6ae6-47b9-82be-e1fc565ededb",
        "NVDA": "https://www.msci.com/documents/10199/178e6643-6ae6-47b9-82be-e1fc565ededb",
        "MSFT": "https://www.msci.com/documents/10199/178e6643-6ae6-47b9-82be-e1fc565ededb",
        "META": "https://www.msci.com/documents/10199/178e6643-6ae6-47b9-82be-e1fc565ededb",
        "TSLA": "https://www.msci.com/documents/10199/178e6643-6ae6-47b9-82be-e1fc565ededb",
        "JPM": "https://www.msci.com/documents/10199/178e6643-6ae6-47b9-82be-e1fc565ededb",
    }
    taxonomy_evidence_notes = {
        "APP": "MSCI 2026-07-01 announcement: GICS sub-industry changed from Application Software to Advertising effective 2026-07-31; consistent with the Communication Services sector proposal, but not by itself ETF benchmark approval.",
        "BRK/A": "MSCI business-segment example (as of 2024-02-29) places Berkshire Hathaway in Financials / Multi-Sector Holdings; A-share identity is a separate gate.",
        "BRK/B": "MSCI business-segment example (as of 2024-02-29) places Berkshire Hathaway in Financials / Multi-Sector Holdings; B-share identity is a separate gate.",
        "AMZN": "MSCI GICS change announcement lists AMAZON.COM moving from Internet & Direct Marketing Retail to Broadline Retail; supports reviewing Consumer Discretionary rather than assuming a technology classification from AWS.",
        "ADP": "MSCI GICS change announcement lists AUTOMATIC DATA PROCESS moving from Data Processing & Outsourced Services to Human Resource & Employment Services; supports Industrials classification, subject to current classification and proxy review.",
        "DASH": "MSCI GICS change announcement lists DOORDASH A moving from Internet & Direct Marketing Retail to Restaurants; supports Consumer Discretionary classification, subject to current classification and proxy review.",
        "NDAQ": "MSCI Inc. 2026 proxy statement lists Nasdaq, Inc. in Financial Services—Capital Markets—Financial Exchanges and Data; supports a Financials benchmark, not a general IT mapping.",
        "CME": "MSCI Inc. 2026 proxy statement lists CME Group in Financial Services—Capital Markets—Financial Exchanges and Data; supports a Financials benchmark.",
        "GOOG": "MSCI Global Transformational Changes Index factsheet dated 2026-04-30 lists Alphabet A in Communication Services; issuer-sector cross-check only, with C-share identity and ETF benchmark fit as separate gates.",
        "GOOGL": "MSCI Global Transformational Changes Index factsheet dated 2026-04-30 lists Alphabet A in Communication Services; supports issuer-sector cross-check only and does not resolve this share class's identity gate.",
        "AVGO": "MSCI Global Transformational Changes Index factsheet dated 2026-04-30 lists Broadcom in Information Technology; issuer-sector cross-check only, not proof that SOXX is the best relative-strength benchmark.",
        "CDNS": "MSCI Global Transformational Changes Index factsheet dated 2026-04-30 lists Cadence Design Systems in Information Technology; issuer-sector cross-check only, not proof that XLK is the best relative-strength benchmark.",
        "AAPL": "MSCI World Index factsheet dated 2026-03-31 lists Apple in Information Technology; sector cross-check only, not proof that XLK is the best relative-strength benchmark.",
        "NVDA": "MSCI World Index factsheet dated 2026-03-31 lists NVIDIA in Information Technology; sector cross-check only, not proof that SOXX is the best relative-strength benchmark.",
        "MSFT": "MSCI World Index factsheet dated 2026-03-31 lists Microsoft in Information Technology; sector cross-check only, not proof that XLK is the best relative-strength benchmark.",
        "META": "MSCI World Index factsheet dated 2026-03-31 lists Meta Platforms in Communication Services; sector cross-check only, not proof that XLC is the best relative-strength benchmark.",
        "TSLA": "MSCI World Index factsheet dated 2026-03-31 lists Tesla in Consumer Discretionary; sector cross-check only, not proof that XLY is the best relative-strength benchmark.",
        "JPM": "MSCI World Index factsheet dated 2026-03-31 lists JPMorgan Chase in Financials; sector cross-check only, not proof that XLF is the best relative-strength benchmark.",
    }
    pending["official_taxonomy_evidence_url"] = pending["symbol"].map(taxonomy_evidence_urls).fillna("")
    pending["official_taxonomy_evidence_note"] = pending["symbol"].map(taxonomy_evidence_notes).fillna("")
    pending["sector_scope_note"] = pending["suggested_sector_benchmark"].map(scope_notes).fillna("Review official sector definitions")
    # Explicitly record only holdings membership visible in the official top-holdings
    # extracts reviewed so far. Absence from a top-holdings excerpt is not evidence
    # of absence from the full portfolio; those cases require a full holdings-file check.
    confirmed_top_holdings = {
        ("AMD", "SOXX"): "2026-10-20",
        ("INTC", "SOXX"): "2026-10-20",
        ("NVDA", "SOXX"): "2026-10-20",
        ("MU", "SOXX"): "2026-10-20",
        ("AVGO", "SOXX"): "2026-10-20",
        ("MRVL", "SOXX"): "2026-10-20",
        ("ADI", "SOXX"): "2026-10-20",
        ("TXN", "SOXX"): "2026-10-20",
        ("QCOM", "SOXX"): "2026-10-20",
        ("KLAC", "SOXX"): "2026-10-20",
        ("AMAT", "SOXX"): "2026-09-10",
        ("LRCX", "SOXX"): "2026-09-10",
        ("AAPL", "XLK"): "2026-10-22",
        ("LRCX", "XLK"): "2026-10-21",
        ("MSFT", "XLK"): "2026-10-22",
        ("XOM", "XLE"): "2026-10-19",
        ("WMT", "XLP"): "2026-10-08",
        ("PEP", "XLP"): "2026-10-08",
        ("EQIX", "XLRE"): "2026-10-20",
        ("LLY", "XLV"): "2026-10-23",
        ("JNJ", "XLV"): "2026-10-23",
        ("ABBV", "XLV"): "2026-10-23",
        ("TMO", "XLV"): "2026-10-23",
        ("GILD", "XLV"): "2026-10-23",
        ("AMZN", "XLY"): "2026-10-20",
        ("TSLA", "XLY"): "2026-10-20",
        ("BKNG", "XLY"): "2026-10-20",
        ("MAR", "XLY"): "2026-10-20",
        ("DASH", "XLY"): "2026-10-09",
        ("ROST", "XLY"): "2026-10-07",
        ("GE", "XLI"): "2026-10-20",
        ("RTX", "XLI"): "2026-10-20",
        ("META", "XLC"): "2026-10-08",
        ("GOOG", "XLC"): "2026-10-08",
        ("GOOGL", "XLC"): "2026-10-08",
        ("WBD", "XLC"): "2026-09-22",
        ("CMCSA", "XLC"): "2026-09-17",
        ("APP", "XLC"): "2026-10-08",
        ("BRK/B", "XLF"): "2026-10-20",
        ("JPM", "XLF"): "2026-10-20",
        ("V", "XLF"): "2026-10-20",
        ("MA", "XLF"): "2026-10-20",
        ("GS", "XLF"): "2026-10-20",
        ("WFC", "XLF"): "2026-10-20",
        ("MS", "XLF"): "2026-10-20",
    }
    # Older/alternate official State Street factsheets are tracked separately
    # from current top-holdings excerpts for the exact US-listed fund.
    secondary_holdings = {
        # Older/alternate official State Street factsheets are tracked separately
        # from current top-holdings excerpts for the exact US-listed fund.
        ("HON", "XLI"): ("2026-03", "https://www.ssga.com/library-content/products/factsheets/etfs/us/factsheet-us-en-xli.pdf", "alternate_official_etf_factsheet", "alternate_official_reference_only"),
        ("MNST", "XLP"): ("2025-11", "https://www.ssga.com/library-content/products/factsheets/etfs/emea/factsheet-emea-nl-zpds-gy.pdf", "alternate_official_etf_factsheet", "alternate_official_reference_only"),
        # Third-party page exposes the full XLY holdings list as of 2026-10-23;
        # unlike issuer top-ten excerpts, this supports checking names lower in the list.
        ("ABNB", "XLY"): ("2026-10-23", "https://www.schwab.wallst.com/schwab/Prospect/research/etfs/schwabETF/index.asp?YYY101_z5K6INmijHnCpVtklYGW7bkbAapCho0FetK1sJkm0JpSnkpN8yChbE2TAtJ5sgDTjvuMuZ5w4lZVVHRABNHHRdIp7wnyzADtSf%2FF7mBhm5Q=&symbol=XLY&type=holdings", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        ("ORLY", "XLY"): ("2026-10-23", "https://www.schwab.wallst.com/schwab/Prospect/research/etfs/schwabETF/index.asp?YYY101_z5K6INmijHnCpVtklYGW7bkbAapCho0FetK1sJkm0JpSnkpN8yChbE2TAtJ5sgDTjvuMuZ5w4lZVVHRABNHHRdIp7wnyzADtSf%2FF7mBhm5Q=&symbol=XLY&type=holdings", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        # Full holdings pages, distinct from issuer top-holdings excerpts.
        ("ADP", "XLI"): ("2026-10-23", "https://www.schwab.wallst.com/schwab/Prospect/research/etfs/schwabETF/index.asp?YYY101_z5K6INmijHnPw1uFe+r9iJB6xIutk7V3PcX8IKx%2Fa+4JprkqnVhzrO5WmXZnUo5FDx3QLs1gxi6fXolyHp3r9z3uSDakWFICy%2FyLZZn1b6Q=&symbol=XLI&type=holdings", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        ("CSX", "XLI"): ("2026-10-23", "https://www.schwab.wallst.com/schwab/Prospect/research/etfs/schwabETF/index.asp?YYY101_z5K6INmijHnPw1uFe+r9iJB6xIutk7V3PcX8IKx%2Fa+4JprkqnVhzrO5WmXZnUo5FDx3QLs1gxi6fXolyHp3r9z3uSDakWFICy%2FyLZZn1b6Q=&symbol=XLI&type=holdings", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        ("ISRG", "XLV"): ("2026-09-28", "https://www.schwab.wallst.com/schwab/Prospect/research/etfs/schwabETF/index.asp?YYY101_z5K6INmijHk7aTSca21P6p0AwqW%2FsobvsYMc1KlgXFKu9CdAhwwyYM9%2FmfqP0pX55DqmtK7s+l3jL+Oh43OJJliAH99o3aofzJbj8rKo7JU=&symbol=XLV&type=holdings", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        ("REGN", "XLV"): ("2026-09-28", "https://www.schwab.wallst.com/schwab/Prospect/research/etfs/schwabETF/index.asp?YYY101_z5K6INmijHk7aTSca21P6p0AwqW%2FsobvsYMc1KlgXFKu9CdAhwwyYM9%2FmfqP0pX55DqmtK7s+l3jL+Oh43OJJliAH99o3aofzJbj8rKo7JU=&symbol=XLV&type=holdings", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        ("VRTX", "XLV"): ("2026-09-28", "https://www.schwab.wallst.com/schwab/Prospect/research/etfs/schwabETF/index.asp?YYY101_z5K6INmijHk7aTSca21P6p0AwqW%2FsobvsYMc1KlgXFKu9CdAhwwyYM9%2FmfqP0pX55DqmtK7s+l3jL+Oh43OJJliAH99o3aofzJbj8rKo7JU=&symbol=XLV&type=holdings", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        # Full third-party XLK holdings list dated 2026-10-22 includes these names
        # below the official fund top-holdings excerpt.
        ("CDNS", "XLK"): ("2026-10-22", "https://etfiq.com/funds/xlk/holdings/", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        ("CRWD", "XLK"): ("2026-10-22", "https://etfiq.com/funds/xlk/holdings/", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        ("DDOG", "XLK"): ("2026-10-22", "https://etfiq.com/funds/xlk/holdings/", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        ("FTNT", "XLK"): ("2026-10-22", "https://etfiq.com/funds/xlk/holdings/", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        ("INTU", "XLK"): ("2026-10-22", "https://etfiq.com/funds/xlk/holdings/", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        ("PANW", "XLK"): ("2026-10-22", "https://etfiq.com/funds/xlk/holdings/", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        ("SHOP", "XLK"): ("2026-10-22", "https://etfiq.com/funds/xlk/holdings/", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        ("SNPS", "XLK"): ("2026-10-22", "https://etfiq.com/funds/xlk/holdings/", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        ("WDC", "XLK"): ("2026-10-22", "https://etfiq.com/funds/xlk/holdings/", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        ("CME", "XLF"): ("2026-10-22", "https://etfiq.com/funds/xlf/holdings/", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
        # Full XLK/XLF holdings lists use the ETF issuer daily holdings data.
        ("NDAQ", "XLF"): ("2026-10-22", "https://etfiq.com/funds/xlf/holdings/", "third_party_full_holdings_list", "confirmed_in_secondary_full_holdings_list"),
    }
    pending["official_holdings_observed_date"] = pending.apply(
        lambda row: confirmed_top_holdings.get(
            (str(row["symbol"]), str(row["suggested_sector_benchmark"])), ""
        ),
        axis=1,
    )
    pending["secondary_holdings_observed_date"] = pending.apply(
        lambda row: secondary_holdings.get(
            (str(row["symbol"]), str(row["suggested_sector_benchmark"])), ("", "", "", "")
        )[0],
        axis=1,
    )
    pending["membership_evidence_url"] = pending.apply(
        lambda row: (
            fund_urls.get(str(row["suggested_sector_benchmark"]), "")
            if (str(row["symbol"]), str(row["suggested_sector_benchmark"])) in confirmed_top_holdings
            else secondary_holdings.get(
                (str(row["symbol"]), str(row["suggested_sector_benchmark"])), ("", "", "", "")
            )[1]
        ),
        axis=1,
    )
    pending["membership_evidence_source_type"] = pending.apply(
        lambda row: (
            "official_etf_issuer_top_holdings_excerpt"
            if (str(row["symbol"]), str(row["suggested_sector_benchmark"])) in confirmed_top_holdings
            else secondary_holdings.get(
                (str(row["symbol"]), str(row["suggested_sector_benchmark"])), ("", "", "not_yet_confirmed", "")
            )[2]
        ),
        axis=1,
    )
    business_fit_notes = {
        "ADI": "Analog Devices designs and manufactures analog, mixed-signal and digital signal-processing semiconductors; supports Semiconductors.",
        "AMAT": "Applied Materials supplies materials-engineering equipment used in semiconductor and display manufacturing; Semiconductors benchmark fit is plausible but equipment exposure should be reviewed.",
        "AMD": "AMD develops CPUs, GPUs and adaptive computing products; supports Semiconductors.",
        "AVGO": "Broadcom develops semiconductor products and infrastructure software; semiconductor benchmark fit is plausible, with software mix noted.",
        "INTC": "Intel designs and manufactures processors and semiconductor products; supports Semiconductors.",
        "KLAC": "KLA supplies process-control and yield-management systems for semiconductor manufacturing; semiconductor-equipment exposure supports the proposed group.",
        "LRCX": "Lam Research supplies wafer-fabrication equipment and services; supports the semiconductor-equipment group.",
        "MRVL": "Marvell develops semiconductor solutions for data infrastructure; supports Semiconductors.",
        "MU": "Micron develops and manufactures memory and storage products; supports Semiconductors.",
        "NVDA": "NVIDIA develops accelerated-computing platforms and GPUs; supports Semiconductors, while platform/software exposure should be noted.",
        "QCOM": "Qualcomm develops wireless communications technologies and semiconductor products; supports Semiconductors.",
        "TXN": "Texas Instruments designs and manufactures analog and embedded-processing semiconductors; supports Semiconductors.",
        "APP": "AppLovin provides mobile advertising technology and software; Communication Services versus Information Technology taxonomy fit needs review.",
        "CMCSA": "Comcast operates connectivity and media businesses; supports Communication Services.",
        "GOOG": "Alphabet's Google business includes internet search, digital advertising and online platforms; supports Communication Services, subject to share-class identity handling.",
        "GOOGL": "Alphabet's Google business includes internet search, digital advertising and online platforms; supports Communication Services, subject to share-class identity handling.",
        "META": "Meta operates social networking and digital communication platforms funded substantially by advertising; supports Communication Services.",
        "WBD": "Warner Bros. Discovery operates film, television and streaming media businesses; supports Communication Services.",
        "XOM": "Issuer describes upstream oil and natural gas plus fuels and chemicals businesses; supports Energy, subject to taxonomy review.",
        "BRK/A": "Berkshire Hathaway is a diversified holding company with insurance, rail, energy and other operating businesses; Financials classification needs taxonomy review and share-class handling.",
        "BRK/B": "Berkshire Hathaway is a diversified holding company with insurance, rail, energy and other operating businesses; Financials classification needs taxonomy review and share-class handling.",
        "CME": "Issuer describes futures, options and other derivatives exchanges across financial and commodity asset classes; supports Financials/capital markets.",
        "GS": "Goldman Sachs provides investment banking, markets, asset and wealth-management services; supports Financials.",
        "JPM": "JPMorgan Chase is a diversified banking and financial-services company; supports Financials.",
        "MA": "Mastercard operates a global payment network; supports Financials/payment networks.",
        "MS": "Morgan Stanley provides investment banking, securities, wealth and investment management; supports Financials.",
        "NDAQ": "Issuer describes a global technology company serving capital markets; Financials versus Information Technology boundary requires taxonomy review.",
        "V": "Visa operates a global electronic payments network; supports Financials/payment networks.",
        "WFC": "Wells Fargo is a diversified banking and financial-services company; supports Financials.",
        "ADP": "ADP provides payroll, human-resources and workforce-management services; Industrials classification versus business-services taxonomy needs review.",
        "CSX": "CSX operates freight rail transportation; supports Industrials/transportation.",
        "GE": "GE Aerospace develops and services aircraft engines and related systems; supports Industrials/aerospace.",
        "HON": "Honeywell provides industrial automation, aerospace and building technologies; supports Industrials, subject to current corporate-structure review.",
        "RTX": "RTX provides aerospace and defense systems and services; supports Industrials/aerospace and defense.",
        "AAPL": "Apple designs consumer devices and related software and services; Information Technology fit is plausible, subject to GICS subindustry review.",
        "CDNS": "Cadence provides electronic-design automation software and engineering services; supports Information Technology, subject to software classification review.",
        "CRWD": "CrowdStrike provides cybersecurity software and services; supports Information Technology.",
        "DDOG": "Datadog provides cloud monitoring and observability software; supports Information Technology.",
        "FTNT": "Fortinet provides cybersecurity products and services; supports Information Technology.",
        "INTU": "Intuit provides financial-management and tax software; supports Information Technology, with financial-software business mix noted.",
        "MSFT": "Microsoft provides software, cloud infrastructure and productivity services; supports Information Technology.",
        "PANW": "Palo Alto Networks provides cybersecurity platforms and services; supports Information Technology.",
        "SHOP": "Shopify provides commerce software and merchant services; Information Technology versus Consumer Discretionary classification needs review.",
        "SNPS": "Synopsys provides electronic-design automation and semiconductor IP software; supports Information Technology.",
        "WDC": "Western Digital develops data-storage devices and technologies; Information Technology fit is plausible, subject to current corporate-structure review.",
        "MNST": "Monster Beverage develops and markets energy drinks; Consumer Staples fit is plausible, subject to beverage subindustry review.",
        "PEP": "PepsiCo manufactures and distributes beverages and convenient foods; supports Consumer Staples.",
        "WMT": "Walmart operates retail stores and e-commerce; Consumer Staples benchmark fit is plausible, with retail classification reviewed against the chosen taxonomy.",
        "ABBV": "AbbVie develops and commercializes medicines across immunology, oncology and other therapeutic areas; supports Health Care.",
        "GILD": "Gilead Sciences develops antiviral and other medicines; supports Health Care.",
        "ISRG": "Intuitive Surgical develops robotic-assisted surgery systems and related instruments; supports Health Care/medical devices.",
        "JNJ": "Johnson & Johnson operates innovative medicine and med-tech businesses; supports Health Care, with current segment mix noted.",
        "LLY": "Eli Lilly develops and commercializes medicines across diabetes, obesity, oncology and other therapeutic areas; supports Health Care.",
        "REGN": "Regeneron develops medicines and biotechnology products; supports Health Care/biotechnology.",
        "TMO": "Thermo Fisher Scientific supplies life-sciences tools, diagnostics and laboratory services; supports Health Care, subject to tools-versus-services taxonomy review.",
        "VRTX": "Vertex Pharmaceuticals develops medicines for serious diseases; supports Health Care/biotechnology.",
        "ABNB": "Airbnb operates an online marketplace for lodging and travel experiences; Consumer Discretionary fit is plausible, subject to platform classification review.",
        "AMZN": "Amazon operates e-commerce, cloud computing and related businesses; Consumer Discretionary benchmark fit needs review because AWS is a material non-retail segment.",
        "BKNG": "Booking Holdings operates online travel reservation brands; supports Consumer Discretionary/travel services.",
        "DASH": "DoorDash operates local commerce and food-delivery marketplaces; Consumer Discretionary fit is plausible, subject to platform classification review.",
        "MAR": "Marriott International operates and franchises lodging brands; supports Consumer Discretionary/travel and leisure.",
        "ORLY": "O'Reilly Automotive operates retail stores selling automotive aftermarket parts; supports Consumer Discretionary/retail.",
        "ROST": "Ross Stores operates off-price apparel and home-fashion retail stores; supports Consumer Discretionary/retail.",
        "TSLA": "Tesla develops electric vehicles, energy generation and storage products; Consumer Discretionary fit is plausible, with energy segment overlap noted.",
        "EQIX": "SEC filing describes a data-center operator that operates as a REIT; supports Real Estate, with digital-infrastructure overlap noted.",
        "CME": "Issuer describes futures, options and other derivatives exchanges across financial and commodity asset classes; supports Financials/capital markets.",
        "NDAQ": "Issuer describes a global technology company serving capital markets; Financials versus Information Technology boundary requires taxonomy review.",
    }
    pending["business_fit_status"] = "pending_issuer_business_review"
    pending["business_fit_evidence_note"] = pending["symbol"].map(business_fit_notes).fillna("")
    taxonomy_boundary_symbols = {
        "AVGO", "NVDA", "APP", "NDAQ", "BRK/A", "BRK/B",
        "ADP", "HON", "SHOP", "WDC", "AMZN", "TSLA",
    }
    share_class_identity_symbols = {"GOOG", "GOOGL"}
    pending["business_fit_review_flag"] = pending["symbol"].map(
        lambda symbol: (
            "priority_taxonomy_or_business_mix_review"
            if str(symbol) in taxonomy_boundary_symbols
            else (
                "share_class_identity_review"
                if str(symbol) in share_class_identity_symbols
                else "standard_business_fit_review"
            )
        )
    )
    # Actionable review directions only; these do not approve sector mappings.
    review_actions = {
        "AVGO": "반도체와 인프라 소프트웨어 사업 비중을 함께 확인",
        "NVDA": "반도체 제품과 컴퓨팅 플랫폼·소프트웨어 범위를 함께 확인",
        "APP": "광고기술·소프트웨어 기업의 분류 기준을 GICS 정의와 대조",
        "NDAQ": "거래소 사업과 금융시장 기술 사업의 분류 경계를 확인",
        "BRK/A": "복합 지주회사 분류 기준과 A주 종목 식별을 별도로 확인",
        "BRK/B": "복합 지주회사 분류 기준과 B주 종목 식별을 별도로 확인",
        "ADP": "급여·인사 서비스의 업종 분류를 공식 분류 정의와 대조",
        "HON": "현재 사업 포트폴리오와 기업 구조 변경 반영 여부 확인",
        "SHOP": "상거래 소프트웨어와 소비자 플랫폼 중 분류 기준 확인",
        "WDC": "저장장치 사업의 현재 기업 구조와 업종 범위 확인",
        "AMZN": "전자상거래와 AWS를 포함한 사업 구성의 분류 기준 확인",
        "TSLA": "자동차와 에너지 저장 사업을 포함한 분류 기준 확인",
        "GOOG": "Alphabet 발행사 확인 후 C종 주식 식별을 별도 확인",
        "GOOGL": "Alphabet 발행사 확인 후 A종 주식 식별을 별도 확인",
    }
    pending["business_fit_review_action"] = pending["symbol"].map(review_actions).fillna(
        "발행사 공식 사업 설명과 제안 업종 정의를 대조; 근거 확인 전 승인 보류"
    )
    # Apply one consistent evidence hierarchy to every provisional mapping.
    # GICS is company-level and principal-business based; ETF membership is a
    # proxy/coverage clue, not proof that the proposed taxonomy is correct.
    pending["business_fit_review_standard"] = (
        "공식 GICS 분류와 발행사 주사업을 우선 대조(매출·이익·시장 인식 고려); "
        "ETF 편입은 보조 근거이며 단독 승인 근거가 아님; 근거 부족 시 미승인 유지"
    )
    pending["index_membership_status"] = pending.apply(
        lambda row: (
            "confirmed_in_official_top_holdings_excerpt"
            if (str(row["symbol"]), str(row["suggested_sector_benchmark"])) in confirmed_top_holdings
            else secondary_holdings.get(
                (str(row["symbol"]), str(row["suggested_sector_benchmark"])), ("", "", "", "needs_full_holdings_list_check")
            )[3]
        ),
        axis=1,
    )
    pending["mapping_status"] = "provisional_not_approved"
    return pending[columns].sort_values(
        ["suggested_sector_benchmark", "proposed_sector", "symbol"]
    ).drop_duplicates(["symbol", "suggested_sector_benchmark"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, default=COVERAGE)
    parser.add_argument("--identity", type=Path, default=IDENTITY)
    parser.add_argument("--market-cap", type=Path, default=MARKET_CAP)
    parser.add_argument("--issuer-evidence", type=Path, default=ISSUER_EVIDENCE)
    parser.add_argument("--yahoo-cap-triage", type=Path, default=YAHOO_CAP_TRIAGE)
    parser.add_argument("--yahoo-cap-observations", type=Path, default=YAHOO_CAP_OBSERVATIONS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=SUMMARY_OUTPUT)
    parser.add_argument("--benchmark-batch-output", type=Path, default=BENCHMARK_BATCH_OUTPUT)
    parser.add_argument("--benchmark-candidate-output", type=Path, default=ROOT / "data" / "sector_benchmark_candidate_review.csv")
    args = parser.parse_args()
    report = build_review_queue(
        pd.read_csv(args.coverage, dtype=str, keep_default_na=False),
        pd.read_csv(args.identity, dtype=str, keep_default_na=False),
        pd.read_csv(args.market_cap, dtype=str, keep_default_na=False),
        pd.read_csv(args.issuer_evidence, dtype=str, keep_default_na=False) if args.issuer_evidence.exists() else None,
        pd.read_csv(args.yahoo_cap_triage, dtype=str, keep_default_na=False) if args.yahoo_cap_triage.exists() else None,
        pd.read_csv(args.yahoo_cap_observations, dtype=str, keep_default_na=False) if args.yahoo_cap_observations.exists() else None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    summary = build_queue_summary(report)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.summary_output, index=False)
    benchmark_batches = build_benchmark_review_batches(report)
    args.benchmark_batch_output.parent.mkdir(parents=True, exist_ok=True)
    benchmark_batches.to_csv(args.benchmark_batch_output, index=False)
    benchmark_candidates = build_benchmark_candidate_review(report)
    args.benchmark_candidate_output.parent.mkdir(parents=True, exist_ok=True)
    benchmark_candidates.to_csv(args.benchmark_candidate_output, index=False)
    print(f"rows={len(report)}")
    print("priority_counts=" + str(report["queue_priority"].value_counts().to_dict()))
    print(f"activation_recommendation_counts={report['activation_recommendation'].value_counts().to_dict()}")
    print(f"report={args.output}")
    print(f"summary_report={args.summary_output}")
    print(f"benchmark_review_batches={len(benchmark_batches)}")
    print(f"benchmark_batch_report={args.benchmark_batch_output}")
    print(f"benchmark_candidate_review_rows={len(benchmark_candidates)}")
    print(f"benchmark_candidate_review_report={args.benchmark_candidate_output}")


if __name__ == "__main__":
    main()
