"""Offline coverage report for pending stock candidates.

This audit never activates candidates and does not prove that KIS supports a symbol;
it only compares candidate metadata with the saved daily-price snapshot.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


PRICE_HISTORY_EXCEPTION_EVIDENCE = {
    "SPCX": {
        "note": "Recent IPO: SpaceX Class A shares began Nasdaq trading on 2026-06-12. Fewer than 150 bars is expected; keep pending until sufficient history accumulates.",
        "source_url": "https://ir.spacex.com/updates/releases-details/2026/Space-Exploration-Technologies-Corp--Announces-Pricing-of-Initial-Public-Offering/default.aspx",
    },
    "HONA": {
        "note": "Recent listing: Honeywell Aerospace began Nasdaq regular-way trading on 2026-06-29. Fewer than 150 bars is expected; keep pending until sufficient history accumulates.",
        "source_url": "https://www.nasdaq.com/press-release/honeywell-aerospace-completes-spin-honeywell-technologies-and-begins-trading-nasdaq",
    },
    "SKHY": {
        "note": "Recent ADR listing: SK hynix ADR trading began on Nasdaq on 2026-07-10. Fewer than 150 bars is expected; ADR identity, ratio, cap, and activation gates remain separate.",
        "source_url": "https://news.skhynix.com/en/skhynix-lists-adrs-on-nasdaq/",
    },
    "ET": {
        "note": "Venue transfer: Energy Transfer moved its ET listing from NYSE to TXSE effective 2026-10-05. If history remains below 150 bars, inspect the pre-transfer NYSE/current-venue merge status.",
        "source_url": "https://ir.energytransfer.com/news-releases/news-release-details/energy-transfer-transfer-stock-exchange-listings-texas-stock",
    },
}

ROOT = Path(__file__).resolve().parent
DEFAULT_CANDIDATES = ROOT / "data" / "stock_universe_candidates.csv"
DEFAULT_UNIVERSE = ROOT / "data" / "monitoring_universe.csv"
DEFAULT_PRICES = ROOT / "data" / "daily_prices.csv"
DEFAULT_CANDIDATE_PRICES = ROOT / "data" / "candidate_daily_prices.csv"
DEFAULT_SECTOR_BENCHMARK_PRICES = ROOT / "data" / "sector_benchmark_candidate_prices.csv"
DEFAULT_ADR_RATIO_REGISTRY = ROOT / "data" / "adr_ratio_primary_source_registry.csv"
DEFAULT_YAHOO_CAP_OBSERVATIONS = ROOT / "data" / "yahoo_market_cap_supplement.csv"


def build_candidate_coverage_report(
    candidates: pd.DataFrame,
    active_universe: pd.DataFrame,
    prices: pd.DataFrame,
    adr_ratio_registry: pd.DataFrame | None = None,
    yahoo_market_cap_observations: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build a conservative per-candidate coverage report from local CSV data."""
    candidate_frame = candidates.copy()
    adr_registry_by_symbol = {}
    if adr_ratio_registry is not None and {"symbol", "status", "depositary_ratio_observed", "depositary_ratio_basis", "depositary_ratio_source_url"}.issubset(adr_ratio_registry.columns):
        confirmed = adr_ratio_registry[adr_ratio_registry["status"].astype(str).str.strip().str.lower().eq("official_source_confirmed")]
        adr_registry_by_symbol = {
            str(row["symbol"]).strip().upper(): row
            for _, row in confirmed.iterrows()
        }
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
    cap_observations = {}
    if yahoo_market_cap_observations is not None and {
        "symbol", "market_cap_usd_b_secondary", "observation_status"
    }.issubset(yahoo_market_cap_observations.columns):
        cap_frame = yahoo_market_cap_observations.copy()
        cap_frame["symbol"] = cap_frame["symbol"].astype(str).str.strip().str.upper()
        cap_frame["market_cap_usd_b_secondary"] = pd.to_numeric(
            cap_frame["market_cap_usd_b_secondary"], errors="coerce"
        )
        cap_frame["observation_status"] = cap_frame["observation_status"].astype(str).str.strip()
        cap_frame = cap_frame.drop_duplicates("symbol", keep="last")
        cap_observations = cap_frame.set_index("symbol").to_dict("index")
    snapshot_latest = pd.to_datetime(prices.get("date", pd.Series(dtype=str)), errors="coerce").max()
    blocker_labels_ko = {
        "adr_depositary_ratio_unverified": "ADR 예탁 비율 미확인",
        "adr_issuer_country_proxy_unverified": "ADR 발행사 국가·시장 대리변수 검토 필요",
        "issuer_country_treatment_unverified": "해외 법인 국가 분류 검토 필요",
        "listing_identity_unverified": "상장 종목 식별 미확인",
        "market_cap_unverified": "최소 시총 추정 자료 부족",
        "market_cap_below_minimum_estimate": "추정 시가총액 10억 달러 미만",
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
        candidate = candidate.copy()
        symbol = str(candidate.get("symbol", "")).strip().upper()
        ratio_evidence = adr_registry_by_symbol.get(symbol)
        if ratio_evidence is not None and str(candidate.get("instrument_type", "")).strip().lower() in {"adr_candidate", "adr", "american_depositary_receipt"}:
            # A registry match verifies only the depositary ratio, not issuer identity,
            # market cap, provider support, benchmark mapping, or activation eligibility.
            candidate["depositary_ratio_status"] = "verified"
            candidate["depositary_ratio_source_url"] = str(ratio_evidence["depositary_ratio_source_url"])
            candidate["depositary_ratio_observed"] = str(ratio_evidence["depositary_ratio_observed"])
            candidate["depositary_ratio_basis"] = str(ratio_evidence["depositary_ratio_basis"])
        market_value = candidate.get("market_benchmark", "")
        sector_value = candidate.get("sector_benchmark", "")
        market_benchmark = "" if pd.isna(market_value) else str(market_value).strip().upper()
        sector_benchmark = "" if pd.isna(sector_value) else str(sector_value).strip().upper()
        asset = coverage_by_symbol.get(symbol, {})
        market_data = coverage_by_symbol.get(market_benchmark, {})
        sector_data = coverage_by_symbol.get(sector_benchmark, {})
        # A suggested benchmark can help evaluate data readiness for provisional
        # analysis, but it never fills the reviewed mapping field or clears a gate.
        suggested_sector_value = candidate.get("proposed_sector_benchmark", "")
        suggested_sector_benchmark = (
            "" if pd.isna(suggested_sector_value) else str(suggested_sector_value).strip().upper()
        )
        suggested_sector_data = coverage_by_symbol.get(suggested_sector_benchmark, {})
        candidate_latest = pd.to_datetime(asset.get("latest_price_date"), errors="coerce")
        market_latest = pd.to_datetime(market_data.get("latest_price_date"), errors="coerce")
        sector_latest = pd.to_datetime(sector_data.get("latest_price_date"), errors="coerce")
        suggested_sector_latest = pd.to_datetime(
            suggested_sector_data.get("latest_price_date"), errors="coerce"
        )
        candidate_lag = (snapshot_latest - candidate_latest).days if pd.notna(snapshot_latest) and pd.notna(candidate_latest) else None
        market_lag = (snapshot_latest - market_latest).days if pd.notna(snapshot_latest) and pd.notna(market_latest) else None
        sector_lag = (snapshot_latest - sector_latest).days if pd.notna(snapshot_latest) and pd.notna(sector_latest) else None
        suggested_sector_lag = (
            (snapshot_latest - suggested_sector_latest).days
            if pd.notna(snapshot_latest) and pd.notna(suggested_sector_latest) else None
        )
        candidate_rows = int(asset.get("price_rows", 0))
        market_rows = int(market_data.get("price_rows", 0))
        sector_rows = int(sector_data.get("price_rows", 0))
        suggested_sector_rows = int(suggested_sector_data.get("price_rows", 0))
        blockers = []
        identity_status = str(candidate.get("identity_status", "review_required")).strip()
        market_cap_status = str(candidate.get("market_cap_status", "not_verified")).strip()
        cap_observation = cap_observations.get(symbol, {})
        candidate_cap = pd.to_numeric(
            pd.Series([candidate.get("market_cap_usd_b_secondary", "")]), errors="coerce"
        ).iloc[0]
        observed_cap = pd.to_numeric(
            pd.Series([cap_observation.get("market_cap_usd_b_secondary", "")]), errors="coerce"
        ).iloc[0]
        if pd.isna(candidate_cap):
            candidate_cap = observed_cap
        observation_status = str(cap_observation.get("observation_status", "")).strip()
        estimate_observed = (
            pd.notna(candidate_cap)
            and (
                market_cap_status in {"verified", "not_applicable"}
                or observation_status in {"observed_usd", "observed_usd_fx_converted"}
            )
        )
        instrument_type = str(candidate.get("instrument_type", "")).strip().lower()
        cap_exempt_instrument_types = {"etf", "etf_candidate", "fund", "index_fund"}
        cap_exempt = instrument_type in cap_exempt_instrument_types
        size_screen_result = (
            "exempt_instrument_type" if cap_exempt
            else "pass_estimate" if estimate_observed and float(candidate_cap) >= 1.0
            else "below_minimum" if estimate_observed
            else "needs_observation"
        )
        provider_status = str(candidate.get("provider_status", "not_checked")).strip()
        depositary_ratio_status = str(candidate.get("depositary_ratio_status", "not_verified")).strip().lower()
        if instrument_type in {"adr_candidate", "adr", "american_depositary_receipt"} and depositary_ratio_status not in {"verified", "not_applicable"}:
            blockers.append("adr_depositary_ratio_unverified")
        if identity_status == "issuer_proxy_review_required":
            blockers.append("adr_issuer_country_proxy_unverified")
        if identity_status == "issuer_country_review_required":
            blockers.append("issuer_country_treatment_unverified")
        if identity_status not in {"verified", "verified_primary_listing"}:
            blockers.append("listing_identity_unverified")
        # The universe rule is a coarse $1B minimum-size screen, not formal
        # share-count reconciliation. A dated secondary USD estimate can clear
        # that screen while its provenance/status remains explicitly unverified.
        if size_screen_result == "below_minimum":
            blockers.append("market_cap_below_minimum_estimate")
        elif size_screen_result == "needs_observation" and market_cap_status not in {"verified", "not_applicable"}:
            blockers.append("market_cap_unverified")
        # A returned price history proves only that rows were observed in the
        # saved snapshot; it does not certify live KIS support or exact instrument identity.
        provider_observed_data_returned = candidate_rows > 0
        # Do not create a redundant provider-discovery blocker when the saved
        # candidate snapshot already contains returned price rows. This is only
        # observed-response evidence: provider_status stays unchanged and formal
        # support/identity approval remains a separate activation gate.
        if provider_status not in {"verified", "supported"} and not provider_observed_data_returned:
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
        if not cap_exempt and not market_cap_source_url:
            evidence_gaps.append("market_cap_source_url_missing")
        if not cap_exempt and not market_cap_asof:
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
        elif "sector_benchmark_not_assigned" in blockers or "sector_benchmark_mapping_mismatch" in blockers or "sector_benchmark_coverage_missing" in blockers:
            review_priority = "P2_benchmark"
            next_review_action = "업종 분류와 업종 벤치마크 매핑·커버리지를 검토"
        elif "market_cap_below_minimum_estimate" in blockers:
            review_priority = "P3_market_cap"
            next_review_action = "최소 10억 달러 허들 미달 추정치 확인"
        elif not cap_exempt and ("market_cap_unverified" in blockers or (
            size_screen_result != "pass_estimate"
            and ("market_cap_source_url_missing" in evidence_gaps or "market_cap_asof_missing" in evidence_gaps)
        )):
            review_priority = "P3_market_cap"
            next_review_action = "최소 10억 달러 허들 판별에 필요한 추정 자료만 확인"
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
            # Suggested mapping is review evidence only; activation gates continue to use
            # the explicitly reviewed sector/benchmark fields above.
            "proposed_market": candidate.get("proposed_market", ""),
            "proposed_sector": candidate.get("proposed_sector", ""),
            "proposed_asset_type": candidate.get("proposed_asset_type", ""),
            "proposed_market_benchmark": candidate.get("proposed_market_benchmark", ""),
            "proposed_sector_benchmark": candidate.get("proposed_sector_benchmark", ""),
            "mapping_status": candidate.get("mapping_status", "sector_mapping_missing"),
            "mapping_note": candidate.get("mapping_note", ""),
            "discovery_industry_code": candidate.get("discovery_industry_code", ""),
            "discovery_dr_country_code": candidate.get("discovery_dr_country_code", ""),
            "market": candidate.get("market", ""),
            "exchange": candidate.get("exchange", ""),
            "country": candidate.get("country", ""),
            "currency": candidate.get("currency", ""),
            "instrument_type": candidate.get("instrument_type", ""),
            "activation_status": candidate.get("activation_status", "pending_review"),
            "identity_status": identity_status,
            "depositary_ratio_status": candidate.get("depositary_ratio_status", "not_verified" if instrument_type in {"adr_candidate", "adr", "american_depositary_receipt"} else "not_applicable_or_not_recorded"),
            "depositary_ratio_source_url": candidate.get("depositary_ratio_source_url", ""),
            "depositary_ratio_observed": candidate.get("depositary_ratio_observed", ""),
            "depositary_ratio_basis": candidate.get("depositary_ratio_basis", ""),
            "market_cap_status": market_cap_status,
            "market_cap_size_screen_result": size_screen_result,
            "market_cap_estimate_usd_b_secondary": candidate_cap if pd.notna(candidate_cap) else "",
            "market_cap_estimate_source_status": observation_status or ("candidate_recorded_cap" if pd.notna(candidate_cap) else ""),
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
            "price_history_exception_note": (
                PRICE_HISTORY_EXCEPTION_EVIDENCE.get(symbol, {}).get("note", "")
                if candidate_rows < 150 else ""
            ),
            "price_history_exception_source_url": (
                PRICE_HISTORY_EXCEPTION_EVIDENCE.get(symbol, {}).get("source_url", "")
                if candidate_rows < 150 else ""
            ),
            "price_history_exception_status": (
                "no_price_rows"
                if candidate_rows == 0
                else "history_sufficient"
                if candidate_rows >= 150
                else "known_recent_listing_short_history"
                if symbol in {"SPCX", "HONA", "SKHY"}
                else "venue_transfer_short_history"
                if symbol == "ET"
                else "short_history_unexplained"
            ),
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
            "suggested_sector_benchmark": suggested_sector_benchmark,
            "suggested_sector_benchmark_active": bool(
                suggested_sector_benchmark and suggested_sector_benchmark in active_symbols
            ),
            "suggested_sector_benchmark_price_rows": suggested_sector_rows,
            "suggested_sector_benchmark_latest_date": suggested_sector_data.get("latest_price_date", ""),
            "suggested_sector_benchmark_lag_calendar_days": suggested_sector_lag,
            "suggested_sector_benchmark_coverage_status": (
                "suggestion_missing"
                if not suggested_sector_benchmark
                else "benchmark_snapshot_missing"
                if suggested_sector_rows == 0
                else "benchmark_snapshot_stale"
                if suggested_sector_lag is None or suggested_sector_lag > 7
                else "usable_for_provisional_analysis_not_approval"
            ),
            "snapshot_coverage_status": (
                "candidate_and_benchmarks_have_snapshot_rows"
                if candidate_rows > 0
                and market_rows > 0
                and bool(sector_benchmark)
                and sector_rows > 0
                else "coverage_missing_or_incomplete"
            ),
            # Explicit gate state prevents a clear-looking snapshot report from being read as approval.
            "activation_gate_status": "blocked_pending_manual_review",
            "activation_gate_reason": "Review-only gate: identity, provider, price history, benchmarks, and final review remain separate; a dated USD estimate >= $1B clears only the coarse size screen, not formal cap verification or activation.",
            "activation_recommendation": "keep_pending_review",
            "coverage_report_is_not_live_provider_verification": True,
        })
    return pd.DataFrame(report_rows)


def load_price_snapshots(
    active_path: Path,
    candidate_path: Path,
    sector_benchmark_path: Path | None = DEFAULT_SECTOR_BENCHMARK_PRICES,
) -> pd.DataFrame:
    """Combine active, stock-candidate, and optional sector-ETF review snapshots."""
    frames = []
    paths = [active_path, candidate_path]
    if sector_benchmark_path is not None:
        paths.append(sector_benchmark_path)
    for path in paths:
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
    parser.add_argument("--sector-benchmark-prices", type=Path, default=DEFAULT_SECTOR_BENCHMARK_PRICES)
    parser.add_argument("--adr-ratio-registry", type=Path, default=DEFAULT_ADR_RATIO_REGISTRY)
    parser.add_argument("--yahoo-market-cap-observations", type=Path, default=DEFAULT_YAHOO_CAP_OBSERVATIONS)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "stock_candidate_coverage_report.csv")
    args = parser.parse_args()

    candidates = pd.read_csv(args.candidates, dtype={"symbol": str})
    universe = pd.read_csv(args.universe, dtype={"symbol": str})
    prices = load_price_snapshots(args.prices, args.candidate_prices, args.sector_benchmark_prices)
    adr_ratio_registry = pd.read_csv(args.adr_ratio_registry, dtype={"symbol": str}) if args.adr_ratio_registry.exists() else pd.DataFrame()
    yahoo_market_cap_observations = (
        pd.read_csv(args.yahoo_market_cap_observations, dtype={"symbol": str})
        if args.yahoo_market_cap_observations.exists() else pd.DataFrame()
    )
    report = build_candidate_coverage_report(
        candidates, universe, prices,
        adr_ratio_registry=adr_ratio_registry,
        yahoo_market_cap_observations=yahoo_market_cap_observations,
    )

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
    deferred_symbols = {str(s).strip().upper() for s in refresh_status.get("deferred_symbols", [])}
    error_symbols = {
        str(item.get("symbol", "")).strip().upper()
        for item in refresh_status.get("errors", [])
        if isinstance(item, dict)
    }
    # Distinguish candidates discovered after the latest price-refresh run from
    # older candidates whose result was not recorded. "Not confirmed" must never
    # be silently interpreted as a provider failure or as successful coverage.
    refresh_attempt_at = pd.to_datetime(refresh_status.get("updated_at_utc", ""), utc=True, errors="coerce")
    if "discovered_at" in candidates.columns:
        discovered_at_by_symbol = (
            candidates.assign(
                _symbol=candidates["symbol"].astype(str).str.strip().str.upper(),
                _discovered_at=pd.to_datetime(candidates["discovered_at"], utc=True, errors="coerce"),
            )
            .drop_duplicates("_symbol", keep="last")
            .set_index("_symbol")["_discovered_at"]
            .to_dict()
        )
    else:
        discovered_at_by_symbol = {}
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
        else "deferred_time_budget"
        if s in deferred_symbols
        else "request_failed"
        if s in failed_symbols or s in error_symbols
        else "not_confirmed_in_latest_attempt"
    )
    report["candidate_discovered_at"] = report["symbol"].map(
        lambda s: candidates.loc[
            candidates["symbol"].astype(str).str.strip().str.upper().eq(str(s).strip().upper()),
            "discovered_at",
        ].iloc[-1]
        if "discovered_at" in candidates.columns
        and not candidates.loc[
            candidates["symbol"].astype(str).str.strip().str.upper().eq(str(s).strip().upper())
        ].empty
        else ""
    )
    def explain_attempt_outcome(row: pd.Series) -> str:
        outcome = str(row.get("refresh_attempt_outcome", ""))
        if outcome != "not_confirmed_in_latest_attempt":
            return outcome
        discovered_at = discovered_at_by_symbol.get(str(row.get("symbol", "")).strip().upper())
        if pd.notna(refresh_attempt_at) and pd.notna(discovered_at) and discovered_at > refresh_attempt_at:
            return "candidate_added_after_latest_attempt"
        return "not_confirmed_in_latest_attempt"
    report["refresh_attempt_outcome_detail"] = report.apply(explain_attempt_outcome, axis=1)
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
