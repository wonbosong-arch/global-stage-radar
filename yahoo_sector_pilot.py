"""Offline Yahoo Sector/Industry pilot; never fetch, approve or write registries.

Accepts explicitly supplied saved observations, not Yahoo market-cap proposals.
The existing yfinance get_info path is deliberately NOT invoked: public access
and the presence of yfinance do not establish permission for automated capture.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from urllib.parse import quote

import pandas as pd

from stock_mapping import proposed_stock_mapping
from yahoo_market_cap_supplement import yahoo_ticker_symbol
from us_sector_mapping_batch import build_report as batch_report, evaluate_new_rows
from us_stage_connection_plan import MAPPING, text
from us_stage_mapping_expansion import INPUTS, baseline_input_match, fingerprint

ROOT = Path(__file__).resolve().parent
SEED = "global-stage-radar/yahoo-sector-pilot/v1"
# Exact provider vocabulary only. No fuzzy matching, industry inference, or SOXX
# substitution: Yahoo's broad Technology sector cannot confirm a semiconductor
# benchmark. Such differences must stay review_required.
SECTOR_TO_ETF = {
    "Technology": ("Information Technology", "XLK"),
    "Financial Services": ("Financials", "XLF"),
    "Communication Services": ("Communication Services", "XLC"),
    "Consumer Cyclical": ("Consumer Discretionary", "XLY"),
    "Consumer Defensive": ("Consumer Staples", "XLP"),
    "Healthcare": ("Health Care", "XLV"),
    "Industrials": ("Industrials", "XLI"),
    "Energy": ("Energy", "XLE"),
    "Basic Materials": ("Materials", "XLB"),
    "Real Estate": ("Real Estate", "XLRE"),
    "Utilities": ("Utilities", "XLU"),
}


def profile_url(symbol):
    return f"https://finance.yahoo.com/quote/{quote(yahoo_ticker_symbol(symbol), safe='-')}/profile/"


def observed_text(record, key):
    """Malformed provider fields withhold that row instead of failing a batch."""
    value = record.get(key)
    return value.strip() if isinstance(value, str) else ""


def conditional_symbols(report):
    """Keep PR215's actual cap/KIS/price/benchmark gates, not a ticker list guess."""
    return sorted(r["symbol"] for r in report["candidates"]
        if r["symbol"] not in report["saved_baseline"]["symbols"]
        and r["proposal_only_stage_inputs"] is not None
        and r["proposal_only_stage_inputs"]["inputs_ready"]
        and r["cap"]["threshold_pass"]
        and r["kis_identity"]["identity_basis"] == "kis_master_consistent")


def balanced_sample(registry, symbols, size=100):
    """Deterministic round-robin of existing proposal sector x KIS venue strata.

    Existing proposals define sampling strata ONLY, never Yahoo observations.
    Seeded SHA256 order avoids dataframe/Python-hash-order dependence. Include
    slash share classes first to exercise the existing Yahoo ticker translation.
    """
    if registry.symbol.duplicated().any() or not set(symbols).issubset(set(registry.symbol)):
        raise ValueError("Sample requires unique registry and known symbols")
    if size < 1 or size > len(set(symbols)):
        raise ValueError("Sample size exceeds available unique population")
    rows = registry.set_index("symbol")
    rank = lambda s: hashlib.sha256(f"{SEED}:{s}".encode()).hexdigest()
    buckets = defaultdict(list)
    for symbol in sorted(set(symbols), key=rank):
        row = rows.loc[symbol]
        p = proposed_stock_mapping(symbol, row.exchange, text(row.get("discovery_dr_country_code")))
        buckets[(p["proposed_sector"], row.exchange)].append(symbol)
    selected = sorted((s for s in set(symbols) if "/" in s), key=rank)[:size]
    while len(selected) < size:
        for key in sorted(buckets):
            pool = buckets[key]
            while pool and pool[0] in selected:
                pool.pop(0)
            if pool and len(selected) < size:
                selected.append(pool.pop(0))
    result = []
    for index, symbol in enumerate(selected, 1):
        row = rows.loc[symbol]
        p = proposed_stock_mapping(symbol, row.exchange, text(row.get("discovery_dr_country_code")))
        result.append({"order": index, "symbol": symbol, "kis_exchange": row.exchange,
            "sampling_sector_proposal": p["proposed_sector"],
            "sampling_etf_proposal": p["proposed_sector_benchmark"],
            "yahoo_symbol": yahoo_ticker_symbol(symbol), "source_url": profile_url(symbol),
            "edge_case": "share_class_translation" if "/" in symbol else
                "broad_sector_vs_specialist_proxy" if p["proposed_sector"] == "Semiconductors" else ""})
    return result


def mapping_packets(registry, observations, universe, as_of):
    """Create separate review packets; Yahoo cannot approve KIS identity/type."""
    if registry.symbol.eq("").any() or registry.symbol.duplicated().any():
        raise ValueError("Registry requires unique nonempty symbols")
    grouped = defaultdict(list)
    for record in observations:
        grouped[observed_text(record, "symbol").upper()].append(record)
    end = pd.Timestamp(as_of, tz="UTC") + pd.Timedelta(days=1)
    result = []
    for _, row in registry.sort_values("symbol").iterrows():
        symbol = row.symbol
        p = proposed_stock_mapping(symbol, row.exchange, text(row.get("discovery_dr_country_code")))
        proposal = {k: p["proposed_" + k] for k in MAPPING}
        matches = grouped.get(symbol, [])
        reasons, mapping = [], None
        observation = {"sector": "", "industry": "", "fetched_at_utc": ""}
        audit = {"source_url": profile_url(symbol), "network_calls_in_this_run": 0,
                 "http_status": None, "duration_ms": None, "error_code": "",
                 "retry_after_seconds": None}
        if not matches:
            reasons.append("yahoo_observation_missing")
        elif len(matches) != 1:
            reasons.append("duplicate_or_conflicting_yahoo_observations")
        else:
            obs = matches[0]
            observation = {k: observed_text(obs, k) for k in observation}
            # Preserve bounded diagnostic fields, never provider messages/cookies.
            for key in ("http_status", "duration_ms", "retry_after_seconds"):
                value = obs.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value < 1e9:
                    audit[key] = value
            error = observed_text(obs, "error_code")
            audit["error_code"] = error if error in {
                "http_401", "http_403", "http_429", "timeout", "network_error", "parse_error"} else "other_error" if error else ""
            if error or (audit["http_status"] is not None and audit["http_status"] != 200):
                reasons.append("yahoo_capture_failed")
            raw_timestamp = observed_text(obs, "fetched_at_utc")
            timestamp = pd.to_datetime(raw_timestamp, utc=True, errors="coerce")
            # Naive dates do not document an observation time/timezone.
            try:
                aware = pd.Timestamp(raw_timestamp).tzinfo is not None
            except (ValueError, TypeError):
                aware = False
            if (pd.isna(timestamp) or not aware or timestamp >= end):
                reasons.append("yahoo_capture_time_invalid_or_future")
            elif end - timestamp > pd.Timedelta(days=7):
                reasons.append("yahoo_observation_stale_over_7_days")
            if (observed_text(obs, "yahoo_symbol") != yahoo_ticker_symbol(symbol)
                    or observed_text(obs, "requested_kis_exchange") != row.exchange
                    or observed_text(obs, "source_url") != profile_url(symbol)):
                reasons.append("yahoo_request_binding_conflict")
            if not observation["industry"]:
                reasons.append("yahoo_industry_missing")
            pair = SECTOR_TO_ETF.get(observation["sector"])
            if pair is None:
                reasons.append("yahoo_sector_missing_or_unsupported")
            else:
                sector, etf = pair
                for sector_key, etf_key in (("sector", "sector_benchmark"),
                                            ("proposed_sector", "proposed_sector_benchmark")):
                    if ((text(row.get(sector_key)) and text(row.get(sector_key)) != sector)
                            or (text(row.get(etf_key)) and text(row.get(etf_key)) != etf)):
                        reasons.append("stored_mapping_conflict")
                if ((proposal["sector"] and proposal["sector"] != sector)
                        or (proposal["sector_benchmark"] and proposal["sector_benchmark"] != etf)):
                    reasons.append("curated_mapping_conflict")
                matches_etf = universe[universe.symbol.eq(etf)]
                if (len(matches_etf) != 1 or text(matches_etf.iloc[0].get("sector")) != sector
                        or text(matches_etf.iloc[0].get("asset_type")) != "sector_etf"
                        or text(matches_etf.iloc[0].get("provider")) != "KIS"
                        or text(matches_etf.iloc[0].get("active")).lower() != "true"):
                    reasons.append("sector_etf_metadata_missing_or_conflicting")
                if not reasons:
                    # Preserve existing country/benchmark policy. Unknown market
                    # metadata cannot be filled by a Yahoo sector observation.
                    mapping = dict(proposal, sector=sector, sector_benchmark=etf)
        result.append({"symbol": symbol, "venue": row.exchange,
            "existing_proposal": proposal, "batch_mapping": mapping,
            "mapping_reasons": sorted(set(reasons)),
            "mapping_class": "yahoo_review_proposal" if mapping else "review_required",
            "yahoo_observation": observation, "audit": audit,
            "operational_approval_granted": False})
    return result


def load_observations(path):
    if path is None:
        return "none", []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (payload.get("schema_version") != 1 or payload.get("data_origin") not in {"cache", "fixture"}
            or not isinstance(payload.get("records"), list)
            or not all(isinstance(r, dict) for r in payload["records"])):
        raise ValueError("Expected version 1 cache/fixture observation envelope")
    return payload["data_origin"], payload["records"]


def build_report(data, as_of, observations_path=None, replay_path=None):
    """All outputs are JSON stdout. No default writes under data/ or elsewhere."""
    if replay_path:
        base = json.loads(replay_path.read_text(encoding="utf-8"))
        if (base["as_of"] != as_of or any(baseline_input_match(data / n, base["input_files"][n])
                                         == "different" for n in INPUTS)
                or any(baseline_input_match(ROOT / n, digest) == "different"
                       for n, digest in base["implementation_files"].items())):
            raise ValueError("Cached batch replay does not match current inputs/code/as-of")
    else:
        base = batch_report(data, as_of)
    read = lambda n: pd.read_csv(data / n, dtype=str, keep_default_na=False)
    registry, master, universe = read(INPUTS[0]), read(INPUTS[1]), read(INPUTS[3])
    targets = conditional_symbols(base)
    selected = balanced_sample(registry, targets, min(100, len(targets))) if targets else []
    origin, observations = load_observations(observations_path)
    # Include pilot and remaining conditional targets; never convert the 85 saved
    # baseline rows into newly evaluated or newly approved Yahoo mappings.
    target_registry = registry[registry.symbol.isin(targets)]
    packets = mapping_packets(target_registry, observations, universe, as_of)
    ready = [p for p in packets if p["batch_mapping"]]
    evaluated = []
    if ready:
        prices = pd.concat([read(INPUTS[4]), read(INPUTS[5])], ignore_index=True)
        evaluated = evaluate_new_rows(ready, target_registry, master,
            read(INPUTS[2]).to_dict("records"), universe, prices, as_of,
            set(base["saved_baseline"]["symbols"]))
    evaluated_by_symbol = {r["symbol"]: r for r in evaluated}
    for p in packets:
        if p["symbol"] in evaluated_by_symbol:
            p.update(evaluated_by_symbol[p["symbol"]])
        else:
            p.update(offline_review_eligible=False, review_only_stage_label=None,
                     blocking_reasons=p["mapping_reasons"])
    pilot_symbols = {r["symbol"] for r in selected}
    pilot = [p for p in packets if p["symbol"] in pilot_symbols]
    complete = lambda p: bool(p["yahoo_observation"]["sector"] and p["yahoo_observation"]["industry"])
    def counts(rows):
        return {"planned": len(rows), "sector_and_industry_present": sum(complete(p) for p in rows),
            "mapping_review_ready": sum(bool(p["batch_mapping"]) for p in rows),
            "stage_review_ready": sum(p["offline_review_eligible"] for p in rows),
            "review_reason_counts": dict(Counter(r for p in rows for r in p["blocking_reasons"]))}
    actual_new = sum(p["offline_review_eligible"] for p in packets) if origin == "cache" else 0
    cache_inventory = {}
    for path in sorted(data.glob("yahoo*.csv")):
        columns = list(pd.read_csv(path, nrows=0).columns)
        cache_inventory[path.name] = {**fingerprint(path), "sector_industry_columns":
            [c for c in columns if c in ("sector", "industry", "sector_benchmark")],
            "usable_as_yahoo_profile_evidence": False}
    return {"schema_version": 1, "as_of": as_of, "data_origin": origin,
        "policy": "offline; Yahoo sector/industry only; KIS identity/type/venue and stored prices authoritative; review only",
        "live": {"ticker_attempts": 0, "ticker_successes": 0, "ticker_success_rate": None,
            "ticker_latency_ms": None, "ticker_rate_limit_tested": False,
            "status": "not_run_offline_only",
            "automatic_login": False, "retries": 0},
        "sample_method": {"seed": SEED, "strata": "existing proposal sector x KIS exchange",
            "algorithm": "SHA256 order; share classes first; round-robin strata",
            "population": "conditional candidates passing PR215 non-sector gates",
            "representative_of_all_2148": False},
        "sample": selected, "pilot": counts(pilot), "conditional_targets": counts(packets),
        "input_files": {n: fingerprint(data / n) for n in INPUTS},
        "batch_replay_file": fingerprint(replay_path) if replay_path else None,
        "observation_file": fingerprint(observations_path) if observations_path else None,
        "observation_records": len(observations),
        "unmatched_observation_symbols": sorted({observed_text(o, "symbol").upper() for o in observations} - set(targets)),
        "existing_yahoo_cache_inventory": cache_inventory,
        "sector_to_etf": {s: {"sector": p[0], "etf": p[1]} for s, p in SECTOR_TO_ETF.items()},
        "saved_baseline": base["saved_baseline"], "baseline_recomputed": 0,
        "actual_additional_review_coverage": actual_new,
        "saved_plus_additional_membership_count": base["saved_baseline"]["count"] + actual_new,
        "current_baseline_labels_revalidated": False, "operational_additions": 0,
        "targets": packets}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--observations", type=Path, help="saved cache/fixture JSON; never initiates collection")
    parser.add_argument("--batch-replay", type=Path, help="optional matching full PR215 batch replay JSON")
    args = parser.parse_args()
    print(json.dumps(build_report(args.data_dir, args.as_of, args.observations, args.batch_replay),
                     ensure_ascii=True, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
