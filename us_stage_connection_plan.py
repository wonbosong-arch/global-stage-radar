"""Offline, review-only Stage adapter. JSON stdout; no registry writes or network.

Replays assigned and suggested inputs without fabricating active/verified statuses.
The returned plan is deliberately not a monitoring-universe or approval payload.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from audit_us_stage_readiness import build_audit, numeric
from stage_engine import (weekly_bars, relative_return_difference, classify_stage,
                          stage_data_freshness_status)
from stock_mapping import proposed_stock_mapping
from us_kis_evidence_readiness import assess_candidates

MAPPING = ("market", "sector", "asset_type", "market_benchmark", "sector_benchmark")


def text(value):
    return "" if pd.isna(value) else str(value).strip()


def cap_provenance(row, observations):
    """Trace the *selected* screen value; unrelated/newer quotes cannot date it."""
    confirmed = text(row.get("market_cap_status")) == "verified"
    value = numeric(row.get("market_cap_usd")) if confirmed else np.nan
    field = "market_cap_usd"
    if pd.isna(value):
        value, field = numeric(row.get("market_cap_usd_b_secondary")) * 1e9, "market_cap_usd_b_secondary"
        confirmed = False
    if pd.isna(value):
        value, field = numeric(row.get("discovery_market_cap_usd")), "discovery_market_cap_usd"
    valid = bool(pd.notna(value) and np.isfinite(value) and value > 0)
    source = text(row.get("market_cap_source_url"))
    matches = []
    for obs in observations:
        observed = numeric(obs.get("discovery_market_cap_usd_b_secondary")) * 1e9
        if valid and pd.notna(observed) and math.isclose(value, observed, rel_tol=1e-10) and source and source == text(obs.get("market_cap_source_url")):
            matches.append(obs)
    # Do not borrow fetched_at/as-of from a different value, URL or revision.
    obs = matches[0] if len(matches) == 1 else {}
    yahoo = "finance.yahoo.com/" in source
    basis = text(obs.get("market_cap_asof_basis"))
    recorded_asof = text(row.get("market_cap_asof"))
    effective_asof = recorded_asof if not yahoo else (
        text(obs.get("market_cap_asof")) if basis == "source_provided_market_cap_date" else "")
    return {"basis": "confirmed_recorded" if confirmed and valid else "screening_estimate" if valid else "missing",
            "selected_usd": float(value) if valid else None,
            "selected_field": field, "source_url": source,
            "threshold_pass": bool(valid and value >= 1e9),
            "recorded_asof": recorded_asof, "effective_asof": effective_asof,
            "asof_basis": basis or "unlinked_or_unspecified",
            "observation_at_utc": text(obs.get("fetched_at_utc")),
            "evidence_link": "unique_value_and_url_match" if len(matches) == 1 else "ambiguous" if matches else "unlinked",
            "evidence_file": "yahoo_large_cap_candidate_review.csv" if obs else "",
            "formal_verification_granted": False}


class OfflineStageReplay:
    """Cache validated weekly inputs for both mapping paths; isolate bad symbols."""
    def __init__(self, prices, as_of):
        self.as_of = pd.Timestamp(as_of).normalize()
        self.weekly, self.daily = {}, {}
        self.latest = {}
        frame = prices.copy()
        frame["symbol"] = frame.symbol.map(text).str.upper()
        frame["date"] = pd.to_datetime(frame.date, errors="coerce")
        cols = ["open", "high", "low", "close", "volume"]
        frame[cols] = frame[cols].apply(pd.to_numeric, errors="coerce")
        for symbol, bars in frame.groupby("symbol"):
            v = bars[cols]
            valid = (bars.date.notna().all() and (bars.date <= self.as_of).all()
                     and not bars.date.duplicated().any() and np.isfinite(v.to_numpy()).all()
                     and (v[cols[:4]] > 0).all().all() and (v.volume >= 0).all()
                     and (v.high >= v[["open", "close", "low"]].max(axis=1)).all()
                     and (v.low <= v[["open", "close", "high"]].min(axis=1)).all())
            if valid:
                self.daily[symbol] = len(bars)
                self.latest[symbol] = bars.date.max()
                self.weekly[symbol] = weekly_bars(bars, as_of_date=self.as_of, min_bars=1)

    def replay(self, symbol, mapping):
        needed = [symbol, text(mapping.get("market_benchmark")), text(mapping.get("sector_benchmark"))]
        reasons = []
        if not all(text(mapping.get(k)) for k in MAPPING) or mapping.get("asset_type") != "stock":
            reasons.append("mapping_incomplete_or_not_stock")
        counts = {s: len(self.weekly[s]) if self.weekly.get(s) is not None else 0 for s in needed}
        if any(counts[s] < 35 for s in needed):
            reasons.append("completed_weeks35_missing")
        if any(self.daily.get(s, 0) < 150 for s in needed):
            reasons.append("valid_daily150_missing")
        if symbol in needed[1:]:
            reasons.append("self_benchmark")
        freshness = stage_data_freshness_status(symbol, "stock", *needed[1:], self.latest, self.as_of)
        bridge_fresh = all(s in self.latest and 0 <= (self.as_of - self.latest[s]).days <= 7 for s in needed)
        if freshness != "fresh" or not bridge_fresh:
            reasons.append("freshness_missing")
        rs = []
        if not reasons:
            w = self.weekly[symbol]
            rs = [relative_return_difference(w, self.weekly[s], 26).iloc[-1] for s in needed[1:]]
            if not np.isfinite(rs).all():
                reasons.append("aligned_rs_missing")
            elif not np.isfinite(w.iloc[-1][["ma30", "slope4_pct"]].to_numpy(dtype=float)).all():
                reasons.append("ma30_or_slope4_missing")
        label = None
        if not reasons:
            last = self.weekly[symbol].iloc[-1]
            label = classify_stage(last.close, last.ma30, last.slope4_pct, *rs, "stock")
        return {"inputs_ready": not reasons, "reasons": reasons,
                "completed_weeks": counts, "weeks30": counts[symbol] >= 30,
                "latest_sessions": {s: str(self.latest[s].date()) if s in self.latest else None for s in needed},
                "bridge_fresh_through": str((min(self.latest[s] for s in needed) + pd.Timedelta(days=7)).date()) if all(s in self.latest for s in needed) else None,
                "engine_freshness": freshness, "bridge_fresh7": bridge_fresh,
                "rs_finite": bool(rs and np.isfinite(rs).all()),
                "review_only_stage_label": label}


def prepare_connection_rows(registry, evidence, observations, prices, as_of):
    """Build review packets; never call an approval bridge with synthesized statuses."""
    selected = {r["symbol"]: r for r in evidence if r["offline_review_eligible"]}
    frame = registry.copy()
    frame["symbol"] = frame.symbol.map(text).str.upper()
    if frame.symbol.duplicated().any():
        raise ValueError("Duplicate registry symbol")
    if not set(selected).issubset(set(frame.symbol)):
        raise ValueError("Evidence membership differs from registry")
    frame = frame[frame.symbol.isin(selected)].sort_values("symbol")
    mappings = {}
    for _, row in frame.iterrows():
        mappings[row.symbol] = proposed_stock_mapping(row.symbol, row.exchange, text(row.get("discovery_dr_country_code")))
    needed = set(frame.symbol)
    for _, row in frame.iterrows():
        needed.update(text(row.get(k)) for k in MAPPING[-2:])
        needed.update(text(mappings[row.symbol].get("proposed_" + k)) for k in MAPPING[-2:])
    replay = OfflineStageReplay(prices[prices.symbol.isin(needed)], as_of)
    result = []
    for _, row in frame.iterrows():
        assigned = {k: text(row.get(k)) for k in MAPPING}
        proposal = mappings[row.symbol]
        suggested = {k: text(proposal.get("proposed_" + k)) for k in MAPPING}
        # Market display wording differs; sector/type/benchmark differences affect inputs.
        differences = [k for k in MAPPING[1:] if assigned[k] != suggested[k]]
        stored_differences = [k for k in MAPPING if text(row.get("proposed_" + k)) != suggested[k]]
        cap = cap_provenance(row, [o for o in observations if text(o.get("symbol")).upper() == row.symbol])
        assigned_run = replay.replay(row.symbol, assigned)
        proposed_run = replay.replay(row.symbol, suggested)
        gates = ["mapping_suitability_review", "explicit_identity_provider_activation_decision"]
        if not cap["threshold_pass"] or cap["evidence_link"] != "unique_value_and_url_match":
            gates.append("cap_source_link_review")
        if differences or stored_differences:
            gates.append("mapping_difference_review")
        if not assigned_run["inputs_ready"]:
            gates.append("stage_inputs_repair")
        result.append({"symbol": row.symbol, "venue": row.exchange,
                       "kis_basis": selected[row.symbol]["identity_basis"], "kis_source": selected[row.symbol]["source"],
                       "kis_review_reasons": selected[row.symbol]["review_reasons"],
                       "cap": cap, "assigned_mapping": assigned, "suggested_mapping": suggested,
                       "mapping_source": "registry assigned fields; origin not certified; current suggestion: stock_mapping.proposed_stock_mapping",
                       "mapping_status_recorded": text(row.get("mapping_status")),
                       "mapping_note": proposal["mapping_note"],
                       "input_mapping_differences": differences, "stored_proposal_differences": stored_differences,
                       "mapping_class": "different_inputs_review" if differences or stored_differences else "consistent_suggestion_review",
                       "assigned_replay": assigned_run, "suggested_replay": proposed_run,
                       "connection_class": "reviewable_inputs_ready" if assigned_run["inputs_ready"] and cap["threshold_pass"] else "data_repair_required",
                       "remaining_gates": gates,
                       "recorded_statuses": {k: text(row.get(k)) for k in ("activation_status", "identity_status", "provider_status", "market_cap_status")},
                       "operational_approval_granted": False})
    return result


def build_plan(data, as_of):
    audit = build_audit(data, as_of, include_rows=True)
    read = lambda name: pd.read_csv(data / name, dtype=str, keep_default_na=False)
    registry = read("stock_universe_candidates.csv")
    evidence = assess_candidates(registry, read("unranked_us_stock_master.csv"),
                                 {r["symbol"]: r for r in audit.pop("candidate_dimensions")})
    prices = pd.concat([read("daily_prices.csv"), read("candidate_daily_prices.csv")], ignore_index=True)
    rows = prepare_connection_rows(registry, evidence, read("yahoo_large_cap_candidate_review.csv").to_dict("records"), prices, as_of)
    universe = read("monitoring_universe.csv")
    benchmark_ids = {s for r in rows for m in ("assigned_mapping", "suggested_mapping") for k, s in r[m].items() if k.endswith("benchmark")}
    benchmark_sources = []
    for symbol in sorted(benchmark_ids):
        matches = universe[universe.symbol.eq(symbol)]
        benchmark_sources.append({"symbol": symbol, "universe_rows": len(matches),
                                  "metadata_source": "monitoring_universe.csv",
                                  "recorded": matches[[c for c in ("name", "market", "sector", "asset_type", "exchange", "provider", "sector_source", "active") if c in universe]].to_dict("records"),
                                  "suitability_approved_by_this_plan": False})
    status = json.loads((data / "candidate_daily_prices_status.json").read_text(encoding="utf-8"))
    recent = set(status.get("fresh_data_symbols", []))
    for row in rows:
        row["stored_price_evidence"] = {"file": "candidate_daily_prices.csv",
                                        "last_attempt_finished_utc": status.get("finished_at_utc"),
                                        "fresh_data_in_last_attempt": row["symbol"] in recent,
                                        "live_provider_verified_by_this_plan": False}
    inputs = audit["input_files"]
    for name in ("unranked_us_stock_master.csv", "yahoo_market_cap_supplement.csv", "yahoo_master_cap_batch_status.json"):
        path = data / name
        inputs[name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
    return {"schema_version": 1, "as_of": as_of, "policy": "offline review only; KIS default trust; no status transitions; observation time is not cap as-of; mapping agreement is not suitability approval",
            "input_files": inputs, "actual_bridge": audit["actual_bridge"], "benchmark_sources": benchmark_sources,
            "counts": {k: dict(Counter(str(r[k]) for r in rows)) for k in ("venue", "mapping_class", "connection_class")},
            "selected_candidates": len(rows), "cap_counts": {k: dict(Counter(str(r["cap"][k]) for r in rows)) for k in ("basis", "evidence_link", "effective_asof", "asof_basis")},
            "assigned_replay_counts": dict(Counter(str(r["assigned_replay"]["inputs_ready"]) for r in rows)),
            "review_only_stage_counts": dict(Counter(str(r["assigned_replay"]["review_only_stage_label"]) for r in rows)),
            "remaining_gate_counts": dict(Counter(g for r in rows for g in r["remaining_gates"])), "candidates": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent / "data")
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    print(json.dumps(build_plan(args.data_dir, args.as_of), ensure_ascii=True, sort_keys=True, indent=2))
