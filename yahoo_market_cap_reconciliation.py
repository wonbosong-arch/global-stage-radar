"""Compare secondary market-cap observations without verifying or activating candidates."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
CANDIDATES = ROOT / "data" / "stock_universe_candidates.csv"
YAHOO = ROOT / "data" / "yahoo_market_cap_supplement.csv"
OUTPUT = ROOT / "data" / "yahoo_market_cap_reconciliation.csv"
MATERIAL_DIFFERENCE_PCT = 10.0
CLOSE_DIFFERENCE_PCT = 5.0
MAX_DATE_GAP_DAYS = 3


def build_reconciliation(candidates: pd.DataFrame, yahoo: pd.DataFrame) -> pd.DataFrame:
    """Build a triage-only source comparison; never promote values to verified cap."""
    if "symbol" not in candidates.columns or "symbol" not in yahoo.columns:
        raise ValueError("Both candidate and Yahoo inputs must contain symbol.")
    c = candidates.copy()
    y = yahoo.copy()
    c["symbol"] = c["symbol"].fillna("").astype(str).str.strip().str.upper()
    y["symbol"] = y["symbol"].fillna("").astype(str).str.strip().str.upper()
    c = c[c["symbol"].ne("")].drop_duplicates("symbol")
    y = y[y["symbol"].ne("")].drop_duplicates("symbol")

    candidate_cap_col = "market_cap_usd_b_secondary"
    yahoo_cap_col = "market_cap_usd_b_secondary"
    if candidate_cap_col not in c.columns:
        c[candidate_cap_col] = pd.NA
    if yahoo_cap_col not in y.columns:
        y[yahoo_cap_col] = pd.NA
    if "market_cap_source_url" not in c.columns:
        c["market_cap_source_url"] = ""
    if "market_cap_asof" not in c.columns:
        c["market_cap_asof"] = ""
    for col in ("source_url", "market_cap_asof", "market_cap_currency", "market_cap_status", "observation_status", "error"):
        if col not in y.columns:
            y[col] = ""

    # Yahoo's first pass is deliberately limited to US common-stock candidates.
    if "instrument_type" in c.columns:
        c = c[c["instrument_type"].fillna("").astype(str).str.lower().isin(
            {"common_stock_candidate", "common_stock_candidate_unverified", "common_stock"}
        )]
    merged = c.merge(
        y[["symbol", yahoo_cap_col, "source_url", "market_cap_asof", "market_cap_currency",
           "market_cap_status", "observation_status", "error"]],
        on="symbol", how="left", suffixes=("_candidate", "_yahoo"),
    )
    rows = []
    for row in merged.to_dict("records"):
        candidate_value = pd.to_numeric(pd.Series([row.get(f"{candidate_cap_col}_candidate")]), errors="coerce").iloc[0]
        yahoo_value = pd.to_numeric(pd.Series([row.get(f"{yahoo_cap_col}_yahoo")]), errors="coerce").iloc[0]
        candidate_date = pd.to_datetime(row.get("market_cap_asof_candidate"), errors="coerce")
        yahoo_date = pd.to_datetime(row.get("market_cap_asof_yahoo"), errors="coerce")
        date_gap = abs((candidate_date - yahoo_date).days) if pd.notna(candidate_date) and pd.notna(yahoo_date) else None
        diff_pct = (
            abs(float(yahoo_value) - float(candidate_value)) / max(abs(float(candidate_value)), 1e-12) * 100
            if pd.notna(candidate_value) and pd.notna(yahoo_value) and float(candidate_value) > 0 and float(yahoo_value) > 0
            else None
        )
        error_value = row.get("error")
        has_error = pd.notna(error_value) and bool(str(error_value).strip())
        if has_error:
            status, note = "yahoo_observation_error", "Yahoo 관측 오류; 수동 확인 필요"
        elif pd.isna(candidate_value) and pd.isna(yahoo_value):
            status, note = "no_usable_cap_observation", "사용 가능한 보조 시가총액 값 없음"
        elif pd.isna(candidate_value) or pd.isna(yahoo_value):
            status, note = "single_source_only", "한 출처 값만 존재; 교차 대조 불가"
        elif row.get("market_cap_currency_yahoo", row.get("market_cap_currency")) != "USD":
            status, note = "yahoo_non_usd", "Yahoo 값이 USD가 아니므로 USD 기준 비교 불가"
        elif date_gap is None or date_gap > MAX_DATE_GAP_DAYS:
            status, note = "effective_date_mismatch", "시가총액 기준일 차이가 크거나 기준일 누락"
        elif diff_pct <= CLOSE_DIFFERENCE_PCT:
            status, note = "close_values_manual_review", "두 출처 값 차이가 작지만 검증 완료는 아님"
        elif diff_pct <= MATERIAL_DIFFERENCE_PCT:
            status, note = "moderate_difference_review", "출처 간 차이 재검토 필요"
        else:
            status, note = "material_difference_review", "출처 간 차이가 커 우선 재검토 필요"
        rows.append({
            "symbol": row["symbol"],
            "instrument_type": row.get("instrument_type", ""),
            "candidate_cap_usd_b": candidate_value,
            "candidate_cap_asof": row.get("market_cap_asof_candidate", ""),
            "candidate_cap_source_url": row.get("market_cap_source_url_candidate", row.get("market_cap_source_url", "")),
            "yahoo_cap_usd_b": yahoo_value,
            "yahoo_cap_asof": row.get("market_cap_asof_yahoo", ""),
            "yahoo_cap_source_url": row.get("source_url", ""),
            "yahoo_observation_status": row.get("observation_status", ""),
            "effective_date_gap_days": date_gap,
            "difference_pct_vs_candidate": diff_pct,
            "comparison_status": status,
            "triage_note_ko": note,
            "market_cap_verified": False,
            "activation_allowed": False,
        })
    columns = [
        "symbol", "instrument_type", "candidate_cap_usd_b", "candidate_cap_asof",
        "candidate_cap_source_url", "yahoo_cap_usd_b", "yahoo_cap_asof",
        "yahoo_cap_source_url", "yahoo_observation_status", "effective_date_gap_days",
        "difference_pct_vs_candidate", "comparison_status", "triage_note_ko",
        "market_cap_verified", "activation_allowed",
    ]
    result = pd.DataFrame(rows, columns=columns)
    if not result.empty:
        order = {
            "material_difference_review": 1, "effective_date_mismatch": 2,
            "moderate_difference_review": 3, "single_source_only": 4,
            "no_usable_cap_observation": 5, "yahoo_observation_error": 6,
            "yahoo_non_usd": 7, "close_values_manual_review": 8,
        }
        result["_order"] = result["comparison_status"].map(order).fillna(99)
        result = result.sort_values(["_order", "symbol"]).drop(columns="_order").reset_index(drop=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=CANDIDATES)
    parser.add_argument("--yahoo", type=Path, default=YAHOO)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    candidates = pd.read_csv(args.candidates, dtype={"symbol": "string"}).fillna("")
    yahoo = pd.read_csv(args.yahoo, dtype={"symbol": "string"}).fillna("") if args.yahoo.exists() else pd.DataFrame(columns=["symbol"])
    report = build_reconciliation(candidates, yahoo)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    print(report["comparison_status"].value_counts(dropna=False).to_dict() if not report.empty else {})
    print(f"Report written: {args.output}; triage only, no candidate verification or activation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
