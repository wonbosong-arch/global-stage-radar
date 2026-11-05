"""Batch saved US sector evidence into review packets, never operational mappings.

No network, registry writes, industry-code decoder, name heuristics or approval
bridge. Source annotations are bounded holdings observations, not full fund files.
Missing evidence is distinct from a disagreement with an existing proposal.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import pandas as pd

from stock_mapping import proposed_stock_mapping
from us_kis_evidence_readiness import assess_candidates
from us_stage_connection_plan import MAPPING, OfflineStageReplay, cap_provenance, text
from us_stage_mapping_expansion import INPUTS, baseline_input_match, fingerprint

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "docs/evidence/us-sector-mapping-sources-20261105.json"
BASELINE = ROOT / "docs/evidence/us-stage-connection-20261104.json"
EXPANSION = ROOT / "docs/evidence/us-stage-mapping-expansion-comparison-20261105.json"
HOLDINGS = "official_fund_top_holdings_name_match"
ISSUER = "retained_KIS_510_and_issuer_diagnostics_business_review"


def saved_baseline(baseline, expansion):
    """Validate saved membership and labels; do not re-run those 85 symbols."""
    rows = baseline["candidates"]
    first = {r["symbol"]: r["review_only_stage_label"] for r in rows}
    if len(first) != len(rows) or len(rows) != baseline["selected_candidates"]:
        raise ValueError("Baseline membership/count mismatch")
    if dict(Counter(first.values())) != baseline["review_only_stage_counts"]:
        raise ValueError("Baseline label/count mismatch")
    if not expansion["same_snapshot_comparison"] or expansion["as_of"] != baseline["as_of"]:
        raise ValueError("Baseline and expansion require the same saved snapshot")
    extra = [r for r in expansion["candidates"] if r["offline_review_eligible"]]
    symbols = [r["symbol"] for r in extra]
    if len(set(symbols)) != len(symbols) or set(symbols) & set(first):
        raise ValueError("Overlapping or duplicate expansion membership")
    first.update({r["symbol"]: r["review_only_stage_label"] for r in extra})
    counts = dict(Counter(first.values()))
    if (counts != expansion["combined_same_snapshot_counts"]
            or len(first) != expansion["cumulative_review_coverage"]):
        raise ValueError("Expansion label/count mismatch")
    return first, counts


def batch_mapping_rows(registry, source_records, universe, as_of):
    """Join exact symbols/venues/names; multiple or contradictory records withhold.

    KIS codes corroborate explicit issuer records only. They never propagate a
    sector to another ticker. Existing curated suggestions remain unchanged.
    """
    frame = registry.copy()
    frame["symbol"] = frame.symbol.map(text).str.upper()
    frame["exchange"] = frame.exchange.map(text).str.upper()
    if frame.symbol.eq("").any() or frame.symbol.duplicated().any():
        raise ValueError("Registry requires unique nonempty symbols")
    grouped = {}
    for record in source_records:
        grouped.setdefault(text(record.get("symbol")).upper(), []).append(record)
    result = []
    for _, row in frame[frame.exchange.isin(["NAS", "NYS", "AMS"])].sort_values("symbol").iterrows():
        current = proposed_stock_mapping(row.symbol, row.exchange, text(row.get("discovery_dr_country_code")))
        records = grouped.get(row.symbol, [])
        reasons = []
        mapping = None
        if len(records) > 1:
            reasons.append("duplicate_or_conflicting_source_records")
        elif len(records) == 1:
            source = records[0]
            sector, etf = text(source.get("proposed_sector")), text(source.get("proposed_sector_benchmark"))
            basis = text(source.get("basis"))
            observed = pd.to_datetime(source.get("observed_on"), errors="coerce")
            effective = pd.to_datetime(source.get("source_as_of"), errors="coerce")
            if (not text(source.get("source_url")).startswith("https://") or pd.isna(observed)
                    or (basis == HOLDINGS and (pd.isna(effective) or effective > pd.Timestamp(as_of)
                                               or effective > observed))):
                reasons.append("source_provenance_missing_or_invalid")
            if basis not in (HOLDINGS, ISSUER):
                reasons.append("unsupported_source_basis")
            if (text(source.get("listing_exchange")).upper() != row.exchange
                    or text(source.get("kis_recorded_name")).upper() != text(row.get("name")).upper()):
                reasons.append("source_listing_or_name_conflict")
            retained = text(source.get("retained_kis_industry_code"))
            code = text(row.get("discovery_industry_code"))
            if retained and retained != code:
                reasons.append("retained_kis_code_conflict")
            if basis == ISSUER and (not retained or retained == "000"):
                reasons.append("issuer_basis_requires_retained_kis_code")
            # An existing assigned/proposed mapping is never silently overwritten.
            for sector_field, etf_field in (("sector", "sector_benchmark"),
                                            ("proposed_sector", "proposed_sector_benchmark")):
                if ((text(row.get(sector_field)) and text(row.get(sector_field)) != sector)
                        or (text(row.get(etf_field)) and text(row.get(etf_field)) != etf)):
                    reasons.append("stored_mapping_conflict")
            if ((current["proposed_sector"] and current["proposed_sector"] != sector)
                    or (current["proposed_sector_benchmark"] and current["proposed_sector_benchmark"] != etf)):
                reasons.append("curated_mapping_conflict")
            matches = universe[universe.symbol.eq(etf)]
            if (not sector or len(matches) != 1 or text(matches.iloc[0].get("sector")) != sector
                    or text(matches.iloc[0].get("asset_type")) != "sector_etf"
                    or text(matches.iloc[0].get("provider")) != "KIS"
                    or text(matches.iloc[0].get("active")).lower() != "true"):
                reasons.append("sector_etf_metadata_missing_or_conflicting")
            if not reasons:
                mapping = {k: current["proposed_" + k] for k in MAPPING}
                mapping.update(sector=sector, sector_benchmark=etf)
        else:
            reasons.append("saved_sector_evidence_missing")
        result.append({"symbol": row.symbol, "venue": row.exchange,
            "retained_kis_industry_code": text(row.get("discovery_industry_code")),
            "existing_proposal": {k: current["proposed_" + k] for k in MAPPING},
            "source_records": records, "batch_mapping": mapping,
            "mapping_class": "evidence_backed_review_proposal" if mapping else
                "mapping_conflict" if any("conflict" in r for r in reasons) else
                "sector_evidence_missing_or_invalid",
            "mapping_reasons": sorted(set(reasons)), "operational_approval_granted": False})
    return result


def evaluate_new_rows(packets, registry, master, observations, universe, prices, as_of, baseline_symbols):
    """Replay only evidence-backed additions, preserving all identity/data gates."""
    by_symbol = {text(r.symbol).upper(): r for _, r in registry.iterrows()}
    identity = {r["symbol"]: r for r in assess_candidates(registry, master, {})}
    selected = [p for p in packets if p["symbol"] not in baseline_symbols]
    needed = {p["symbol"] for p in selected}
    for p in selected:
        mapping = p["batch_mapping"] or p["existing_proposal"]
        needed.update(mapping[k] for k in MAPPING[-2:] if mapping[k])
    replay = OfflineStageReplay(prices[prices.symbol.isin(needed)], as_of) if selected else None
    observations_by_symbol = {}
    for obs in observations:
        observations_by_symbol.setdefault(text(obs.get("symbol")).upper(), []).append(obs)
    result = []
    for packet in packets:
        p = dict(packet)
        symbol = p["symbol"]
        row = by_symbol[symbol]
        cap = cap_provenance(row, observations_by_symbol.get(symbol, []))
        p.update(cap=cap, kis_identity=identity[symbol], stage_inputs=None,
                 proposal_only_stage_inputs=None, candidate_price_inputs=None,
                 review_only_stage_label=None, offline_review_eligible=False,
                 recorded_statuses={k: text(row.get(k)) for k in
                     ("identity_status", "provider_status", "activation_status", "market_cap_status")})
        if symbol in baseline_symbols:
            p.update(evaluation_class="saved_baseline_preserved", blocking_reasons=[])
            result.append(p)
            continue
        reasons = list(p["mapping_reasons"])
        if not cap["threshold_pass"]:
            reasons.append("market_cap_below_1b_or_missing")
        if identity[symbol]["identity_basis"] != "kis_master_consistent":
            reasons.append("kis_identity_review_required")
        weeks = len(replay.weekly[symbol]) if replay.weekly.get(symbol) is not None else 0
        daily = replay.daily.get(symbol, 0)
        p["candidate_price_inputs"] = {"valid_daily_rows": daily, "completed_weeks": weeks,
            "completed_weeks35": weeks >= 35,
            "latest_session": str(replay.latest[symbol].date()) if symbol in replay.latest else None}
        if weeks < 35:
            reasons.append("candidate_completed_weeks35_missing")
        if daily < 150:
            reasons.append("candidate_valid_daily150_missing")
        if not p["batch_mapping"] and p["existing_proposal"]["sector"]:
            # Diagnostic of already-stored suggestions, never new mapping evidence.
            run = replay.replay(symbol, p["existing_proposal"])
            run.pop("review_only_stage_label")
            p["proposal_only_stage_inputs"] = run
        if p["batch_mapping"]:
            mapping = p["batch_mapping"]
            market = universe[universe.symbol.eq(mapping["market_benchmark"])]
            if (len(market) != 1 or text(market.iloc[0].get("asset_type")) != "market_etf"
                    or text(market.iloc[0].get("provider")) != "KIS"
                    or text(market.iloc[0].get("active")).lower() != "true"):
                reasons.append("market_benchmark_metadata_missing_or_conflicting")
            run = replay.replay(symbol, mapping)
            label = run.pop("review_only_stage_label")
            reasons.extend(run["reasons"])
            p["stage_inputs"] = run
            if not reasons:
                p.update(review_only_stage_label=label, offline_review_eligible=True)
        p.update(blocking_reasons=sorted(set(reasons)), evaluation_class=
                 "additional_review_eligible" if not reasons else "withheld")
        result.append(p)
    return result


def build_report(data, as_of, sources=SOURCES, baseline_path=BASELINE, expansion_path=EXPANSION):
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    expansion = json.loads(expansion_path.read_text(encoding="utf-8"))
    saved, labels = saved_baseline(baseline, expansion)
    source = json.loads(sources.read_text(encoding="utf-8"))
    read = lambda n: pd.read_csv(data / n, dtype=str, keep_default_na=False)
    registry, master, universe = read(INPUTS[0]), read(INPUTS[1]), read(INPUTS[3])
    packets = batch_mapping_rows(registry, source["records"], universe, as_of)
    if not set(saved).issubset({p["symbol"] for p in packets}):
        raise ValueError("Saved baseline missing from current registry")
    prices = pd.concat([read("daily_prices.csv"), read("candidate_daily_prices.csv")], ignore_index=True)
    rows = evaluate_new_rows(packets, registry, master, read(INPUTS[2]).to_dict("records"),
                             universe, prices, as_of, set(saved))
    counts = Counter(p["review_only_stage_label"] for p in rows if p["offline_review_eligible"])
    comparable = (as_of == baseline["as_of"] and all(
        baseline_input_match(data / n, baseline["input_files"][n]) != "different" for n in INPUTS))
    return {"schema_version": 1, "as_of": as_of,
        "policy": "saved evidence only; review only; KIS default trust; no code inference, status transitions or baseline replay",
        "input_files": {n: fingerprint(data / n) for n in INPUTS},
        "evidence_files": {p.name: fingerprint(p) for p in (sources, baseline_path, expansion_path)},
        "implementation_files": {n: fingerprint(ROOT / n) for n in (
            "us_sector_mapping_batch.py", "stock_mapping.py", "stage_engine.py",
            "us_stage_connection_plan.py", "us_kis_evidence_readiness.py")},
        "saved_baseline": {"as_of": baseline["as_of"], "count": len(saved),
            "stage_counts": labels, "symbols": sorted(saved), "recomputed_candidates": 0},
        "same_snapshot_comparison": comparable,
        "combined_same_snapshot_counts": dict(Counter(labels) + counts) if comparable else None,
        "additional_eligible_count": sum(counts.values()), "additional_stage_counts": dict(counts),
        "cumulative_review_coverage": len(saved) + sum(counts.values()),
        "current_baseline_labels_revalidated": False,
        "source_inventory": {"records": len(source["records"]),
            "holdings_annotations": sum(r.get("basis") == HOLDINGS for r in source["records"]),
            "full_holdings_file_available": False,
            "unmatched_source_symbols": sorted({text(r.get("symbol")).upper() for r in source["records"]}
                                               - {p["symbol"] for p in packets})},
        "counts": {k: dict(Counter(p[k] for p in rows)) for k in ("mapping_class", "evaluation_class")},
        "additional_blocker_counts": dict(Counter(r for p in rows if p["symbol"] not in saved
                                                 for r in p["blocking_reasons"])),
        "proposal_only_diagnostic": {
            "count": sum(p["proposal_only_stage_inputs"] is not None for p in rows),
            "otherwise_ready_without_saved_sector_evidence": sum(
                p["proposal_only_stage_inputs"] is not None
                and p["proposal_only_stage_inputs"]["inputs_ready"]
                and p["cap"]["threshold_pass"]
                and p["kis_identity"]["identity_basis"] == "kis_master_consistent" for p in rows),
            "labels_withheld": True},
        "kis_inventory": {"master_rows": len(master),
            "master_has_industry_column": any("industry" in c for c in master),
            "registry_code_counts": dict(Counter(p["retained_kis_industry_code"] for p in rows))},
        "candidates": rows, "operational_additions": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--sources", type=Path, default=SOURCES)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    print(json.dumps(build_report(args.data_dir, args.as_of, args.sources),
                     ensure_ascii=True, sort_keys=True, indent=2))
