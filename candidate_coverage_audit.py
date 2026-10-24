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
        normalized = normalized.dropna(subset=["date"])
        coverage = normalized.groupby("symbol").agg(
            price_rows=("date", "size"),
            first_price_date=("date", "min"),
            latest_price_date=("date", "max"),
        ).reset_index()
        for column in ("first_price_date", "latest_price_date"):
            coverage[column] = coverage[column].dt.strftime("%Y-%m-%d")

    coverage_by_symbol = coverage.set_index("symbol").to_dict("index") if not coverage.empty else {}
    report_rows = []
    for _, candidate in candidate_frame.iterrows():
        symbol = str(candidate.get("symbol", "")).strip().upper()
        market_benchmark = str(candidate.get("market_benchmark", "") or "").strip().upper()
        sector_benchmark = str(candidate.get("sector_benchmark", "") or "").strip().upper()
        asset = coverage_by_symbol.get(symbol, {})
        market_data = coverage_by_symbol.get(market_benchmark, {})
        sector_data = coverage_by_symbol.get(sector_benchmark, {})
        report_rows.append({
            "symbol": symbol,
            "name": candidate.get("name", ""),
            "sector": candidate.get("sector", ""),
            "instrument_type": candidate.get("instrument_type", ""),
            "activation_status": candidate.get("activation_status", "pending_review"),
            "provider_status": candidate.get("provider_status", "not_checked"),
            "candidate_already_active": symbol in active_symbols,
            "candidate_price_rows": int(asset.get("price_rows", 0)),
            "candidate_first_price_date": asset.get("first_price_date", ""),
            "candidate_latest_price_date": asset.get("latest_price_date", ""),
            "market_benchmark": market_benchmark,
            "market_benchmark_active": market_benchmark in active_symbols,
            "market_benchmark_price_rows": int(market_data.get("price_rows", 0)),
            "market_benchmark_latest_date": market_data.get("latest_price_date", ""),
            "sector_benchmark": sector_benchmark,
            "sector_benchmark_active": bool(sector_benchmark and sector_benchmark in active_symbols),
            "sector_benchmark_price_rows": int(sector_data.get("price_rows", 0)),
            "sector_benchmark_latest_date": sector_data.get("latest_price_date", ""),
            "snapshot_coverage_status": (
                "candidate_and_benchmarks_have_snapshot_rows"
                if int(asset.get("price_rows", 0)) > 0
                and int(market_data.get("price_rows", 0)) > 0
                and bool(sector_benchmark)
                and int(sector_data.get("price_rows", 0)) > 0
                else "coverage_missing_or_incomplete"
            ),
            "activation_recommendation": "keep_pending_review",
        })
    return pd.DataFrame(report_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE)
    parser.add_argument("--prices", type=Path, default=DEFAULT_PRICES)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "stock_candidate_coverage_report.csv")
    args = parser.parse_args()

    candidates = pd.read_csv(args.candidates, dtype={"symbol": str})
    universe = pd.read_csv(args.universe, dtype={"symbol": str})
    prices = pd.read_csv(args.prices, dtype={"symbol": str}) if args.prices.exists() else pd.DataFrame()
    report = build_candidate_coverage_report(candidates, universe, prices)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    print(f"Saved {len(report)} pending-candidate coverage rows to {args.output}")
    print(report["snapshot_coverage_status"].value_counts(dropna=False).to_string())
    print("No candidates were activated; snapshot presence does not establish current KIS endpoint support.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
