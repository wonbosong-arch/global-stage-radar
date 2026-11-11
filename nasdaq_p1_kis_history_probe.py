"""Bounded, opt-in KIS history probe for the 16 unapproved Nasdaq P1 gaps.

The approved screener receipt and saved KIS master determine the allowlist.
Default mode performs ZERO network calls. Live mode reports only aggregates by
default and NEVER writes prices, candidate registries, or operational data.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from candidate_refresh_state import classify_failure
from kis_provider import KISOverseasPrices, KISError
from nasdaq_coverage_gap_audit import ROOT, SEC_REGISTRY
from nasdaq_gap_price_readiness import P1, build_report, price_inventory

MATCHED_SEC_VENUE = "sec_reference_same_saved_kis_venue_review_only"
US_VENUES = frozenset({"NAS", "NYS", "AMS"})
MAX_COHORT = 16


def select_probe_rows(inventory: dict, max_symbols: int) -> tuple[list[dict], int]:
    """Allow only absent saved histories with one SEC-linked saved KIS venue."""
    if not 1 <= max_symbols <= MAX_COHORT:
        raise ValueError("max_symbols must be between 1 and 16")
    rows = inventory["review_rows"]
    if len(rows) != inventory["p1_symbols"] or len(rows) > MAX_COHORT:
        raise ValueError("Unexpected P1 inventory size")
    symbols = [r["symbol"] for r in rows]
    if len(set(symbols)) != len(symbols):
        raise ValueError("Duplicate P1 symbol")
    eligible = [
        r for r in rows
        if r["price_inventory_status"] == "missing"
        and r["sec_reference_status"] == MATCHED_SEC_VENUE
        and r["saved_kis_venue"] in US_VENUES
    ]
    eligible.sort(key=lambda r: r["symbol"])
    return eligible[:max_symbols], len(eligible)


def probe_live(rows: list[dict], client: KISOverseasPrices, evaluated_at: datetime,
               max_pages: int, pause_seconds: float) -> dict:
    """Use existing KIS client with one shared token; no other venue fallback."""
    if not 1 <= max_pages <= 5 or not 2.0 <= pause_seconds <= 30.0:
        raise ValueError("Probe bounds: max_pages 1..5; pause_seconds 2..30")
    observations = []
    stop_reason = None
    for row in rows:
        symbol, venue = row["symbol"], row["saved_kis_venue"]
        try:
            bars = client.daily_bars(
                symbol, exchange=venue, max_pages=max_pages,
                pause_seconds=pause_seconds,
            )
            if bars.empty:
                status = "kis_empty_response_support_unknown"
                completed_daily = completed_weeks = 0
            else:
                # The KIS adapter returns normalized pandas dates; existing
                # inventory replay accepts only date-only strings.
                prices = bars.copy(deep=True)
                dates = pd.to_datetime(prices["date"], errors="coerce")
                prices["date"] = dates.dt.strftime("%Y-%m-%d")
                single_gap = {
                    "source_sha256": "live_probe_review_only",
                    "review_rows": [{
                        "symbol": symbol, "issuer_identity_review_cohort": P1,
                        "kis_venues_by_ticker": [venue],
                        "sec_reference_status": MATCHED_SEC_VENUE,
                    }],
                }
                checked = price_inventory(single_gap, prices, evaluated_at)["review_rows"][0]
                status = checked["price_inventory_status"]
                completed_daily = checked["completed_daily_rows"]
                completed_weeks = checked["completed_weeks"]
            observations.append({
                "symbol": symbol, "venue": venue, "status": status,
                "completed_daily_rows": completed_daily,
                "completed_weeks": completed_weeks,
                "security_cap_verified": False,
                "activation_approved": False,
            })
        except (KISError, ValueError, KeyError, TypeError) as exc:
            failure = classify_failure(exc)
            observations.append({
                "symbol": symbol, "venue": venue, "status": "kis_error_" + failure,
                "security_cap_verified": False, "activation_approved": False,
            })
            # Do not burn the rate limit or token budget after systemic failures.
            if failure in {"rate_limited", "authentication_failed", "temporary_server_error"}:
                stop_reason = failure
                break
    return {
        "live_probe_performed": True,
        "attempted_symbols": len(observations),
        "result_counts": dict(sorted(Counter(r["status"] for r in observations).items())),
        "stopped_early_reason": stop_reason,
        "review_rows": observations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nasdaq-csv", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--sec-registry", type=Path, default=SEC_REGISTRY)
    parser.add_argument("--evaluated-at", default=None,
                        help="Timezone-aware ISO clock; default current UTC")
    parser.add_argument("--max-symbols", type=int, default=2)
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--pause-seconds", type=float, default=2.0)
    parser.add_argument("--execute", action="store_true",
                        help="Explicitly allow KIS API reads (never saves OHLCV)")
    parser.add_argument("--preview", type=int, default=0,
                        help="Show up to 16 unapproved per-symbol observations")
    args = parser.parse_args()
    if not 1 <= args.max_symbols <= MAX_COHORT:
        parser.error("--max-symbols must be 1..16")
    if not 1 <= args.max_pages <= 5 or not 2 <= args.pause_seconds <= 30:
        parser.error("--max-pages must be 1..5 and --pause-seconds 2..30")
    if not 0 <= args.preview <= MAX_COHORT:
        parser.error("--preview must be 0..16")
    clock = (datetime.fromisoformat(args.evaluated_at) if args.evaluated_at
             else datetime.now(timezone.utc))
    if clock.tzinfo is None or clock.utcoffset() is None:
        parser.error("--evaluated-at must contain a timezone")
    inventory = build_report(
        args.nasdaq_csv.read_bytes(),
        json.loads(args.receipt.read_text(encoding="utf-8")),
        args.data_dir,
        json.loads(args.sec_registry.read_text(encoding="utf-8")),
        clock,
    )
    selected, eligible = select_probe_rows(inventory, args.max_symbols)
    result = {
        "mode": "nasdaq_p1_kis_history_probe_review_only",
        "source_sha256": inventory["source_sha256"],
        "input_file_hashes": {name: entry["sha256"]
                              for name, entry in inventory["input_files"].items()},
        "p1_inventory_count": inventory["p1_symbols"],
        "eligible_missing_with_matched_reference": eligible,
        "selected_count": len(selected),
        "selection_truncated": eligible > len(selected),
        "live_probe_performed": False,
        "price_files_written": False,
        "candidate_intake": False,
        "operational_additions": 0,
        "security_cap_verified": False,
        "notes": [
            "KIS response availability is not proof of instrument or market-cap eligibility.",
            "KIS adapter may discard invalid OHLCV; raw-response provenance is not audited.",
            "150 daily/35 weekly/freshness checks remain review-only.",
            "Use approved source and receipt; never commit real per-symbol probe output.",
        ],
    }
    if args.execute and selected:
        result.update(probe_live(selected, KISOverseasPrices(), clock,
                                 args.max_pages, args.pause_seconds))
    observations = result.pop("review_rows", None)
    if args.preview:
        result["unapproved_preview"] = (
            observations[:args.preview] if observations is not None else [
                {"symbol": r["symbol"], "venue": r["saved_kis_venue"],
                 "status": "eligible_for_probe_unapproved"}
                for r in selected[:args.preview]
            ]
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
