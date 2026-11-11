"""Offline P1 cap/class review; aggregates never identify live-history pass tickers.

Reuses the approved Nasdaq receipt, gap audit, saved Yahoo master observations
and SEC reference registry. No network, files written, intake or activation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

import pandas as pd

from nasdaq_coverage_gap_audit import ROOT, SEC_REGISTRY, _sec_reference_index, audit_gap
from nasdaq_gap_price_readiness import P1
from nasdaq_local_csv_review import clean

PROBE_EVIDENCE = ROOT / "docs/evidence/us-p1-kis-aggregate-20261112.json"
CAP_FIELDS = ("market_cap_usd_b_secondary", "market_cap_currency",
              "market_cap_asof", "market_cap_asof_basis", "fetched_at_utc",
              "quote_type", "exchange_name", "source_url", "observation_status")


def aggregate_probes(entries: list[dict]) -> dict:
    """Validate complete, disjoint aggregate batches, without inventing a map."""
    if not entries:
        raise ValueError("Probe evidence is required")
    slots, counts, run_ids = set(), Counter(), set()
    first = entries[0]["summary"]
    size = first["p1_inventory_count"]
    if type(size) is not int or not 1 <= size <= 16:
        raise ValueError("Invalid probe cohort size")
    for entry in entries:
        probe, run_id = entry["summary"], entry["run_id"]
        start = probe.get("selected_start_index", 0)  # #252 predates this field.
        count = probe["selected_count"]
        results = probe["result_counts"]
        if (run_id in run_ids or type(start) is not int or type(count) is not int
                or start < 0 or count < 1 or start + count > size
                or probe.get("mode") != "nasdaq_p1_kis_history_probe_review_only"
                or probe.get("live_probe_performed") is not True
                or probe.get("stopped_early_reason") is not None
                or probe.get("p1_inventory_count") != size
                or probe.get("eligible_missing_with_matched_reference") != size
                or probe.get("attempted_symbols") != count
                or probe.get("source_sha256") != first["source_sha256"]
                or probe.get("input_file_hashes") != first["input_file_hashes"]
                or "unapproved_preview" in probe or "review_rows" in probe
                or not isinstance(results, dict)
                or any(type(n) is not int or n < 0 for n in results.values())
                or sum(results.values()) != count):
            raise ValueError("Incomplete, incompatible or non-aggregate probe evidence")
        batch = set(range(start, start + count))
        if slots & batch:
            raise ValueError("Overlapping probe batches")
        slots.update(batch)
        run_ids.add(run_id)
        counts.update(results)
    if slots != set(range(size)):
        raise ValueError("Probe evidence does not cover the complete cohort")
    return {"attempted_symbols": len(slots), "result_counts": dict(sorted(counts.items())),
            "individual_ticker_mapping_available": False,
            "identified_history_pass_tickers": 0,
            "source_sha256": first["source_sha256"],
            "input_file_hashes": dict(first["input_file_hashes"])}


def cap_observation(record: dict | None) -> dict:
    """Compare a secondary observation in USD billions, never certify cap."""
    record = record or {}
    fields = {key: clean(record.get(key)) for key in CAP_FIELDS}
    try:
        number = Decimal(fields["market_cap_usd_b_secondary"])
    except InvalidOperation:
        number = Decimal("NaN")
    usable = (number.is_finite() and number > 0
              and fields["market_cap_currency"] == "USD"
              and fields["observation_status"] == "observed_usd")
    status = ("at_or_above_usd1b_observation_only" if usable and number >= 1
              else "below_usd1b_observation_only" if usable
              else "missing_or_unusable_observation")
    # Same explicit-date rule as yahoo_market_cap_reconciliation; neither quote
    # time nor fetched_at_utc establishes a market-cap effective date.
    effective = None
    if fields["market_cap_asof_basis"] == "source_provided_market_cap_date":
        try:
            effective = datetime.strptime(fields["market_cap_asof"], "%Y-%m-%d").date().isoformat()
        except ValueError:
            pass
    return {**fields, "cap_threshold_observation": status,
            "cap_effective_date": effective, "security_cap_verified": False,
            "share_class_cap_basis": "not_established_by_yahoo_equity_label"}


def review_evidence(gaps: dict, yahoo: pd.DataFrame, registry: dict,
                    probes: list[dict], input_hashes: dict) -> dict:
    references = _sec_reference_index(registry)
    aggregate = aggregate_probes(probes)
    p1 = [r for r in gaps["review_rows"] if r["issuer_identity_review_cohort"] == P1]
    symbols = [r["symbol"] for r in p1]
    if len(symbols) != len(set(symbols)):
        raise ValueError("Duplicate P1 symbol")
    if "symbol" not in yahoo:
        raise ValueError("Yahoo observations require symbol")
    observed = yahoo.copy(deep=True)
    observed["symbol"] = observed.symbol.fillna("").astype(str).str.strip().str.upper()
    observed = observed[observed.symbol.isin(symbols)]
    if observed.symbol.duplicated().any():
        raise ValueError("Ambiguous Yahoo observations; do not choose a row silently")
    indexed = {r["symbol"]: r for r in observed.to_dict("records")}
    rows = []
    for gap in sorted(p1, key=lambda r: r["symbol"]):
        symbol = gap["symbol"]
        sec = references.get(symbol, {})
        venue_match = (gap["kis_venues_by_ticker"] == [sec.get("kis_venue")])
        rows.append({
            "symbol": symbol,
            "live_history_status": "unknown_aggregate_only",
            "nasdaq_issuer_cap_usd_unverified": gap["nasdaq_reported_cap_usd"],
            "yahoo": cap_observation(indexed.get(symbol)),
            "sec_security_class": sec.get("security_class"),
            "sec_filing_period_or_date": sec.get("filing_period_or_date"),
            "sec_source_url": sec.get("source_url"),
            "sec_review_note": sec.get("review_note", ""),
            "sec_saved_venue_matches": venue_match,
            "exact_listing_identity": "saved_reference_only_pending_review",
            "listing_continuity_verified": False,
            "activation_approved": False,
        })
    binding = (aggregate["source_sha256"] == gaps["source_sha256"]
               and all(input_hashes.get(name) == aggregate["input_file_hashes"].get(name)
                       for name in ("stock_universe_candidates.csv", "unranked_us_stock_master.csv")))
    return {
        "mode": "offline_p1_cap_identity_review", "source_sha256": gaps["source_sha256"],
        "p1_metadata_review_count": len(rows), "historical_live_probe": aggregate,
        "current_metadata_hashes_match_probe": binding,
        "input_file_hashes": input_hashes,
        "cap_observation_counts": dict(sorted(Counter(r["yahoo"]["cap_threshold_observation"] for r in rows).items())),
        "missing_cap_effective_dates": sum(r["yahoo"]["cap_effective_date"] is None for r in rows),
        "saved_sec_class_records": sum(bool(r["sec_security_class"]) for r in rows),
        "saved_sec_venue_matches": sum(r["sec_saved_venue_matches"] for r in rows),
        "saved_sec_records_with_review_notes": sum(bool(r["sec_review_note"]) for r in rows),
        "security_cap_verified_count": 0, "operational_additions": 0,
        "network_requests": 0, "candidate_intake": False,
        "review_rows": rows,
    }


def build_report(raw: bytes, receipt: dict, data_dir: Path, registry: dict,
                 probes: list[dict], evaluated_at: datetime) -> dict:
    from io import BytesIO
    names = ("stock_universe_candidates.csv", "unranked_us_stock_master.csv",
             "yahoo_unranked_master_market_caps.csv")
    payloads = {name: (data_dir / name).read_bytes() for name in names}
    frames = {name: pd.read_csv(BytesIO(data), dtype=str, keep_default_na=False)
              for name, data in payloads.items()}
    gaps = audit_gap(raw, receipt, frames[names[0]], frames[names[1]],
                     now=evaluated_at, sec_registry=registry)
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()}
    hashes["sec_registry_canonical_json"] = hashlib.sha256(
        json.dumps(registry, sort_keys=True).encode()).hexdigest()
    return review_evidence(gaps, frames[names[2]], registry, probes, hashes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nasdaq-csv", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--sec-registry", type=Path, default=SEC_REGISTRY)
    parser.add_argument("--probe-evidence", type=Path, default=PROBE_EVIDENCE)
    parser.add_argument("--preview", type=int, default=0)
    args = parser.parse_args()
    if not 0 <= args.preview <= 16:
        parser.error("--preview must be 0..16")
    report = build_report(args.nasdaq_csv.read_bytes(),
                          json.loads(args.receipt.read_text(encoding="utf-8")), args.data_dir,
                          json.loads(args.sec_registry.read_text(encoding="utf-8")),
                          json.loads(args.probe_evidence.read_text(encoding="utf-8")),
                          datetime.now(timezone.utc))
    rows = report.pop("review_rows")
    if args.preview:
        report["unapproved_preview"] = rows[:args.preview]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
