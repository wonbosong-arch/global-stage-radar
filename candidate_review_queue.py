"""Consolidated, conservative action queue for pending stock candidates.

Combines existing candidate coverage, identity-evidence, and market-cap triage
reports. It prioritizes work only; it never verifies or activates a candidate.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
COVERAGE = ROOT / "data" / "stock_candidate_coverage_report.csv"
IDENTITY = ROOT / "data" / "candidate_identity_evidence_coverage.csv"
MARKET_CAP = ROOT / "data" / "candidate_market_cap_reconciliation.csv"
OUTPUT = ROOT / "data" / "candidate_review_queue.csv"
SUMMARY_OUTPUT = ROOT / "data" / "candidate_review_queue_summary.csv"


def build_review_queue(
    coverage: pd.DataFrame,
    identity: pd.DataFrame,
    market_cap: pd.DataFrame,
    provider_observations: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Join reports by symbol and assign a transparent, conservative work priority.

    Copy inputs before normalization so callers can safely reuse their source frames.
    """
    coverage = coverage.copy()
    identity = identity.copy()
    market_cap = market_cap.copy()
    for frame in (coverage, identity, market_cap):
        if "symbol" not in frame.columns:
            raise ValueError("Each input report must contain a symbol column.")
        frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
        if frame["symbol"].eq("").any():
            raise ValueError("Input reports cannot contain blank symbols.")
        duplicates = sorted(frame.loc[frame["symbol"].duplicated(keep=False), "symbol"].unique())
        if duplicates:
            raise ValueError(f"Input report contains duplicate symbols: {duplicates}")

    # Use explicit row markers: a present report row may legitimately have blank status/priority fields.
    identity = identity.copy()
    market_cap = market_cap.copy()
    identity["_identity_source_row_present"] = True
    market_cap["_market_cap_source_row_present"] = True

    id_cols = [c for c in (
        "symbol", "name", "exchange", "country", "instrument_type", "review_note", "identity_status", "identity_marked_verified",
        "identity_source_url_present", "identity_evidence_source_class", "listing_fields_present", "identity_review_date_present",
        "depositary_ratio_required", "depositary_ratio_verified",
        "market_cap_marked_verified", "provider_status", "provider_marked_checked",
        "review_gaps", "identity_evidence_url", "identity_reviewed_at", "depositary_ratio_status",
        "market_cap_source_url", "market_cap_asof", "market_cap_usd_b_secondary",
        "_identity_source_row_present",
    ) if c in identity.columns]
    cap_cols = [c for c in (
        "symbol", "date_review_priority", "date_review_reason",
        "price_date", "close_usd", "secondary_market_cap_asof", "secondary_market_cap_source_url",
        "price_to_cap_asof_gap_days", "price_to_share_count_asof_gap_days",
        "price_after_market_cap_asof_days", "market_cap_date_alignment",
        "price_after_share_count_asof_days", "share_count_date_alignment",
        "secondary_market_cap_usd_b", "implied_shares_m_from_cap_and_close",
        "reported_shares_m", "reported_shares_asof", "reported_shares_source_url",
        "reported_shares_note", "implied_vs_reported_shares_pct", "triage_outcome",
        "market_cap_status_remains", "verification_note", "_market_cap_source_row_present",
    ) if c in market_cap.columns]

    result = coverage.merge(identity[id_cols], on="symbol", how="left", suffixes=("", "_identity"))
    result["identity_report_row_present"] = result["_identity_source_row_present"].fillna(False).astype(bool)
    result = result.merge(market_cap[cap_cols], on="symbol", how="left", suffixes=("", "_market_cap"))
    result["market_cap_report_row_present"] = result["_market_cap_source_row_present"].fillna(False).astype(bool)
    result = result.drop(columns=["_identity_source_row_present", "_market_cap_source_row_present"], errors="ignore")

    # A price response is evidence that a request returned data, not proof that
    # KIS officially supports the instrument or that the listing identity is correct.
    if provider_observations is not None:
        observations = provider_observations.copy()
        if "symbol" not in observations.columns:
            raise ValueError("Provider observation report must contain a symbol column.")
        observations["symbol"] = observations["symbol"].astype(str).str.strip().str.upper()
        if observations["symbol"].eq("").any():
            raise ValueError("Provider observation report cannot contain blank symbols.")
        if observations["symbol"].duplicated().any():
            raise ValueError("Provider observation report contains duplicate symbols.")
        keep = [column for column in (
            "symbol", "requested_exchange", "response_exchange", "exchange_fallback_used",
            "response_rows", "latest_response_date", "response_error", "provider_support_status",
            "instrument_identity_status", "activation_recommendation",
        ) if column in observations.columns]
        result = result.merge(observations[keep], on="symbol", how="left", suffixes=("", "_observation"))
    for column in (
        "requested_exchange", "response_exchange", "response_rows", "latest_response_date",
        "provider_support_status", "instrument_identity_status", "response_error",
    ):
        if column not in result.columns:
            result[column] = ""
    if "exchange_fallback_used" not in result.columns:
        result["exchange_fallback_used"] = False
    result["price_response_observed"] = pd.to_numeric(result["response_rows"], errors="coerce").fillna(0).gt(0)
    result["price_response_interpretation"] = result["price_response_observed"].map({
        True: "price_returned_support_unverified",
        False: "no_price_response_observed",
    })

    # Identity coverage is required for queue ordering; market-cap reconciliation is optional.
    result["required_review_reports_present"] = result["identity_report_row_present"].astype(bool)
    result["all_review_reports_present"] = (
        result["identity_report_row_present"] & result["market_cap_report_row_present"]
    )

    # Keep candidate-price freshness and benchmark-relative freshness distinct.
    # A benchmark lag is measured against each candidate's own latest available bar,
    # not against today's calendar date, so weekends/market holidays are not conflated
    # with a mismatch between the two series.
    candidate_dates = pd.to_datetime(result.get("candidate_latest_price_date", pd.Series("", index=result.index)), errors="coerce")
    benchmark_dates = pd.to_datetime(result.get("market_benchmark_latest_date", pd.Series("", index=result.index)), errors="coerce")
    result["market_benchmark_lag_vs_candidate_calendar_days"] = (
        candidate_dates.dt.normalize() - benchmark_dates.dt.normalize()
    ).dt.days
    result.loc[candidate_dates.isna() | benchmark_dates.isna(), "market_benchmark_lag_vs_candidate_calendar_days"] = pd.NA

    def decide(row: pd.Series) -> tuple[str, str]:
        status = str(row.get("identity_status", "")).strip()
        if not bool(row.get("identity_report_row_present", False)):
            return "P1_report_reconciliation", "후보 식별 보고서의 누락 행을 복구한 뒤 검토 계속"
        if status in {"issuer_proxy_review_required", "issuer_country_review_required"}:
            return "P1_identity_classification", "상장 거래시장과 발행사 국가/ADR 기준을 분리해 공식 근거 검토"
        # Market-cap arithmetic is a coarse screening aid, not a candidate-review bottleneck.
        # Keep its detailed triage in the separate report, but do not let share-count/date
        # discrepancies outrank listing identity or provider mapping in the main work queue.
        if status not in {"verified", "verified_primary_listing"}:
            return "P2_identity_evidence", "공식 거래소/발행사 자료로 상장 종목과 발행사 정보를 검토"
        ratio_required = str(row.get("depositary_ratio_required", "")).strip().casefold() in {"true", "1", "yes"}
        ratio_verified = str(row.get("depositary_ratio_verified", "")).strip().casefold() in {"true", "1", "yes"}
        if ratio_required and not ratio_verified:
            return "P2_ADR_ratio", "ADR/ADS 1단위당 원주 수와 해당 주식 종류를 공식 발행사 자료로 확인"
        benchmark_raw = row.get("market_benchmark", "")
        benchmark_latest_raw = row.get("market_benchmark_latest_date", "")
        benchmark_active_value = row.get("market_benchmark_active", "")
        benchmark = "" if pd.isna(benchmark_raw) else str(benchmark_raw).strip().upper()
        benchmark_active_raw = (
            "" if pd.isna(benchmark_active_value)
            else str(benchmark_active_value).strip().casefold()
        )
        benchmark_latest = "" if pd.isna(benchmark_latest_raw) else str(benchmark_latest_raw).strip()
        benchmark_inactive = benchmark_active_raw in {"false", "0", "no", "inactive"}
        benchmark_active_missing = (
            "market_benchmark_active" not in row.index
            or not benchmark_active_raw
            or benchmark_active_raw in {"nan", "nat", "none", "<na>"}
        )
        benchmark_latest_parsed = pd.to_datetime(benchmark_latest, errors="coerce")
        benchmark_missing_coverage = (
            "market_benchmark_latest_date" not in row.index
            or not benchmark_latest
            or benchmark_latest.casefold() in {"nan", "nat", "none", "<na>"}
            or pd.isna(benchmark_latest_parsed)
        )
        benchmark_lag_raw = row.get("market_benchmark_lag_vs_candidate_calendar_days", pd.NA)
        try:
            benchmark_lag_days = int(benchmark_lag_raw) if not pd.isna(benchmark_lag_raw) else None
        except (TypeError, ValueError, OverflowError):
            benchmark_lag_days = None
        benchmark_materially_lagged = benchmark_lag_days is not None and benchmark_lag_days > 4
        if (
            not benchmark
            or benchmark_inactive
            or benchmark_active_missing
            or benchmark_missing_coverage
            or benchmark_materially_lagged
        ):
            if benchmark_materially_lagged:
                return "P3_market_benchmark_mapping", f"국가 대표지수 데이터가 후보 종목보다 {benchmark_lag_days}일 오래됨: 대표지수 시계열 갱신 확인"
            return "P3_market_benchmark_mapping", "국가 대표지수 심볼·활성 유니버스 포함 여부·최근 가격 기준일 확인"
        if str(row.get("provider_status", "")).strip() not in {"verified", "supported"}:
            return "P4_provider_mapping", "KIS 응답의 종목 매핑과 지원 여부를 별도 확인"
        # Market cap remains an optional coarse-screening reference, not a queue gate.
        return "P5_final_review", "모든 독립 검토 항목을 확인한 뒤 활성화 적격성을 판단"

    if result.empty:
        decisions = pd.DataFrame(index=result.index, columns=["queue_priority", "next_action_ko"])
    else:
        decisions = result.apply(decide, axis=1, result_type="expand")
        decisions.columns = ["queue_priority", "next_action_ko"]
    result = pd.concat([result, decisions], axis=1)
    result["activation_recommendation"] = "keep_pending_review"
    result["queue_is_not_verification"] = True
    order = {
        "P1_report_reconciliation": 0,
        "P1_identity_classification": 1,
        "P2_identity_evidence": 4,
        "P2_ADR_ratio": 5,
        "P3_market_benchmark_mapping": 6,
        "P4_provider_mapping": 7,
        "P5_final_review": 8,
    }
    result["_order"] = result["queue_priority"].map(order).fillna(99)
    result = result.sort_values(["_order", "symbol"]).drop(columns="_order").reset_index(drop=True)
    result.insert(0, "review_sequence", range(1, len(result) + 1))
    result["review_batch"] = result["queue_priority"].map({
        "P1_report_reconciliation": "0단계: 보고서 누락 복구",
        "P1_identity_classification": "1단계: 발행사/ADR 분류",
        "P2_identity_evidence": "4단계: 상장 식별 근거",
        "P2_ADR_ratio": "4단계: ADR/ADS 비율 확인",
        "P3_market_benchmark_mapping": "5단계: 국가 대표지수 매핑",
        "P4_provider_mapping": "6단계: KIS 매핑 확인",
        "P5_final_review": "7단계: 최종 검토",
    }).fillna("기타 검토")
    result["review_steps_ko"] = result["queue_priority"].map({
        "P1_report_reconciliation": "식별 보고서와 시가총액 보고서의 생성 실패/누락 원인 확인 → symbol 키 일치 확인 → 보고서 재생성 후 검토 재개",
        "P1_identity_classification": "공식 거래소·발행사 자료 확인 → 발행사 소재국과 거래시장 분리 → ADR/ADS 비율 및 주식 종류 확인",
        "P2_identity_evidence": "공식 거래소·발행사 자료로 티커·거래소·발행사 확인 → 증거 URL과 검토 결과 기록",
        "P2_ADR_ratio": "발행사 공식 ADR/ADS 안내 확인 → 예탁증서 1단위당 원주 수·주식 종류 기록 → 별도 검토 전까지 대기",
        "P3_market_benchmark_mapping": "국가 대표지수 심볼 확인 → 활성 유니버스 포함 여부 확인 → 최근 가격 기준일과 지연 확인 (업종 RS는 사용하지 않음)",
        "P4_provider_mapping": "requested_exchange·response_exchange·exchange_fallback_used·response_rows·latest_response_date·response_error를 확인하고 기록 → KIS 공식 종목코드/지원 근거를 별도로 대조 → 가격 응답만으로 provider_status를 verified로 바꾸지 않음",
        "P5_final_review": "미해결 차단 사유 재확인 → 독립 근거 대조 → 별도 승인 전까지 대기 유지",
    }).fillna("미해결 근거를 확인하고 대기 상태 유지")
    result["review_plan_is_not_approval"] = True
    return result






def assess_report_freshness(
    queue_stamp: str,
    summary_stamp: str,
    now=None,
    max_age_hours: float = 36,
) -> dict:
    """Compare report timestamps without treating missing/invalid metadata as fresh."""
    current = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if current.tzinfo is None:
        current = current.tz_localize("UTC")
    else:
        current = current.tz_convert("UTC")

    def parse_stamp(value):
        # Pandas missing scalars (for example pd.NA/pd.NaT) cannot safely be
        # evaluated in boolean expressions, so detect them before stringifying.
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
        value = str(value).strip()
        if not value:
            return None
        try:
            parsed = pd.to_datetime(value, utc=True, errors="raise")
            return parsed if not pd.isna(parsed) else None
        except (TypeError, ValueError, OverflowError):
            return None

    queue_time = parse_stamp(queue_stamp)
    summary_time = parse_stamp(summary_stamp)
    age_hours = (
        (current - queue_time).total_seconds() / 3600
        if queue_time is not None else None
    )
    # Allow minor clock skew, but don't silently treat materially future-dated reports as fresh.
    queue_timestamp_in_future = age_hours is not None and age_hours < -(5 / 60)
    return {
        "queue_time": queue_time,
        "summary_time": summary_time,
        "queue_stamp_valid": queue_time is not None,
        "summary_stamp_valid": summary_time is not None,
        "stamps_match": (
            queue_time is not None and summary_time is not None
            and queue_time == summary_time
        ),
        "queue_age_hours": age_hours,
        "queue_timestamp_in_future": queue_timestamp_in_future,
        "queue_stale": age_hours is not None and age_hours > max_age_hours,
    }



def build_manual_review_worksheet(queue: pd.DataFrame) -> pd.DataFrame:
    """Create a human-review worksheet without changing candidate activation state."""
    worksheet = queue.copy()
    defaults = {
        "manual_review_date": "",
        "manual_reviewer": "",
        "identity_review_result": "not_reviewed",
        "depositary_ratio_review_result": "not_reviewed_or_not_applicable",
        "market_cap_review_result": "not_reviewed",
        "kis_support_review_result": "not_verified",
        "benchmark_mapping_review_result": "not_reviewed",
        "manual_findings": "",
        "remaining_action": "",
        "manual_activation_decision": "keep_pending_review",
        "worksheet_is_not_activation": True,
    }
    for column, default in defaults.items():
        if column not in worksheet.columns:
            worksheet[column] = default
    if "next_action_ko" in worksheet.columns:
        existing_action = worksheet["remaining_action"].fillna("").astype(str).str.strip()
        next_action = worksheet["next_action_ko"].fillna("").astype(str)
        worksheet["remaining_action"] = existing_action.where(existing_action.ne(""), next_action)
    # A downloaded worksheet is a record of proposed manual work, never an approval.
    worksheet["manual_activation_decision"] = "keep_pending_review"
    worksheet["worksheet_is_not_activation"] = True
    return worksheet


def build_queue_summary(report: pd.DataFrame) -> pd.DataFrame:
    """Summarize queue priorities, activation gates, and report consistency."""
    columns = ["summary_type", "category", "candidate_count"]
    if report.empty:
        return pd.DataFrame(columns=columns)

    summaries = []
    grouped_fields = [
        ("queue_priority", "queue_priority"),
        ("activation_gate_status", "activation_gate_status"),
        ("activation_recommendation", "activation_recommendation"),
    ]
    for field, summary_type in grouped_fields:
        if field not in report.columns:
            continue
        part = (
            report.groupby(field, dropna=False)
            .agg(candidate_count=("symbol", "nunique"))
            .reset_index()
            .rename(columns={field: "category"})
        )
        part["summary_type"] = summary_type
        summaries.append(part[columns])

    for field, label in [
        ("identity_report_row_present", "identity_report"),
        ("market_cap_report_row_present", "market_cap_report"),
        ("required_review_reports_present", "required_reports"),
        ("all_review_reports_present", "all_reports_reference_only"),
    ]:
        if field not in report.columns:
            continue
        values = report[field].map(
            lambda value: value if isinstance(value, bool) else str(value).strip().lower() in {"true", "1", "yes"}
        )
        part = pd.DataFrame([
            {"summary_type": "report_presence", "category": f"{label}_present", "candidate_count": int(values.sum())},
            {"summary_type": "report_presence", "category": f"{label}_missing", "candidate_count": int((~values).sum())},
        ])
        summaries.append(part[columns])

    if "next_action_ko" in report.columns:
        actions = (
            report.groupby("next_action_ko", dropna=False)
            .agg(candidate_count=("symbol", "nunique"))
            .reset_index()
            .rename(columns={"next_action_ko": "category"})
        )
        actions["summary_type"] = "next_action"
        summaries.append(actions[columns])

    if not summaries:
        return pd.DataFrame(columns=columns)
    return pd.concat(summaries, ignore_index=True).sort_values(
        ["summary_type", "category"]
    ).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, default=COVERAGE)
    parser.add_argument("--identity", type=Path, default=IDENTITY)
    parser.add_argument("--market-cap", type=Path, default=MARKET_CAP)
    parser.add_argument(
        "--provider-observations",
        type=Path,
        default=ROOT / "data" / "candidate_provider_observation_audit.csv",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=SUMMARY_OUTPUT)
    args = parser.parse_args()
    report = build_review_queue(
        pd.read_csv(args.coverage, dtype=str, keep_default_na=False),
        pd.read_csv(args.identity, dtype=str, keep_default_na=False),
        pd.read_csv(args.market_cap, dtype=str, keep_default_na=False),
        pd.read_csv(args.provider_observations, dtype=str, keep_default_na=False)
        if args.provider_observations.exists() else None,
    )
    generated_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    report["report_generated_at_utc"] = generated_at_utc
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    summary = build_queue_summary(report)
    summary["report_generated_at_utc"] = generated_at_utc
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.summary_output, index=False)
    print(f"rows={len(report)}")
    print("priority_counts=" + str(report["queue_priority"].value_counts().to_dict()))
    print(f"activation_recommendation_counts={report['activation_recommendation'].value_counts().to_dict()}")
    print(f"report={args.output}")
    print(f"summary_report={args.summary_output}")


if __name__ == "__main__":
    main()
