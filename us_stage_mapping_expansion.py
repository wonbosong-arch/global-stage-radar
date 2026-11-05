"""Offline review of additional US mappings; reuse the saved 72-stock baseline.

Only the explicit additions enter the weekly engine. No network or data writes.
Use the original baseline inputs/as-of for an exactly comparable count; a newer
snapshot produces incremental results without re-labelling the historical 72.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import pandas as pd

from stock_mapping import (US_REVIEW_SECTOR_ADDITIONS, US_REVIEW_SOURCE_URLS,
                           proposed_stock_mapping)
from us_kis_evidence_readiness import assess_candidates
from us_stage_connection_plan import MAPPING, OfflineStageReplay, cap_provenance, text

ROOT = Path(__file__).resolve().parent
INPUTS = ("stock_universe_candidates.csv", "unranked_us_stock_master.csv",
          "yahoo_large_cap_candidate_review.csv", "monitoring_universe.csv",
          "daily_prices.csv", "candidate_daily_prices.csv")


def fingerprint(path):
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size}


def baseline_input_match(path, recorded):
    """The saved Windows audit hashes CRLF checkout bytes, unlike Linux Git blobs."""
    raw = path.read_bytes()
    variants = {"exact_bytes": raw,
                "lf_equivalent": raw.replace(b"\r\n", b"\n"),
                "crlf_equivalent": raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")}
    for basis, value in variants.items():
        if recorded == {"sha256": hashlib.sha256(value).hexdigest(), "bytes": len(value)}:
            return basis
    return "different"


def expand_rows(registry, master, observations, universe, prices, as_of, baseline_symbols):
    """Do not fill assigned fields or synthesize bridge approval statuses."""
    frame = registry.copy()
    frame["symbol"] = frame.symbol.map(text).str.upper()
    frame["exchange"] = frame.exchange.map(text).str.upper()
    if frame.symbol.eq("").any() or frame.symbol.duplicated().any():
        raise ValueError("Registry requires unique non-empty symbols")
    if set(US_REVIEW_SECTOR_ADDITIONS) & set(baseline_symbols):
        raise ValueError("Additions overlap the already validated baseline")
    selected = frame[frame.symbol.isin(US_REVIEW_SECTOR_ADDITIONS)
                     & frame.exchange.isin(["NAS", "NYS", "AMS"])].sort_values("symbol")
    identity = {r["symbol"]: r for r in assess_candidates(selected, master, {})}
    proposals = {r.symbol: proposed_stock_mapping(r.symbol, r.exchange,
                 text(r.get("discovery_dr_country_code"))) for _, r in selected.iterrows()}
    needed = set(selected.symbol)
    for p in proposals.values():
        needed.update(p["proposed_" + k] for k in MAPPING[-2:])
    # Filtering happens BEFORE weekly resampling: the historical 72 are not replayed.
    replay = OfflineStageReplay(prices[prices.symbol.isin(needed)], as_of)
    results = []
    for _, row in selected.iterrows():
        p = proposals[row.symbol]
        mapping = {k: p["proposed_" + k] for k in MAPPING}
        cap = cap_provenance(row, [o for o in observations if text(o.get("symbol")).upper() == row.symbol])
        run = replay.replay(row.symbol, mapping)
        reasons = list(run["reasons"])
        if not cap["threshold_pass"]:
            reasons.append("market_cap_below_1b_or_missing")
        if identity[row.symbol]["identity_basis"] != "kis_master_consistent":
            reasons.append("kis_identity_review_required")
        benchmarks = []
        for kind in ("market", "sector"):
            symbol = mapping[kind + "_benchmark"]
            matches = universe[universe.symbol.eq(symbol)]
            valid = (len(matches) == 1 and text(matches.iloc[0].get("provider")) == "KIS"
                     and text(matches.iloc[0].get("active")).lower() == "true"
                     and text(matches.iloc[0].get("asset_type")) == kind + "_etf"
                     and (kind == "market" or text(matches.iloc[0].get("sector")) == mapping["sector"]))
            if not valid:
                reasons.append(kind + "_benchmark_metadata_missing_or_conflicting")
            benchmarks.append({"symbol": symbol, "metadata_valid": bool(valid),
                               "recorded": matches.to_dict("records")})
        # Cap/identity/metadata failures also suppress the review label.
        label = run.pop("review_only_stage_label") if not reasons else None
        run.pop("review_only_stage_label", None)
        results.append({"symbol": row.symbol, "name": row["name"], "venue": row.exchange,
                        "stored_assigned_mapping": {k: text(row.get(k)) for k in MAPPING},
                        "stored_proposed_sector": text(row.get("proposed_sector")),
                        "proposed_mapping": mapping, "mapping_status": p["mapping_status"],
                        "mapping_source_url": US_REVIEW_SOURCE_URLS[mapping["sector"]],
                        "retained_kis_industry_code": text(row.get("discovery_industry_code")),
                        "kis_identity": {k: identity[row.symbol][k] for k in
                            ("identity_basis", "source", "security_type", "review_reasons")},
                        "cap": cap,
                        "benchmarks": benchmarks, "stage_inputs": run,
                        "blocking_reasons": reasons, "offline_review_eligible": not reasons,
                        "review_only_stage_label": label,
                        "recorded_statuses": {k: text(row.get(k)) for k in
                            ("identity_status", "provider_status", "activation_status", "market_cap_status")},
                        "operational_approval_granted": False})
    return results


def build_report(data, as_of, baseline_path):
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    ids = [r["symbol"] for r in baseline["candidates"]]
    if len(ids) != len(set(ids)) or len(ids) != baseline["selected_candidates"]:
        raise ValueError("Saved baseline membership/count mismatch")
    baseline_counts = Counter(r["review_only_stage_label"] for r in baseline["candidates"])
    if dict(baseline_counts) != baseline["review_only_stage_counts"]:
        raise ValueError("Saved baseline labels/counts mismatch")
    inputs = {name: fingerprint(data / name) for name in INPUTS}
    read = lambda name: pd.read_csv(data / name, dtype=str, keep_default_na=False)
    registry, master = read(INPUTS[0]), read(INPUTS[1])
    prices = pd.concat([read("daily_prices.csv"), read("candidate_daily_prices.csv")], ignore_index=True)
    rows = expand_rows(registry, master, read(INPUTS[2]).to_dict("records"),
                       read(INPUTS[3]), prices, as_of, ids)
    counts = Counter(r["review_only_stage_label"] for r in rows if r["offline_review_eligible"])
    match_basis = {n: baseline_input_match(data / n, baseline["input_files"].get(n)) for n in INPUTS}
    matches = {n: basis != "different" for n, basis in match_basis.items()}
    comparable = as_of == baseline["as_of"] and all(matches.values())
    us = registry[registry.exchange.isin(["NAS", "NYS", "AMS"])]
    missing = us[us.proposed_sector.eq("") | us.proposed_sector_benchmark.eq("")]
    return {"schema_version": 1, "as_of": as_of,
            "policy": "review only; no status transitions; only additions replayed; KIS default trust; cap estimates are not confirmed values",
            "input_files": inputs,
            "implementation_files": {n: fingerprint(ROOT / n) for n in
                ("stock_mapping.py", "stage_engine.py", "us_stage_connection_plan.py",
                 "us_kis_evidence_readiness.py", "us_stage_mapping_expansion.py")},
            "baseline": {"file": baseline_path.name, **fingerprint(baseline_path),
                         "as_of": baseline["as_of"], "selected_candidates": len(ids),
                         "review_only_stage_counts": dict(baseline_counts),
                         "recomputed_candidates": 0, "matching_input_files": matches,
                         "input_match_basis": match_basis},
            "same_snapshot_comparison": comparable,
            "combined_same_snapshot_counts": dict(baseline_counts + counts) if comparable else None,
            "cumulative_review_coverage": len(ids) + sum(counts.values()),
            "coverage_note": "Historical baseline plus additional eligible names; current labels for the baseline are not revalidated.",
            "additional_mapping_count": len(US_REVIEW_SECTOR_ADDITIONS),
            "additional_registry_count": len(rows), "additional_eligible_count": sum(counts.values()),
            "additional_stage_counts": dict(counts),
            "additional_blocker_counts": dict(Counter(reason for r in rows for reason in r["blocking_reasons"])),
            "mapping_gap_inventory": {"us_registry_count": len(us),
                "stored_proposal_missing_count": len(missing),
                "missing_with_usable_kis_industry_code": int((~missing.discovery_industry_code.isin(["", "000"])).sum()),
                "master_has_industry_code_column": any("industry" in c for c in master)},
            "missing_addition_registry_symbols": sorted(set(US_REVIEW_SECTOR_ADDITIONS) - {r["symbol"] for r in rows}),
            "candidates": rows, "operational_additions": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--baseline", type=Path,
                        default=ROOT / "docs/evidence/us-stage-connection-20261104.json")
    args = parser.parse_args()
    print(json.dumps(build_report(args.data_dir, args.as_of, args.baseline),
                     ensure_ascii=True, sort_keys=True, indent=2))
