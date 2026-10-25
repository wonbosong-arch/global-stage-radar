"""Offline coverage report for pending stock candidates.

This audit never activates candidates and does not prove that KIS supports a symbol;
it only compares candidate metadata with the saved daily-price snapshot.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_CANDIDATES = ROOT / "data" / "stock_universe_candidates.csv"
DEFAULT_UNIVERSE = ROOT / "data" / "monitoring_universe.csv"
DEFAULT_PRICES = ROOT / "data" / "daily_prices.csv"
DEFAULT_CANDIDATE_PRICES = ROOT / "data" / "candidate_daily_prices.csv"


def build_candidate_coverage_report(
    candidates: pd.DataFrame,
    active_universe: pd.DataFrame,
    prices: pd.DataFrame,
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Build a conservative per-candidate coverage report from local CSV data.

    Freshness is measured against the report's as-of date, not the newest date
    found anywhere in the snapshot; otherwise an entirely stale snapshot looks fresh.
    """
    as_of_timestamp = pd.to_datetime(
        as_of_date if as_of_date is not None else pd.Timestamp.now(tz="UTC").date(),
        errors="coerce",
    )
    if pd.isna(as_of_timestamp):
        raise ValueError("as_of_date must be a valid date.")
    if getattr(as_of_timestamp, "tzinfo", None) is not None:
        as_of_timestamp = as_of_timestamp.tz_convert("UTC").tz_localize(None)
    as_of_timestamp = as_of_timestamp.normalize()
    candidate_frame = candidates.copy()
    if "symbol" not in candidate_frame.columns:
        raise ValueError("Candidate metadata must contain a symbol column.")
    candidate_frame["symbol"] = candidate_frame["symbol"].astype(str).str.strip().str.upper()
    if candidate_frame["symbol"].eq("").any():
        raise ValueError("Candidate metadata cannot contain blank symbols.")
    duplicates = sorted(candidate_frame.loc[candidate_frame["symbol"].duplicated(keep=False), "symbol"].unique())
    if duplicates:
        raise ValueError(f"Candidate metadata contains duplicate symbols: {duplicates}")
    active_symbols = set(active_universe["symbol"].astype(str).str.strip().str.upper())
    if prices.empty or not {"symbol", "date"}.issubset(prices.columns):
        coverage = pd.DataFrame(columns=["symbol", "price_rows", "first_price_date", "latest_price_date"])
    else:
        normalized = prices.copy()
        normalized["symbol"] = normalized["symbol"].astype(str).str.strip().str.upper()
        normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce")
        normalized = normalized.dropna(subset=["date"]).drop_duplicates(["symbol", "date"])
        coverage = normalized.groupby("symbol").agg(
            price_rows=("date", "nunique"),
            first_price_date=("date", "min"),
            latest_price_date=("date", "max"),
        ).reset_index()
        for column in ("first_price_date", "latest_price_date"):
            coverage[column] = coverage[column].dt.strftime("%Y-%m-%d")

    coverage_by_symbol = coverage.set_index("symbol").to_dict("index") if not coverage.empty else {}
    snapshot_latest = pd.to_datetime(prices.get("date", pd.Series(dtype=str)), errors="coerce").max()
    blocker_labels_ko = {
        "adr_depositary_ratio_unverified": "ADR 예탁 비율 미확인",
        "adr_issuer_country_proxy_unverified": "ADR 발행사 국가·시장 대리변수 검토 필요",
        "issuer_country_treatment_unverified": "해외 법인 국가 분류 검토 필요",
        "listing_identity_unverified": "상장 종목 식별 미확인",
        "provider_support_unverified": "KIS 데이터 지원 미확인",
        "candidate_price_history_missing": "후보 가격 이력 없음",
        "candidate_history_below_150_unique_bars": "고유 일봉 150개 미만",
        "market_benchmark_coverage_missing": "시장 벤치마크 데이터 누락",
        "candidate_price_date_may_be_stale": "후보 가격 기준일 지연 가능성",
        "market_benchmark_date_may_be_stale": "시장 벤치마크 기준일 지연 가능성",
    }
    report_rows = []
    for _, candidate in candidate_frame.iterrows():
        symbol = str(candidate.get("symbol", "")).strip().upper()
        market_value = candidate.get("market_benchmark", "")
        sector_value = candidate.get("sector_benchmark", "")
        market_benchmark = "" if pd.isna(market_value) else str(market_value).strip().upper()
        sector_benchmark = "" if pd.isna(sector_value) else str(sector_value).strip().upper()
        asset = coverage_by_symbol.get(symbol, {})
        market_data = coverage_by_symbol.get(market_benchmark, {})
        sector_data = coverage_by_symbol.get(sector_benchmark, {})
        candidate_latest = pd.to_datetime(asset.get("latest_price_date"), errors="coerce")
        market_latest = pd.to_datetime(market_data.get("latest_price_date"), errors="coerce")
        sector_latest = pd.to_datetime(sector_data.get("latest_price_date"), errors="coerce")
        candidate_lag = (snapshot_latest - candidate_latest).days if pd.notna(snapshot_latest) and pd.notna(candidate_latest) else None
        market_lag = (snapshot_latest - market_latest).days if pd.notna(snapshot_latest) and pd.notna(market_latest) else None
        sector_lag = (snapshot_latest - sector_latest).days if pd.notna(snapshot_latest) and pd.notna(sector_latest) else None
        candidate_lag_as_of = (as_of_timestamp - candidate_latest).days if pd.notna(candidate_latest) else None
        market_lag_as_of = (as_of_timestamp - market_latest).days if pd.notna(market_latest) else None
        candidate_rows = int(asset.get("price_rows", 0))
        market_rows = int(market_data.get("price_rows", 0))
        sector_rows = int(sector_data.get("price_rows", 0))
        blockers = []
        identity_status = str(candidate.get("identity_status", "review_required")).strip()
        market_cap_status = str(candidate.get("market_cap_status", "not_verified")).strip()
        provider_status = str(candidate.get("provider_status", "not_checked")).strip()
        instrument_type = str(candidate.get("instrument_type", "")).strip().lower()
        depositary_ratio_status = str(candidate.get("depositary_ratio_status", "not_verified")).strip().lower()
        if instrument_type in {"adr_candidate", "adr", "american_depositary_receipt"} and depositary_ratio_status not in {"verified", "not_applicable"}:
            blockers.append("adr_depositary_ratio_unverified")
        if identity_status == "issuer_proxy_review_required":
            blockers.append("adr_issuer_country_proxy_unverified")
        if identity_status == "issuer_country_review_required":
            blockers.append("issuer_country_treatment_unverified")
        if identity_status not in {"verified", "verified_primary_listing"}:
            blockers.append("listing_identity_unverified")
        # Market cap is a coarse size filter, not a precision-verification blocker.
        # A returned price history proves only that rows were observed in the
        # saved snapshot; it does not certify live KIS support or exact instrument identity.
        provider_observed_data_returned = candidate_rows > 0
        if provider_status not in {"verified", "supported"}:
            blockers.append("provider_support_unverified")
        if candidate_rows == 0:
            blockers.append("candidate_price_history_missing")
        elif candidate_rows < 150:
            blockers.append("candidate_history_below_150_unique_bars")
        if not market_benchmark or market_benchmark not in active_symbols or market_rows == 0:
            blockers.append("market_benchmark_coverage_missing")
        # Sector proxy coverage is informational only while sector RS is disabled.
        if candidate_lag_as_of is None or candidate_lag_as_of < 0 or candidate_lag_as_of > 7:
            blockers.append("candidate_price_date_may_be_stale")
        if market_lag_as_of is None or market_lag_as_of < 0 or market_lag_as_of > 7:
            blockers.append("market_benchmark_date_may_be_stale")
        # Review priorities include missing provenance fields, not just blocker codes.
        identity_blockers = {"listing_identity_unverified", "adr_depositary_ratio_unverified", "adr_issuer_country_proxy_unverified", "issuer_country_treatment_unverified"}
        identity_evidence_url = str(candidate.get("identity_evidence_url", "") or "").strip()
        identity_reviewed_at = str(candidate.get("identity_reviewed_at", "") or "").strip()
        market_cap_source_url = str(candidate.get("market_cap_source_url", "") or "").strip()
        market_cap_asof = str(candidate.get("market_cap_asof", "") or "").strip()
        is_adr = "adr" in str(candidate.get("instrument_type", "") or "").lower()
        evidence_gaps = []
        if not identity_evidence_url:
            evidence_gaps.append("identity_evidence_url_missing")
        if not identity_reviewed_at:
            evidence_gaps.append("identity_review_date_missing")
        if not market_cap_source_url:
            evidence_gaps.append("market_cap_source_url_missing")
        if not market_cap_asof:
            evidence_gaps.append("market_cap_asof_missing")
        if is_adr and str(candidate.get("depositary_ratio_status", "") or "").strip().lower() not in {"verified", "not_applicable"}:
            evidence_gaps.append("adr_ratio_evidence_missing")
        evidence_fields_present = not evidence_gaps

        if identity_blockers.intersection(blockers) or "identity_evidence_url_missing" in evidence_gaps or "identity_review_date_missing" in evidence_gaps or "adr_ratio_evidence_missing" in evidence_gaps:
            review_priority = "P1_identity"
            if identity_status == "issuer_proxy_review_required":
                next_review_action = "ADR 상장 종목의 발행사 국가·거래시장 벤치마크를 분리 확인하고 예탁비율 및 ADS 기준 시가총액 산식을 검토"
            elif identity_status == "issuer_country_review_required":
                next_review_action = "상장 종목의 발행사 법적 소재지와 미국 상장 거래소를 구분해 국가 분류 근거를 확인"
            else:
                next_review_action = "공식 거래소/발행사 자료로 상장 종목·발행사 국가를 확인하고 근거를 기록"
        # Market-cap source/date gaps are retained as reference fields, not review priorities.
        elif "provider_support_unverified" in blockers or "candidate_price_history_missing" in blockers:
            review_priority = "P4_data"
            next_review_action = "데이터 공급자 응답과 가격 이력 품질을 확인"
        elif blockers:
            review_priority = "P5_freshness"
            next_review_action = "가격 및 벤치마크 기준일과 나머지 차단 항목을 검토"
        else:
            review_priority = "P6_final_review"
            next_review_action = "모든 근거를 재검토한 뒤에만 활성화 적격성을 판단"

        report_rows.append({
            "symbol": symbol,
            "name": candidate.get("name", ""),
            "sector": candidate.get("sector", ""),
            "market": candidate.get("market", ""),
            "exchange": candidate.get("exchange", ""),
            "country": candidate.get("country", ""),
            "currency": candidate.get("currency", ""),
            "instrument_type": candidate.get("instrument_type", ""),
            "activation_status": candidate.get("activation_status", "pending_review"),
            "identity_status": identity_status,
            "depositary_ratio_status": candidate.get("depositary_ratio_status", "not_verified" if instrument_type in {"adr_candidate", "adr", "american_depositary_receipt"} else "not_applicable_or_not_recorded"),
            "market_cap_status": market_cap_status,
            # Secondary-source reference only; never equivalent to verified market cap.
            "market_cap_usd_b_secondary": candidate.get("market_cap_usd_b_secondary", ""),
            "market_cap_source_url": candidate.get("market_cap_source_url", ""),
            "market_cap_asof": candidate.get("market_cap_asof", ""),
            "provider_status": provider_status,
            "review_priority": review_priority,
            "next_review_action": next_review_action,
            "evidence_gaps": ";".join(evidence_gaps),
            "evidence_fields_complete": evidence_fields_present,
            "identity_evidence_url": candidate.get("identity_evidence_url", ""),
            "identity_reviewed_at": candidate.get("identity_reviewed_at", ""),
            "provider_observed_data_returned": provider_observed_data_returned,
            "review_blocker_count": len(blockers),
            "review_blockers": ";".join(blockers) if blockers else "metadata_and_snapshot_checks_clear",
            "review_blockers_ko": " / ".join(blocker_labels_ko.get(code, code) for code in blockers) if blockers else "메타데이터·저장 스냅샷 검사상 차단 항목 없음(활성화 승인 아님)",
            "candidate_already_active": symbol in active_symbols,
            "candidate_price_rows": candidate_rows,
            "candidate_history_150_plus_bars": candidate_rows >= 150,
            "candidate_first_price_date": asset.get("first_price_date", ""),
            "candidate_latest_price_date": asset.get("latest_price_date", ""),
            "report_as_of_date": as_of_timestamp.strftime("%Y-%m-%d"),
            "candidate_lag_calendar_days_vs_as_of": candidate_lag_as_of,
            "market_benchmark_lag_calendar_days_vs_as_of": market_lag_as_of,
            "candidate_lag_calendar_days_vs_snapshot": candidate_lag,
            "market_benchmark": market_benchmark,
            "market_benchmark_active": market_benchmark in active_symbols,
            "market_benchmark_price_rows": market_rows,
            "market_benchmark_latest_date": market_data.get("latest_price_date", ""),
            "market_benchmark_lag_calendar_days": market_lag,
            "sector_benchmark": sector_benchmark,
            "sector_benchmark_active": bool(sector_benchmark and sector_benchmark in active_symbols),
            "sector_benchmark_price_rows": sector_rows,
            "sector_benchmark_latest_date": sector_data.get("latest_price_date", ""),
            "sector_benchmark_lag_calendar_days": sector_lag,
            "snapshot_coverage_status": (
                "candidate_and_benchmarks_have_snapshot_rows"
                if candidate_rows > 0
                and market_rows > 0
                else "coverage_missing_or_incomplete"
            ),
            # Explicit gate state prevents a clear-looking snapshot report from being read as approval.
            "activation_gate_status": "blocked_pending_manual_review",
            "activation_gate_reason": "Automated snapshot coverage is triage only; identity, provider mapping, country-index benchmark coverage, and final review require explicit review. Sector benchmark coverage is informational while sector RS is disabled. Market cap is an optional coarse-screening reference, not an activation-review priority.",
            "activation_recommendation": "keep_pending_review",
            "coverage_report_is_not_live_provider_verification": True,
        })
    return pd.DataFrame(report_rows)


def load_price_snapshots(active_path: Path, candidate_path: Path) -> pd.DataFrame:
    """Combine active and review-only price snapshots without duplicate symbol/date rows."""
    frames = []
    for path in (active_path, candidate_path):
        if path.exists():
            frame = pd.read_csv(path, dtype={"symbol": str})
            if not frame.empty:
                frames.append(frame)
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    if {"symbol", "date"}.issubset(combined.columns):
        combined["symbol"] = combined["symbol"].astype(str).str.strip().str.upper()
        combined["date"] = pd.to_datetime(combined["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        combined = combined.dropna(subset=["date"]).drop_duplicates(["symbol", "date"], keep="first")
    return combined


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE)
    parser.add_argument("--prices", type=Path, default=DEFAULT_PRICES)
    parser.add_argument("--candidate-prices", type=Path, default=DEFAULT_CANDIDATE_PRICES)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "stock_candidate_coverage_report.csv")
    args = parser.parse_args()

    candidates = pd.read_csv(args.candidates, dtype={"symbol": str})
    universe = pd.read_csv(args.universe, dtype={"symbol": str})
    prices = load_price_snapshots(args.prices, args.candidate_prices)
    report = build_candidate_coverage_report(candidates, universe, prices)

    # Attach the latest recorded fetch attempt without confusing retained history
    # with data fetched successfully during that attempt.
    status_path = ROOT / "data" / "candidate_daily_prices_status.json"
    refresh_status = {}
    if status_path.exists():
        try:
            refresh_status = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            refresh_status = {}
    fresh_symbols = {str(s).strip().upper() for s in refresh_status.get("fresh_data_symbols", [])}
    failed_symbols = {str(s).strip().upper() for s in refresh_status.get("failed_symbols", [])}
    error_symbols = {
        str(item.get("symbol", "")).strip().upper()
        for item in refresh_status.get("errors", [])
        if isinstance(item, dict)
    }
    # A "*" error means the refresh failed before it could reliably report
    # individual symbol outcomes (for example, missing credentials or setup failure).
    run_level_failed = "*" in failed_symbols or "*" in error_symbols
    report["refresh_attempt_at_utc"] = refresh_status.get("updated_at_utc", "")
    report["refresh_attempt_error_count"] = refresh_status.get("error_count", "")
    report["refresh_attempt_requested_symbols"] = refresh_status.get("requested_symbols", "")
    report["refresh_attempt_fresh_data_symbol_count"] = refresh_status.get("fresh_data_symbol_count", "")
    report["refresh_attempt_run_level_failed"] = run_level_failed
    report["refresh_attempt_outcome"] = report["symbol"].map(
        lambda s: "refresh_run_failed"
        if run_level_failed
        else "fresh_data_returned"
        if s in fresh_symbols
        else "request_failed"
        if s in failed_symbols or s in error_symbols
        else "not_confirmed_in_latest_attempt"
    )
    # The candidate refresh calls KISUSProvider directly. Keep this run-scoped
    # observation separate from provider_status, which requires instrument-level
    # identity review before it can be considered verified.
    report["latest_attempt_kis_response_observed"] = report["symbol"].isin(fresh_symbols)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    print(f"Saved {len(report)} pending-candidate coverage rows to {args.output}")
    print(report["snapshot_coverage_status"].value_counts(dropna=False).to_string())
    print("No candidates were activated; snapshot presence does not establish current KIS endpoint support.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
