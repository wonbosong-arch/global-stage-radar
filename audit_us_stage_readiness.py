"""Offline US candidate inventory. JSON stdout only; never activates or collects.

Uses stored raw price rows and the existing weekly engine. Presence, review
suggestions, bridge metadata and operational approval are separate dimensions.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from candidate_stage_integration import extend_universe_with_approved_candidates
from stage_engine import relative_return_difference, stage_data_freshness_status, weekly_bars

ROOT = Path(__file__).resolve().parent


def numeric(value):
    return pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]


def summarize(rows):
    """Count unique symbols, all intersections and exhaustive disjoint signatures."""
    if len({r["symbol"] for r in rows}) != len(rows):
        raise ValueError("Duplicate US symbol")
    dimensions = sorted({k for r in rows for k, v in r.items() if isinstance(v, bool)})
    counts = {k: sum(r.get(k, False) for r in rows) for k in dimensions}
    core = ["cap_screen_pass", "cap_url_and_asof_present", "weeks30", "weeks35", "mapping_fields_present", "active"]
    intersections = {}
    for size in range(2, len(core) + 1):
        for keys in itertools.combinations(core, size):
            intersections[" & ".join(keys)] = sum(all(r[k] for k in keys) for r in rows)
    blockers = ["cap_screen_pass", "weeks35", "mapping_fields_present",
                "identity_verified", "provider_supported", "active"]
    signatures = Counter(";".join(k for k in blockers if not r[k]) or "none" for r in rows)
    # Data-first ordered waterfall: each symbol belongs to exactly one bucket.
    order = ["cap_screen_pass", "weeks30", "weeks35", "mapping_fields_present",
             "identity_verified", "provider_supported", "active"]
    waterfall = Counter(next((k for k in order if not r[k]), "all_dimensions_pass") for r in rows)
    return {"unique_us_symbols": len(rows), "counts": counts,
            "intersections": intersections, "disjoint_missing_signatures": dict(sorted(signatures.items())),
            "disjoint_first_missing_order": order, "disjoint_first_missing": dict(waterfall)}


def build_audit(data: Path, as_of: str):
    as_of_date = pd.Timestamp(as_of).normalize()
    names = ["stock_universe_candidates.csv", "stock_candidate_coverage_report.csv",
             "provisional_candidate_stage_report.csv", "candidate_review_queue.csv",
             "daily_prices.csv", "candidate_daily_prices.csv",
             "monitoring_universe.csv", "candidate_daily_prices_status.json",
             "daily_prices_status.json", "candidate_collection_status.json",
             "yahoo_large_cap_candidate_review.csv"]
    inputs = {n: {"sha256": hashlib.sha256((data / n).read_bytes()).hexdigest(),
                  "bytes": (data / n).stat().st_size} for n in names}
    def read(name):
        return pd.read_csv(data / name, dtype={"symbol": str}, keep_default_na=False)
    registry = read(names[0])
    for col in ["symbol", "exchange"]:
        registry[col] = registry[col].str.strip().str.upper()
    # US listing venues, including foreign issuers/ADRs; not issuer domicile.
    us = registry[registry.exchange.isin(["NAS", "NYS", "AMS"])].copy()
    if us.symbol.eq("").any() or us.symbol.duplicated().any():
        raise ValueError("US registry requires unique non-empty symbols")
    active_prices, candidate_prices = read("daily_prices.csv"), read("candidate_daily_prices.csv")
    prices = pd.concat([active_prices, candidate_prices], ignore_index=True)
    prices["symbol"] = prices.symbol.str.strip().str.upper()
    prices["date"] = pd.to_datetime(prices.date, errors="coerce")
    cols = ["open", "high", "low", "close", "volume"]
    prices[cols] = prices[cols].apply(pd.to_numeric, errors="coerce")
    groups = dict(tuple(prices.groupby("symbol")))
    weekly = {}
    quality = {}
    for symbol, bars in groups.items():
        values = bars[cols]
        valid = (bars.date.notna().all() and np.isfinite(values.to_numpy()).all()
                 and not bars.duplicated(["symbol", "date"]).any()
                 and (values[["open", "high", "low", "close"]] > 0).all().all()
                 and (values.volume >= 0).all()
                 and (values.high >= values[["open", "close", "low"]].max(axis=1)).all()
                 and (values.low <= values[["open", "close", "high"]].min(axis=1)).all()
                 and (bars.date <= as_of_date).all())
        quality[symbol] = bool(valid)
        if valid:
            weekly[symbol] = weekly_bars(bars, as_of_date=as_of_date, min_bars=1)
    rows = []
    latest_dates = prices.groupby("symbol").date.max().to_dict()
    for _, r in us.iterrows():
        symbol = r.symbol
        bars, w = groups.get(symbol), weekly.get(symbol)
        count = 0 if w is None else len(w)
        cap = numeric(r.get("market_cap_usd", "")) if r.market_cap_status == "verified" else np.nan
        if pd.isna(cap):
            cap = numeric(r.market_cap_usd_b_secondary) * 1e9
        if pd.isna(cap):
            cap = numeric(r.discovery_market_cap_usd)
        mapping = all(str(r[k]).strip() for k in ["name", "market", "sector", "asset_type", "market_benchmark", "sector_benchmark", "exchange"])
        bench_symbols = [r.market_benchmark, r.sector_benchmark]
        benchmarks35 = all(s in weekly and weekly[s] is not None and len(weekly[s]) >= 35 for s in bench_symbols)
        rs_finite = bool(w is not None and benchmarks35 and all(
            s != symbol and np.isfinite(relative_return_difference(w, weekly[s], 26).iloc[-1])
            for s in bench_symbols))
        freshness = stage_data_freshness_status(symbol, "stock", *bench_symbols, latest_dates, as_of_date)
        latest = None if bars is None else bars.date.max()
        row = {"symbol": symbol, "cap_screen_pass": bool(pd.notna(cap) and cap >= 1e9),
               "cap_value_present": bool(pd.notna(cap) and cap > 0),
               "cap_verified": r.market_cap_status == "verified",
               "cap_source_url_present": bool(str(r.market_cap_source_url).strip()),
               "cap_asof_present": bool(str(r.market_cap_asof).strip()),
               "cap_url_and_asof_present": bool(str(r.market_cap_source_url).strip() and str(r.market_cap_asof).strip()),
               "price_quality_pass": quality.get(symbol, False),
               "daily150": bool(bars is not None and bars.date.nunique() >= 150),
               "fresh7_at_asof": bool(latest is not None and 0 <= (as_of_date-latest).days <= 7),
               "weeks30": count >= 30, "weeks34": count >= 34, "weeks35": count >= 35,
               "ma30_finite": bool(w is not None and np.isfinite(w.iloc[-1].ma30)),
               "slope4_finite": bool(w is not None and np.isfinite(w.iloc[-1].slope4_pct)),
               "mapping_fields_present": bool(mapping),
               "proposed_mapping_present": all(bool(str(r[k]).strip()) for k in ["proposed_sector", "proposed_market_benchmark", "proposed_sector_benchmark"]),
               "assigned_benchmarks35": bool(benchmarks35),
               "assigned_rs_finite": rs_finite,
               "assigned_stage_data_inputs_available": bool(mapping and count >= 35 and rs_finite and freshness == "fresh"),
               "identity_verified": r.identity_status == "verified",
               "provider_supported": r.provider_status == "supported",
               "active": r.activation_status == "active"}
        rows.append(row)
    result = summarize(rows)
    result["as_of_date"] = as_of_date.strftime("%Y-%m-%d")
    result["input_files"] = inputs
    result["exchange_counts"] = us.exchange.value_counts().to_dict()
    result["registry_status_counts"] = {k: us[k].value_counts().to_dict() for k in ["activation_status", "identity_status", "provider_status", "mapping_status", "instrument_type", "discovery_source", "market_cap_asof"]}
    ids = set(us.symbol)
    yahoo = read("yahoo_large_cap_candidate_review.csv")
    yahoo.symbol = yahoo.symbol.str.strip().str.upper()
    yahoo = yahoo[yahoo.symbol.isin(ids)]
    if yahoo.symbol.duplicated().any():
        raise ValueError("Duplicate Yahoo review symbol")
    observed = pd.to_datetime(yahoo.fetched_at_utc, errors="coerce", utc=True)
    result["yahoo_review_provenance"] = {
        "matching_registry_symbols": len(yahoo),
        "source_url_present": int(yahoo.market_cap_source_url.str.strip().ne("").sum()),
        "cap_asof_present": int(yahoo.market_cap_asof.str.strip().ne("").sum()),
        "fetched_at_valid": int(observed.notna().sum()),
        "fetched_at_min_utc": str(observed.min()), "fetched_at_max_utc": str(observed.max()),
        "asof_basis_counts": yahoo.market_cap_asof_basis.value_counts().to_dict(),
        "note": "Observation time is not market-cap as-of time; no evidence or approval promotion."}
    for name in ["stock_candidate_coverage_report.csv", "provisional_candidate_stage_report.csv", "candidate_review_queue.csv"]:
        saved = read(name)
        saved.symbol = saved.symbol.str.strip().str.upper()
        subset = saved[saved.symbol.isin(ids)]
        if subset.symbol.duplicated().any() or set(subset.symbol) != ids:
            raise ValueError("Saved report membership mismatch: " + name)
        columns = [c for c in ["review_blockers", "data_status", "provisional_stage_label", "size_screen_result", "market_cap_size_screen_result"] if c in subset]
        result[name] = {c: subset[c].value_counts().to_dict() for c in columns}
    base = read("monitoring_universe.csv")
    extended, errors = extend_universe_with_approved_candidates(base, us, prices, pd.to_datetime(active_prices.date).max())
    result["actual_bridge"] = {"added": len(extended)-len(base), "errors": len(errors)}
    result["price_date_ranges"] = {n: {"min": str(pd.to_datetime(f.date).min().date()), "max": str(pd.to_datetime(f.date).max().date())} for n, f in [("daily_prices.csv", active_prices), ("candidate_daily_prices.csv", candidate_prices)]}
    result["status_timestamps"] = {n: {k: v for k, v in json.loads((data/n).read_text(encoding="utf-8")).items() if k in ["started_at_utc", "finished_at_utc", "updated_at_utc", "updated_at_kst"]} for n in names if n.endswith(".json")}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--as-of", required=True, help="Explicit YYYY-MM-DD; no wall-clock default")
    args = parser.parse_args()
    print(json.dumps(build_audit(args.data_dir, args.as_of), ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
