"""Consolidated, conservative action queue for pending stock candidates.

Combines existing candidate coverage, identity-evidence, and market-cap triage
reports. It prioritizes work only; it never verifies or activates a candidate.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
COVERAGE = ROOT / "data" / "stock_candidate_coverage_report.csv"
IDENTITY = ROOT / "data" / "candidate_identity_evidence_coverage.csv"
MARKET_CAP = ROOT / "data" / "candidate_market_cap_reconciliation.csv"
OUTPUT = ROOT / "data" / "candidate_review_queue.csv"
SUMMARY_OUTPUT = ROOT / "data" / "candidate_review_queue_summary.csv"


def build_review_queue(coverage: pd.DataFrame, identity: pd.DataFrame, market_cap: pd.DataFrame) -> pd.DataFrame:
    """Join reports by symbol and assign a transparent, conservative work priority."""
    for frame in (coverage, identity, market_cap):
        if "symbol" not in frame.columns:
            raise ValueError("Each input report must contain a symbol column.")
        frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()

    id_cols = [c for c in (
        "symbol", "identity_status", "identity_marked_verified",
        "identity_source_url_present", "identity_review_date_present",
        "depositary_ratio_required", "depositary_ratio_verified",
        "market_cap_marked_verified", "provider_status", "provider_marked_checked",
        "review_gaps", "identity_evidence_url", "identity_reviewed_at", "depositary_ratio_status",
        "market_cap_source_url", "market_cap_asof", "market_cap_usd_b_secondary",
    ) if c in identity.columns]
    cap_cols = [c for c in (
        "symbol", "date_review_priority", "date_review_reason",
        "price_date", "close_usd", "secondary_market_cap_asof", "secondary_market_cap_source_url",
        "price_to_cap_asof_gap_days", "price_to_share_count_asof_gap_days",
        "secondary_market_cap_usd_b", "implied_shares_m_from_cap_and_close",
        "reported_shares_m", "reported_shares_asof", "reported_shares_source_url",
        "reported_shares_note", "implied_vs_reported_shares_pct", "triage_outcome",
        "market_cap_status_remains", "verification_note",
    ) if c in market_cap.columns]

    result = coverage.merge(identity[id_cols], on="symbol", how="left", suffixes=("", "_identity"))
    result = result.merge(market_cap[cap_cols], on="symbol", how="left", suffixes=("", "_market_cap"))

    def decide(row: pd.Series) -> tuple[str, str]:
        status = str(row.get("identity_status", "")).strip()
        cap_priority = str(row.get("date_review_priority", "")).strip()
        if status in {"issuer_proxy_review_required", "issuer_country_review_required"}:
            return "P1_identity_classification", "상장 거래시장과 발행사 국가/ADR 기준을 분리해 공식 근거 검토"
        if cap_priority in {"P1_material_mismatch", "P1_stale_share_count"}:
            return "P1_market_cap_reconciliation", "시가총액 역산 차이 또는 오래된 주식 수 기준일을 우선 재검토"
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
    summary = pd.concat(
        [priority_summary, gate_summary, recommendation_summary],
        ignore_index=True,
    )[["summary_type", "category", "candidate_count"]]
    summary = summary.sort_values(["summary_type", "category"]).reset_index(drop=True)
    
    return summary.sort_values(["summary_type", "category"]).reset_index(drop=True)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, default=COVERAGE)
    parser.add_argument("--identity", type=Path, default=IDENTITY)
    parser.add_argument("--market-cap", type=Path, default=MARKET_CAP)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=SUMMARY_OUTPUT)
    args = parser.parse_args()
    report = build_review_queue(
        pd.read_csv(args.coverage, dtype=str, keep_default_na=False),
        pd.read_csv(args.identity, dtype=str, keep_default_na=False),
        pd.read_csv(args.market_cap, dtype=str, keep_default_na=False),
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
