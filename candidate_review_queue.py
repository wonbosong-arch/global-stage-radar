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
OUTPUT = ROOT / "data" / "candidate_review_queue.csv"
SUMMARY_OUTPUT = ROOT / "data" / "candidate_review_queue_summary.csv"


def build_review_queue(coverage: pd.DataFrame, identity: pd.DataFrame, market_cap: pd.DataFrame, issuer_evidence: pd.DataFrame | None = None, yahoo_cap_triage: pd.DataFrame | None = None) -> pd.DataFrame:
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

    def decide(row: pd.Series) -> tuple[str, str]:
        status = str(row.get("identity_status", "")).strip()
        cap_priority = str(row.get("date_review_priority", "")).strip()
        instrument_type = str(row.get("instrument_type", "")).strip().lower()

        # ADR-specific share-class and depositary-ratio reconciliation is deliberately
        # deferred during MVP completion. Keep ADRs pending; prioritize practical
        # provider and market-cap evidence without auto-verifying or activating them.
        if instrument_type == "adr_candidate":
            if str(row.get("provider_status", "")).strip() not in {"verified", "supported"}:
                return "P3_provider_mapping", "MVP 우선순위: KIS 지원 여부를 먼저 확인하고 ADR 세부 검증은 후순위로 보류"
            if str(row.get("market_cap_status", "")).strip() != "verified":
                return "P3_market_cap_evidence", "MVP 우선순위: 조회 가능한 시가총액 근거만 확인하고 ADR 세부 산식 검증은 후순위로 보류"
            return "P4_final_review", "ADR 추가 검증은 후순위로 보류; 기존 신원·예탁비율 검토 게이트는 미확인 상태로 유지"

        if status in {"issuer_proxy_review_required", "issuer_country_review_required"}:
            return "P1_identity_classification", "상장 거래시장과 발행사 국가/ADR 기준을 분리해 공식 근거 검토"
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
        "P1_identity_classification": 1,
        "P1_market_cap_reconciliation": 2,
        "P2_market_cap_reconciliation": 3,
        "P2_identity_evidence": 4,
        "P3_provider_mapping": 5,
        "P3_market_cap_evidence": 6,
        "P4_final_review": 7,
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

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, default=COVERAGE)
    parser.add_argument("--identity", type=Path, default=IDENTITY)
    parser.add_argument("--market-cap", type=Path, default=MARKET_CAP)
    parser.add_argument("--issuer-evidence", type=Path, default=ISSUER_EVIDENCE)
    parser.add_argument("--yahoo-cap-triage", type=Path, default=YAHOO_CAP_TRIAGE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=SUMMARY_OUTPUT)
    args = parser.parse_args()
    report = build_review_queue(
        pd.read_csv(args.coverage, dtype=str, keep_default_na=False),
        pd.read_csv(args.identity, dtype=str, keep_default_na=False),
        pd.read_csv(args.market_cap, dtype=str, keep_default_na=False),
        pd.read_csv(args.issuer_evidence, dtype=str, keep_default_na=False) if args.issuer_evidence.exists() else None,
        pd.read_csv(args.yahoo_cap_triage, dtype=str, keep_default_na=False) if args.yahoo_cap_triage.exists() else None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    summary = build_queue_summary(report)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.summary_output, index=False)
    print(f"rows={len(report)}")
    print("priority_counts=" + str(report["queue_priority"].value_counts().to_dict()))
    print(f"activation_recommendation_counts={report['activation_recommendation'].value_counts().to_dict()}")
    print(f"report={args.output}")
    print(f"summary_report={args.summary_output}")


if __name__ == "__main__":
    main()
