"""Offline coverage report for pending stock candidates.

This audit never activates candidates and does not prove that KIS supports a symbol;
it only compares candidate metadata with the saved daily-price snapshot.
"""
from __future__ import annotations

import argparse
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
) -> pd.DataFrame:
    """Build a conservative per-candidate coverage report from local CSV data."""
    candidate_frame = candidates.copy()
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

    expected_sector_benchmarks = {
        "Semiconductors": "SOXX",
        "Information Technology": "XLK",
        "Communication Services": "XLC",
        "Consumer Discretionary": "XLY",
        "Consumer Staples": "XLP",
        "Energy": "XLE",
        "Financials": "XLF",
        "Health Care": "XLV",
        "Industrials": "XLI",
        "Materials": "XLB",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
    }
    coverage_by_symbol = coverage.set_index("symbol").to_dict("index") if not coverage.empty else {}
    snapshot_latest = pd.to_datetime(prices.get("date", pd.Series(dtype=str)), errors="coerce").max()
    blocker_labels_ko = {
        "adr_depositary_ratio_unverified": "ADR 예탁 비율 미확인",
        "adr_issuer_country_proxy_unverified": "ADR 발행사 국가·시장 대리변수 검토 필요",
        "issuer_country_treatment_unverified": "해외 법인 국가 분류 검토 필요",
        "listing_identity_unverified": "상장 종목 식별 미확인",
        "market_cap_unverified": "시가총액 검증 미완료",
        "provider_support_unverified": "KIS 데이터 지원 미확인",
        "candidate_price_history_missing": "후보 가격 이력 없음",
        "candidate_history_below_150_unique_bars": "고유 일봉 150개 미만",
        "market_benchmark_coverage_missing": "시장 벤치마크 데이터 누락",
        "sector_benchmark_not_assigned": "업종 벤치마크 미지정",
        "sector_benchmark_coverage_missing": "업종 벤치마크 데이터 누락",
        "sector_benchmark_mapping_mismatch": "업종과 벤치마크 매핑 불일치",
        "candidate_price_date_may_be_stale": "후보 가격 기준일 지연 가능성",
        "market_benchmark_date_may_be_stale": "시장 벤치마크 기준일 지연 가능성",
        "sector_benchmark_date_may_be_stale": "업종 벤치마크 기준일 지연 가능성",
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
        if market_cap_status not in {"verified", "not_applicable"}:
            blockers.append("market_cap_unverified")
        if provider_status not in {"verified", "supported"}:
            blockers.append("provider_support_unverified")
        if candidate_rows == 0:
            blockers.append("candidate_price_history_missing")
        elif candidate_rows < 150:
            blockers.append("candidate_history_below_150_unique_bars")
        if not market_benchmark or market_benchmark not in active_symbols or market_rows == 0:
            blockers.append("market_benchmark_coverage_missing")
        sector_name = str(candidate.get("sector", "")).strip()
        expected_sector_benchmark = expected_sector_benchmarks.get(sector_name, "")
        if not sector_benchmark:
            blockers.append("sector_benchmark_not_assigned")
        elif sector_benchmark not in active_symbols or sector_rows == 0:
            blockers.append("sector_benchmark_coverage_missing")
        if expected_sector_benchmark and sector_benchmark and sector_benchmark != expected_sector_benchmark:
            blockers.append("sector_benchmark_mapping_mismatch")
        if candidate_lag is None or candidate_lag > 7:
            blockers.append("candidate_price_date_may_be_stale")
        if market_lag is None or market_lag > 7:
            blockers.append("market_benchmark_date_may_be_stale")
        if sector_benchmark and (sector_lag is None or sector_lag > 7):
            blockers.append("sector_benchmark_date_may_be_stale")
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
            "provider_status": provider_status,
            "review_blocker_count": len(blockers),
            "review_blockers": ";".join(blockers) if blockers else "metadata_and_snapshot_checks_clear",
            "review_blockers_ko": " / ".join(blocker_labels_ko.get(code, code) for code in blockers) if blockers else "메타데이터·저장 스냅샷 검사상 차단 항목 없음(활성화 승인 아님)",
            "candidate_already_active": symbol in active_symbols,
            "candidate_price_rows": candidate_rows,
            "candidate_history_150_plus_bars": candidate_rows >= 150,
            "candidate_first_price_date": asset.get("first_price_date", ""),
            "candidate_latest_price_date": asset.get("latest_price_date", ""),
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
                and bool(sector_benchmark)
                and sector_rows > 0
                else "coverage_missing_or_incomplete"
            ),
            "activation_recommendation": "keep_pending_review",
            "coverage_report_is_not_live_provider_verification": True,
        })
    return pd.DataFrame(report_rows)


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
    active_prices = pd.read_csv(args.prices, dtype={"symbol": str}) if args.prices.exists() else pd.DataFrame()
    candidate_prices = pd.read_csv(args.candidate_prices, dtype={"symbol": str}) if args.candidate_prices.exists() else pd.DataFrame()
    available_prices = [frame for frame in (active_prices, candidate_prices) if not frame.empty]
    prices = pd.concat(available_prices, ignore_index=True) if available_prices else pd.DataFrame()
    if not prices.empty and {"symbol", "date"}.issubset(prices.columns):
        prices = prices.drop_duplicates(["symbol", "date"], keep="first")
    report = build_candidate_coverage_report(candidates, universe, prices)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    print(f"Saved {len(report)} pending-candidate coverage rows to {args.output}")
    print(report["snapshot_coverage_status"].value_counts(dropna=False).to_string())
    print("No candidates were activated; snapshot presence does not establish current KIS endpoint support.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
