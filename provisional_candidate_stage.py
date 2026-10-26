"""Compute a review-only Stage snapshot for pending stock candidates.

This report never approves or activates a candidate. It uses suggested benchmark
mappings solely to help identify missing data and inspect possible Stage labels.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from stage_engine import (
    classify_stage,
    relative_return_difference,
    stage_data_freshness_status,
    stage_label_with_data_guards,
    volume_confirmation,
    weekly_bars,
)

ROOT = Path(__file__).resolve().parent
DEFAULT_REPORT = ROOT / "data" / "stock_candidate_coverage_report.csv"
DEFAULT_ACTIVE_PRICES = ROOT / "data" / "daily_prices.csv"
DEFAULT_CANDIDATE_PRICES = ROOT / "data" / "candidate_daily_prices.csv"
DEFAULT_SECTOR_PRICES = ROOT / "data" / "sector_benchmark_candidate_prices.csv"
DEFAULT_OUTPUT = ROOT / "data" / "provisional_candidate_stage_report.csv"
PRICE_COLUMNS = {"date", "symbol", "open", "high", "low", "close", "volume"}


def _load_prices(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        if path.exists() and path.stat().st_size:
            frame = pd.read_csv(path, dtype={"symbol": str})
            frame.columns = [str(c).strip().lower() for c in frame.columns]
            if PRICE_COLUMNS.issubset(frame.columns) and not frame.empty:
                frames.append(frame[list(PRICE_COLUMNS)].copy())
    if not frames:
        return pd.DataFrame(columns=sorted(PRICE_COLUMNS))
    # Active-universe prices are last and take precedence for overlapping symbols.
    prices = pd.concat(frames, ignore_index=True)
    prices["symbol"] = prices["symbol"].astype(str).str.strip().str.upper()
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    for col in ("open", "high", "low", "close", "volume"):
        prices[col] = pd.to_numeric(prices[col], errors="coerce")
    prices = prices.dropna(subset=["date", "close"])
    prices = prices.drop_duplicates(["symbol", "date"], keep="last")
    return prices.sort_values(["symbol", "date"]).reset_index(drop=True)


def build_provisional_stage_report(
    candidates: pd.DataFrame,
    prices: pd.DataFrame,
    as_of_date=None,
) -> pd.DataFrame:
    """Return one provisional row per candidate; all results remain review-only."""
    output_columns = [
        "symbol", "name", "proposed_sector", "market_benchmark",
        "suggested_sector_benchmark", "candidate_latest_daily_date",
        "completed_weekly_date", "weekly_bars", "close", "ma30",
        "ma30_slope_4w_pct", "market_rs_26w_pct", "sector_rs_26w_pct",
        "volume_context", "provisional_stage_label", "data_status",
        "activation_status",
    ]
    if candidates.empty or prices.empty or not PRICE_COLUMNS.issubset(prices.columns):
        return pd.DataFrame(columns=output_columns)

    frame = prices.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    as_of = pd.Timestamp(as_of_date).normalize() if as_of_date is not None else frame["date"].max().normalize()
    latest_dates = frame.groupby("symbol")["date"].max().to_dict()
    daily_by_symbol = {
        str(symbol): group.sort_values("date").copy()
        for symbol, group in frame.dropna(subset=["date", "close"]).groupby("symbol")
    }
    weekly_by_symbol = {}
    for symbol, daily in daily_by_symbol.items():
        weekly = weekly_bars(daily, as_of_date=as_of)
        if weekly is not None and not weekly.empty:
            weekly_by_symbol[symbol] = weekly

    rows = []
    for _, candidate in candidates.iterrows():
        symbol = str(candidate.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        market_benchmark = str(
            candidate.get("proposed_market_benchmark", candidate.get("market_benchmark", ""))
        ).strip().upper()
        sector_benchmark = str(
            candidate.get("suggested_sector_benchmark", candidate.get("proposed_sector_benchmark", ""))
        ).strip().upper()
        asset_weekly = weekly_by_symbol.get(symbol)
        daily = daily_by_symbol.get(symbol)
        result = {
            "symbol": symbol,
            "name": candidate.get("name", ""),
            "proposed_sector": candidate.get("proposed_sector", candidate.get("sector", "")),
            "market_benchmark": market_benchmark,
            "suggested_sector_benchmark": sector_benchmark,
            "candidate_latest_daily_date": latest_dates.get(symbol, pd.NaT),
            "completed_weekly_date": pd.NaT,
            "weekly_bars": 0 if asset_weekly is None else len(asset_weekly),
            "close": np.nan, "ma30": np.nan, "ma30_slope_4w_pct": np.nan,
            "market_rs_26w_pct": np.nan, "sector_rs_26w_pct": np.nan,
            "volume_context": "거래량 데이터 부족",
            "provisional_stage_label": "데이터 부족 · 예비 판정 불가",
            "data_status": "candidate_price_or_history_missing",
            "activation_status": "pending_review_not_activated",
        }
        if asset_weekly is None or daily is None:
            rows.append(result)
            continue

        asset_weekly = asset_weekly.copy()
        last = asset_weekly.iloc[-1]
        market_weekly = weekly_by_symbol.get(market_benchmark)
        sector_weekly = weekly_by_symbol.get(sector_benchmark)
        if market_weekly is not None and market_benchmark != symbol:
            asset_weekly["market_rs"] = relative_return_difference(asset_weekly, market_weekly, 26).to_numpy()
        elif market_benchmark == symbol:
            asset_weekly["market_rs"] = np.nan
        else:
            asset_weekly["market_rs"] = np.nan
        if sector_weekly is not None and sector_benchmark != symbol:
            asset_weekly["sector_rs"] = relative_return_difference(asset_weekly, sector_weekly, 26).to_numpy()
        else:
            asset_weekly["sector_rs"] = np.nan
        last = asset_weekly.iloc[-1]
        market_rs = last.get("market_rs", np.nan)
        sector_rs = last.get("sector_rs", np.nan)
        label = classify_stage(
            close=last["close"], ma30=last["ma30"], slope4_pct=last["slope4_pct"],
            market_rs=market_rs, sector_rs=sector_rs, asset_type="stock",
        )
        freshness = stage_data_freshness_status(
            symbol=symbol, asset_type="stock",
            market_benchmark=market_benchmark, sector_benchmark=sector_benchmark,
            latest_dates=latest_dates, as_of_date=as_of,
        )
        market_missing = market_weekly is None or pd.isna(market_rs)
        sector_missing = sector_weekly is None or pd.isna(sector_rs)
        label = stage_label_with_data_guards(
            label, freshness, market_rs_missing=market_missing,
            sector_rs_missing=sector_missing,
        )
        if not market_benchmark or not sector_benchmark:
            label = "벤치마크 매핑 미완료 · 판정 보류"
        if len(asset_weekly) < 35:
            label = "완료 주봉 35개 미만 · 판정 보류"
        result.update({
            "completed_weekly_date": last["date"],
            "weekly_bars": len(asset_weekly),
            "close": last["close"], "ma30": last["ma30"],
            "ma30_slope_4w_pct": last["slope4_pct"],
            "market_rs_26w_pct": market_rs, "sector_rs_26w_pct": sector_rs,
            "volume_context": volume_confirmation(last.get("vol_ratio", np.nan)),
            "provisional_stage_label": label,
            "data_status": freshness if market_benchmark and sector_benchmark else "benchmark_mapping_missing",
        })
        rows.append(result)
    report = pd.DataFrame(rows, columns=output_columns)
    for col in ("candidate_latest_daily_date", "completed_weekly_date"):
        report[col] = pd.to_datetime(report[col], errors="coerce").dt.strftime("%Y-%m-%d")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--active-prices", type=Path, default=DEFAULT_ACTIVE_PRICES)
    parser.add_argument("--candidate-prices", type=Path, default=DEFAULT_CANDIDATE_PRICES)
    parser.add_argument("--sector-prices", type=Path, default=DEFAULT_SECTOR_PRICES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    candidates = pd.read_csv(args.candidates, dtype={"symbol": str}) if args.candidates.exists() else pd.DataFrame()
    # Keep this order: sector proxy snapshot, candidate snapshot, then active prices.
    prices = _load_prices([args.sector_prices, args.candidate_prices, args.active_prices])
    report = build_provisional_stage_report(candidates, prices)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(args.output, index=False)
    print(f"Provisional Stage report: {len(report)} candidates -> {args.output}")
    if not report.empty:
        print(report["provisional_stage_label"].value_counts(dropna=False).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
