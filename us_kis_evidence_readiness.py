"""Read-only KIS evidence assessment; no registry transitions or live calls.

KIS listing/type evidence can satisfy an offline identity basis without an
external issuer lookup. It never writes verified/supported/approved/active.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import pandas as pd

from audit_us_stage_readiness import build_audit
from kis_universe import normalize_market_cap_candidates


def assess_candidates(registry, master, dimensions):
    """Assess stored KIS master rows and existing audit dimensions independently.

    Missing evidence is not a conflict. Duplicate ticker/master keys fail closed
    per row; ordinary candidates with coherent KIS evidence need no external ID.
    The saved unranked master is partial: absence says nothing about delisting.
    """
    registry, master = registry.copy(), master.copy()
    for frame in (registry, master):
        for col in ("symbol",):
            frame[col] = frame[col].fillna("").astype(str).str.strip().str.upper()
    master["listing_exchange"] = master.listing_exchange.str.strip().str.upper()
    registry["exchange"] = registry.exchange.str.strip().str.upper()
    registry = registry[registry.exchange.isin(["NAS", "NYS", "AMS"])]
    groups = {s: g for s, g in master.groupby("symbol")}
    duplicate = set(registry.loc[registry.symbol.duplicated(False), "symbol"])
    result = []
    for _, r in registry.iterrows():
        s = r.symbol
        d = dimensions.get(s, {})
        matches = groups.get(s, master.iloc[:0])
        source = "unranked_us_stock_master.csv" if len(matches) else "missing"
        # Discovery persists the normalized authoritative master type for KIS
        # ranking rows. Reuse this explicit field, never infer it from prices.
        if matches.empty and r.get("discovery_source") == "KIS market-cap ranking" and r.get("discovery_security_type") in ("stock", "etp", "index", "warrant"):
            code = {"stock": "2", "etp": "3", "index": "1", "warrant": "4"}[r.discovery_security_type]
            matches = pd.DataFrame([{"listing_exchange": r.exchange, "master_security_type": code}])
            source = "stock_universe_candidates.csv:discovery_source+discovery_security_type"
        reasons = []
        basis = "missing_kis_master"
        kind = "unknown"
        if s in duplicate or len(matches) > 1:
            reasons.append("duplicate_ticker_or_master")
        elif len(matches) == 1:
            m = matches.iloc[0]
            if m.listing_exchange != r.exchange:
                reasons.append("exchange_conflict")
            raw_type = str(m.master_security_type).strip()
            # Reuse discovery's established ETF/preferred/warrant/ADR heuristics.
            normalized = normalize_market_cap_candidates(pd.DataFrame([{
                "symb": s, "listing_exchange": m.listing_exchange,
                "ename": m.get("english_name", ""), "name": r.get("name", ""),
                "master_security_type": raw_type,
                "master_dr_flag": m.get("master_dr_flag", ""),
                "master_dr_country_code": m.get("master_dr_country_code", r.get("discovery_dr_country_code", "")),
            }])).iloc[0]
            kind = normalized.master_instrument_type
            if raw_type != "2":
                reasons.append("security_type_unknown_or_non_stock")
            if normalized.instrument_type_guess in ("fund_or_etf_likely", "non_common_security_likely"):
                reasons.append("non_common_or_fund_signal")
            declared_type = str(r.get("discovery_security_type", "")).strip()
            if declared_type and declared_type not in (raw_type, kind):
                reasons.append("registry_master_type_conflict")
            adr = bool(normalized.is_adr_candidate) or "adr" in str(r.get("instrument_type", "")).lower()
            if adr and r.get("depositary_ratio_status", "") != "verified":
                reasons.append("adr_ratio_unconfirmed")
            basis = "kis_master_consistent" if not reasons else "review_needed"
        if len(matches) != 1 and "adr" in str(r.get("instrument_type", "")).lower():
            reasons.append("adr_master_and_ratio_review")
        if reasons:
            basis = "review_needed"
        data_ready = all(d.get(k, False) for k in (
            "cap_screen_pass", "price_quality_pass", "weeks35",
            "assigned_stage_data_inputs_available"))
        result.append({
            "symbol": s, "exchange": r.exchange, "identity_basis": basis,
            "security_type": kind, "review_reasons": sorted(set(reasons)),
            "additional_review_required": bool(reasons),
            "provider_evidence": "stored_valid_prices" if d.get("price_quality_pass") else "untested_or_invalid_prices",
            "provider_status_recorded": r.get("provider_status", ""),
            "identity_status_recorded": r.get("identity_status", ""),
            "mapping_status_recorded": r.get("mapping_status", ""),
            "activation_status_recorded": r.get("activation_status", ""),
            "cap_basis": "confirmed" if d.get("cap_verified") else "estimate" if d.get("cap_value_present") else "missing",
            "cap_threshold_pass": bool(d.get("cap_screen_pass")),
            "price_quality_pass": bool(d.get("price_quality_pass")),
            "completed_weeks35": bool(d.get("weeks35")),
            "assigned_benchmarks35": bool(d.get("assigned_benchmarks35")),
            "assigned_rs_finite": bool(d.get("assigned_rs_finite")),
            "assigned_mapping_present": bool(d.get("mapping_fields_present")),
            "proposed_mapping_present": bool(d.get("proposed_mapping_present")),
            "data_inputs_ready": data_ready,
            "offline_review_eligible": basis == "kis_master_consistent" and data_ready,
            "operational_approval_granted": False,
            "source": source,
        })
    return result


def build_report(data: Path, as_of: str):
    audit = build_audit(data, as_of, include_rows=True)
    dims = {r["symbol"]: r for r in audit.pop("candidate_dimensions")}
    read = lambda name: pd.read_csv(data / name, dtype=str, keep_default_na=False)
    rows = assess_candidates(read("stock_universe_candidates.csv"), read("unranked_us_stock_master.csv"), dims)
    master_path = data / "unranked_us_stock_master.csv"
    audit["input_files"][master_path.name] = {"sha256": hashlib.sha256(master_path.read_bytes()).hexdigest(), "bytes": master_path.stat().st_size}
    return {"as_of_date": as_of, "input_files": audit["input_files"],
            "policy": "offline only; evidence does not transition registry statuses; missing master requires retained KIS evidence, not routine external lookup",
            "counts": {k: dict(Counter(str(r[k]) for r in rows)) for k in (
                "identity_basis", "security_type", "provider_evidence", "cap_basis", "cap_threshold_pass", "completed_weeks35", "assigned_mapping_present", "proposed_mapping_present", "assigned_benchmarks35", "assigned_rs_finite", "data_inputs_ready", "offline_review_eligible", "activation_status_recorded")},
            "review_reason_counts": dict(Counter(v for r in rows for v in r["review_reasons"])),
            "actual_bridge": audit["actual_bridge"], "candidates": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent / "data")
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    print(json.dumps(build_report(args.data_dir, args.as_of), indent=2, sort_keys=True))
