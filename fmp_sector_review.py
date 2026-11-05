"""Offline FMP profile adapter. No API client, credentials, writes or approvals.

Only an explicitly licensed observed cache can contribute actual additions.
Synthetic fixtures exercise the real existing KIS/cap/price/Stage gates separately.
SEC SIC is retained as its own taxonomy; it is never decoded into GICS/ETFs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse

import pandas as pd

from stock_mapping import proposed_stock_mapping
from us_sector_mapping_batch import build_report, evaluate_new_rows
from us_stage_connection_plan import MAPPING, text
from us_stage_mapping_expansion import INPUTS, fingerprint

ROOT = Path(__file__).resolve().parent
PROFILE_URL = "https://financialmodelingprep.com/stable/profile"
# FMP-native labels, not a claim that FMP uses the GICS methodology.
SECTORS = {
    "Basic Materials": ("Materials", "XLB"),
    "Communication Services": ("Communication Services", "XLC"),
    "Consumer Cyclical": ("Consumer Discretionary", "XLY"),
    "Consumer Defensive": ("Consumer Staples", "XLP"),
    "Energy": ("Energy", "XLE"),
    "Financial Services": ("Financials", "XLF"),
    "Healthcare": ("Health Care", "XLV"),
    "Industrials": ("Industrials", "XLI"),
    "Real Estate": ("Real Estate", "XLRE"),
    "Technology": ("Information Technology", "XLK"),
    "Utilities": ("Utilities", "XLU"),
}
VENUES = {"NASDAQ": "NAS", "NYSE": "NYS", "AMEX": "AMS"}


def profile_symbol(symbol):
    """Explicit share-class spelling only; never strip a class or try fallbacks."""
    symbol = text(symbol).upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]*(?:[/-][A-Z])?", symbol):
        raise ValueError("Unsupported provider symbol spelling")
    return symbol.replace("/", "-")


def utc_observation(value, as_of):
    if not isinstance(value, str):
        return False
    observed = pd.to_datetime(value, errors="coerce")
    return bool(not pd.isna(observed) and observed.tzinfo is not None
                and observed.utcoffset().total_seconds() == 0
                and observed.date() <= pd.Timestamp(as_of).date())


def source_matches(url, symbol):
    parsed = urlparse(text(url))
    return (parsed.scheme == "https" and parsed.netloc == "financialmodelingprep.com"
            and parsed.path == "/stable/profile" and parsed.fragment == ""
            and parse_qs(parsed.query, keep_blank_values=True) == {"symbol": [symbol]})


def cache_policy(cache):
    mode = cache.get("mode", "missing")
    if mode not in {"missing", "synthetic", "observed"}:
        raise ValueError("Cache mode must be missing, synthetic or observed")
    # A caller's statement records permission evidence; it does not grant a licence.
    rights = cache.get("rights", {})
    allowed = (mode == "synthetic" or (mode == "observed"
        and rights.get("local_storage") is True
        and rights.get("offline_processing") is True
        and bool(text(rights.get("evidence_reference")))))
    return mode, allowed


def profile_packets(registry, universe, cache, as_of):
    """Provider proposals for normal rows; only exceptions need manual review."""
    mode, allowed = cache_policy(cache)
    frame = registry.copy()
    frame["symbol"] = frame.symbol.map(text).str.upper()
    if frame.symbol.eq("").any() or frame.symbol.duplicated().any():
        raise ValueError("Registry requires unique nonempty symbols")
    grouped = defaultdict(list)
    for obs in cache.get("observations", []):
        grouped[text(obs.get("registry_symbol")).upper()].append(obs)
    packets = []
    for _, row in frame.sort_values("symbol").iterrows():
        venue = text(row.exchange).upper()
        if venue not in {"NAS", "NYS", "AMS"}:
            continue
        current = proposed_stock_mapping(row.symbol, venue, text(row.get("discovery_dr_country_code")))
        proposal = {k: current["proposed_" + k] for k in MAPPING}
        reasons, mapping, native = [], None, None
        records = grouped.get(row.symbol, [])
        if not records:
            reasons.append("fmp_profile_missing")
        elif len(records) != 1:
            reasons.append("duplicate_profile_observations")
        else:
            obs = records[0]
            payload = obs.get("response")
            if not allowed:
                reasons.append("storage_or_processing_permission_unverified")
            if obs.get("http_status") != 200:
                reasons.append("profile_request_not_successful")
            if not utc_observation(obs.get("fetched_at_utc"), as_of):
                reasons.append("observation_time_missing_future_or_not_utc")
            try:
                expected = profile_symbol(row.symbol)
            except ValueError:
                expected = ""
                reasons.append("provider_symbol_spelling_unsupported")
            if (not expected or text(obs.get("requested_symbol")) != expected
                    or not source_matches(obs.get("source_url"), expected)):
                reasons.append("request_symbol_or_source_mismatch")
            if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
                reasons.append("profile_payload_invalid_or_ambiguous")
            else:
                p = payload[0]
                native = {k: p.get(k) for k in ("sector", "industry", "exchange", "companyName", "cik")}
                if (text(p.get("symbol")) != expected
                        or VENUES.get(text(p.get("exchange"))) != venue):
                    reasons.append("provider_listing_identity_conflict")
                if not text(p.get("companyName")):
                    reasons.append("provider_company_name_missing")
                if (p.get("isEtf") is not False or p.get("isFund") is not False
                        or p.get("isActivelyTrading") is not True):
                    reasons.append("provider_security_type_or_active_status_unverified")
                target = SECTORS.get(text(p.get("sector")))
                if target is None:
                    reasons.append("provider_sector_unsupported")
                if not text(p.get("industry")):
                    reasons.append("provider_industry_missing")
                if target:
                    sector, etf = target
                    for sector_field, etf_field in (("sector", "sector_benchmark"),
                                                    ("proposed_sector", "proposed_sector_benchmark")):
                        if ((text(row.get(sector_field)) and text(row.get(sector_field)) != sector)
                                or (text(row.get(etf_field)) and text(row.get(etf_field)) != etf)):
                            reasons.append("stored_mapping_conflict")
                    if ((proposal["sector"] and proposal["sector"] != sector)
                            or (proposal["sector_benchmark"] and proposal["sector_benchmark"] != etf)):
                        reasons.append("curated_mapping_conflict")
                    matches = universe[universe.symbol.eq(etf)]
                    if (len(matches) != 1 or text(matches.iloc[0].get("sector")) != sector
                            or text(matches.iloc[0].get("asset_type")) != "sector_etf"
                            or text(matches.iloc[0].get("provider")) != "KIS"
                            or text(matches.iloc[0].get("active")).lower() != "true"):
                        reasons.append("sector_etf_metadata_missing_or_conflicting")
                    if not reasons:
                        mapping = dict(proposal, sector=sector, sector_benchmark=etf)
        packets.append({"symbol": row.symbol, "venue": venue,
            "existing_proposal": proposal, "batch_mapping": mapping,
            "mapping_class": "provider_based_proposed" if mapping else
                "provider_data_missing" if not records else "review_required",
            "mapping_reasons": sorted(set(reasons)), "provider_native": native,
            "classification_system": "FMP-native; explicit project ETF crosswalk",
            "source_as_of": None,  # Profile has no dated classification history.
            "cache_mode": mode, "operational_approval_granted": False})
    return packets


def normalize_sec_sic(payload, source_url, fetched_at_utc, as_of):
    """Retain issuer SIC and ticker/exchange pairs without assigning an ETF.

    Current submissions metadata has no SIC effective date. Filing date is not
    substituted for that date. A CIK is issuer identity, not a share-class key.
    """
    cik = text(payload.get("cik"))
    sic = text(payload.get("sic"))
    tickers, exchanges = payload.get("tickers", []), payload.get("exchanges", [])
    if (not cik.isdigit() or len(cik) > 10
            or source_url != f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
            or not utc_observation(fetched_at_utc, as_of)
            or not re.fullmatch(r"[0-9]{3,4}", sic)
            or int(sic) == 0
            or not text(payload.get("sicDescription"))
            or not tickers or len(tickers) != len(exchanges)):
        raise ValueError("Invalid SEC SIC provenance or listing pairs")
    pairs = [{"ticker": text(t), "exchange": text(e)} for t, e in zip(tickers, exchanges)]
    if any(not p["ticker"] or not p["exchange"] for p in pairs):
        raise ValueError("Blank SEC listing identity")
    return {"cik": cik.zfill(10), "classification_system": "SEC SIC",
        "industry_code": sic.zfill(4), "industry": payload["sicDescription"],
        "listing_pairs": pairs, "source_url": source_url,
        "observed_at_utc": fetched_at_utc, "source_as_of": None,
        "proposed_sector": None, "proposed_sector_benchmark": None,
        "mapping_status": "crosswalk_not_established", "operational_approval_granted": False}


def pilot_plan(rows, limit=5):
    """Deterministic sector/venue round-robin of the otherwise-ready candidates."""
    buckets = defaultdict(list)
    for row in sorted(rows, key=lambda r: r["symbol"]):
        buckets[(row["existing_proposal"]["sector"], row["venue"])].append(row)
    result = []
    while len(result) < limit and any(buckets.values()):
        for key in sorted(buckets):
            if buckets[key] and len(result) < limit:
                row = buckets[key].pop(0)
                result.append({"registry_symbol": row["symbol"], "venue": row["venue"],
                    "requested_symbol": profile_symbol(row["symbol"]),
                    "source_url": PROFILE_URL + "?symbol=" + profile_symbol(row["symbol"]),
                    "planned_only": True})
    return result


def report(data, as_of, cache=None):
    cache = cache or {"mode": "missing", "observations": []}
    mode, _ = cache_policy(cache)
    baseline = build_report(data, as_of)
    conditional = [p for p in baseline["candidates"] if p["proposal_only_stage_inputs"] is not None
        and p["proposal_only_stage_inputs"]["inputs_ready"] and p["cap"]["threshold_pass"]
        and p["kis_identity"]["identity_basis"] == "kis_master_consistent"]
    symbols = {p["symbol"] for p in conditional}
    read = lambda n: pd.read_csv(data / n, dtype=str, keep_default_na=False)
    registry = read(INPUTS[0])
    registry = registry[registry.symbol.isin(symbols)]
    universe = read(INPUTS[3])
    packets = profile_packets(registry, universe, cache, as_of)
    prices = pd.concat([read(INPUTS[4]), read(INPUTS[5])], ignore_index=True)
    rows = evaluate_new_rows(packets, registry, read(INPUTS[1]), read(INPUTS[2]).to_dict("records"),
                             universe, prices, as_of, set())
    eligible = [r["symbol"] for r in rows if r["offline_review_eligible"]]
    actual = eligible if mode == "observed" else []
    actual_profiles = sum(bool(r["batch_mapping"]) for r in rows) if mode == "observed" else 0
    return {"schema_version": 1, "as_of": as_of, "cache_mode": mode,
        "network_requests_this_run": 0, "fmp_api_key_used": False,
        "saved_baseline_count": baseline["saved_baseline"]["count"],
        "saved_baseline_recomputed": False, "otherwise_ready_count": len(conditional),
        "otherwise_ready_symbols": sorted(symbols), "planned_five_symbol_pilot": pilot_plan(conditional),
        "observed_usable_profiles": actual_profiles, "actual_additional_eligible_count": len(actual),
        "actual_additional_eligible_symbols": actual,
        "cumulative_review_coverage": baseline["saved_baseline"]["count"] + len(actual),
        "synthetic_eligible_count": len(eligible) if mode == "synthetic" else 0,
        "mapping_counts": dict(Counter(r["mapping_class"] for r in rows)),
        "blocker_counts": dict(Counter(x for r in rows for x in r["blocking_reasons"])),
        "input_files": {n: fingerprint(data / n) for n in INPUTS},
        "implementation_files": {n: fingerprint(ROOT / n) for n in (
            "fmp_sector_review.py", "stock_mapping.py", "us_sector_mapping_batch.py",
            "us_stage_connection_plan.py", "stage_engine.py")},
        "cache_observation_count": len(cache.get("observations", [])),
        "scope": "existing conditional candidates only; no approval, activation or baseline label claims",
        "operational_additions": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    cache = json.loads(args.cache.read_text(encoding="utf-8")) if args.cache else None
    result = report(args.data_dir, args.as_of, cache)
    if args.cache:
        result["cache_file"] = fingerprint(args.cache)
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
